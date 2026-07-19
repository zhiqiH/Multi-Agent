from __future__ import annotations

import re
from typing import Any


_DOI_PATTERN = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
_ARXIV_PATTERN = re.compile(
    r"(?:arxiv\s*:\s*|arxiv\.org/(?:abs|pdf)/)(\d{4}\.\d{4,5}(?:v\d+)?)",
    re.IGNORECASE,
)
_MARKDOWN_DECORATION = re.compile(r"[*_`#]")


def build_response_audit(
    task: dict[str, Any],
    final_output: str,
    evidence_audit: dict[str, Any],
) -> dict[str, Any]:
    """Extract deterministic, directly observable answer-format facts.

    This audit deliberately avoids semantic grading. It only checks properties
    such as Markdown table headers, exact item counts, section labels, academic
    identifiers, and a small set of objectively detectable hard-fail rules.
    """

    text = str(final_output or "")
    tables = _markdown_tables(text)
    table_headers = [table["headers"] for table in tables]
    flattened_headers = {
        _normalize_label(header)
        for headers in table_headers
        for header in headers
        if _normalize_label(header)
    }
    section_labels = _required_section_labels(str(task.get("required_output_format") or ""))
    section_presence = {
        label: _section_is_present(label, text) for label in section_labels
    }
    academic_identifier_count = len(
        {
            *(match.group(0).lower().rstrip(".,;)") for match in _DOI_PATTERN.finditer(text)),
            *(f"arxiv:{match.group(1).lower()}" for match in _ARXIV_PATTERN.finditer(text)),
        }
    )
    reference_entry_count = _reference_entry_count(text)
    paper_table_row_counts = [
        table["row_count"]
        for table in tables
        if any("paper" in _normalize_label(header) for header in table["headers"])
    ]
    selected_paper_count = max(
        [academic_identifier_count, reference_entry_count, *paper_table_row_counts],
        default=0,
    )
    question_count = _numbered_question_count(text)

    criterion_caps: dict[str, dict[str, Any]] = {}
    for criterion in task.get("evaluation_criteria") or []:
        if not isinstance(criterion, dict) or criterion.get("id") is None:
            continue
        criterion_id = str(criterion["id"])
        description = str(criterion.get("criterion") or "")
        finding = _criterion_cap(
            description,
            flattened_headers=flattened_headers,
            section_presence=section_presence,
            selected_paper_count=selected_paper_count,
            question_count=question_count,
            academic_identifier_count=academic_identifier_count,
            text=text,
        )
        if finding is not None:
            criterion_caps[criterion_id] = finding

    hard_fail_rules = _hard_fail_rules(task)
    triggered_hard_fail_rules: list[str] = []
    unresolved_hard_fail_rules: list[str] = []
    for rule in hard_fail_rules:
        triggered = _detect_hard_fail(rule, text, evidence_audit)
        if triggered is True:
            triggered_hard_fail_rules.append(rule)
        elif triggered is None:
            unresolved_hard_fail_rules.append(rule)

    return {
        "word_count": len(re.findall(r"\b[\w'-]+\b", text)),
        "markdown_table_count": len(tables),
        "markdown_table_headers": table_headers,
        "markdown_table_row_counts": [table["row_count"] for table in tables],
        "required_section_presence": section_presence,
        "numbered_question_count": question_count,
        "academic_identifier_count": academic_identifier_count,
        "reference_entry_count": reference_entry_count,
        "selected_paper_count": selected_paper_count,
        "criterion_score_caps": criterion_caps,
        "triggered_hard_fail_rules": triggered_hard_fail_rules,
        "unresolved_hard_fail_rules": unresolved_hard_fail_rules,
        "deterministic_hard_fail_score_cap": 0.0 if triggered_hard_fail_rules else 1.0,
    }


def apply_criterion_caps(
    criterion_scores: list[dict[str, Any]],
    response_audit: dict[str, Any],
) -> list[dict[str, Any]]:
    """Apply only deterministic caps; preserve the Judge's semantic findings."""

    caps = response_audit.get("criterion_score_caps") or {}
    effective: list[dict[str, Any]] = []
    for item in criterion_scores:
        rendered = dict(item)
        criterion_id = str(item["id"])
        finding = caps.get(criterion_id)
        if isinstance(finding, dict):
            cap = float(finding.get("score_cap", 1.0))
            raw_score = float(item["score"])
            rendered["score"] = min(raw_score, cap)
            if rendered["score"] < raw_score:
                rendered["judge_score"] = raw_score
                rendered["deterministic_correction"] = str(finding.get("reason") or "")
        effective.append(rendered)
    return effective


