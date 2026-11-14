"""The OpenAI-compatible adapter, tested with a fake HTTP layer: no network, no GPU."""
import json

import pytest
from google.genai import types

import app.agent.agent as agent_module
from app.agent.agent import TOOLS, BudgetAgent, build_llm_client
from app.agent.evals import CANDIDATES, stub_tools
from app.agent.openai_compat import (OpenAICompatClient, from_openai_response,
                                     to_openai_messages, to_openai_tools)
from app.agent.tracing import AgentTrace
from app.core.config import settings


class FakeResponse:
    def __init__(self, body, status_code=200):
        self._body = body
        self.status_code = status_code
        self.text = json.dumps(body)

    def json(self):
        return self._body


class FakeServer:
    """Stands in for `requests.post`: records each request and replies from a script."""

    def __init__(self, script):
        self.script = list(script)
        self.requests = []

    def __call__(self, url, json=None, headers=None, timeout=None):
        self.requests.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        reply = self.script.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def text_reply(text):
    return FakeResponse({
        "choices": [{"message": {"role": "assistant", "content": text}}],
        "usage": {"prompt_tokens": 50, "completion_tokens": 7},
    })


def tool_reply(*calls):
    return FakeResponse({
        "choices": [{"message": {"role": "assistant", "content": None, "tool_calls": [
            {"id": f"server_{i}", "type": "function",
             "function": {"name": name, "arguments": arguments}}
            for i, (name, arguments) in enumerate(calls)
        ]}}],
        "usage": {"prompt_tokens": 120, "completion_tokens": 15},
    })


def agent_for(server):
    client = OpenAICompatClient("http://llm.test/v1", api_key="k", post=server)
    return BudgetAgent(client=client, tool_registry=stub_tools())


# --- Translating requests -------------------------------------------------------------------

def test_tool_schemas_become_json_schema_with_lowercase_types():
    tools = to_openai_tools(TOOLS)
    by_name = {tool["function"]["name"]: tool["function"] for tool in tools}

    assert set(by_name) == {
        "run_budget_optimizer", "find_substitutes", "make_product_decision",
        "find_products", "explain_price_trend", "retrieve_savings_tips",
    }
    optimiser = by_name["run_budget_optimizer"]["parameters"]
    assert optimiser["type"] == "object"
    assert optimiser["properties"]["budget"]["type"] == "number"
    assert optimiser["required"] == ["budget"]
    assert by_name["find_products"]["parameters"]["properties"]["query"]["type"] == "string"
    assert "OBJECT" not in json.dumps(tools)


def test_conversation_is_translated_with_matching_tool_call_ids():
    contents = [
        types.Content(role="user", parts=[types.Part(text="Earlier question")]),
        types.Content(role="model", parts=[types.Part(text="Earlier answer")]),
        types.Content(role="user", parts=[types.Part(text="Decide on 3 and find swaps")]),
        types.Content(role="model", parts=[
            types.Part(function_call=types.FunctionCall(name="make_product_decision", args={"product_id": 3})),
            types.Part(function_call=types.FunctionCall(name="find_substitutes", args={"product_id": 3})),
        ]),
        types.Content(role="user", parts=[
            types.Part.from_function_response(name="make_product_decision", response={"result": {"decision": "BUY"}}),
            types.Part.from_function_response(name="find_substitutes", response={"result": []}),
        ]),
    ]

    messages = to_openai_messages(contents, "You are a test.")

    assert [m["role"] for m in messages] == ["system", "user", "assistant", "user", "assistant", "tool", "tool"]
    assert messages[0]["content"] == "You are a test."

    calls = messages[4]["tool_calls"]
    assert [c["function"]["name"] for c in calls] == ["make_product_decision", "find_substitutes"]
    assert json.loads(calls[0]["function"]["arguments"]) == {"product_id": 3}
    # Every tool result must point at the call that asked for it, or the server rejects the request.
    assert [m["tool_call_id"] for m in messages[5:]] == [c["id"] for c in calls]
    assert json.loads(messages[5]["content"]) == {"result": {"decision": "BUY"}}


def test_same_tool_called_twice_keeps_results_in_order():
    contents = [
        types.Content(role="model", parts=[
            types.Part(function_call=types.FunctionCall(name="find_products", args={"query": "milk"})),
            types.Part(function_call=types.FunctionCall(name="find_products", args={"query": "bread"})),
        ]),
        types.Content(role="user", parts=[
            types.Part.from_function_response(name="find_products", response={"result": "milk result"}),
            types.Part.from_function_response(name="find_products", response={"result": "bread result"}),
        ]),
    ]
    messages = to_openai_messages(contents, None)
    ids = [c["id"] for c in messages[0]["tool_calls"]]
    assert len(set(ids)) == 2
    assert [(m["tool_call_id"], json.loads(m["content"])["result"]) for m in messages[1:]] == [
        (ids[0], "milk result"), (ids[1], "bread result"),
    ]


