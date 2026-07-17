from __future__ import annotations

import json
import re
import urllib.parse
from typing import Any

from .tools import DISCOVERY_TOOL_NAMES, EVIDENCE_TOOL_NAMES


_URL_PATTERN = re.compile(r"https?://[^\s<>\"\]]+", re.IGNORECASE)
_DOI_PATTERN = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
_ARXIV_PATTERN = re.compile(
    r"(?:arxiv\s*:\s*|arxiv\.org/(?:abs|pdf)/)(\d{4}\.\d{4,5}(?:v\d+)?)",
    re.IGNORECASE,
)
_MAX_SOURCE_RECORDS = 30
_MAX_EXCERPT_CHARS = 24_000
_MAX_SUBSTANTIVE_EXCERPT = 1_600
_MAX_DISCOVERY_EXCERPT = 300


def build_evidence_audit(
    run_log: dict[str, Any],
    task: dict[str, Any],
    final_output: str,
) -> dict[str, Any]:
    """Build a deterministic audit from executed tools and answer citations."""

    requirement = str(task.get("tool_requirement") or run_log.get("tool_requirement") or "").strip()
    normalized_requirement = requirement.lower()
    call_trace: list[dict[str, Any]] = []
    source_records: list[dict[str, Any]] = []
    successful_substantive_calls = 0
    successful_discovery_calls = 0

    raw_calls = run_log.get("tool_calls") or []
    if not isinstance(raw_calls, list):
        raw_calls = []
    for index, call in enumerate(raw_calls, start=1):
        if not isinstance(call, dict):
            continue
        tool_name = str(call.get("tool_name") or "")
        success = bool(call.get("success"))
        if tool_name in EVIDENCE_TOOL_NAMES:
            evidence_level = "substantive"
        elif tool_name in DISCOVERY_TOOL_NAMES:
            evidence_level = "discovery_only"
        else:
            evidence_level = "non_evidence"

        payload = _parse_tool_output(call.get("output"))
        records = _records_from_tool(tool_name, payload) if success else []
        if success and records and evidence_level == "substantive":
            successful_substantive_calls += 1
        elif success and records and evidence_level == "discovery_only":
            successful_discovery_calls += 1
        for record in records:
            record["evidence_level"] = evidence_level
            record["tool_name"] = tool_name
            record["tool_call_index"] = index
            source_records.append(record)
        call_trace.append(
            {
                "index": index,
                "tool_name": tool_name,
                "success": success,
                "evidence_level": evidence_level,
                "source_records": len(records),
                "error": str(call.get("error") or "")[:500] or None,
            }
        )

    source_records = _bounded_source_records(_deduplicate_records(source_records))
    substantive_records = [
        record for record in source_records if record.get("evidence_level") == "substantive"
    ]
    discovery_records = [
        record for record in source_records if record.get("evidence_level") == "discovery_only"
    ]

    retrieved_urls = {
        normalized
        for record in substantive_records
        if (normalized := _normalize_url(record.get("url")))
    }
    discovered_urls = {
        normalized
        for record in discovery_records
        if (normalized := _normalize_url(record.get("url")))
    }
    retrieved_identifiers = {
        normalized
        for record in substantive_records
        for raw_identifier in (record.get("doi"), record.get("arxiv_id"))
        if (normalized := _normalize_identifier(raw_identifier))
    }

    answer_urls = {_normalize_url(value) for value in _extract_urls(final_output)}
    answer_urls.discard("")
    answer_identifiers = {
        _normalize_identifier(value)
        for value in _extract_identifiers(final_output)
        if _normalize_identifier(value)
    }
    traceable_urls = answer_urls & retrieved_urls
    search_only_urls = (answer_urls & discovered_urls) - retrieved_urls
    unaccessed_urls = answer_urls - retrieved_urls - discovered_urls
    traceable_identifiers = answer_identifiers & retrieved_identifiers
    unaccessed_identifiers = answer_identifiers - retrieved_identifiers
    citation_units = answer_urls | answer_identifiers
    traceable_units = traceable_urls | traceable_identifiers
    traceability_rate = (
        round(len(traceable_units) / len(citation_units), 4) if citation_units else None
    )

    normalized_answer = _normalize_title(final_output)
    matched_titles = sorted(
        {
            str(record.get("title"))
            for record in substantive_records
            if _title_is_present(record.get("title"), normalized_answer)
        }
    )
    source_domains = sorted(
        {
            domain
            for record in substantive_records
            if (domain := _url_domain(record.get("url")))
        }
    )
    academic_source_providers = sorted(
        {
            str(record.get("source_provider"))
            for record in substantive_records
            if record.get("source_provider")
        }
    )
    retrieval_dates = sorted(
        {
            str(record.get("retrieved_at"))[:10]
            for record in substantive_records
            if record.get("retrieved_at")
        }
    )
    local_document_paths = sorted(
        {
            str(record.get("path"))
            for record in substantive_records
            if record.get("path")
        }
    )
    academic_records = [record for record in substantive_records if record.get("source_provider")]
    identifier_records = [
        record
        for record in academic_records
        if record.get("doi") or record.get("arxiv_id")
    ]

    if normalized_requirement == "required":
        execution_satisfied = successful_substantive_calls > 0 and bool(substantive_records)
        invalid_reason = (
            None
            if execution_satisfied
            else "Required task completed without successfully reading or querying a substantive evidence source."
        )
    elif normalized_requirement == "prohibited":
        execution_satisfied = not raw_calls
        invalid_reason = None if execution_satisfied else "Prohibited task recorded one or more tool calls."
    else:
        execution_satisfied = True
        invalid_reason = None

    deterministic_score_cap = 1.0 if execution_satisfied else 0.0
    deterministic_cap_reasons = [invalid_reason] if invalid_reason else []
    if not execution_satisfied:
        citation_alignment_status = "invalid_execution"
    elif normalized_requirement == "required":
        if citation_units and not traceable_units and not matched_titles:
            deterministic_score_cap = 0.4
            deterministic_cap_reasons.append(
                "None of the answer's machine-readable citations were traceable to a substantively accessed source."
            )
            citation_alignment_status = "untraceable"
        elif traceability_rate is not None and traceability_rate < 0.5 and not matched_titles:
            deterministic_score_cap = 0.6
            deterministic_cap_reasons.append(
                "Fewer than half of the answer's machine-readable citations were traceable to accessed sources."
            )
            citation_alignment_status = "weak"
        elif not citation_units and not matched_titles:
            deterministic_score_cap = 0.5
            deterministic_cap_reasons.append(
                "The Required answer contained no machine-traceable URL, academic identifier, or accessed source title."
            )
            citation_alignment_status = "not_machine_traceable"
        elif traceability_rate == 1.0:
            citation_alignment_status = "aligned"
        elif matched_titles:
            citation_alignment_status = "title_traceable"
        else:
            citation_alignment_status = "partial"
    elif normalized_requirement == "prohibited":
        citation_alignment_status = "not_applicable"
    else:
        citation_alignment_status = "not_required"

    evidence_policy = task.get("evidence_policy") if isinstance(task.get("evidence_policy"), dict) else {}
    policy_violations = _evidence_policy_violations(
        evidence_policy,
        substantive_source_count=len(substantive_records),
        academic_records=academic_records,
        identifier_record_count=len(identifier_records),
        local_document_count=len(local_document_paths),
        source_domains=source_domains,
        academic_source_providers=academic_source_providers,
        retrieval_dates=retrieval_dates,
        traceability_rate=traceability_rate,
        matched_title_count=len(matched_titles),
    )
    if execution_satisfied and policy_violations:
        policy_cap = float(evidence_policy.get("violation_score_cap", 0.5))
        deterministic_score_cap = min(deterministic_score_cap, policy_cap)
        deterministic_cap_reasons.extend(policy_violations)

    return {
        "tool_requirement": requirement,
        "execution_requirement_satisfied": execution_satisfied,
        "execution_status": "valid" if execution_satisfied else "invalid",
        "score_eligible": execution_satisfied,
        "citation_alignment_status": citation_alignment_status,
        "evidence_policy_satisfied": not policy_violations,
        "evidence_policy_violations": policy_violations,
        "deterministic_score_cap": deterministic_score_cap,
        "deterministic_cap_reasons": deterministic_cap_reasons,
        "tool_call_count": len(raw_calls),
        "successful_tool_call_count": sum(bool(call.get("success")) for call in call_trace),
        "successful_substantive_tool_call_count": successful_substantive_calls,
        "successful_discovery_tool_call_count": successful_discovery_calls,
        "substantive_source_count": len(substantive_records),
        "discovery_source_count": len(discovery_records),
        "academic_record_count": len(academic_records),
        "identifier_record_count": len(identifier_records),
        "local_document_count": len(local_document_paths),
        "substantive_source_domains": source_domains,
        "academic_source_providers": academic_source_providers,
        "retrieval_dates": retrieval_dates,
        "local_document_paths": local_document_paths,
        "call_trace": call_trace,
        "citation_audit": {
            "answer_urls": sorted(answer_urls),
            "answer_identifiers": sorted(answer_identifiers),
            "traceable_urls": sorted(traceable_urls),
            "traceable_identifiers": sorted(traceable_identifiers),
            "search_result_only_urls": sorted(search_only_urls),
            "unaccessed_urls": sorted(unaccessed_urls),
            "unaccessed_identifiers": sorted(unaccessed_identifiers),
            "traceability_rate": traceability_rate,
            "matched_retrieved_titles": matched_titles,
        },
        "source_records": source_records,
    }


