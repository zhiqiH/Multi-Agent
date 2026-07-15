from __future__ import annotations

import io
import json
import stat
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.configure_models import configure_keys  # noqa: E402
from src.llm_client import (  # noqa: E402
    MockLLMClient,
    OpenAICompatibleClient,
    build_client,
    resolve_api_key,
    resolve_profile,
)


class _FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = json.dumps(payload).encode("utf-8")

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self) -> bytes:
        return self._payload


def _config() -> dict[str, object]:
    return {
        "defaults": {"agent": "deepseek", "judge": "openai-judge"},
        "client_defaults": {
            "timeout_seconds": 7,
            "max_retries": 0,
            "max_tokens": 99,
            "agent_max_tokens": 50,
            "final_max_tokens": 80,
            "pricing_per_1m_tokens": {"input": 0, "output": 0},
        },
        "profiles": {
            "deepseek": {
                "provider": "deepseek",
                "base_url": "https://api.deepseek.com",
                "model": "deepseek-v4-flash",
                "api_key_env": "DEEPSEEK_API_KEY",
                "max_tokens_param": "max_tokens",
                "request_options": {
                    "temperature": 0.0,
                    "extra_body": {"thinking": {"type": "disabled"}},
                },
            },
            "openai-judge": {
                "provider": "openai",
                "base_url": "https://api.openai.com/v1",
                "model": "gpt-test-judge",
                "api_key_env": "OPENAI_API_KEY",
                "max_tokens_param": "max_completion_tokens",
                "request_options": {"reasoning_effort": "high"},
            },
        },
    }


class ProfileTests(unittest.TestCase):
    def test_agent_judge_defaults_and_model_override(self) -> None:
        config = _config()
        agent = resolve_profile(config)
        judge = resolve_profile(config, role="judge", model="gpt-overridden")

        self.assertEqual(agent["profile"], "deepseek")
        self.assertEqual(agent["provider"], "deepseek")
        self.assertEqual(agent["max_tokens_param"], "max_tokens")
        self.assertEqual(judge["profile"], "openai-judge")
        self.assertEqual(judge["provider"], "openai")
        self.assertEqual(judge["model"], "gpt-overridden")
        self.assertEqual(judge["max_tokens_param"], "max_completion_tokens")

    def test_environment_key_precedes_local_secret(self) -> None:
        resolved = resolve_profile(_config(), role="judge")
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "keys.json"
            path.write_text(json.dumps({"OPENAI_API_KEY": "stored-secret"}), encoding="utf-8")
            self.assertEqual(
                resolve_api_key(resolved, secrets_path=path, environ={"OPENAI_API_KEY": "environment-secret"}),
                "environment-secret",
            )
            self.assertEqual(resolve_api_key(resolved, secrets_path=path, environ={}), "stored-secret")

    def test_secret_fields_are_rejected_from_profiles(self) -> None:
        config = _config()
        config["profiles"]["deepseek"]["api_key"] = "must-not-be-here"  # type: ignore[index]
        with self.assertRaisesRegex(ValueError, "Secret field"):
            resolve_profile(config)


class ClientTests(unittest.TestCase):
    def test_dry_run_exposes_redacted_effective_config(self) -> None:
        client = build_client(_config(), role="judge", dry_run=True)

        self.assertIsInstance(client, MockLLMClient)
        self.assertEqual(client.provider, "openai")
        self.assertEqual(client.profile, "openai-judge")
        self.assertEqual(client.model, "mock-gpt-test-judge")
        self.assertEqual(client.effective_config["agent_max_tokens"], 50)
        self.assertNotIn("api_key", client.effective_config)

    def test_openai_request_uses_profile_options_and_token_parameter(self) -> None:
        api_key = "sk-unit-test-secret"
        client = OpenAICompatibleClient(
            api_key=api_key,
            provider="openai",
            profile="judge",
            base_url="https://api.openai.com/v1",
            model="gpt-test",
            request_options={"reasoning_effort": "high"},
            max_tokens=30,
            max_tokens_param="max_completion_tokens",
            max_retries=0,
        )
        fake = _FakeResponse(
            {
                "model": "gpt-test-snapshot",
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5},
                "debug": api_key,
            }
        )

        with mock.patch("src.llm_client.urllib.request.urlopen", return_value=fake) as urlopen:
            response = client.chat(
                [{"role": "user", "content": "hello"}],
                response_format={"type": "json_object"},
                max_tokens=41,
            )

        request = urlopen.call_args.args[0]
        body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(request.full_url, "https://api.openai.com/v1/chat/completions")
        self.assertEqual(body["max_completion_tokens"], 41)
        self.assertNotIn("max_tokens", body)
        self.assertEqual(body["reasoning_effort"], "high")
        self.assertEqual(body["response_format"], {"type": "json_object"})
        self.assertEqual(response.response_model, "gpt-test-snapshot")
        self.assertEqual(response.total_tokens, 5)
        self.assertNotIn(api_key, json.dumps(response.raw))
        self.assertNotIn(api_key, repr(client))
        self.assertNotIn(api_key, json.dumps(client.effective_config))

    def test_http_error_redacts_key(self) -> None:
        api_key = "sk-sensitive-value"
        client = OpenAICompatibleClient(
            api_key=api_key,
            provider="openai",
            profile="test",
            base_url="https://api.openai.com/v1",
            model="gpt-test",
            max_retries=0,
        )
        error = urllib.error.HTTPError(
            url="https://api.openai.com/v1/chat/completions",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=io.BytesIO(f"server echoed {api_key}".encode("utf-8")),
        )
        with mock.patch("src.llm_client.urllib.request.urlopen", side_effect=error):
            with self.assertRaises(RuntimeError) as raised:
                client.chat([{"role": "user", "content": "hello"}])
        self.assertNotIn(api_key, str(raised.exception))
        self.assertIn("[REDACTED]", str(raised.exception))

    def test_deepseek_profile_uses_unified_client_and_flattens_extra_body(self) -> None:
        client = build_client(
            _config(),
            role="agent",
            environ={"DEEPSEEK_API_KEY": "test-key"},
        )
        fake = _FakeResponse(
            {
                "model": "deepseek-v4-flash",
                "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            }
        )
        with mock.patch("src.llm_client.urllib.request.urlopen", return_value=fake) as urlopen:
            client.chat([{"role": "user", "content": "hello"}])

        body = json.loads(urlopen.call_args.args[0].data.decode("utf-8"))
        self.assertIsInstance(client, OpenAICompatibleClient)
        self.assertEqual(client.provider, "deepseek")
        self.assertEqual(body["thinking"], {"type": "disabled"})
        self.assertEqual(body["temperature"], 0.0)
        self.assertNotIn("extra_body", body)


class ConfigureScriptTests(unittest.TestCase):
    def test_configure_keys_writes_mode_600_without_printing_key(self) -> None:
        values = iter(["deepseek-secret", "openai-secret"])
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / ".secrets" / "model_keys.json"
            configured = configure_keys(_config(), path, prompt=lambda _: next(values))

            self.assertEqual(configured, ["deepseek", "openai"])
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["DEEPSEEK_API_KEY"], "deepseek-secret")
            self.assertEqual(payload["OPENAI_API_KEY"], "openai-secret")


if __name__ == "__main__":
    unittest.main()
