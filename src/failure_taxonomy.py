from __future__ import annotations

from collections.abc import Iterable
from typing import Any


NO_FAILURE = "None"
NO_FAILURE_DISPLAY = "No Failure"
OTHER_FAILURE = "Other Failure"

COLLABORATION_FAILURE_TYPES = (
    "Coordination Failure",
    "Communication Failure",
    "Role Confusion",
    "Hallucination Propagation",
    "Premature Consensus",
    "Over-Collaboration",
    "Manager Bottleneck",
    "Noise Accumulation",
)

FAILURE_TYPES = (NO_FAILURE, *COLLABORATION_FAILURE_TYPES, OTHER_FAILURE)

# The benchmark uses ``single_agent`` internally. ``single`` is accepted only as
# a human-facing alias so the policy below matches the protocol IDs in raw logs.
PROTOCOL_FAILURE_TYPES: dict[str, tuple[str, ...]] = {
    "single_agent": (NO_FAILURE, OTHER_FAILURE),
    "unstructured_group_chat": (
        NO_FAILURE,
        "Coordination Failure",
        "Communication Failure",
        "Role Confusion",
        "Hallucination Propagation",
        "Premature Consensus",
        "Over-Collaboration",
        "Noise Accumulation",
        OTHER_FAILURE,
    ),
    "sequential_handoff": (
        NO_FAILURE,
        "Communication Failure",
        "Role Confusion",
        "Hallucination Propagation",
        OTHER_FAILURE,
    ),
    "shared_blackboard": (
        NO_FAILURE,
        "Coordination Failure",
        "Communication Failure",
        "Role Confusion",
        "Hallucination Propagation",
        "Premature Consensus",
        "Over-Collaboration",
        "Noise Accumulation",
        OTHER_FAILURE,
    ),
    "manager_worker": (
        NO_FAILURE,
        "Coordination Failure",
        "Communication Failure",
        "Role Confusion",
        "Hallucination Propagation",
        "Premature Consensus",
        "Over-Collaboration",
        "Manager Bottleneck",
        "Noise Accumulation",
        OTHER_FAILURE,
    ),
    "debate": (
        NO_FAILURE,
        "Coordination Failure",
        "Communication Failure",
        "Role Confusion",
        "Hallucination Propagation",
        "Premature Consensus",
        "Over-Collaboration",
        "Noise Accumulation",
        OTHER_FAILURE,
    ),
    "voting": (
        NO_FAILURE,
        "Communication Failure",
        "Role Confusion",
        "Hallucination Propagation",
        "Premature Consensus",
        OTHER_FAILURE,
    ),
    "dynamic_task_allocation": (
        NO_FAILURE,
        "Coordination Failure",
        "Communication Failure",
        "Role Confusion",
        "Hallucination Propagation",
        "Premature Consensus",
        "Over-Collaboration",
        "Noise Accumulation",
        OTHER_FAILURE,
    ),
}

OTHER_FAILURE_SUBTYPES = (
    "tool_failure",
    "runtime_error",
    "malformed_output",
    "single_agent_answer_error",
    "unmapped_non_collaboration_failure",
)

LEGACY_FAILURE_ALIASES = {
    "Tool Failure": OTHER_FAILURE,
}

MINIMAL_FAILURE_PROMPT = (
    "Analyze failure independently of score. Check every collaboration category allowed for this protocol "
    "as a separate yes/no question; several categories may be present in the same log. A process failure "
    "may be recovered and may coexist with a high-quality final answer. Other Failure is a residual category: "
    "use it only when all allowed collaboration categories are absent and a concrete logged non-collaboration "
    "failure remains. If neither collaboration nor Other Failure is supported, the code records No Failure. "
    "A low score alone is never failure evidence."
)