def tool_call_has_substantive_source(call: dict[str, Any]) -> bool:
    if not call.get("success") or call.get("tool_name") not in EVIDENCE_TOOL_NAMES:
        return False
    payload = _parse_tool_output(call.get("output"))
    return bool(_records_from_tool(str(call.get("tool_name") or ""), payload))


def _evidence_policy_violations(
    policy: dict[str, Any],
    *,
    substantive_source_count: int,
    academic_records: list[dict[str, Any]],
    identifier_record_count: int,
    local_document_count: int,
    source_domains: list[str],
    academic_source_providers: list[str],
    retrieval_dates: list[str],
    traceability_rate: float | None,
    matched_title_count: int,
) -> list[str]:
    if not policy:
        return []
    violations: list[str] = []
    minimum_sources = int(policy.get("minimum_substantive_sources", 0))
    if substantive_source_count < minimum_sources:
        violations.append(
            f"Evidence policy requires at least {minimum_sources} substantive sources; "
            f"the run accessed {substantive_source_count}."
        )
    minimum_academic = int(policy.get("minimum_academic_records", 0))
    if len(academic_records) < minimum_academic:
        violations.append(
            f"Evidence policy requires at least {minimum_academic} academic records; "
            f"the run accessed {len(academic_records)}."
        )
    minimum_identifiers = int(policy.get("minimum_identifier_records", 0))
    if identifier_record_count < minimum_identifiers:
        violations.append(
            f"Evidence policy requires at least {minimum_identifiers} academic records with DOI or ArXiv IDs; "
            f"the run accessed {identifier_record_count}."
        )
    minimum_local = int(policy.get("minimum_local_documents", 0))
    if local_document_count < minimum_local:
        violations.append(
            f"Evidence policy requires at least {minimum_local} local documents; "
            f"the run read {local_document_count}."
        )

    minimum_recent = int(policy.get("minimum_recent_academic_records", 0))
    minimum_year = int(policy.get("minimum_publication_year", 0))
    if minimum_recent:
        recent_count = sum(
            _as_int(record.get("year")) >= minimum_year for record in academic_records
        )
        if recent_count < minimum_recent:
            violations.append(
                f"Evidence policy requires at least {minimum_recent} academic records from {minimum_year} or later; "
                f"the run accessed {recent_count}."
            )

    for domains in policy.get("required_domain_groups") or []:
        normalized_domains = [str(domain).strip().lower() for domain in domains]
        if not any(
            _domain_matches(source_domain, allowed_domain)
            for source_domain in source_domains
            for allowed_domain in normalized_domains
        ):
            violations.append(
                "Evidence policy requires a substantively accessed official source from one of: "
                + ", ".join(normalized_domains)
                + "."
            )

    if policy.get("academic_provider_consistency") and len(academic_source_providers) != 1:
        violations.append(
            "Evidence policy requires one consistent academic citation provider across all records."
        )
    if policy.get("common_retrieval_date") and len(retrieval_dates) != 1:
        violations.append("Evidence policy requires one common retrieval date across source records.")

    minimum_traceability = float(policy.get("minimum_traceability_rate", 0.0))
    title_target = max(1, minimum_academic or minimum_sources)
    title_traceability_sufficient = matched_title_count >= title_target
    if minimum_traceability and (
        traceability_rate is None or traceability_rate < minimum_traceability
    ) and not title_traceability_sufficient:
        rendered_rate = "none" if traceability_rate is None else f"{traceability_rate:.2f}"
        violations.append(
            f"Evidence policy requires citation traceability of at least {minimum_traceability:.2f}; "
            f"the measured rate was {rendered_rate}."
        )
    return violations


