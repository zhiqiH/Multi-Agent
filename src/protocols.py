from __future__ import annotations
import hashlib
import json
import re
import time
from typing import Any, Callable, Union
from .deepseek_client import DeepSeekClient, LLMResponse, MockLLMClient
from .io_utils import utc_now_iso
from .prompts import ROLE_SYSTEM_PROMPTS, agent_prompt, single_agent_prompt

Client = Union[DeepSeekClient, MockLLMClient]


PROTOCOLS: dict[str, dict[str, Any]] = {
    "single_agent": {
        "name": "Single Agent",
        "active_agents": 1,
        "description": "A single LLM completes the task without inter-agent communication.",
    },
    "unstructured_group_chat": {
        "name": "Unstructured Group Chat",
        "active_agents": 5,
        "description": "Planner, Researcher, Analyst, Critic, and Writer share one conversation history.",
    },
    "sequential_handoff": {
        "name": "Sequential Handoff",
        "active_agents": 4,
        "description": "Planner -> Researcher -> Analyst -> Writer; no backward communication.",
    },
    "shared_blackboard": {
        "name": "Shared Blackboard",
        "active_agents": 5,
        "description": "Agents contribute to a shared workspace, then Writer synthesizes.",
    },
    "manager_worker": {
        "name": "Manager-Worker",
        "active_agents": 6,
        "description": "Manager assigns subtasks, workers report back, Writer produces final answer.",
    },
    "debate": {
        "name": "Debate",
        "active_agents": 4,
        "description": "Agents independently answer, critique, then Writer/Arbiter synthesizes.",
    },
}


DEFAULT_PROTOCOLS = [
    "single_agent",
    "sequential_handoff",
    "shared_blackboard",
    "manager_worker",
]


class RunState:
    def __init__(self, candidate_task: dict[str, Any], client: Client, model: str, config: dict[str, Any]) -> None:
        # This object is the hard candidate/Judge boundary. It must never receive
        # the raw benchmark task containing evaluation-only fields.
        self.task = candidate_task
        self.client = client
        self.model = model
        self.config = config
        self.intermediate_messages: list[dict[str, Any]] = []
        self.prompts: list[dict[str, Any]] = []
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0

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
        record_intermediate: bool = True,
        max_tokens: int | None = None,
    ) -> str:
        messages = [
            {"role": "system", "content": ROLE_SYSTEM_PROMPTS[role]},
            {"role": "user", "content": agent_prompt(role, self.task, instruction, visible_context)},
        ]
        self.prompts.append({"role": role, "messages": messages})
        response = self.client.chat(messages, max_tokens=max_tokens)
        self.add_usage(response)
        if record_intermediate:
            self.intermediate_messages.append(
                {
                    "agent_role": role,
                    "content": response.content,
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                }
            )
        return response.content


def run_protocol(
    protocol_id: str,
    candidate_task: dict[str, Any],
    client: Client,
    config: dict[str, Any],
    *,
    task_metadata: dict[str, Any] | None = None,
    run_id: str | None = None,
    run_number: int = 1,
    candidate_visible_fields: list[str] | None = None,
    validity_warnings: list[str] | None = None,
) -> dict[str, Any]:
    if protocol_id not in PROTOCOLS:
        raise ValueError(f"Unknown protocol: {protocol_id}")

    if candidate_visible_fields is not None and set(candidate_task) != set(candidate_visible_fields):
        raise ValueError(
            "Candidate task keys do not match candidate_visible_fields; refusing to run with an ambiguous data boundary."
        )

    model = getattr(client, "model", config.get("model", "unknown-model"))
    provider = getattr(client, "provider", config.get("provider", "unknown-provider"))
    profile = getattr(client, "profile", config.get("profile", "legacy"))
    metadata = dict(task_metadata or candidate_task)
    task_id = metadata.get("task_id") or candidate_task.get("task_id")
    if not task_id:
        raise ValueError("task_metadata.task_id is required to identify a benchmark run.")
    effective_run_id = run_id or build_run_id(task_id, protocol_id, profile, model, run_number)

    state = RunState(candidate_task, client, model, config)
    start_time = utc_now_iso()
    started = time.perf_counter()
    errors: list[str] = []

    try:
        final_output = _RUNNERS[protocol_id](state)
    except Exception as exc:  # noqa: BLE001 - log protocol failure in benchmark schema.
        final_output = ""
        errors.append(str(exc))

    end_time = utc_now_iso()
    runtime_seconds = round(time.perf_counter() - started, 3)
    protocol = PROTOCOLS[protocol_id]
    estimated_cost = estimate_cost(model, state.input_tokens, state.output_tokens, config)
    message_count = 0 if protocol_id == "single_agent" else len(state.intermediate_messages)
    communication_density = 0.0
    if protocol["active_agents"]:
        communication_density = round(message_count / protocol["active_agents"], 4)

    return {
        "run_id": effective_run_id,
        "task_id": task_id,
        "category": metadata.get("category"),
        "difficulty": metadata.get("difficulty"),
        "protocol": protocol["name"],
        "protocol_id": protocol_id,
        "protocol_version": "2.0-field-isolated",
        "protocol_definition": protocol,
        "candidate_provider": provider,
        "candidate_profile": profile,
        "candidate_model": model,
        "model": model,
        "temperature": config.get("temperature", 0.0),
        "tool_requirement": metadata.get("tool_requirement"),
        "tool_access_used": False,
        "start_time": start_time,
        "end_time": end_time,
        "runtime_seconds": runtime_seconds,
        "input_tokens": state.input_tokens,
        "output_tokens": state.output_tokens,
        "total_tokens": state.total_tokens,
        "estimated_cost": estimated_cost,
        "message_count": message_count,
        "communication_density": communication_density,
        "tool_call_count": 0,
        "intermediate_messages": state.intermediate_messages,
        "tool_calls": [],
        "candidate_visible_fields": list(candidate_task),
        "candidate_view_sha256": _stable_sha256(candidate_task),
        "prompts": state.prompts,
        "final_output": final_output,
        "validity_warnings": list(validity_warnings or []),
        "errors": errors,
    }


