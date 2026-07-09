from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass
class LLMResponse:
    content: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    raw: dict[str, Any]


class DeepSeekClient:
    """Small OpenAI-compatible client implemented with Python stdlib only."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        temperature: float = 0.0,
        max_tokens: int = 900,
        thinking: str = "disabled",
        reasoning_effort: str = "high",
        timeout_seconds: int = 120,
        max_retries: int = 2,
    ) -> None:
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY is required unless --dry-run is used.")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.thinking = thinking
        self.reasoning_effort = reasoning_effort
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        response_format: dict[str, str] | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "max_tokens": max_tokens or self.max_tokens,
        }
        if response_format:
            body["response_format"] = response_format
        if self.thinking == "enabled":
            body["thinking"] = {"type": "enabled"}
            body["reasoning_effort"] = self.reasoning_effort
        else:
            body["thinking"] = {"type": "disabled"}
            body["temperature"] = self.temperature

        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                message = payload["choices"][0]["message"]
                content = message.get("content") or ""
                usage = payload.get("usage") or {}
                input_tokens = int(usage.get("prompt_tokens") or 0)
                output_tokens = int(usage.get("completion_tokens") or 0)
                total_tokens = int(usage.get("total_tokens") or input_tokens + output_tokens)
                return LLMResponse(content, input_tokens, output_tokens, total_tokens, payload)
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                last_error = RuntimeError(f"DeepSeek HTTP {exc.code}: {detail}")
            except Exception as exc:  # noqa: BLE001 - surface API errors with retry context.
                last_error = exc
            if attempt < self.max_retries:
                time.sleep(1.5 * (attempt + 1))
        raise RuntimeError(f"DeepSeek request failed after retries: {last_error}")


class MockLLMClient:
    """Deterministic local client for smoke tests without spending API tokens."""

    def __init__(self, model: str = "mock-deepseek", **_: Any) -> None:
        self.model = model

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        response_format: dict[str, str] | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        joined = "\n".join(m.get("content", "") for m in messages)
        if response_format and response_format.get("type") == "json_object":
            payload = {
                "accuracy_raw": 4,
                "completeness_norm": 0.75,
                "helpfulness_raw": 4,
                "hallucination_rate": 0.05,
                "notes": "Dry-run mock score. Replace with live DeepSeek scoring for real experiments.",
                "failure_type": "None",
            }
            content = json.dumps(payload, ensure_ascii=False)
        else:
            role = _infer_role(joined)
            task_id = _infer_marker(joined, "Task ID") or "TASK"
            content = (
                f"[DRY-RUN {role} output for {task_id}]\n"
                "1. 识别任务目标并拆分为关键维度。\n"
                "2. 覆盖评价标准中的主要要求。\n"
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
        )


def build_client(config: dict[str, Any], *, dry_run: bool = False) -> DeepSeekClient | MockLLMClient:
    model = os.environ.get("DEEPSEEK_MODEL") or config.get("model") or "deepseek-v4-flash"
    if dry_run:
        return MockLLMClient(model=f"mock-{model}")
    return DeepSeekClient(
        api_key=os.environ.get("DEEPSEEK_API_KEY", ""),
        base_url=os.environ.get("DEEPSEEK_BASE_URL") or config.get("base_url") or "https://api.deepseek.com",
        model=model,
        temperature=float(config.get("temperature", 0.0)),
        max_tokens=int(config.get("max_tokens", 900)),
        thinking=str(config.get("thinking", "disabled")),
        reasoning_effort=str(config.get("reasoning_effort", "high")),
        timeout_seconds=int(config.get("timeout_seconds", 120)),
        max_retries=int(config.get("max_retries", 2)),
    )


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
    for role in ("Planner", "Researcher", "Analyst", "Critic", "Writer", "Manager", "Judge"):
        if role in text:
            return role
    return "Agent"
