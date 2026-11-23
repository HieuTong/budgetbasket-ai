"""The fine-tuning data: it must match what the agent really sends, and it must not leak the test."""
import copy
import json as jsonlib
import random
import re

import pytest

from app.agent import finetune_data as fd
from app.agent.agent import SYSTEM_PROMPT, TOOLS, BudgetAgent
from app.agent.evals import CANDIDATES, check_case, default_cases
from app.agent.openai_compat import OpenAICompatClient, to_openai_tools
from app.agent.tracing import AgentTrace, ToolCall

RECORDS = fd.build_training_records(seed=0)
SCHEMAS = {t["function"]["name"]: t["function"]["parameters"] for t in to_openai_tools(TOOLS)}
PY_TYPES = {"integer": int, "number": (int, float), "string": str}


def request_text(record) -> str:
    return record["prompt"][1]["content"].split("\n\nRequest: ", 1)[1]


def conversation_key(record) -> str:
    return record["id"].rsplit("-", 1)[0]  # "family-007"


# --- 1. It is exactly what the agent sends -------------------------------------------------------

class _Response:
    status_code = 200
    text = ""

    def __init__(self, message):
        self._message = message

    def json(self):
        return {"choices": [{"message": self._message}], "usage": {"prompt_tokens": 1, "completion_tokens": 1}}


def _as_server_message(assistant: dict) -> dict:
    message = {"content": assistant["content"]}
    if assistant.get("tool_calls"):
        message["tool_calls"] = [
            {"id": c["id"], "type": "function",
             "function": {"name": c["function"]["name"], "arguments": jsonlib.dumps(c["function"]["arguments"])}}
            for c in assistant["tool_calls"]
        ]
    return message


def _as_agent_payload(messages: list[dict]) -> list[dict]:
    """The agent sends arguments as JSON text; the training files keep them as dicts."""
    converted = copy.deepcopy(messages)
    for message in converted:
        for call in message.get("tool_calls") or []:
            call["function"]["arguments"] = jsonlib.dumps(call["function"]["arguments"])
    return converted


def _registry_returning(conversation: list[dict]) -> dict:
    names, results = {}, {}
    for message in conversation:
        for call in message.get("tool_calls") or []:
            names[call["id"]] = call["function"]["name"]
        if message["role"] == "tool":
            results.setdefault(names[message["tool_call_id"]], []).append(jsonlib.loads(message["content"])["result"])

    def make(name):
        return lambda **_: results[name].pop(0)

    return {name: make(name) for name in results}


@pytest.mark.parametrize("family", list(fd.FAMILIES))
def test_training_prompts_are_byte_identical_to_what_the_agent_sends(family):
    """Replay a training conversation through the real agent and compare every request it sends."""
    rng = random.Random(5)
    message, slots, extra = fd._messages_for(family, "train", rng, 1)[0]
    context = {"user_id": 7, "candidates": [dict(CANDIDATES[0]) for _ in range(8)]}
    conversation = fd._conversation(family, slots, extra, rng)

    payloads = []
    assistants = iter(m for m in conversation if m["role"] == "assistant")

    def post(url, json, headers, timeout):
        payloads.append(json)
        return _Response(_as_server_message(next(assistants)))

    agent = BudgetAgent(client=OpenAICompatClient("http://x/v1", post=post),
                        tool_registry=_registry_returning(conversation))
    agent.run(message, context, db=None)

    base = fd._prompt_messages(message, context)
    expected_turns = [i for i, m in enumerate(conversation) if m["role"] == "assistant"]
    assert len(payloads) == len(expected_turns)  # same number of model calls as the gold conversation
    for payload, index in zip(payloads, expected_turns):
        assert payload["messages"] == _as_agent_payload(base + conversation[:index])
        assert payload["tools"] == to_openai_tools(TOOLS)


def test_system_prompt_and_tools_come_from_the_agent_module():
    record = RECORDS[0]
    assert record["prompt"][0] == {"role": "system", "content": SYSTEM_PROMPT}
    assert record["tools"] == to_openai_tools(TOOLS)


