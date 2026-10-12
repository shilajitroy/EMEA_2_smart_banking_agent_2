from __future__ import annotations

from typing import Any

from langchain.agents import create_agent

from app.agent.llm_factory import get_chat_model
from app.agent.prompts import BANKING_AGENT_PROMPT
from app.agent.tools import (
    calculate_loan_emi,
    prepare_loan_application,
    retrieve_account_details,
    submit_loan_application,
    verify_loan_eligibility,
)


def create_banking_agent() -> Any:
    """Build the project's one LangChain agent and its five banking tools."""
    return create_agent(
        model=get_chat_model(),
        tools=[
            calculate_loan_emi,
            verify_loan_eligibility,
            retrieve_account_details,
            prepare_loan_application,
            submit_loan_application,
        ],
        system_prompt=BANKING_AGENT_PROMPT,
    )
