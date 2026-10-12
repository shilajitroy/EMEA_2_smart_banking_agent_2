import app.agent.banking_agent as banking_agent
from app.agent.tools import (
    prepare_loan_application,
    retrieve_account_details,
    verify_loan_eligibility,
)


def test_agent_is_built_once_with_exact_five_banking_tools(monkeypatch):
    captured = {}

    def fake_create_agent(**kwargs):
        captured.update(kwargs)
        return "agent"

    monkeypatch.setattr(banking_agent, "get_chat_model", lambda: "mock-model")
    monkeypatch.setattr(banking_agent, "create_agent", fake_create_agent)

    result = banking_agent.create_banking_agent()
    assert result == "agent"
    assert captured["model"] == "mock-model"
    assert {tool.name for tool in captured["tools"]} == {
        "calculate_loan_emi",
        "verify_loan_eligibility",
        "retrieve_account_details",
        "prepare_loan_application",
        "submit_loan_application",
    }
    assert len(captured["tools"]) == 5


def test_eligibility_tool_derives_emi_and_cannot_accept_model_supplied_zero():
    result = verify_loan_eligibility.invoke(
        {
            "loan_amount": 500000,
            "monthly_salary": 60000,
            "existing_monthly_emi": 5000,
            "tenure_months": 36,
            "annual_interest_rate": 12,
        }
    )
    assert result["success"] is True
    assert result["eligible"] is True
    assert float(result["proposed_monthly_emi"]) == 16607.15
    assert float(result["foir_percent"]) == 36.01
    assert "proposed_monthly_emi" not in verify_loan_eligibility.args


def test_account_tool_rejects_invented_customer_id_before_http_call():
    result = retrieve_account_details.invoke({"customer_id": "unknown"})
    assert result["success"] is False
    assert "do not invent one" in result["error"]


def test_prepare_tool_rejects_invented_customer_id_before_http_call():
    result = prepare_loan_application.invoke(
        {
            "customer_id": "unknown",
            "loan_amount": 500000,
            "tenure_months": 36,
            "annual_interest_rate": 12,
            "calculated_emi": 16607.15,
            "monthly_salary": 60000,
            "existing_emi": 5000,
            "foir_percent": 36.01,
            "eligible": True,
        }
    )
    assert result["success"] is False
    assert "do not invent one" in result["error"]
