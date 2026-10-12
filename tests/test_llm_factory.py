import pytest

import app.agent.llm_factory as factory
from app.config import settings


def test_openrouter_model_receives_configured_settings(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "openrouter")
    monkeypatch.setattr(settings, "openrouter_api_key", "unit-test-key")
    monkeypatch.setattr(settings, "openrouter_model", "openai/test-model")
    monkeypatch.setattr(factory, "ChatOpenAI", lambda **kwargs: kwargs)

    model = factory.get_chat_model()
    assert model == {
        "model": "openai/test-model",
        "api_key": "unit-test-key",
        "base_url": "https://openrouter.ai/api/v1",
        "temperature": 0,
    }


def test_openrouter_requires_api_key(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "openrouter")
    monkeypatch.setattr(settings, "openrouter_api_key", "")
    with pytest.raises(factory.LLMFactoryError, match="OPENROUTER_API_KEY is required"):
        factory.get_chat_model()


def test_ollama_model_receives_configured_settings(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "ollama")
    monkeypatch.setattr(settings, "ollama_model", "llama3.1:8b")
    monkeypatch.setattr(settings, "ollama_base_url", "http://localhost:11434")
    monkeypatch.setattr(factory, "ChatOllama", lambda **kwargs: kwargs)

    assert factory.get_chat_model() == {
        "model": "llama3.1:8b",
        "base_url": "http://localhost:11434",
        "temperature": 0,
    }


def test_unsupported_provider_is_rejected(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "unrecognized")
    with pytest.raises(factory.LLMFactoryError, match="Unsupported LLM_PROVIDER"):
        factory.get_chat_model()
