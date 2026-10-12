from __future__ import annotations

import sys
from typing import Any

import httpx
from langchain_core.messages import HumanMessage
from langchain_core.exceptions import LangChainException
from openai import APIError

from app.agent.banking_agent import create_banking_agent
from app.agent.llm_factory import LLMFactoryError
from app.config import settings


def _selected_model() -> str:
    if settings.llm_provider.strip().lower() == "ollama":
        return settings.ollama_model
    return settings.openrouter_model


def _print_startup() -> None:
    print("Smart Banking Agent — training demo")
    print(f"Provider/model: {settings.llm_provider} / {_selected_model()}")
    print(f"FastAPI URL: {settings.banking_api_url}")
    print("Training demo only: eligibility is indicative; submission is not final loan approval.")
    print("Commands: help, clear, exit, quit")


def _assistant_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            str(part.get("text", "")) for part in content if isinstance(part, dict)
        )
    return str(content)


def main() -> None:
    _print_startup()
    try:
        agent = create_banking_agent()
    except (LLMFactoryError, ValueError) as exc:
        print(f"Model configuration error: {exc}", file=sys.stderr)
        if settings.llm_provider.strip().lower() == "openrouter":
            print("Set OPENROUTER_API_KEY in .env, or switch LLM_PROVIDER to ollama.", file=sys.stderr)
        return

    history: list[Any] = []
    while True:
        try:
            user_text = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            return

        command = user_text.lower()
        if command in {"exit", "quit"}:
            print("Goodbye.")
            return
        if command == "clear":
            history.clear()
            print("Conversation cleared. Start with your loan requirements.")
            continue
        if command == "help":
            print("Describe the loan you need. Commands: help, clear, exit, quit.")
            continue
        if not user_text:
            continue

        try:
            result = agent.invoke({"messages": [*history, HumanMessage(content=user_text)]})
            history = result["messages"]
            print(f"\nAssistant: {_assistant_text(history[-1].content)}")
        except (APIError, httpx.HTTPError, LangChainException, OSError, RuntimeError, TimeoutError, ValueError) as exc:
            provider = settings.llm_provider.strip().lower()
            if provider == "ollama":
                print(
                    "Ollama request failed. Start it with `ollama serve`, pull the model with "
                    f"`ollama pull {settings.ollama_model}`, run `ollama list`, and verify "
                    "OLLAMA_BASE_URL. Also ensure FastAPI is running.",
                    file=sys.stderr,
                )
            else:
                print(
                    "The model request failed. Verify OPENROUTER_API_KEY, OPENROUTER_MODEL, "
                    "and that FastAPI is running. No application was assumed submitted.",
                    file=sys.stderr,
                )
            print(f"Failure type: {type(exc).__name__}", file=sys.stderr)


if __name__ == "__main__":
    main()
