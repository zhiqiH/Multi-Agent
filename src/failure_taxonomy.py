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
    "Manager Bottleneck",
    "Noise Accumulation",
    "Other Failure",
)

LEGACY_FAILURE_ALIASES = {
    "Tool Failure": "Other Failure",
}

MINIMAL_FAILURE_PROMPT = (
    "Classify failure independently of score. Use the protocol log to prove one of the eight "
    "collaboration failures; use Other Failure only for a concrete logged non-collaboration "
    "failure such as a tool, single-agent execution/output, or objectively verifiable final-answer "
    "failure. Use None when no category has observable evidence. A high score may still have a "
    "failure; a low score alone is never evidence."
)

FAILURE_DEFINITIONS: dict[str, dict[str, str]] = {
    NO_FAILURE: {
        "definition": (
            "None of the nine failure types has sufficient observable log evidence. The answer may still "
            "receive a low quality score because of ordinary factual errors, weak reasoning, or omissions."
        ),
        "observable_signals": (
            "Use when all failure evidence gates remain unmet, regardless of answer score. Single-agent "
            "runs normally use None, but may use Other Failure when a concrete execution, tool, or output "
            "failure is visible in the trusted log."
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
            "The same identifiable unsupported claim appears in an upstream message, at least one downstream message "
            "that accepts, repeats, or expands it, and the final output. A hallucination appearing only in the final "
            "output is an answer error, not propagation."
        ),
    },
    "Premature Consensus": {
        "definition": (
            "Agents converge on a proposal before checking a critical fact, constraint, counterexample, or recorded "
            "critique, and the unverified consensus materially shapes the final output."
        ),
        "observable_signals": (
            "The trace shows an initial proposal or majority choice, explicit agreement or convergence by at least "
            "one additional agent, and no intervening verification of a visible unresolved issue before finalization. "
            "A high agreement rate or a unanimous vote by itself is insufficient."
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
    "Manager Bottleneck": {
        "definition": (
            "In a hierarchical protocol, the manager becomes the proximal cause of failure by omitting or distorting "
            "requirements, misassigning work, suppressing useful worker results, or blocking necessary collaboration."
        ),
        "observable_signals": (
            "A recorded Manager message contains the omission, misassignment, lossy summary, rejected useful result, "
            "or blocked handoff; at least one downstream worker message shows the consequence; and the same consequence "
            "is visible in the final output. Ordinary worker error without a causal Manager action is insufficient."
        ),
    },
    "Noise Accumulation": {
        "definition": (
            "A shared workspace accumulates irrelevant, redundant, contradictory, or misleading entries that agents "
            "subsequently use or fail to resolve, materially degrading final integration."
        ),
        "observable_signals": (
            "At least two recorded shared-workspace entries exhibit repeated, conflicting, or irrelevant content; a "
            "later agent relies on or fails to clean up that content; and the resulting noise is visible in the final "
            "output. Workspace size or message count alone is insufficient."
        ),
    },
    "Other Failure": {
        "definition": (
            "A concrete non-collaboration failure materially affects task completion or the final output and cannot "
            "be classified as any of the eight collaboration failures. This includes objective tool-policy or tool-"
            "execution failures, observable single-agent execution or output failures, and an objectively wrong or "
            "unusable final answer when no collaboration-process cause is traceable."
        ),
        "observable_signals": (
            "The trusted log shows a required tool condition or output contract failing, prohibited or unauthorized "
            "tool use, an execution error, an empty, truncated, or malformed output, or a specific material answer "
            "error directly verifiable against the task and ground truth. Use this residual category only when no "
            "collaboration category fits. A low score by itself is insufficient."
        ),
    },
}


def normalize_failure_type(value: Any) -> str:
    """Normalize current and legacy stored failure values."""

    normalized = str(value or "").strip()
    if normalized.lower().replace(" ", "") in {"", "none", "nofailure"}:
        return NO_FAILURE
    normalized = LEGACY_FAILURE_ALIASES.get(normalized, normalized)
    if normalized not in FAILURE_TYPES:
        raise ValueError(
            f"Unknown failure_type={normalized!r}; expected one of: {', '.join(FAILURE_TYPES)}"
        )
    return normalized


def display_failure_type(value: Any) -> str:
    """Normalize a stored failure value and return its figure label."""

    normalized = normalize_failure_type(value)
    return NO_FAILURE_DISPLAY if normalized == NO_FAILURE else normalized


def failure_prompt_text() -> str:
    """Render the single authoritative taxonomy for the Judge prompt."""

    sections: list[str] = [MINIMAL_FAILURE_PROMPT]
    for failure_type in FAILURE_TYPES:
        details = FAILURE_DEFINITIONS[failure_type]
        sections.append(
            f"- {failure_type}\n"
            f"  Strict definition: {details['definition']}\n"
            f"  Observable signals: {details['observable_signals']}"
        )
    return "\n".join(sections)
