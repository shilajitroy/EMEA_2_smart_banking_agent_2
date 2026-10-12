from __future__ import annotations

from pydantic import BaseModel, Field


class AgentConversationRequest(BaseModel):
    customer_id: str
    message: str


class AgentConversationResponse(BaseModel):
    response: str
    pending_application_id: str | None = None
    requires_confirmation: bool = False
