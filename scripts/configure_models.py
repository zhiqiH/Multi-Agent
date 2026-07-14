from __future__ import annotations
import argparse
import getpass
import json
import os
import sys
import tempfile
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.llm_client import DEFAULT_SECRETS_PATH, format_profiles, load_secrets  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Store model API keys locally using hidden prompts. Keys are never accepted as CLI arguments.")
    parser.add_argument("--config", default="configs/model_config.json", help="Model profile configuration file.")
    parser.add_argument("--secrets",default=str(DEFAULT_SECRETS_PATH.relative_to(PROJECT_ROOT)),help="Local secrets JSON file (default: .secrets/model_keys.json).",)
    parser.add_argument("--provider",action="append",default=[],help="Configure only this provider; repeat or use comma-separated names. Empty means all providers.",)
    parser.add_argument("--list-profiles", action="store_true", help="List non-secret model profiles and exit.")
    return parser.parse_args()


def configure_keys(
    config: Mapping[str, Any],
    secrets_path: Path,
    *,
    providers: Sequence[str] = (),
    prompt: Callable[[str], str] = getpass.getpass,
) -> list[str]:
    """Prompt for provider keys and persist only non-empty replacements."""

    targets = _key_targets(config)
    requested = {provider.strip().lower() for provider in providers if provider.strip()}
    available = {provider for provider, _ in targets}
    unknown = sorted(requested - available)
    if unknown:
        raise ValueError(f"Unknown providers: {unknown}. Available: {sorted(available)}")
    if requested:
        targets = [(provider, env_name) for provider, env_name in targets if provider in requested]

    existing = load_secrets(secrets_path)
    updated = dict(existing)
    configured: list[str] = []
    for provider, env_name in targets:
        has_stored_key = bool(existing.get(env_name, "").strip())
        suffix = "press Enter to keep the stored key" if has_stored_key else "press Enter to skip"
        value = prompt(f"{provider} API key for {env_name} ({suffix}): ")
        if value.strip():
            updated[env_name] = value.strip()
            configured.append(provider)

    if configured or secrets_path.exists():
        _write_secrets(secrets_path, updated)
    return configured


def _key_targets(config: Mapping[str, Any]) -> list[tuple[str, str]]:
    profiles = config.get("profiles")
    targets: set[tuple[str, str]] = set()
    if isinstance(profiles, Mapping) and profiles:
        for profile in profiles.values():
            if not isinstance(profile, Mapping):
                raise ValueError("Each model profile must be a JSON object")
            provider = str(profile.get("provider") or "").strip().lower()
            env_name = str(profile.get("api_key_env") or _default_key_env(provider)).strip()
            if provider and env_name:
                targets.add((provider, env_name))
    else:
        provider = str(config.get("provider") or "deepseek").strip().lower()
        env_name = str(config.get("api_key_env") or _default_key_env(provider)).strip()
        if provider and env_name:
            targets.add((provider, env_name))
    if not targets:
        raise ValueError("No provider/api_key_env pairs were found in the model configuration")
    return sorted(targets)


def _default_key_env(provider: str) -> str:
    return {
        "deepseek": "DEEPSEEK_API_KEY",
        "openai": "OPENAI_API_KEY",
    }.get(provider, "")


def _write_secrets(path: Path, values: Mapping[str, str]) -> None:
    if path.is_symlink():
        raise ValueError(f"Refusing to replace symlinked secrets file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(prefix=".model_keys.", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        os.fchmod(file_descriptor, 0o600)
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as handle:
            json.dump(dict(sorted(values.items())), handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary_path, path)
        os.chmod(path, 0o600)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def _project_path(raw: str) -> Path:
    path = Path(raw).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path


def main() -> int:
    args = parse_args()
    config_path = _project_path(args.config)
    try:
        with config_path.open("r", encoding="utf-8") as handle:
            config = json.load(handle)
        if not isinstance(config, dict):
            raise ValueError("Model configuration must be a JSON object")
        if args.list_profiles:
            print(format_profiles(config))
            return 0

        providers = [
            item.strip().lower()
            for raw_group in args.provider
            for item in raw_group.split(",")
            if item.strip()
        ]
        secrets_path = _project_path(args.secrets)
        configured = configure_keys(config, secrets_path, providers=providers)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if configured:
        print(
            f"Saved {len(configured)} provider key(s) to {secrets_path} with file permissions 600. "
            "Environment variables take precedence at runtime."
        )
    else:
        print("No keys changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())