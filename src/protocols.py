from __future__ import annotations

import re
import time
from collections import Counter
from typing import Any, Callable, Union

from .llm_client import LLMResponse, MockLLMClient, OpenAICompatibleClient
from .io_utils import utc_now_iso
from .prompts import (
    ROLE_SYSTEM_PROMPTS,
    agent_prompt,
    single_agent_prompt,
)


Client = Union[OpenAICompatibleClient, MockLLMClient]
CORE_AGENT_ROLES = ("Planner", "Researcher", "Analyst", "Critic", "Writer")
WORK_ROLES = ("Planner", "Researcher", "Analyst", "Critic")


PROTOCOLS: dict[str, dict[str, Any]] = {
    "single_agent": {
        "condition": "Baseline",
        "name": "Single Agent",
        "active_agents": 1,
        "message_flow": "One agent receives the task and produces the final output.",
        "visibility": "The agent sees only the configured task view.",
        "default_max_rounds": 1,
        "default_max_interactions": 1,
        "termination": "Stop after the final output or when the interaction budget is reached.",
    },
    "unstructured_group_chat": {
        "condition": "Condition 0",
        "name": "Unstructured Group Chat",
        "active_agents": 5,
        "message_flow": "Agents freely contribute to a shared conversation; Writer finalizes.",
        "visibility": "Every agent sees the task and complete shared conversation history.",
        "default_max_rounds": 3,
        "default_max_interactions": 13,
        "termination": "Stop after the configured discussion rounds and Writer output.",
    },
    "sequential_handoff": {
        "condition": "Condition 1",
        "name": "Sequential Handoff",
        "active_agents": 4,
        "message_flow": "Planner -> Researcher -> Analyst -> Writer.",
        "visibility": "Each agent sees the task and upstream outputs only; no backward messages.",
        "default_max_rounds": 1,
        "default_max_interactions": 4,
        "termination": "Stop after one forward pass and Writer output.",
    },
    "shared_blackboard": {
        "condition": "Condition 2",
        "name": "Shared Blackboard",
        "active_agents": 5,
        "message_flow": "Agents post structured contributions to a shared blackboard; Writer synthesizes.",
        "visibility": "Every agent sees the task and current full blackboard.",
        "default_max_rounds": 2,
        "default_max_interactions": 9,
        "termination": "Stop after all rounds or budget exhaustion, then Writer output.",
    },
    "manager_worker": {
        "condition": "Condition 3",
        "name": "Manager-Worker",
        "active_agents": 6,
        "message_flow": "Manager assigns work, workers report, Manager resolves conflicts, Writer finalizes.",
        "visibility": "Manager sees all messages; workers see the task, assignment, and relevant summaries.",
        "default_max_rounds": 3,
        "default_max_interactions": 8,
        "termination": "Stop after Manager synthesis and Writer output or budget exhaustion.",
    },
    "debate": {
        "condition": "Condition 4",
        "name": "Debate",
        "active_agents": 4,
        "message_flow": "Agents answer independently, critique competing answers, and Writer synthesizes.",
        "visibility": "Initial answers are private; critique round exposes competing answers.",
        "default_max_rounds": 2,
        "default_max_interactions": 7,
        "termination": "Stop after the configured critique rounds and Writer output.",
    },
    "voting": {
        "condition": "Condition 5",
        "name": "Voting",
        "active_agents": 4,
        "message_flow": "Agents answer independently, then cast private ballots; plurality selects the output.",
        "visibility": "Answers are private before voting; voters see all anonymized proposals during voting.",
        "default_max_rounds": 2,
        "default_max_interactions": 8,
        "termination": "Stop after ballot aggregation; deterministic lowest-index tie break.",
    },
    "dynamic_task_allocation": {
        "condition": "Condition 6",
        "name": "Dynamic Task Allocation",
        "active_agents": 6,
        "message_flow": "Agents negotiate roles, execute an allocation, adapt to gaps, and Writer finalizes.",
        "visibility": "Agents see shared negotiation history and relevant intermediate work.",
        "default_max_rounds": 3,
        "default_max_interactions": 15,
        "termination": "Stop after adaptation and Writer output or when the interaction budget is reached.",
    },
}

DEFAULT_PROTOCOLS = list(PROTOCOLS)


class InteractionBudgetExceeded(RuntimeError):
    pass