# --- Translating responses ------------------------------------------------------------------

def test_text_response_and_token_usage_are_read():
    response = from_openai_response(text_reply("Hello").json())
    parts = response.candidates[0].content.parts
    assert [p.text for p in parts] == ["Hello"]
    assert response.usage_metadata.prompt_token_count == 50
    assert response.usage_metadata.candidates_token_count == 7


def test_tool_call_arguments_are_parsed_from_json_text():
    response = from_openai_response(tool_reply(("run_budget_optimizer", '{"budget": 40}')).json())
    call = response.candidates[0].content.parts[0].function_call
    assert call.name == "run_budget_optimizer"
    assert dict(call.args) == {"budget": 40}


@pytest.mark.parametrize("broken", ['{"budget": 40', "not json", "[1, 2]", ""])
def test_broken_tool_arguments_do_not_crash(broken):
    response = from_openai_response(tool_reply(("run_budget_optimizer", broken)).json())
    assert dict(response.candidates[0].content.parts[0].function_call.args or {}) == {}


# --- The whole agent loop through the adapter ---------------------------------------------

def test_agent_runs_a_tool_and_answers_through_an_openai_compatible_server():
    server = FakeServer([
        tool_reply(("run_budget_optimizer", '{"budget": 30}')),
        text_reply("Here is your basket."),
    ])
    trace = AgentTrace()

    answer = agent_for(server).run(
        "Build a basket for $30", {"user_id": 1, "candidates": CANDIDATES}, None, trace=trace,
    )

    assert answer == "Here is your basket."
    assert trace.tools_called == ["run_budget_optimizer"]
    assert trace.tool_calls[0].ok
    assert trace.tool_calls[0].result["total_cost"] <= 30
    assert trace.prompt_tokens == 170 and trace.output_tokens == 22

    first, second = server.requests
    assert first["url"] == "http://llm.test/v1/chat/completions"
    assert first["headers"]["Authorization"] == "Bearer k"
    assert first["json"]["model"] == settings.LLM_MODEL
    assert first["json"]["tool_choice"] == "auto"
    assert len(first["json"]["tools"]) == 6
    # The second request carries the tool call and its result back to the model.
    assert [m["role"] for m in second["json"]["messages"]] == ["system", "user", "assistant", "tool"]
    tool_message = second["json"]["messages"][3]
    assert tool_message["tool_call_id"] == second["json"]["messages"][2]["tool_calls"][0]["id"]
    assert "total_cost" in tool_message["content"]


def test_broken_arguments_are_reported_to_the_model_not_raised():
    server = FakeServer([
        tool_reply(("run_budget_optimizer", "{broken")),
        text_reply("Sorry, I could not build that basket."),
    ])
    trace = AgentTrace()

    answer = agent_for(server).run("Basket for $30", {"user_id": 1, "candidates": CANDIDATES}, None, trace=trace)

    assert answer == "Sorry, I could not build that basket."
    assert trace.tool_calls[0].ok is False
    assert "error" in server.requests[1]["json"]["messages"][3]["content"]


def test_503_is_retried_and_429_is_not(monkeypatch):
    monkeypatch.setattr(agent_module.time, "sleep", lambda seconds: None)

    recovering = FakeServer([FakeResponse({"error": "busy"}, 503), text_reply("Recovered.")])
    assert agent_for(recovering).run("hi", {"user_id": 1}, None) == "Recovered."
    assert len(recovering.requests) == 2

    out_of_quota = FakeServer([FakeResponse({"error": "quota"}, 429), text_reply("never sent")])
    assert "quota" in agent_for(out_of_quota).run("hi", {"user_id": 1}, None).lower()
    assert len(out_of_quota.requests) == 1


def test_timeout_is_retried(monkeypatch):
    import requests
    monkeypatch.setattr(agent_module.time, "sleep", lambda seconds: None)
    server = FakeServer([requests.exceptions.ReadTimeout("slow"), text_reply("Back.")])
    assert agent_for(server).run("hi", {"user_id": 1}, None) == "Back."


# --- Choosing the provider from configuration ----------------------------------------------

def test_provider_is_chosen_by_configuration(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "openai")
    monkeypatch.setattr(settings, "LLM_BASE_URL", "http://localhost:8000/v1")
    assert isinstance(build_llm_client(), OpenAICompatClient)


def test_openai_provider_without_a_url_fails_loudly(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "openai")
    monkeypatch.setattr(settings, "LLM_BASE_URL", "")
    with pytest.raises(RuntimeError):
        build_llm_client()


def test_unknown_provider_fails_loudly(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "something-else")
    with pytest.raises(RuntimeError):
        build_llm_client()
