from __future__ import annotations

from typing import Any


NO_FAILURE = "None"
NO_FAILURE_DISPLAY = "No Failure"

FAILURE_TYPES = (
    NO_FAILURE,
    "Coordination Failure",
    "Communication Failure",
    "Role Confusion",
    "Hallucination Propagation",
    "Premature Consensus",
    "Over-Collaboration",
)

FAILURE_DEFINITIONS: dict[str, dict[str, str]] = {
    NO_FAILURE: {
        "definition": (
            "No dominant multi-agent collaboration failure is observable. The answer may still contain "
            "ordinary factual errors, weak reasoning, or minor omissions."
        ),
        "observable_signals": (
            "Use only when none of the six collaboration failures passes its evidence gate. "
            "Single-agent runs must use None because propagation between agents cannot be observed."
        ),
    },
    "Coordination Failure": {
        "definition": (
            "Task decomposition, execution order, dependency handling, ownership, or result integration failed, "
            "causing omitted, duplicated, conflicting, or incomplete work."
        ),
        "observable_signals": (
            "An assigned subtask is never completed; dependent work starts without its prerequisite; agents "
            "duplicate or contradict work without resolution; or the final output fails to integrate available results."
        ),
    },
    "Communication Failure": {
        "definition": (
            "Important information produced by one agent was not successfully transferred to an intended downstream "
            "agent, or the transferred content was empty, truncated, or lost, so the final output did not use it."
        ),
        "observable_signals": (
            "The trace contains the important upstream information and an intended handoff path, but it disappears "
            "downstream; a handoff is empty or length-truncated; or the final output is blank despite usable upstream work."
        ),
    },
    "Role Confusion": {
        "definition": (
            "An agent performs work inconsistent with its assigned role, or fails to perform the work that role is "
            "responsible for, and this mismatch materially harms the collaboration result."
        ),
        "observable_signals": (
            "Planner presents unverified conclusions instead of a plan; Researcher only restates a plan without "
            "collecting evidence; Critic does not verify or challenge; or Writer returns a plan or role report instead "
            "of the requested final deliverable."
        ),
    },
    "Hallucination Propagation": {
        "definition": (
            "One agent introduces a false or unsupported claim and at least one downstream agent accepts, repeats, "
            "or expands it without verification, allowing the same claim to enter the final output."
        ),
        "observable_signals": (
            "The same identifiable unsupported claim appears in an upstream message and the final output, with an "
            "observable downstream acceptance or missed correction. A hallucination appearing only in the final output "
            "is an ordinary answer error, not propagation."
        ),
    },
    "Premature Consensus": {
        "definition": (
            "Agents converge on a decision before critical facts, constraints, or disagreements are checked, and stop "
            "meaningful exploration while a material issue remains unresolved."
        ),
        "observable_signals": (
            "A proposal is selected only because it is the first or majority choice; all agents adopt an unverified "
            "premise; or an explicit Critic objection is ignored and the disputed conclusion remains in the final output. "
            "Agreement rate alone is insufficient."
        ),
    },
    "Over-Collaboration": {
        "definition": (
            "The run spends excessive rounds, messages, or tokens on repeated coordination or duplicated work without "
            "a corresponding improvement in the final result, or with a clear reduction in final-answer quality."
        ),
        "observable_signals": (
            "High communication or token use is accompanied by repeated message content and a final output that remains "
            "incomplete, noisy, or worse integrated. High cost or message count by itself is insufficient."
        ),
    },
}


def display_failure_type(value: Any) -> str:
    """Normalize a stored failure value and return its figure label."""

    normalized = str(value or "").strip()
    if normalized.lower().replace(" ", "") in {"", "none", "nofailure"}:
        return NO_FAILURE_DISPLAY
    if normalized not in FAILURE_TYPES:
        raise ValueError(
            f"Unknown failure_type={normalized!r}; expected one of: {', '.join(FAILURE_TYPES)}"
        )
    return normalized


def failure_prompt_text() -> str:
    """Render the single authoritative taxonomy for the Judge prompt."""

    sections: list[str] = []
    for failure_type in FAILURE_TYPES:
        details = FAILURE_DEFINITIONS[failure_type]
        sections.append(
            f"- {failure_type}\n"
            f"  Strict definition: {details['definition']}\n"
            f"  Observable signals: {details['observable_signals']}"
        )
    return "\n".join(sections)