def _criterion_cap(
    description: str,
    *,
    flattened_headers: set[str],
    section_presence: dict[str, bool],
    selected_paper_count: int,
    question_count: int,
    academic_identifier_count: int,
    text: str,
) -> dict[str, Any] | None:
    normalized = description.lower()
    header_match = re.search(
        r"exact\s+column(?:\s+header)?\s*(?:contains|is|:)?\s*['\"]([^'\"]+)['\"]",
        description,
        re.IGNORECASE,
    )
    if not header_match:
        header_match = re.search(
            r"exact\s+column\s+header\s+['\"]([^'\"]+)['\"]",
            description,
            re.IGNORECASE,
        )
    if header_match:
        expected = header_match.group(1)
        present = _normalize_label(expected) in flattened_headers
        return {
            "score_cap": 1.0 if present else 0.0,
            "reason": (
                f"Exact Markdown table header {expected!r} was found."
                if present
                else f"Exact Markdown table header {expected!r} was not found."
            ),
        }

    papers_match = re.search(r"selects?\s+exactly\s+(\d+)\s+academic\s+papers?", normalized)
    if papers_match:
        expected = int(papers_match.group(1))
        return {
            "score_cap": 1.0 if selected_paper_count == expected else 0.0,
            "reason": (
                f"Detected {selected_paper_count} selected papers; exactly {expected} required."
            ),
        }

    questions_match = re.search(r"contains?\s+exactly\s+(\d+)\s+questions?", normalized)
    if questions_match:
        expected = int(questions_match.group(1))
        return {
            "score_cap": 1.0 if question_count == expected else 0.0,
            "reason": f"Detected {question_count} numbered questions; exactly {expected} required.",
        }

    sections_match = re.search(r"includes?\s+all\s+(\d+)\s+requested\s+layout\s+sections?", normalized)
    if sections_match and section_presence:
        expected = int(sections_match.group(1))
        present = sum(section_presence.values())
        cap = 1.0 if present >= expected else (0.5 if present else 0.0)
        return {
            "score_cap": cap,
            "reason": f"Detected {present} of {expected} required section labels.",
        }

    if "includes a formal references section" in normalized:
        present = bool(re.search(r"(?im)^\s{0,3}#{1,6}\s+references?\s*:?\s*$", text)) or bool(
            re.search(
                r"(?im)^\s*(?:\d+[.)]\s*)?\*{0,2}references?\s*:?\*{0,2}\s*:?\s*$",
                text,
            )
        )
        return {
            "score_cap": 1.0 if present else 0.0,
            "reason": "A References section was found." if present else "No References section was found.",
        }

    identifiers_match = re.search(
        r"references?\s+include\s+verifiable\s+doi\s+or\s+arxiv\s+ids?\s+for\s+all\s+(\d+)\s+papers?",
        normalized,
    )
    if identifiers_match:
        expected = int(identifiers_match.group(1))
        cap = 1.0 if academic_identifier_count >= expected else (
            0.5 if academic_identifier_count else 0.0
        )
        return {
            "score_cap": cap,
            "reason": (
                f"Detected {academic_identifier_count} unique DOI/ArXiv identifiers; {expected} required."
            ),
        }
    return None