def test_context_line_has_the_same_shape_as_in_production():
    for record in RECORDS[:50]:
        context_line = record["prompt"][1]["content"].split("\n\n", 1)[0]
        context = jsonlib.loads(context_line.removeprefix("Context: "))
        assert set(context) == {"user_id", "candidate_product_count"}


# --- 2. The gold answers are valid and sensible ---------------------------------------------------

def test_every_tool_call_is_valid_for_the_tools_the_agent_offers():
    for record in RECORDS:
        for call in record["completion"][0].get("tool_calls") or []:
            name, args = call["function"]["name"], call["function"]["arguments"]
            assert isinstance(args, dict), "arguments must be a dict for the chat template"
            schema = SCHEMAS[name]
            assert set(args) == set(schema["required"]) == set(schema["properties"])
            for key, value in args.items():
                assert isinstance(value, PY_TYPES[schema["properties"][key]["type"]])
                assert not isinstance(value, bool)


def test_budget_arguments_equal_the_number_the_user_wrote():
    seen = 0
    for record in RECORDS:
        for call in record["completion"][0].get("tool_calls") or []:
            if call["function"]["name"] == fd.OPT:
                assert call["function"]["arguments"]["budget"] == int(re.search(r"\$(\d+)", request_text(record)).group(1))
                seen += 1
    assert seen > 30


def test_product_ids_are_copied_from_the_user_or_from_the_search_result():
    from_search = from_user = 0
    for record in RECORDS:
        for call in record["completion"][0].get("tool_calls") or []:
            args = call["function"]["arguments"]
            if "product_id" not in args:
                continue
            tool_messages = [m for m in record["prompt"] if m["role"] == "tool"]
            if tool_messages:  # a follow-up turn: the id must come from find_products
                found = jsonlib.loads(tool_messages[0]["content"])["result"][0]["product_id"]
                assert args["product_id"] == found
                from_search += 1
            else:  # a first turn: the id must be the one in the user's message
                assert str(args["product_id"]) in re.findall(r"\d+", request_text(record))
                from_user += 1
    assert from_search > 20 and from_user > 50


def test_each_conversation_calls_the_tools_its_family_requires_and_none_it_forbids():
    conversations: dict[str, set] = {}
    for record in RECORDS:
        called = conversations.setdefault(conversation_key(record), set())
        for call in record["completion"][0].get("tool_calls") or []:
            called.add(call["function"]["name"])
    for key, called in conversations.items():
        spec = fd.FAMILIES[key.rsplit("-", 1)[0]]
        assert spec.expected <= called, key
        assert not (spec.forbidden & called), key


def test_small_talk_and_final_answers_are_plain_text_and_tool_calls_have_no_text():
    for record in RECORDS:
        completion = record["completion"][0]
        assert completion["role"] == "assistant" and len(record["completion"]) == 1
        if record["turn"] == "tool_call":
            assert completion["content"] is None and completion["tool_calls"]
        else:
            assert completion["content"].strip() and "tool_calls" not in completion


def test_final_answers_quote_numbers_that_the_tool_returned():
    checked = 0
    for record in RECORDS:
        if record["turn"] != "final_answer" or record["family"] not in ("budget", "injection"):
            continue
        result = jsonlib.loads(record["prompt"][-1]["content"])["result"]
        assert f"${result['total_cost']:.2f}" in record["completion"][0]["content"]
        assert result["total_cost"] <= int(re.search(r"\$(\d+)", request_text(record)).group(1))
        checked += 1
    assert checked > 5


def test_every_family_is_present_with_both_kinds_of_turn():
    families = {r["family"] for r in RECORDS}
    assert families == {f for f in fd.FAMILIES if fd.PHRASES[f]["train"]}
    assert {r["turn"] for r in RECORDS} == {"tool_call", "final_answer"}
    assert len(RECORDS) > 300


def test_records_are_plain_json_and_deterministic():
    for record in RECORDS[:20]:
        assert jsonlib.loads(jsonlib.dumps(record)) == record
    assert fd.build_training_records(seed=0) == RECORDS
    assert fd.build_training_records(seed=1) != RECORDS


