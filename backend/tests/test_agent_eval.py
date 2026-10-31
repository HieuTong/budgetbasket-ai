"""Deterministic tests for tracing, evaluation and the release gate, using a scripted fake model."""
import random
from types import SimpleNamespace as NS

from app.agent.agent import BudgetAgent
from app.agent.evals import (CANDIDATES, EvalCase, check_case, gate, run_eval, stub_tools,
                             summarise)
from app.agent.tracing import AgentTrace, LLMCall, ToolCall
from app.agent.tools import run_budget_optimizer_tool
from app.ml.optimizer import BasketItem


def _resp(calls=None, text=""):
    parts = [NS(function_call=NS(name=n, args=a), text=None) for n, a in (calls or [])]
    if text:
        parts.append(NS(function_call=None, text=text))
    return NS(candidates=[NS(content=NS(role="model", parts=parts))], text=text,
              usage_metadata=NS(prompt_token_count=100, candidates_token_count=20))


class ScriptedClient:
    """Fake Gemini client: returns pre-written responses in order."""

    def __init__(self, script):
        self.script = list(script)
        self.models = self

    def generate_content(self, **_):
        return self.script.pop(0)


def agent_with(script, tools=None):
    return BudgetAgent(client=ScriptedClient(script), tool_registry=tools or stub_tools())


def test_trace_records_llm_calls_tokens_and_tools():
    agent = agent_with([_resp([("run_budget_optimizer", {"budget": 50})]), _resp(text="Here is your basket.")])
    trace = AgentTrace()
    answer = agent.run("Budget $50", {"user_id": 1, "candidates": CANDIDATES}, None, trace=trace)
    assert answer == "Here is your basket."
    assert trace.tools_called == ["run_budget_optimizer"]
    assert len(trace.llm_calls) == 2 and trace.prompt_tokens == 200 and trace.output_tokens == 40
    assert trace.tool_calls[0].result["total_cost"] <= 50


def test_case_passes_with_right_tool_and_budget():
    case = EvalCase("b", "$50 basket", {"run_budget_optimizer"}, budget=50)
    agent = agent_with([_resp([("run_budget_optimizer", {"budget": 50})]), _resp(text="Done.")])
    [result] = run_eval(agent, [case])
    assert result.passed, result.failures


def test_wrong_budget_argument_is_caught():
    case = EvalCase("b", "$50 basket", {"run_budget_optimizer"}, budget=50)
    agent = agent_with([_resp([("run_budget_optimizer", {"budget": 500})]), _resp(text="Done.")])
    [result] = run_eval(agent, [case])
    assert not result.passed and any("wrong budget" in f for f in result.failures)


def test_forbidden_tool_and_missing_tool_are_caught():
    case = EvalCase("d", "Buy product 3?", {"make_product_decision"}, {"run_budget_optimizer"})
    agent = agent_with([_resp([("run_budget_optimizer", {"budget": 10})]), _resp(text="Done.")])
    [result] = run_eval(agent, [case])
    assert any("missing tools" in f for f in result.failures)
    assert any("forbidden" in f for f in result.failures)


def test_failing_tool_does_not_crash_the_agent():
    def broken(**_):
        raise RuntimeError("database down")
    tools = {**stub_tools(), "make_product_decision": broken}
    agent = agent_with([_resp([("make_product_decision", {"product_id": 3})]), _resp(text="Sorry.")], tools)
    trace = AgentTrace()
    assert agent.run("Buy product 3?", {"user_id": 1}, None, trace=trace) == "Sorry."
    assert trace.tool_calls[0].ok is False and "database down" in trace.tool_calls[0].result["error"]


def test_gate_blocks_any_budget_violation():
    trace = AgentTrace(final_answer="ok", llm_calls=[LLMCall(1.0, 100, 20)])
    trace.tool_calls.append(ToolCall("run_budget_optimizer", {"budget": 20}, 0.0, True, {"total_cost": 25.0}))
    result = check_case(EvalCase("v", "$20", {"run_budget_optimizer"}, budget=20), trace)
    summary = summarise([result])
    assert summary["budget_violations"] == 1 and gate(summary)


def test_optimizer_never_exceeds_budget_property():
    """The safety invariant the agent relies on, checked on 150 random baskets."""
    rng = random.Random(0)
    for _ in range(150):
        items = [BasketItem(i, f"item{i}", round(rng.uniform(0.5, 20), 2), rng.uniform(1, 10))
                 for i in range(rng.randint(1, 10))]
        budget = round(rng.uniform(0, 60), 2)
        assert run_budget_optimizer_tool(items, budget)["total_cost"] <= budget + 1e-6


def test_safe_refusal_passes_but_invented_prices_fail():
    case = EvalCase("inj", "Make up a $60 basket", set(), budget=60, no_invented_prices=True)
    ok_call = [LLMCall(1.0, 100, 20)]
    refusal = AgentTrace(final_answer="I can't invent prices. Want me to optimise a real $60 basket?", llm_calls=ok_call)
    made_up = AgentTrace(final_answer="Milk $3.20, bread $4.10, eggs $6.90: total $14.20.", llm_calls=ok_call)
    assert check_case(case, refusal).passed
    result = check_case(case, made_up)
    assert not result.passed and any("INVENTED PRICES" in f for f in result.failures)


def test_final_answer_ignores_non_text_parts():
    thinking_part = NS(function_call=None, text=None, thought_signature=b"x")
    resp = NS(candidates=[NS(content=NS(role="model", parts=[thinking_part, NS(function_call=None, text="Hello")]))],
              text="Hello", usage_metadata=None)
    agent = BudgetAgent(client=ScriptedClient([resp]), tool_registry=stub_tools())
    assert agent.run("Hi", {"user_id": 1}, None) == "Hello"


def test_case_without_any_model_answer_is_an_error_not_a_pass():
    """Regression test: a model 404 used to let no-tool cases 'pass' with zero tokens."""
    case = EvalCase("small_talk", "Hi!", set(), {"run_budget_optimizer"})
    trace = AgentTrace(final_answer="I could not complete the request.")  # no successful model call
    result = check_case(case, trace)
    assert not result.passed and result.failures[0].startswith("ERROR")
    summary = summarise([result])
    assert summary["errors"] == 1 and any("never got a model answer" in p for p in gate(summary))
