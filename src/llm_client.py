from __future__ import annotations
import copy
import json
import os
import time
import urllib.error
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SECRETS_PATH = PROJECT_ROOT / ".secrets" / "model_keys.json"

_SENSITIVE_CONFIG_KEYS = {
    "api_key",
    "apikey",
    "authorization",
    "bearer_token",
    "access_token",
}

_EFFECTIVE_CONFIG_KEYS = {
    "display_name",
    "description",
    "supported_roles",
    "capabilities",
    "provider",
    "profile",
    "base_url",
    "model",
    "api_key_env",
    "max_tokens",
    "max_tokens_param",
    "timeout_seconds",
    "max_retries",
    "request_options",
    "agent_max_tokens",
    "final_max_tokens",
    "judge_max_tokens",
    "pricing_per_1m_tokens",
}


@dataclass
class LLMResponse:
    content: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    raw: dict[str, Any]
    response_model: str | None = None
    finish_reason: str | None = None


def load_secrets(path: Path | str | None = None) -> dict[str, str]:
    """Load local model keys without ever printing or logging their values."""

    secrets_path = Path(path) if path is not None else DEFAULT_SECRETS_PATH
    if not secrets_path.exists():
        return {}
    try:
        with secrets_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read model secrets file: {secrets_path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Model secrets file must contain a JSON object: {secrets_path}")

    return {
        str(name): value
        for name, value in payload.items()
        if isinstance(value, str) and value.strip()
    }


def resolve_profile(
    config: Mapping[str, Any],
    *,
    role: str = "agent",
    profile: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """Resolve a named model profile and optional model override."""

    if role not in {"agent", "judge"}:
        raise ValueError("role must be either 'agent' or 'judge'")

    raw_profiles = config.get("profiles")
    if not isinstance(raw_profiles, Mapping) or not raw_profiles:
        raise ValueError("model config must define a non-empty 'profiles' object")
    defaults = config.get("defaults") or {}
    if not isinstance(defaults, Mapping):
        raise ValueError("model config 'defaults' must be a JSON object")
    selected_name = profile or str(defaults.get(role) or "")
    if not selected_name:
        raise ValueError(f"No default {role} profile is configured")
    if selected_name not in raw_profiles:
        available = ", ".join(sorted(str(name) for name in raw_profiles))
        raise ValueError(f"Unknown model profile '{selected_name}'. Available: {available}")

    common = config.get("client_defaults") or {}
    selected = raw_profiles[selected_name]
    if not isinstance(common, Mapping) or not isinstance(selected, Mapping):
        raise ValueError("client_defaults and each model profile must be JSON objects")
    merged = copy.deepcopy(dict(common))
    common_options = merged.pop("request_options", {}) or {}
    selected_copy = copy.deepcopy(dict(selected))
    selected_options = selected_copy.pop("request_options", {}) or {}
    if not isinstance(common_options, Mapping) or not isinstance(selected_options, Mapping):
        raise ValueError("request_options must be a JSON object")
    merged.update(selected_copy)
    request_options = copy.deepcopy(dict(common_options))
    request_options.update(copy.deepcopy(dict(selected_options)))

    _reject_embedded_secrets(merged)
    _reject_embedded_secrets(request_options)

    provider = str(merged.get("provider") or "").strip().lower()
    base_url = str(merged.get("base_url") or "").strip()
    resolved_model = str(model or merged.get("model") or "").strip()
    api_key_env = str(merged.get("api_key_env") or "").strip()
    max_tokens_param = str(merged.get("max_tokens_param") or "").strip()

    if not provider:
        raise ValueError(f"Profile '{selected_name}' has no provider")
    if not base_url:
        raise ValueError(f"Profile '{selected_name}' has no base_url")
    if not resolved_model:
        raise ValueError(f"Profile '{selected_name}' has no model")
    if not api_key_env:
        raise ValueError(f"Profile '{selected_name}' has no api_key_env")
    if not max_tokens_param or any(character.isspace() for character in max_tokens_param):
        raise ValueError(f"Profile '{selected_name}' has an invalid max_tokens_param")
    supported_roles = merged.get("supported_roles") or []
    if supported_roles and role not in supported_roles:
        raise ValueError(f"Profile '{selected_name}' does not support the {role} role")

    resolved: dict[str, Any] = copy.deepcopy(merged)
    resolved.update(
        {
            "provider": provider,
            "profile": selected_name,
            "base_url": base_url.rstrip("/"),
            "model": resolved_model,
            "api_key_env": api_key_env,
            "max_tokens_param": max_tokens_param,
            "request_options": request_options,
        }
    )

    return resolved


def resolve_api_key(
    resolved_profile: Mapping[str, Any],
    *,
    secrets_path: Path | str | None = None,
    environ: Mapping[str, str] | None = None,
) -> str:
    """Resolve an API key with environment variables taking precedence."""

    env = os.environ if environ is None else environ
    env_name = str(resolved_profile.get("api_key_env") or "")
    environment_value = env.get(env_name, "") if env_name else ""
    if environment_value.strip():
        return environment_value

    secrets = load_secrets(secrets_path)
    stored_value = secrets.get(env_name, "")
    if stored_value.strip():
        return stored_value

    profile_name = resolved_profile.get("profile", "unknown")
    provider = resolved_profile.get("provider", "provider")
    raise ValueError(
        f"No API key configured for profile '{profile_name}' ({provider}). "
        f"Set {env_name} or run scripts/configure_models.py."
    )


def list_profiles(config: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return redacted profile summaries suitable for display."""

    raw_profiles = config.get("profiles")
    if not isinstance(raw_profiles, Mapping) or not raw_profiles:
        raise ValueError("model config must define a non-empty 'profiles' object")
    summaries: list[dict[str, Any]] = []
    for name in sorted(raw_profiles):
        profile = raw_profiles[name]
        roles = profile.get("supported_roles") if isinstance(profile, Mapping) else None
        role = "agent" if not roles or "agent" in roles else "judge"
        summaries.append(_effective_config(resolve_profile(config, role=role, profile=str(name))))
    return summaries


def format_profiles(config: Mapping[str, Any]) -> str:
    lines = []
    defaults = config.get("defaults") if isinstance(config.get("defaults"), Mapping) else {}
    for item in list_profiles(config):
        roles = [role for role in ("agent", "judge") if defaults.get(role) == item["profile"]]
        suffix = f" [default: {', '.join(roles)}]" if roles else ""
        lines.append(f"{item['profile']}: {item['provider']} / {item['model']}{suffix}")
    return "\n".join(lines)


class OpenAICompatibleClient:
    """Small stdlib-only client for OpenAI-compatible Chat Completions APIs."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        *,
        provider: str = "openai-compatible",
        profile: str = "adhoc",
        request_options: Mapping[str, Any] | None = None,
        max_tokens: int = 900,
        max_tokens_param: str = "max_tokens",
        timeout_seconds: int = 120,
        max_retries: int = 2,
        effective_config: Mapping[str, Any] | None = None,
    ) -> None:
        if not api_key or not api_key.strip():
            raise ValueError(f"An API key is required for profile '{profile}'.")
        if not base_url or not model:
            raise ValueError("base_url and model are required")
        if max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        if max_retries < 0:
            raise ValueError("max_retries cannot be negative")

        options = copy.deepcopy(dict(request_options or {}))
        _reject_embedded_secrets(options)
        extra_body = options.get("extra_body") or {}
        if not isinstance(extra_body, Mapping):
            raise ValueError("request_options.extra_body must be a JSON object")
        reserved = {"model", "messages", "stream"} & (set(options) | set(extra_body))
        if reserved:
            raise ValueError(f"request_options cannot override reserved fields: {sorted(reserved)}")

        self._api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.provider = provider
        self.profile = profile
        self.max_tokens = int(max_tokens)
        self.max_tokens_param = max_tokens_param
        self.timeout_seconds = int(timeout_seconds)
        self.max_retries = int(max_retries)
        self._request_options = options
        initial_effective = effective_config or {
            "provider": provider,
            "profile": profile,
            "base_url": self.base_url,
            "model": model,
            "max_tokens": self.max_tokens,
            "max_tokens_param": max_tokens_param,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "request_options": options,
        }
        self._effective_config = _sanitize_effective_config(initial_effective)

    @property
    def effective_config(self) -> dict[str, Any]:
        return copy.deepcopy(self._effective_config)

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(provider={self.provider!r}, profile={self.profile!r}, "
            f"model={self.model!r}, base_url={self.base_url!r})"
        )

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        response_format: dict[str, Any] | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        body = self._build_request_body(messages, response_format=response_format, max_tokens=max_tokens)
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        endpoint = self._chat_completions_url()

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            request = urllib.request.Request(
                endpoint,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self._api_key}",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                if not isinstance(payload, dict):
                    raise ValueError("API response must be a JSON object")
                payload = self._redact_value(payload)
                message = payload["choices"][0]["message"]
                content = message.get("content") or ""
                usage = payload.get("usage") or {}
                input_tokens = int(usage.get("prompt_tokens") or 0)
                output_tokens = int(usage.get("completion_tokens") or 0)
                total_tokens = int(usage.get("total_tokens") or input_tokens + output_tokens)
                return LLMResponse(
                    content=content,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    raw=payload,
                    response_model=str(payload.get("model") or self.model),
                    finish_reason=str(payload["choices"][0].get("finish_reason") or "") or None,
                )
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                message = self._redact(f"{self.provider} HTTP {exc.code}: {detail}")
                if exc.code not in {408, 409, 429} and exc.code < 500:
                    raise RuntimeError(message) from None
                last_error = RuntimeError(message)
            except Exception as exc:  # noqa: BLE001 - add bounded retry context.
                last_error = RuntimeError(self._redact(str(exc)))
            if attempt < self.max_retries:
                time.sleep(1.5 * (attempt + 1))
        raise RuntimeError(
            f"{self.provider} request failed after {self.max_retries + 1} attempt(s): {last_error}"
        )

    def _build_request_body(
        self,
        messages: list[dict[str, str]],
        *,
        response_format: dict[str, Any] | None,
        max_tokens: int | None,
    ) -> dict[str, Any]:
        token_limit = self.max_tokens if max_tokens is None else int(max_tokens)
        if token_limit <= 0:
            raise ValueError("max_tokens must be positive")
        body = copy.deepcopy(self._request_options)
        extra_body = body.pop("extra_body", {}) or {}
        body.update(copy.deepcopy(dict(extra_body)))
        body.update(
            {
                "model": self.model,
                "messages": messages,
                "stream": False,
                self.max_tokens_param: token_limit,
            }
        )
        if response_format is not None:
            body["response_format"] = copy.deepcopy(response_format)
        return body

    def _chat_completions_url(self) -> str:
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        return f"{self.base_url}/chat/completions"

    def _redact(self, text: str) -> str:
        return text.replace(self._api_key, "[REDACTED]") if self._api_key else text

    def _redact_value(self, value: Any) -> Any:
        if isinstance(value, str):
            return self._redact(value)
        if isinstance(value, dict):
            return {key: self._redact_value(nested) for key, nested in value.items()}
        if isinstance(value, list):
            return [self._redact_value(nested) for nested in value]
        return value


class MockLLMClient:
    """Deterministic local client for smoke tests without API calls."""

    def __init__(
        self,
        model: str = "mock-model",
        *,
        provider: str = "mock",
        profile: str = "mock",
        effective_config: Mapping[str, Any] | None = None,
    ) -> None:
        self.model = model
        self.provider = provider
        self.profile = profile
        self._effective_config = _sanitize_effective_config(
            effective_config
            or {
                "provider": provider,
                "profile": profile,
                "model": model,
                "request_options": {},
            }
        )

    @property
    def effective_config(self) -> dict[str, Any]:
        return copy.deepcopy(self._effective_config)

    def __repr__(self) -> str:
        return f"MockLLMClient(provider={self.provider!r}, profile={self.profile!r}, model={self.model!r})"

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        response_format: dict[str, Any] | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        joined = "\n".join(message.get("content", "") for message in messages)
        if response_format and response_format.get("type") == "json_object":
            score = {
                "accuracy_raw": 4,
                "completeness_norm": 0.75,
                "helpfulness_raw": 4,
                "hallucination_rate": 0.05,
                "notes": "Dry-run mock score. Replace with live model scoring for real experiments.",
                "failure_type": "None",
            }
            content = json.dumps(score, ensure_ascii=False)
        else:
            role = _infer_role(joined)
            task_id = _infer_marker(joined, "Task ID") or "TASK"
            content = (
                f"[DRY-RUN {role} output for {task_id}]\n"
                "1. 识别任务目标并拆分为关键维度。\n"
                "2. 覆盖题面中可见的主要要求。\n"
                "3. 给出结构化结论、风险提示和可执行建议。\n"
                "4. 这是本地模拟输出，不代表真实模型质量。"
            )
        input_tokens = _estimate_tokens(joined)
        output_tokens = _estimate_tokens(content)
        return LLMResponse(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            raw={"mock": True, "max_tokens": max_tokens},
            response_model=self.model,
            finish_reason="stop",
        )


def build_client(
    config: Mapping[str, Any],
    *,
    dry_run: bool = False,
    role: str = "agent",
    profile: str | None = None,
    model: str | None = None,
    secrets_path: Path | str | None = None,
    environ: Mapping[str, str] | None = None,
) -> OpenAICompatibleClient | MockLLMClient:
    """Build an agent or judge client from a named, non-secret profile."""

    resolved = resolve_profile(config, role=role, profile=profile, model=model)
    effective = _effective_config(resolved)
    if dry_run:
        return MockLLMClient(
            model=f"mock-{resolved['model']}",
            provider=resolved["provider"],
            profile=resolved["profile"],
            effective_config=effective,
        )

    api_key = resolve_api_key(resolved, secrets_path=secrets_path, environ=environ)
    return OpenAICompatibleClient(
        api_key=api_key,
        base_url=resolved["base_url"],
        model=resolved["model"],
        provider=resolved["provider"],
        profile=resolved["profile"],
        request_options=resolved.get("request_options") or {},
        max_tokens=int(resolved["max_tokens"]),
        max_tokens_param=resolved["max_tokens_param"],
        timeout_seconds=int(resolved["timeout_seconds"]),
        max_retries=int(resolved["max_retries"]),
        effective_config=effective,
    )


def _effective_config(resolved: Mapping[str, Any]) -> dict[str, Any]:
    return _sanitize_effective_config(resolved)


def _sanitize_effective_config(config: Mapping[str, Any]) -> dict[str, Any]:
    safe = {key: copy.deepcopy(value) for key, value in config.items() if key in _EFFECTIVE_CONFIG_KEYS}
    _reject_embedded_secrets(safe)
    return safe


def _reject_embedded_secrets(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized = str(key).strip().lower().replace("-", "_")
            if normalized in _SENSITIVE_CONFIG_KEYS:
                raise ValueError(f"Secret field '{key}' is not allowed in model configuration")
            _reject_embedded_secrets(nested)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            _reject_embedded_secrets(nested)


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _infer_marker(text: str, marker: str) -> str | None:
    prefix = f"{marker}:"
    for line in text.splitlines():
        if line.strip().startswith(prefix):
            return line.split(":", 1)[1].strip()
    return None


def _infer_role(text: str) -> str:
    for line in text.splitlines():
        marker = "You are acting as role:"
        if marker in line:
            return line.split(marker, 1)[1].strip().strip(".")
    if "single-agent baseline" in text or "single-agent" in text.lower():
        return "Single Agent"
    for role in ("Planner", "Researcher", "Analyst", "Critic", "Writer", "Manager"):
        if role in text:
            return role
    return "Agent"


__all__ = [
    "DEFAULT_SECRETS_PATH",
    "LLMResponse",
    "MockLLMClient",
    "OpenAICompatibleClient",
    "build_client",
    "format_profiles",
    "list_profiles",
    "load_secrets",
    "resolve_api_key",
    "resolve_profile",
]