class RunState:
    def __init__(
        self,
        agent_task: dict[str, Any],
        client: Client,
        model: str,
        config: dict[str, Any],
        protocol_config: dict[str, Any],
    ) -> None:
        # Hard Agent/Judge boundary: raw private benchmark data must never reach
        # this object unless the caller explicitly selected those fields.
        self.task = agent_task
        self.client = client
        self.model = model
        self.config = config
        self.protocol_config = protocol_config
        self.intermediate_messages: list[dict[str, Any]] = []
        self.prompts: list[dict[str, Any]] = []
        self.tool_calls: list[dict[str, Any]] = []
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0
        self.interaction_count = 0
        self.active_roles: set[str] = set()
        self.rounds_completed = 0
        self.termination_reason = "completed"
        self.last_output = ""
        self.agreement_rate: float | None = None
        self.critique_count = 0
        self.accepted_critique_count: int | None = None

    @property
    def max_interactions(self) -> int:
        return int(self.protocol_config.get("max_interactions", 1))

    @property
    def max_total_tokens(self) -> int:
        return int(self.protocol_config.get("max_total_tokens", 0) or 0)

    def add_usage(self, response: LLMResponse) -> None:
        self.input_tokens += response.input_tokens
        self.output_tokens += response.output_tokens
        self.total_tokens += response.total_tokens

    def call_agent(
        self,
        role: str,
        instruction: str,
        visible_context: str = "",
        *,
        round_number: int,
        channel: str,
        recipients: list[str] | None = None,
        record_intermediate: bool = True,
        max_tokens: int | None = None,
    ) -> str:
        if self.interaction_count >= self.max_interactions:
            self.termination_reason = "max_interactions"
            raise InteractionBudgetExceeded(
                f"Protocol interaction budget exhausted ({self.max_interactions}) before {role} could run"
            )
        if self.max_total_tokens and self.total_tokens >= self.max_total_tokens:
            self.termination_reason = "max_total_tokens"
            raise InteractionBudgetExceeded(
                f"Protocol token budget exhausted ({self.max_total_tokens}) before {role} could run"
            )

        system_prompt = ROLE_SYSTEM_PROMPTS[role]
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": agent_prompt(role, self.task, instruction, visible_context)},
        ]
        self.prompts.append(
            {
                "agent_role": role,
                "round": round_number,
                "channel": channel,
                "messages": messages,
            }
        )
        response = self.client.chat(messages, max_tokens=max_tokens)
        self.interaction_count += 1
        self.active_roles.add(role)
        if channel != "final":
            self.rounds_completed = max(self.rounds_completed, round_number)
        self.add_usage(response)
        self.last_output = response.content
        if record_intermediate:
            self.intermediate_messages.append(
                {
                    "message_id": f"m{len(self.intermediate_messages) + 1:03d}",
                    "sender": role,
                    "recipients": recipients or ["shared"],
                    "round": round_number,
                    "channel": channel,
                    "content": response.content,
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "total_tokens": response.total_tokens,
                    "finish_reason": response.finish_reason,
                    "response_model": response.response_model,
                }
            )
        return response.content


