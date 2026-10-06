"""Tests the agent loop and API with a fake LLM client (no API key or network needed)."""
from types import SimpleNamespace as NS

import app as app_module
from agent import ProctorPalAgent


class FakeClient:
    """Returns a tool call on the first request, then a spoken answer."""

    def __init__(self):
        self.calls = 0
        self.messages = self

    def create(self, **kwargs):
        self.calls += 1
        if self.calls == 1:
            return NS(stop_reason="tool_use", content=[
                NS(type="tool_use", id="t1", name="search_policies",
                   input={"query": "what ID do I need"})])
        last = kwargs["messages"][-1]["content"][0]
        assert last["type"] == "tool_result" and "photo ID" in last["content"]
        return NS(stop_reason="end_turn",
                  content=[NS(type="text", text="Bring a valid photo ID, like your student ID.")])


def test_agent_runs_tool_then_answers():
    agent = ProctorPalAgent(client=FakeClient())
    reply, history, events = agent.respond([{"role": "user", "content": "What ID do I need?"}])
    assert "photo ID" in reply
    assert events[0]["tool"] == "search_policies" and events[0]["output"]["found"]
    assert len(history) == 4


def test_chat_endpoint(monkeypatch):
    monkeypatch.setattr(app_module, "_agent", ProctorPalAgent(client=FakeClient()))
    client = app_module.app.test_client()
    res = client.post("/api/chat", json={"session_id": "abc", "message": "What ID do I need?"})
    body = res.get_json()
    assert res.status_code == 200 and "photo ID" in body["reply"]
    assert body["tool_calls"][0]["tool"] == "search_policies"


def test_chat_requires_fields():
    res = app_module.app.test_client().post("/api/chat", json={})
    assert res.status_code == 400


def test_health_index_and_bookings():
    c = app_module.app.test_client()
    assert c.get("/health").get_json()["status"] == "ok"
    assert b"ProctorPal" in c.get("/").data
    assert c.get("/api/bookings").get_json() == {"bookings": []}
