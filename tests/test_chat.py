from langchain_core.messages import AIMessage, HumanMessage, ToolMessage


class FakeAgent:
    def __init__(self):
        self.received_histories = []

    def invoke(self, state):
        messages = state["messages"]
        self.received_histories.append(messages)
        return {
            "messages": [
                *messages,
                ToolMessage(content="private-confirmation-token", tool_call_id="test-call"),
                AIMessage(content=f"Assistant reply {len(self.received_histories)}"),
            ]
        }


def test_browser_homepage_is_served(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Smart Banking Agent" in response.text
    assert 'id="chat-form"' in response.text
    assert "/api/chat" in response.text


def test_chat_requires_authentication(client):
    response = client.post("/api/chat", json={"message": "hello"})
    assert response.status_code == 401


def test_chat_keeps_history_on_server_and_does_not_return_tool_tokens(client, auth_headers):
    fake_agent = FakeAgent()
    client.app.state.banking_agent = fake_agent

    first = client.post(
        "/api/chat", headers=auth_headers, json={"message": "I need a loan."}
    )
    assert first.status_code == 200, first.text
    first_body = first.json()
    assert first_body["reply"] == "Assistant reply 1"
    assert "private-confirmation-token" not in first.text

    second = client.post(
        "/api/chat",
        headers=auth_headers,
        json={
            "message": "My customer ID is CUST1001.",
            "conversation_id": first_body["conversation_id"],
        },
    )
    assert second.status_code == 200, second.text
    assert second.json()["reply"] == "Assistant reply 2"
    assert len(fake_agent.received_histories) == 2
    assert any(
        isinstance(message, HumanMessage) and message.content == "I need a loan."
        for message in fake_agent.received_histories[1]
    )


def test_chat_rejects_unknown_conversation_id(client, auth_headers):
    response = client.post(
        "/api/chat",
        headers=auth_headers,
        json={"message": "continue", "conversation_id": "x" * 32},
    )
    assert response.status_code == 404