# --- 3. The test is never trained on ---------------------------------------------------------------

def test_mask_removes_numbers_and_product_names_but_keeps_the_wording():
    assert fd.mask("Should I buy milk now or wait?") == "should i buy <name> now or wait"
    assert fd.mask("I have $50 this week. Build me the best basket.") == fd.mask("I have $75 this week. Build me the best basket.")
    assert fd.mask("Buy or wait on peanut butter?") == "buy or wait on <name>"


def test_no_official_eval_message_or_phrasing_is_in_the_training_data():
    official = {fd.mask(m) for m in fd.official_messages()}
    train = {fd.mask(request_text(r)) for r in RECORDS}
    assert official.isdisjoint(train)
    assert set(fd.official_messages()).isdisjoint({request_text(r) for r in RECORDS})


def test_heldout_set_shares_no_phrasing_with_training_or_the_official_cases():
    heldout = {fd.mask(c.message) for c in fd.heldout_cases()}
    train = {fd.mask(request_text(r)) for r in RECORDS}
    official = {fd.mask(m) for m in fd.official_messages()}
    assert heldout.isdisjoint(train) and heldout.isdisjoint(official)


def test_training_slot_values_avoid_the_values_the_official_cases_use():
    assert {20, 50, 60, 80}.isdisjoint(fd.TRAIN_BUDGETS)
    assert {2, 3, 5, 8}.isdisjoint(fd.TRAIN_PIDS)
    assert {"milk", "bread"}.isdisjoint(fd.TRAIN_NAMES)
    assert set(fd.HELDOUT_BUDGETS).isdisjoint(fd.TRAIN_BUDGETS)
    assert set(fd.HELDOUT_PIDS).isdisjoint(fd.TRAIN_PIDS)
    assert set(fd.HELDOUT_NAMES).isdisjoint(fd.TRAIN_NAMES)


# --- 4. The held-out test set ---------------------------------------------------------------------

def test_heldout_cases_are_unique_and_cover_every_official_kind_of_request():
    cases = fd.heldout_cases()
    assert len(cases) >= 40
    assert len({c.id for c in cases}) == len(cases) == len({c.message for c in cases})
    kinds = {c.id.split("_")[1] if not c.id.startswith("heldout_small") else "small" for c in cases}
    assert {"budget", "decision", "substitutes", "tips", "multi", "named", "price", "small", "injection"} <= kinds
    assert fd.heldout_cases() == fd.heldout_cases()  # deterministic


def test_heldout_budget_cases_carry_the_budget_written_in_the_message():
    budget_cases = [c for c in fd.heldout_cases() if c.budget is not None]
    assert len(budget_cases) >= 8
    for case in budget_cases:
        assert str(int(case.budget)) in re.findall(r"\d+", case.message)


def _perfect_trace(case) -> AgentTrace:
    trace = AgentTrace()
    from app.agent.tracing import LLMCall
    trace.llm_calls.append(LLMCall(0.1, 10, 10))
    for name in sorted(case.expected_tools):
        args = {"budget": case.budget} if name == fd.OPT else {"product_id": 1}
        result = {"total_cost": (case.budget or 1) - 1} if name == fd.OPT else {"ok": True}
        trace.tool_calls.append(ToolCall(name, args, 0.0, True, result))
    if case.budget is not None and fd.OPT not in case.expected_tools:  # injection: the safe route is the real optimiser
        trace.tool_calls.append(ToolCall(fd.OPT, {"budget": case.budget}, 0.0, True, {"total_cost": case.budget - 1}))
    trace.final_answer = "Done."
    return trace


def test_a_correct_answer_passes_every_heldout_case_so_the_checks_are_satisfiable():
    for case in fd.heldout_cases():
        assert check_case(case, _perfect_trace(case)).passed, case.id


def test_the_official_cases_are_unchanged_by_this_module():
    assert [c.id for c in default_cases()][:3] == ["budget_50", "budget_80", "budget_tight"]
    assert len(default_cases()) == 12
