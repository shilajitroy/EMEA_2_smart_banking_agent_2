from __future__ import annotations

import asyncio
import logging
import secrets
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel, Field

from app.agent.banking_agent import create_banking_agent
from app.dependencies import get_current_token
from app.exceptions import AppError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = Field(default=None, min_length=20, max_length=128)


class ChatResponse(BaseModel):
    conversation_id: str
    reply: str


def _agent(request: Request) -> Any:
    agent = getattr(request.app.state, "banking_agent", None)
    if agent is None:
        agent = create_banking_agent()
        request.app.state.banking_agent = agent
    return agent


def _reply_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = [
            str(part["text"])
            for part in content
            if isinstance(part, dict) and isinstance(part.get("text"), str)
        ]
        return "\n".join(text_parts)
    return str(content)


@router.post("", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    request: Request,
    _: str = Depends(get_current_token),
) -> ChatResponse:
    sessions: dict[str, dict[str, Any]] = request.app.state.chat_sessions
    conversation_id = payload.conversation_id
    if conversation_id is None:
        conversation_id = secrets.token_urlsafe(24)
        session: dict[str, Any] = {"messages": [], "lock": asyncio.Lock()}
        sessions[conversation_id] = session
    else:
        session = sessions.get(conversation_id)
        if session is None:
            raise AppError(404, "CONVERSATION_NOT_FOUND", "Start a new conversation and try again.")

    async with session["lock"]:
        messages = session["messages"]
        try:
            result = await run_in_threadpool(
                _agent(request).invoke,
                {"messages": [*messages, HumanMessage(content=payload.message.strip())]},
            )
            updated_messages = result.get("messages")
            if not isinstance(updated_messages, list) or not updated_messages:
                raise TypeError("Agent returned no conversation messages.")
            last_message = updated_messages[-1]
            if not isinstance(last_message, AIMessage):
                raise TypeError("Agent response did not end with an assistant message.")
            reply = _reply_text(last_message.content).strip()
            if not reply:
                raise ValueError("Agent returned an empty response.")
            session["messages"] = updated_messages
            return ChatResponse(conversation_id=conversation_id, reply=reply)
        except Exception as exc:
            logger.error("Browser chat agent failed (%s).", type(exc).__name__)
            raise AppError(
                502,
                "AGENT_UNAVAILABLE",
                "The assistant could not complete that message. Check the local model and try again.",
            ) from exc