FAILURE_DEFINITIONS: dict[str, dict[str, str]] = {
    NO_FAILURE: {
        "definition": (
            "None of the protocol-allowed collaboration failures and no concrete residual non-collaboration "
            "failure has sufficient observable log evidence."
        ),
        "observable_signals": (
            "This state is derived by code only after every allowed collaboration check is false and the residual "
            "Other check is false. Ordinary factual errors, weak reasoning, omissions, or a low score are not enough."
        ),
    },
    "Coordination Failure": {
        "definition": (
            "Task decomposition, ownership, execution order, dependency handling, or result integration breaks down "
            "during collaboration, producing omitted, duplicated, conflicting, or stranded work."
        ),
        "observable_signals": (
            "An assigned subtask is not completed; dependent work starts before its prerequisite; agents duplicate or "
            "contradict work without resolution; or an integrator ignores an available result. Identify the assignment "
            "or dependency and the later consequence. Mere division of labor is not failure."
        ),
    },
    "Communication Failure": {
        "definition": (
            "Important information produced by one agent is lost, empty, truncated, materially distorted, or not "
            "transferred to an intended downstream recipient."
        ),
        "observable_signals": (
            "Cite the upstream information and the downstream handoff, message, or output where it disappears or is "
            "corrupted. A downstream agent disagreeing after receiving the information is not communication failure."
        ),
    },
    "Role Confusion": {
        "definition": (
            "An agent performs work inconsistent with its recorded role or expected action, or omits the work that "
            "the role/phase explicitly assigns. The process failure may later be recovered."
        ),
        "observable_signals": (
            "Compare the message's sender, phase, expected_action, and content. Examples include a Planner directly "
            "submitting unverified conclusions when asked for allocation, a Researcher returning only a plan, or a "
            "Writer returning a work report instead of a deliverable. A different writing style is not role confusion."
        ),
    },
    "Hallucination Propagation": {
        "definition": (
            "One agent introduces a specific false or unsupported claim and at least one downstream agent accepts, "
            "repeats, or expands that same claim without verification. The claim need not survive the final Writer if "
            "the propagation is directly visible and later recovered."
        ),
        "observable_signals": (
            "Cite an upstream message containing the identifiable claim and a later message that accepts, repeats, or "
            "extends it. Similar wording alone is insufficient; the shared factual error or unsupported premise must "
            "be identifiable. A false claim appearing in only one message is not propagation."
        ),
    },
    "Premature Consensus": {
        "definition": (
            "Agents converge on a proposal before checking a visible critical fact, constraint, counterexample, or "
            "critique, and the convergence closes or materially narrows the remaining decision process."
        ),
        "observable_signals": (
            "Show the unresolved issue, at least two acts of agreement/convergence or the structured vote outcome, and "
            "the absence of intervening verification. Unanimity, a plurality result, or agreement on a verified answer "
            "is not sufficient by itself. Ballot integers are proposal indices, not answer values."
        ),
    },
    "Over-Collaboration": {
        "definition": (
            "The collaboration performs clearly redundant rounds or near-duplicate work that adds coordination cost "
            "without adding material information, correction, or coverage. The final answer may still be correct."
        ),
        "observable_signals": (
            "Use run metrics plus at least two substantially repeated messages and explain the absent information gain. "
            "High token use, many messages, or a long answer alone is insufficient."
        ),
    },
    "Manager Bottleneck": {
        "definition": (
            "Within manager_worker, a Manager action becomes a bottleneck by omitting or distorting requirements, "
            "misassigning work, suppressing useful worker results, or delaying/blocking necessary collaboration."
        ),
        "observable_signals": (
            "Cite a Manager message containing the causal omission, distortion, misassignment, rejection, or block and "
            "at least one affected downstream message. Ordinary worker error without a causal Manager action is not a "
            "Manager Bottleneck. It may coexist with the failure propagated through the hierarchy."
        ),
    },
    "Noise Accumulation": {
        "definition": (
            "Across a protocol's shared conversation, workspace, debate, hierarchy, or allocation context, irrelevant, "
            "redundant, contradictory, or misleading content accumulates and is subsequently reused or left unresolved."
        ),
        "observable_signals": (
            "Cite at least two context-visible messages showing accumulated noise and a later message that relies on or "
            "fails to resolve it. A single noisy message, ordinary disagreement, or message count alone is insufficient."
        ),
    },
    OTHER_FAILURE: {
        "definition": (
            "A concrete non-collaboration failure remains after every collaboration category allowed for the protocol "
            "has been checked and rejected. Other Failure must be assigned one explicit residual subtype."
        ),
        "observable_signals": (
            "Allowed residuals are tool failure, runtime error, malformed/empty output, a directly verifiable single-agent "
            "answer error, or another specifically evidenced non-collaboration failure. It must not be used as a safe "
            "fallback for uncertainty, generic answer weakness, or a multi-agent error whose trace fits a collaboration "
            "category."
        ),
    },
}