def run_protocol(
    protocol_id: str,
    agent_task: dict[str, Any],
    client: Client,
    config: dict[str, Any],
    *,
    task_metadata: dict[str, Any] | None = None,
    run_id: str | None = None,
    run_number: int = 1,
    agent_visible_fields: list[str],
    validity_warnings: list[str] | None = None,
    protocol_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if protocol_id not in PROTOCOLS:
        raise ValueError(f"Unknown protocol: {protocol_id}")
    if set(agent_task) != set(agent_visible_fields):
        raise ValueError(
            "Agent task keys do not match agent_visible_fields; refusing to run with an ambiguous data boundary."
        )

    definition = PROTOCOLS[protocol_id]
    effective_protocol_config = {
        "max_rounds": definition["default_max_rounds"],
        "max_interactions": definition["default_max_interactions"],
        "max_total_tokens": 0,
    }
    effective_protocol_config.update(protocol_config or {})
    if int(effective_protocol_config["max_rounds"]) <= 0:
        raise ValueError("protocol max_rounds must be positive")
    if int(effective_protocol_config["max_interactions"]) <= 0:
        raise ValueError("protocol max_interactions must be positive")

    model = client.model
    provider = client.provider
    metadata = dict(task_metadata or agent_task)
    task_id = metadata.get("task_id") or agent_task.get("task_id")
    if not task_id:
        raise ValueError("task_metadata.task_id is required to identify a benchmark run")
    effective_run_id = run_id or build_run_id(task_id, protocol_id, model, run_number)

    state = RunState(
        agent_task,
        client,
        model,
        config,
        effective_protocol_config,
    )
    start_time = utc_now_iso()
    started = time.perf_counter()
    errors: list[str] = []
    try:
        final_output = _RUNNERS[protocol_id](state)
    except Exception as exc:  # noqa: BLE001 - failures belong in the standardized run log.
        final_output = state.last_output
        errors.append(str(exc))

    end_time = utc_now_iso()
    runtime_seconds = round(time.perf_counter() - started, 3)
    estimated_cost = estimate_cost(state.input_tokens, state.output_tokens, config)
    message_count = 0 if protocol_id == "single_agent" else len(state.intermediate_messages)
    active_agents = len(state.active_roles) or int(definition["active_agents"])
    communication_density = round(message_count / active_agents, 4) if active_agents else 0.0
    critique_acceptance_rate = None
    if state.accepted_critique_count is not None and state.critique_count:
        critique_acceptance_rate = round(state.accepted_critique_count / state.critique_count, 4)

    return {
        "record_type": "agent_run",
        "run_id": effective_run_id,
        "run_number": run_number,
        "task_id": task_id,
        "category": metadata.get("category"),
        "difficulty": metadata.get("difficulty"),
        "protocol": definition["name"],
        "protocol_id": protocol_id,
        "protocol_definition": definition,
        "protocol_config": effective_protocol_config,
        "agent_provider": provider,
        "agent_model": model,
        "temperature": (config.get("request_options") or {}).get("temperature"),
        "tool_requirement": metadata.get("tool_requirement"),
        "tool_access_used": bool(state.tool_calls),
        "start_time": start_time,
        "end_time": end_time,
        "runtime_seconds": runtime_seconds,
        "input_tokens": state.input_tokens,
        "output_tokens": state.output_tokens,
        "total_tokens": state.total_tokens,
        "estimated_cost": estimated_cost,
        "active_agent_count": active_agents,
        "interaction_count": state.interaction_count,
        "rounds_completed": state.rounds_completed,
        "termination_reason": state.termination_reason,
        "message_count": message_count,
        "communication_density": communication_density,
        "agreement_rate": state.agreement_rate,
        "critique_count": state.critique_count,
        "accepted_critique_count": state.accepted_critique_count,
        "critique_acceptance_rate": critique_acceptance_rate,
        "tool_call_count": len(state.tool_calls),
        "intermediate_messages": state.intermediate_messages,
        "tool_calls": state.tool_calls,
        "agent_visible_fields": list(agent_task),
        "prompts": state.prompts,
        "final_output": final_output,
        "validity_warnings": list(validity_warnings or []),
        "errors": errors,
    }


def build_run_id(
    task_id: str,
    protocol_id: str,
    model: str,
    run_number: int,
) -> str:
    components = [
        _slug_component(task_id),
        _slug_component(protocol_id),
        _slug_component(model),
    ]
    components.append(f"run{run_number:02d}")
    return "__".join(components)


def resolve_protocols(raw: list[str]) -> list[str]:
    if not raw:
        return DEFAULT_PROTOCOLS
    if len(raw) == 1 and raw[0] == "all":
        return list(PROTOCOLS)
    unknown = sorted(set(raw) - set(PROTOCOLS))
    if unknown:
        raise ValueError(f"Unknown protocols: {unknown}. Available: {sorted(PROTOCOLS)}")
    return raw


def estimate_cost(input_tokens: int, output_tokens: int, config: dict[str, Any]) -> float:
    pricing = config.get("pricing_per_1m_tokens", {})
    rates = pricing if isinstance(pricing, dict) else {}
    return round(
        (input_tokens / 1_000_000) * float(rates.get("input", 0.0))
        + (output_tokens / 1_000_000) * float(rates.get("output", 0.0)),
        8,
    )


def _agent_tokens(state: RunState) -> int:
    return int(state.config["agent_max_tokens"])


def _final_tokens(state: RunState) -> int:
    return int(state.config["final_max_tokens"])


def _run_single_agent(state: RunState) -> str:
    messages = single_agent_prompt(state.task)
    state.prompts.append(
        {"agent_role": "Single Agent", "round": 1, "channel": "final", "messages": messages}
    )
    response = state.client.chat(messages, max_tokens=_final_tokens(state))
    state.interaction_count = 1
    state.active_roles.add("Single Agent")
    state.rounds_completed = 1
    state.add_usage(response)
    state.last_output = response.content
    return response.content


def _run_unstructured_group_chat(state: RunState) -> str:
    transcript = "Shared conversation starts empty."
    max_rounds = min(3, int(state.protocol_config["max_rounds"]))
    roles = list(WORK_ROLES)
    for round_number in range(1, max_rounds + 1):
        rotated = roles[round_number - 1 :] + roles[: round_number - 1]
        for role in rotated:
            output = state.call_agent(
                role,
                "Join the free-form group discussion. Add a useful, non-duplicative contribution and respond to the shared history.",
                transcript,
                round_number=round_number,
                channel="group_chat",
                recipients=list(CORE_AGENT_ROLES),
                max_tokens=_agent_tokens(state),
            )
            transcript += f"\n\n[Round {round_number} - {role}]\n{output}"
    return state.call_agent(
        "Writer",
        "Produce the final answer from the group transcript and follow the required output format.",
        transcript,
        round_number=max_rounds + 1,
        channel="final",
        recipients=["user"],
        record_intermediate=False,
        max_tokens=_final_tokens(state),
    )


def _run_sequential_handoff(state: RunState) -> str:
    plan = state.call_agent(
        "Planner",
        "Create a concise execution plan and deliverable structure.",
        round_number=1,
        channel="handoff",
        recipients=["Researcher"],
        max_tokens=_agent_tokens(state),
    )
    evidence = state.call_agent(
        "Researcher",
        "Use the plan and permitted information to collect evidence, constraints, and missing-evidence warnings.",
        f"[Planner]\n{plan}",
        round_number=1,
        channel="handoff",
        recipients=["Analyst"],
        max_tokens=_agent_tokens(state),
    )
    analysis = state.call_agent(
        "Analyst",
        "Synthesize upstream work into conclusions tied to the task requirements.",
        f"[Planner]\n{plan}\n\n[Researcher]\n{evidence}",
        round_number=1,
        channel="handoff",
        recipients=["Writer"],
        max_tokens=_agent_tokens(state),
    )
    return state.call_agent(
        "Writer",
        "Write the final answer using all upstream outputs. Do not add unsupported claims.",
        f"[Planner]\n{plan}\n\n[Researcher]\n{evidence}\n\n[Analyst]\n{analysis}",
        round_number=1,
        channel="final",
        recipients=["user"],
        record_intermediate=False,
        max_tokens=_final_tokens(state),
    )


def _run_shared_blackboard(state: RunState) -> str:
    blackboard = "Shared blackboard starts empty."
    max_rounds = min(3, int(state.protocol_config["max_rounds"]))
    base_instructions = {
        "Planner": "Post or refine the plan and output skeleton.",
        "Researcher": "Post evidence, source needs, constraints, and missing-evidence warnings.",
        "Analyst": "Post synthesis, tradeoffs, calculations, and likely conclusions.",
        "Critic": "Post verification findings, coordination risks, and required fixes.",
    }
    for round_number in range(1, max_rounds + 1):
        for role in WORK_ROLES:
            output = state.call_agent(
                role,
                base_instructions[role] + " Read the current board and avoid duplicating resolved material.",
                blackboard,
                round_number=round_number,
                channel="blackboard",
                recipients=list(CORE_AGENT_ROLES),
                max_tokens=_agent_tokens(state),
            )
            blackboard += f"\n\n[Round {round_number} - {role}]\n{output}"
    return state.call_agent(
        "Writer",
        "Synthesize the blackboard into the final answer. Resolve conflicts and follow the required format.",
        blackboard,
        round_number=max_rounds + 1,
        channel="final",
        recipients=["user"],
        record_intermediate=False,
        max_tokens=_final_tokens(state),
    )


def _run_manager_worker(state: RunState) -> str:
    max_rounds = min(4, int(state.protocol_config["max_rounds"]))
    assignment = state.call_agent(
        "Manager",
        "Decompose the task and assign distinct subtasks to Planner, Researcher, Analyst, Critic, and Writer.",
        round_number=1,
        channel="management",
        recipients=list(CORE_AGENT_ROLES),
        max_tokens=_agent_tokens(state),
    )
    worker_outputs: list[tuple[str, str]] = []
    if max_rounds >= 2:
        for role in CORE_AGENT_ROLES:
            worker_outputs.append(
                (
                    role,
                    state.call_agent(
                        role,
                        f"Complete the {role} assignment. Report evidence, assumptions, and unresolved issues to Manager.",
                        f"[Manager assignment]\n{assignment}",
                        round_number=2,
                        channel="worker_report",
                        recipients=["Manager"],
                        max_tokens=_agent_tokens(state),
                    ),
                )
            )
    worker_context = "\n\n".join(f"[{role}]\n{content}" for role, content in worker_outputs)
    manager_summary = assignment
    if max_rounds >= 3:
        manager_summary = state.call_agent(
            "Manager",
            "Resolve conflicts, preserve important details, and issue final synthesis instructions to Writer.",
            f"[Initial assignment]\n{assignment}\n\n[Worker reports]\n{worker_context}",
            round_number=3,
            channel="management",
            recipients=["Writer"],
            max_tokens=_agent_tokens(state),
        )
    if max_rounds >= 4:
        critic_revision = state.call_agent(
            "Critic",
            "Review the Manager synthesis for major issues and provide only essential revision instructions.",
            f"[Manager synthesis]\n{manager_summary}\n\n[Worker reports]\n{worker_context}",
            round_number=4,
            channel="revision",
            recipients=["Manager", "Writer"],
            max_tokens=_agent_tokens(state),
        )
        state.critique_count += 1
        manager_summary += f"\n\n[Optional Critic revision]\n{critic_revision}"
    return state.call_agent(
        "Writer",
        "Produce the final answer according to the Manager decision and worker reports.",
        f"[Manager decision]\n{manager_summary}\n\n[Worker reports]\n{worker_context}",
        round_number=max_rounds + 1,
        channel="final",
        recipients=["user"],
        record_intermediate=False,
        max_tokens=_final_tokens(state),
    )


def _run_debate(state: RunState) -> str:
    debate_roles = ("Planner", "Analyst", "Critic")
    proposals: list[tuple[str, str]] = []
    for role in debate_roles:
        proposals.append(
            (
                role,
                state.call_agent(
                    role,
                    "Independently produce a complete solution. You cannot see other answers yet.",
                    round_number=1,
                    channel="private_answer",
                    recipients=["debate_controller"],
                    max_tokens=_agent_tokens(state),
                ),
            )
        )
    proposal_context = "\n\n".join(f"[Proposal {index + 1}]\n{text}" for index, (_, text) in enumerate(proposals))
    critiques: list[tuple[str, str]] = []
    max_rounds = min(3, max(2, int(state.protocol_config["max_rounds"])))
    debate_context = proposal_context
    for round_number in range(2, max_rounds + 1):
        round_critiques: list[tuple[str, str]] = []
        for role in debate_roles:
            round_critiques.append(
                (
                    role,
                    state.call_agent(
                        role,
                        "Critique competing proposals and prior critiques. Identify disagreements, respond to challenges, and recommend corrections.",
                        debate_context,
                        round_number=round_number,
                        channel="debate",
                        recipients=["Writer", *debate_roles],
                        max_tokens=_agent_tokens(state),
                    ),
                )
            )
        critiques.extend(round_critiques)
        debate_context += "\n\n" + "\n\n".join(
            f"[Round {round_number} - {role} critique]\n{text}"
            for role, text in round_critiques
        )
    state.critique_count = len(critiques)
    critique_context = "\n\n".join(f"[{role} critique]\n{text}" for role, text in critiques)
    return state.call_agent(
        "Writer",
        "Synthesize the strongest corrected answer. Resolve disagreements explicitly but return only the requested deliverable.",
        f"{proposal_context}\n\n{critique_context}",
        round_number=max_rounds + 1,
        channel="final",
        recipients=["user"],
        record_intermediate=False,
        max_tokens=_final_tokens(state),
    )


def _run_voting(state: RunState) -> str:
    proposals: list[tuple[str, str]] = []
    for role in WORK_ROLES:
        proposals.append(
            (
                role,
                state.call_agent(
                    role,
                    "Independently produce a complete final-form answer. You cannot see other proposals.",
                    round_number=1,
                    channel="private_answer",
                    recipients=["voting_controller"],
                    max_tokens=_final_tokens(state),
                ),
            )
        )
    anonymized = "\n\n".join(
        f"[Proposal {index + 1}]\n{text}" for index, (_, text) in enumerate(proposals)
    )
    if int(state.protocol_config["max_rounds"]) < 2:
        state.termination_reason = "max_rounds"
        return proposals[0][1]
    ballots: list[int] = []
    for role in WORK_ROLES:
        ballot = state.call_agent(
            role,
            f"Vote for the strongest proposal. Return exactly one integer from 1 to {len(proposals)} and nothing else.",
            anonymized,
            round_number=2,
            channel="private_ballot",
            recipients=["voting_controller"],
            max_tokens=300,
        )
        selected = _parse_ballot(ballot, len(proposals))
        if selected is not None:
            ballots.append(selected)
    counts = Counter(ballots)
    winner = min((index for index in range(1, len(proposals) + 1)), key=lambda index: (-counts[index], index))
    if ballots:
        state.agreement_rate = round(counts[winner] / len(ballots), 4)
    state.termination_reason = "vote_complete"
    return proposals[winner - 1][1]


def _run_dynamic_task_allocation(state: RunState) -> str:
    max_rounds = min(4, int(state.protocol_config["max_rounds"]))
    negotiation = "Negotiation starts without a fixed allocation."
    for role in WORK_ROLES:
        proposal = state.call_agent(
            role,
            "Propose a task allocation, volunteer for responsibilities, identify dependencies, and request help where needed.",
            negotiation,
            round_number=1,
            channel="negotiation",
            recipients=["Manager", *WORK_ROLES],
            max_tokens=_agent_tokens(state),
        )
        negotiation += f"\n\n[{role} allocation proposal]\n{proposal}"
    allocation = state.call_agent(
        "Manager",
        "Synthesize the negotiation into a concrete allocation with owners, dependencies, and completion checks.",
        negotiation,
        round_number=1,
        channel="allocation",
        recipients=list(WORK_ROLES),
        max_tokens=_agent_tokens(state),
    )
    execution_outputs: list[tuple[str, str]] = []
    if max_rounds >= 2:
        for role in WORK_ROLES:
            execution_outputs.append(
                (
                    role,
                    state.call_agent(
                        role,
                        "Execute your allocated responsibilities and flag gaps that require another agent's help.",
                        f"[Negotiation]\n{negotiation}\n\n[Final allocation]\n{allocation}",
                        round_number=2,
                        channel="execution",
                        recipients=["Manager", *WORK_ROLES],
                        max_tokens=_agent_tokens(state),
                    ),
                )
            )
    execution_context = "\n\n".join(f"[{role} execution]\n{text}" for role, text in execution_outputs)
    adaptation_context = execution_context
    if max_rounds >= 3:
        gap_review = state.call_agent(
            "Critic",
            "Identify unresolved gaps, duplicated work, unsupported claims, and the smallest useful reallocation.",
            execution_context,
            round_number=3,
            channel="adaptation",
            recipients=["Manager", *WORK_ROLES],
            max_tokens=_agent_tokens(state),
        )
        state.critique_count = 1
        adaptation_context += f"\n\n[Adaptive gap review]\n{gap_review}"
    if max_rounds >= 4:
        reallocation = state.call_agent(
            "Manager",
            "Revise the allocation in response to the gap review. Preserve completed work and specify only necessary adaptations.",
            f"[Initial allocation]\n{allocation}\n\n{adaptation_context}",
            round_number=4,
            channel="reallocation",
            recipients=list(CORE_AGENT_ROLES),
            max_tokens=_agent_tokens(state),
        )
        adaptation_context += f"\n\n[Dynamic reallocation]\n{reallocation}"
    return state.call_agent(
        "Writer",
        "Produce the final answer from the negotiated allocation and adapted work. Resolve remaining gaps without inventing evidence.",
        f"[Allocation]\n{allocation}\n\n{adaptation_context}",
        round_number=max_rounds + 1,
        channel="final",
        recipients=["user"],
        record_intermediate=False,
        max_tokens=_final_tokens(state),
    )


def _parse_ballot(text: str, upper: int) -> int | None:
    match = re.search(r"\b(\d+)\b", text)
    if not match:
        return None
    value = int(match.group(1))
    return value if 1 <= value <= upper else None


def _slug_component(value: Any) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value)).strip("-._").lower()
    return slug or "unknown"


_RUNNERS: dict[str, Callable[[RunState], str]] = {
    "single_agent": _run_single_agent,
    "unstructured_group_chat": _run_unstructured_group_chat,
    "sequential_handoff": _run_sequential_handoff,
    "shared_blackboard": _run_shared_blackboard,
    "manager_worker": _run_manager_worker,
    "debate": _run_debate,
    "voting": _run_voting,
    "dynamic_task_allocation": _run_dynamic_task_allocation,
}
