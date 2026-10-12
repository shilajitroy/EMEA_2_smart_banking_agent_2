from __future__ import annotations

from typing import Any

from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from app.config import settings


class LLMFactoryError(RuntimeError):
    """Raised when the selected chat model cannot be configured."""


def get_chat_model() -> Any:
    provider = settings.llm_provider.strip().lower()
    if provider == "openrouter":
        if not settings.openrouter_api_key:
            raise LLMFactoryError("OPENROUTER_API_KEY is required when LLM_PROVIDER=openrouter.")
        return ChatOpenAI(
            model=settings.openrouter_model,
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            temperature=0,
        )
    if provider == "ollama":
        if not settings.ollama_base_url:
            raise LLMFactoryError("OLLAMA_BASE_URL is required when LLM_PROVIDER=ollama.")
        return ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=0,
        )
    raise LLMFactoryError(f"Unsupported LLM_PROVIDER value: {settings.llm_provider!r}.")


build_llm = get_chat_model