def build_run_id(
    task_id: str,
    protocol_id: str,
    candidate_profile: str,
    model: str,
    run_number: int,
) -> str:
    candidate_tag = _slug_component(f"{candidate_profile}-{model}")
    return f"{_slug_component(task_id)}__{_slug_component(protocol_id)}__{candidate_tag}__run{run_number:02d}"


def _slug_component(value: Any) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value)).strip("-._").lower()
    return slug or "unknown"


def _stable_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def resolve_protocols(raw: list[str]) -> list[str]:
    if not raw:
        return DEFAULT_PROTOCOLS
    if len(raw) == 1 and raw[0] == "all":
        return list(PROTOCOLS)
    unknown = sorted(set(raw) - set(PROTOCOLS))
    if unknown:
        raise ValueError(f"Unknown protocols: {unknown}. Available: {sorted(PROTOCOLS)}")
    return raw


def estimate_cost(model: str, input_tokens: int, output_tokens: int, config: dict[str, Any]) -> float:
    pricing = config.get("pricing_per_1m_tokens", {})
    rates = pricing.get(model) or pricing.get("default") or {"input": 0.0, "output": 0.0}
    return round((input_tokens / 1_000_000) * rates["input"] + (output_tokens / 1_000_000) * rates["output"], 8)


def _run_single_agent(state: RunState) -> str:
    messages = single_agent_prompt(state.task)
    state.prompts.append({"role": "Single Agent", "messages": messages})
    response = state.client.chat(messages, max_tokens=int(state.config.get("final_max_tokens", 1200)))
    state.add_usage(response)
    return response.content


def _run_unstructured_group_chat(state: RunState) -> str:
    transcript = ""
    roles = ["Planner", "Researcher", "Analyst", "Critic"]
    for role in roles:
        output = state.call_agent(
            role,
            "Join the shared group chat. Add your role-specific contribution and respond to prior messages if useful.",
            transcript,
            max_tokens=int(state.config.get("agent_max_tokens", 700)),
        )
        transcript += f"\n\n[{role}]\n{output}"
    return state.call_agent(
        "Writer",
        "Use the group chat transcript to produce the final answer in the required output format.",
        transcript,
        record_intermediate=False,
        max_tokens=int(state.config.get("final_max_tokens", 1200)),
    )


def _run_sequential_handoff(state: RunState) -> str:
    plan = state.call_agent(
        "Planner",
        "Create a concise task plan with deliverable structure and evaluation checkpoints.",
        max_tokens=int(state.config.get("agent_max_tokens", 700)),
    )
    evidence = state.call_agent(
        "Researcher",
        "Use only the task prompt and allowed common knowledge. Collect relevant evidence, examples, and constraints.",
        f"[Planner]\n{plan}",
        max_tokens=int(state.config.get("agent_max_tokens", 700)),
    )
    analysis = state.call_agent(
        "Analyst",
        "Synthesize the plan and evidence into conclusions tied to the stated task requirements.",
        f"[Planner]\n{plan}\n\n[Researcher]\n{evidence}",
        max_tokens=int(state.config.get("agent_max_tokens", 700)),
    )
    return state.call_agent(
        "Writer",
        "Write the final answer using all upstream outputs. Do not add unsupported claims.",
        f"[Planner]\n{plan}\n\n[Researcher]\n{evidence}\n\n[Analyst]\n{analysis}",
        record_intermediate=False,
        max_tokens=int(state.config.get("final_max_tokens", 1200)),
    )