def _markdown_tables(text: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    tables: list[dict[str, Any]] = []
    index = 0
    while index + 1 < len(lines):
        headers = _split_table_row(lines[index])
        separator = _split_table_row(lines[index + 1])
        if headers and separator and len(headers) == len(separator) and all(
            re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in separator
        ):
            row_count = 0
            cursor = index + 2
            while cursor < len(lines):
                row = _split_table_row(lines[cursor])
                if not row:
                    break
                row_count += 1
                cursor += 1
            tables.append(
                {
                    "headers": [_clean_label(cell) for cell in headers],
                    "row_count": row_count,
                }
            )
            index = cursor
            continue
        index += 1
    return tables


def _split_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if "|" not in stripped:
        return []
    return [cell.strip() for cell in stripped.strip("|").split("|")]


def _required_section_labels(required_format: str) -> list[str]:
    labels: list[str] = []
    for match in re.finditer(r"(?m)^\s*\d+[.)]\s+(.+?)\s*$", required_format):
        label = match.group(1).strip().rstrip(".")
        label = re.sub(r"\s*\([^)]*\)\s*$", "", label).strip()
        if label:
            labels.append(label)
    return labels


def _section_is_present(label: str, text: str) -> bool:
    stop_words = {"a", "an", "and", "of", "the", "to", "paragraph"}
    expected_ordered = [
        token for token in _normalize_label(label).split() if token not in stop_words
    ]
    expected = set(expected_ordered)
    if not expected_ordered:
        return False
    for line in text.splitlines():
        candidate_normalized = _normalize_label(line)
        candidate = {
            token for token in candidate_normalized.split() if token not in stop_words
        }
        if not candidate:
            continue
        overlap = len(expected & candidate) / len(expected)
        prefix_present = len(expected_ordered) >= 2 and set(expected_ordered[:2]) <= candidate
        if prefix_present or (
            overlap >= 0.6 and (len(expected & candidate) >= 2 or len(expected) == 1)
        ):
            return True
    return False


def _numbered_question_count(text: str) -> int:
    counts: set[int] = set()
    for raw_line in text.splitlines():
        line = _MARKDOWN_DECORATION.sub("", raw_line).strip()
        match = re.match(r"(?:[-+]\s*)?(?:question\s*)?(\d+)[.)\s:-]+(.+)", line, re.IGNORECASE)
        if match and "?" in match.group(2):
            counts.add(int(match.group(1)))
    return len(counts)


def _reference_entry_count(text: str) -> int:
    section = re.split(r"(?im)^\s*(?:#{1,6}\s*)?references?\s*:?[ \t]*$", text, maxsplit=1)
    if len(section) != 2:
        return 0
    return len(
        {
            int(match.group(1))
            for match in re.finditer(r"(?m)^\s*(\d+)[.)]\s+\S", section[1])
        }
    )


def _hard_fail_rules(task: dict[str, Any]) -> list[str]:
    rubric = task.get("scoring_rubric")
    if not isinstance(rubric, dict):
        return []
    rules = rubric.get("hard_fail_rules") or []
    return [str(rule).strip() for rule in rules if str(rule).strip()]


def _detect_hard_fail(
    rule: str,
    text: str,
    evidence_audit: dict[str, Any],
) -> bool | None:
    normalized = rule.lower()
    if "tool use/citations" in normalized and "prohibited" in normalized:
        citation_audit = evidence_audit.get("citation_audit") or {}
        citation_count = len(citation_audit.get("answer_urls") or []) + len(
            citation_audit.get("answer_identifiers") or []
        )
        return bool(evidence_audit.get("tool_call_count") or citation_count)

    recommendation_match = re.search(
        r"fail\s+if\s+(.+?)\s+is\s+recommended", rule, re.IGNORECASE
    )
    if recommendation_match:
        target = recommendation_match.group(1).strip(" ' \"")
        recommendation_text = _recommendation_section(text)
        return bool(
            re.search(
                rf"\b(?:recommend(?:ed|ation)?|choose|select)\w*\b[^.\n]{{0,100}}\b{re.escape(target)}\b",
                recommendation_text,
                re.IGNORECASE,
            )
            or re.search(
                rf"\b{re.escape(target)}\b[^.\n]{{0,80}}\b(?:is|as)\s+(?:the\s+)?recommend",
                recommendation_text,
                re.IGNORECASE,
            )
            or re.search(
                rf"\b{re.escape(target)}\b[^.\n]{{0,100}}\b(?:most\s+suitable|best\s+(?:fit|option|choice)|preferred\s+(?:option|choice)|recommended)\b",
                recommendation_text,
                re.IGNORECASE,
            )
        )

    if "required scholarly evidence is not cited" in normalized:
        # The evidence audit already applies the benchmark's configured cap;
        # do not turn a graded evidence shortfall into an unconditional zero.
        return False
    return None


def _recommendation_section(text: str) -> str:
    match = re.search(r"(?is)(?:final\s+strategic\s+recommendation|recommendation)\s*:?(.*)", text)
    return match.group(1) if match else text


def _clean_label(value: str) -> str:
    return _MARKDOWN_DECORATION.sub("", value).strip()


def _normalize_label(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", _clean_label(value).lower()))