def compact_evidence_audit(audit: dict[str, Any]) -> dict[str, Any]:
    """Remove source excerpts before persisting the audit in score records."""

    compact = {key: value for key, value in audit.items() if key != "source_records"}
    compact["source_records"] = [
        {key: value for key, value in record.items() if key != "excerpt"}
        for record in audit.get("source_records") or []
        if isinstance(record, dict)
    ]
    return compact


def _parse_tool_output(raw_output: Any) -> dict[str, Any]:
    if not isinstance(raw_output, str) or not raw_output.strip():
        return {}
    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError:
        return {"raw_excerpt": raw_output[:_MAX_SUBSTANTIVE_EXCERPT]}
    return payload if isinstance(payload, dict) else {}


def _records_from_tool(tool_name: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    if tool_name == "web_search":
        return [_web_record(item) for item in payload.get("results") or [] if isinstance(item, dict)]
    if tool_name == "fetch_url":
        return [_fetch_record(payload)]
    if tool_name == "fetch_urls":
        return [
            _fetch_record(item)
            for item in payload.get("results") or []
            if isinstance(item, dict) and item.get("ok")
        ]
    if tool_name == "academic_search":
        provider = payload.get("source")
        return [
            _academic_record(item, provider, payload.get("retrieved_at"))
            for item in payload.get("results") or []
            if isinstance(item, dict)
        ]
    if tool_name == "academic_lookup":
        provider = payload.get("source")
        records = []
        for item in payload.get("results") or []:
            if isinstance(item, dict) and isinstance(item.get("match"), dict):
                records.append(
                    _academic_record(item["match"], provider, payload.get("retrieved_at"))
                )
        return records
    if tool_name == "list_local_documents":
        return [
            {"path": item.get("path"), "title": item.get("path")}
            for item in payload.get("documents") or []
            if isinstance(item, dict)
        ]
    if tool_name == "read_local_document":
        return [_local_record(payload)]
    if tool_name == "read_local_documents":
        return [
            _local_record(item)
            for item in payload.get("documents") or []
            if isinstance(item, dict) and item.get("ok")
        ]
    return []


def _web_record(item: dict[str, Any]) -> dict[str, Any]:
    return _clean_record(
        {
            "url": item.get("url"),
            "title": item.get("title"),
            "published_at": item.get("published_at"),
            "excerpt": item.get("snippet"),
        }
    )


def _fetch_record(item: dict[str, Any]) -> dict[str, Any]:
    return _clean_record(
        {
            "url": item.get("url"),
            "title": item.get("title"),
            "retrieved_at": item.get("retrieved_at"),
            "excerpt": item.get("content"),
        }
    )


def _academic_record(item: dict[str, Any], provider: Any, retrieved_at: Any) -> dict[str, Any]:
    external_ids = item.get("external_ids") if isinstance(item.get("external_ids"), dict) else {}
    return _clean_record(
        {
            "source_provider": provider,
            "url": item.get("url"),
            "title": item.get("title"),
            "authors": item.get("authors"),
            "year": item.get("year"),
            "publication_date": item.get("publication_date"),
            "venue": item.get("venue"),
            "citation_count": item.get("citation_count"),
            "retrieved_at": retrieved_at,
            "doi": item.get("doi") or external_ids.get("DOI"),
            "arxiv_id": external_ids.get("ArXiv"),
            "excerpt": item.get("abstract"),
        }
    )


def _local_record(item: dict[str, Any]) -> dict[str, Any]:
    return _clean_record(
        {
            "path": item.get("path"),
            "title": item.get("title") or item.get("path"),
            "excerpt": item.get("content"),
        }
    )


def _clean_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in record.items()
        if value not in (None, "", [], {})
    }


