"""Compatibility imports for the former DeepSeek-only client module.

New code should import from :mod:`src.llm_client`. Existing imports continue to
work while gaining named DeepSeek/OpenAI profiles and safe credential loading.
"""

from .llm_client import (
    DEFAULT_SECRETS_PATH,
    DeepSeekClient,
    LLMResponse,
    MockLLMClient,
    OpenAICompatibleClient,
    build_client,
    format_profiles,
    list_profiles,
    load_secrets,
    resolve_api_key,
    resolve_profile,
)


__all__ = [
    "DEFAULT_SECRETS_PATH",
    "DeepSeekClient",
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