def _run_shared_blackboard(state: RunState) -> str:
    blackboard = "Shared blackboard starts empty."
    for role, instruction in [
        ("Planner", "Post a plan and output skeleton to the blackboard."),
        ("Researcher", "Post evidence, constraints, and missing-evidence warnings to the blackboard."),
        ("Analyst", "Post tradeoff analysis and likely conclusions to the blackboard."),
        ("Critic", "Post verification notes, risks, and required fixes to the blackboard."),
    ]:
        output = state.call_agent(role, instruction, blackboard, max_tokens=int(state.config.get("agent_max_tokens", 700)))
        blackboard += f"\n\n[{role} contribution]\n{output}"
    return state.call_agent(
        "Writer",
        "Synthesize the blackboard into the final answer. Resolve redundancy and follow the required format.",
        blackboard,
        record_intermediate=False,
        max_tokens=int(state.config.get("final_max_tokens", 1200)),
    )


def _run_manager_worker(state: RunState) -> str:
    assignment = state.call_agent(
        "Manager",
        "Assign concise subtasks to Planner, Researcher, Analyst, and Critic. Define final synthesis expectations.",
        max_tokens=int(state.config.get("agent_max_tokens", 700)),
    )
    worker_outputs = []
    for role in ["Planner", "Researcher", "Analyst", "Critic"]:
        worker_outputs.append(
            (
                role,
                state.call_agent(
                    role,
                    f"Complete your assigned {role} subtask from the Manager. Stay within your role.",
                    f"[Manager assignment]\n{assignment}",
                    max_tokens=int(state.config.get("agent_max_tokens", 700)),
                ),
            )
        )
    worker_context = "\n\n".join(f"[{role}]\n{content}" for role, content in worker_outputs)
    manager_summary = state.call_agent(
        "Manager",
        "Review worker outputs, resolve conflicts, and give final instructions to Writer.",
        f"[Initial assignment]\n{assignment}\n\n[Worker reports]\n{worker_context}",
        max_tokens=int(state.config.get("agent_max_tokens", 700)),
    )
    return state.call_agent(
        "Writer",
        "Produce the final answer according to the Manager summary and worker reports.",
        f"[Manager summary]\n{manager_summary}\n\n[Worker reports]\n{worker_context}",
        record_intermediate=False,
        max_tokens=int(state.config.get("final_max_tokens", 1200)),
    )


def _run_debate(state: RunState) -> str:
    independent = []
    for role in ["Planner", "Analyst", "Critic"]:
        independent.append(
            (
                role,
                state.call_agent(
                    role,
                    "Independently solve the task from your role perspective. Do not read other agents.",
                    max_tokens=int(state.config.get("agent_max_tokens", 700)),
                ),
            )
        )
    answer_context = "\n\n".join(f"[{role} independent answer]\n{content}" for role, content in independent)
    critique = state.call_agent(
        "Critic",
        "Critique the independent answers. Identify disagreements, missing task requirements, and unsupported claims.",
        answer_context,
        max_tokens=int(state.config.get("agent_max_tokens", 700)),
    )
    arbiter = state.call_agent(
        "Arbiter",
        "Select or synthesize the strongest answer direction after considering the critique.",
        f"{answer_context}\n\n[Critique]\n{critique}",
        max_tokens=int(state.config.get("agent_max_tokens", 700)),
    )
    return state.call_agent(
        "Writer",
        "Write the final answer using the Arbiter direction and critique.",
        f"[Arbiter]\n{arbiter}\n\n[Critique]\n{critique}\n\n{answer_context}",
        record_intermediate=False,
        max_tokens=int(state.config.get("final_max_tokens", 1200)),
    )


_RUNNERS: dict[str, Callable[[RunState], str]] = {
    "single_agent": _run_single_agent,
    "unstructured_group_chat": _run_unstructured_group_chat,
    "sequential_handoff": _run_sequential_handoff,
    "shared_blackboard": _run_shared_blackboard,
    "manager_worker": _run_manager_worker,
    "debate": _run_debate,
}