def _deduplicate_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for record in records:
        key = (
            str(record.get("evidence_level") or ""),
            _normalize_url(record.get("url")),
            str(record.get("path") or "").lower(),
            _normalize_title(record.get("title")),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(record)
    return unique


def _bounded_source_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bounded: list[dict[str, Any]] = []
    remaining = _MAX_EXCERPT_CHARS
    for record in records[:_MAX_SOURCE_RECORDS]:
        item = dict(record)
        excerpt = str(item.get("excerpt") or "")
        if excerpt and remaining > 0:
            per_source_limit = (
                _MAX_DISCOVERY_EXCERPT
                if item.get("evidence_level") == "discovery_only"
                else _MAX_SUBSTANTIVE_EXCERPT
            )
            limit = min(per_source_limit, remaining)
            item["excerpt"] = excerpt[:limit]
            item["excerpt_truncated"] = len(excerpt) > limit
            remaining -= len(item["excerpt"])
        else:
            item.pop("excerpt", None)
        bounded.append(item)
    return bounded


def _extract_urls(text: str) -> list[str]:
    return [_trim_url(match.group(0)) for match in _URL_PATTERN.finditer(text)]


def _trim_url(value: str) -> str:
    cleaned = value.rstrip(".,;:!?\"'")
    while cleaned.endswith(")") and cleaned.count(")") > cleaned.count("("):
        cleaned = cleaned[:-1]
    return cleaned


def _normalize_url(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        return ""
    candidate = _trim_url(value.strip())
    try:
        parsed = urllib.parse.urlsplit(candidate)
    except ValueError:
        return ""
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        return ""
    host = parsed.hostname.lower()
    try:
        parsed_port = parsed.port
    except ValueError:
        return ""
    port = f":{parsed_port}" if parsed_port else ""
    path = parsed.path.rstrip("/") or ""
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{parsed.scheme.lower()}://{host}{port}{path}{query}"


def _url_domain(value: Any) -> str:
    normalized = _normalize_url(value)
    return (urllib.parse.urlsplit(normalized).hostname or "") if normalized else ""


def _domain_matches(source_domain: str, allowed_domain: str) -> bool:
    return source_domain == allowed_domain or source_domain.endswith(f".{allowed_domain}")


def _extract_identifiers(text: str) -> list[str]:
    identifiers = [match.group(0) for match in _DOI_PATTERN.finditer(text)]
    identifiers.extend(match.group(1) for match in _ARXIV_PATTERN.finditer(text))
    return identifiers


def _normalize_identifier(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        return ""
    normalized = value.strip().lower()
    normalized = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", normalized)
    normalized = re.sub(r"^doi\s*:\s*", "", normalized)
    normalized = re.sub(r"^arxiv\s*:\s*", "", normalized)
    normalized = normalized.rstrip(".,;:!?\"]}")
    while normalized.endswith(")") and normalized.count(")") > normalized.count("("):
        normalized = normalized[:-1]
    return normalized


def _normalize_title(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _title_is_present(title: Any, normalized_answer: str) -> bool:
    normalized_title = _normalize_title(title)
    return len(normalized_title) >= 20 and normalized_title in normalized_answer


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return -1