def _protocol_id(value: Any) -> str:
    normalized = str(value or "").strip()
    return "single_agent" if normalized == "single" else normalized


def allowed_failure_types(protocol_id: Any) -> tuple[str, ...]:
    """Return the exhaustive classification policy for one raw-log protocol ID."""

    normalized = _protocol_id(protocol_id)
    try:
        return PROTOCOL_FAILURE_TYPES[normalized]
    except KeyError as exc:
        raise ValueError(f"Unknown protocol_id for failure analysis: {protocol_id!r}") from exc


def allowed_collaboration_failure_types(protocol_id: Any) -> tuple[str, ...]:
    return tuple(
        failure_type
        for failure_type in allowed_failure_types(protocol_id)
        if failure_type in COLLABORATION_FAILURE_TYPES
    )


def normalize_failure_type(value: Any) -> str:
    """Normalize one current or legacy stored failure value."""

    normalized = str(value or "").strip()
    if normalized.lower().replace(" ", "").replace("_", "") in {
        "",
        "none",
        "nofailure",
    }:
        return NO_FAILURE
    normalized = LEGACY_FAILURE_ALIASES.get(normalized, normalized)
    if normalized not in FAILURE_TYPES:
        raise ValueError(
            f"Unknown failure_type={normalized!r}; expected one of: {', '.join(FAILURE_TYPES)}"
        )
    return normalized


def normalize_failure_types(values: Any) -> list[str]:
    """Normalize a stored multi-label value and enforce the taxonomy's exclusivity rules."""

    if isinstance(values, str) or values is None:
        raw_values: list[Any] = [values]
    elif isinstance(values, Iterable):
        raw_values = list(values)
    else:
        raw_values = [values]
    normalized_set = {normalize_failure_type(value) for value in raw_values}
    collaboration = [
        failure_type
        for failure_type in COLLABORATION_FAILURE_TYPES
        if failure_type in normalized_set
    ]
    if collaboration:
        return collaboration
    if OTHER_FAILURE in normalized_set:
        return [OTHER_FAILURE]
    return [NO_FAILURE]


def display_failure_type(value: Any) -> str:
    """Normalize one stored value and return its figure label."""

    normalized = normalize_failure_type(value)
    return NO_FAILURE_DISPLAY if normalized == NO_FAILURE else normalized


def display_failure_types(values: Any) -> list[str]:
    return [display_failure_type(value) for value in normalize_failure_types(values)]


def failure_prompt_text(protocol_id: Any) -> str:
    """Render only the taxonomy entries allowed for one protocol."""

    allowed = allowed_failure_types(protocol_id)
    sections: list[str] = [MINIMAL_FAILURE_PROMPT]
    for failure_type in allowed:
        if failure_type == NO_FAILURE:
            continue
        details = FAILURE_DEFINITIONS[failure_type]
        sections.append(
            f"- {failure_type}\n"
            f"  Strict definition: {details['definition']}\n"
            f"  Observable signals and exclusions: {details['observable_signals']}"
        )
    return "\n".join(sections)
