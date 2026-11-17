"""The benchmark harness, tested with a fake agent: no network, no GPU, no real timing."""
import threading

import pytest

from app.agent.benchmark import (benchmark, build_workload, compare, percentile, run_one,
                                 run_workload, summarise_run)
from app.agent.evals import default_cases
from app.agent.tracing import AgentTrace, LLMCall, ToolCall

CASES_BY_MESSAGE = {case.message: case for case in default_cases()}


class FakeAgent:
    """Behaves correctly for every eval case, and can be told to fail some requests."""

    def __init__(self, fail_messages=(), latency_s=1.0, output_tokens=100):
        self.fail_messages = set(fail_messages)
        self.latency_s = latency_s
        self.output_tokens = output_tokens
        self.calls = 0
        self._lock = threading.Lock()

    def run(self, message, context, db, trace: AgentTrace, **_):
        with self._lock:
            self.calls += 1
        trace.total_latency_s = self.latency_s
        if message in self.fail_messages:
            trace.error = "503 from LLM server"  # no llm_calls: the model never answered
            return "The AI service is temporarily unavailable."
        case = CASES_BY_MESSAGE[message]
        trace.llm_calls.append(LLMCall(self.latency_s, 50, self.output_tokens))
        for name in sorted(case.expected_tools):
            args = {"budget": case.budget} if name == "run_budget_optimizer" else {"product_id": 1}
            result = {"total_cost": (case.budget or 1) - 1} if name == "run_budget_optimizer" else {"ok": True}
            trace.tool_calls.append(ToolCall(name, args, 0.01, True, result))
        trace.final_answer = "Done."
        return trace.final_answer


class CrashingAgent:
    def run(self, *args, **kwargs):
        raise ConnectionError("server unreachable")


# --- Percentiles --------------------------------------------------------------------------

def test_percentile_uses_nearest_rank_and_handles_empty():
    values = [5, 1, 4, 2, 3]
    assert percentile(values, 50) == 3
    assert percentile(values, 95) == 5
    assert percentile(values, 0) == 1
    assert percentile([], 50) is None
    assert percentile([7], 95) == 7


# --- One request and one workload ---------------------------------------------------------

def test_a_crashing_agent_becomes_an_error_result_not_an_exception():
    result = run_one(CrashingAgent(), default_cases()[0])
    assert not result.passed
    assert result.failures[0].startswith("ERROR")


def test_workload_cycles_through_the_cases():
    cases = default_cases()
    workload = build_workload(cases, len(cases) + 2)
    assert [c.id for c in workload[-2:]] == [cases[0].id, cases[1].id]
    assert len(workload) == len(cases) + 2


@pytest.mark.parametrize("concurrency", [1, 6])
def test_every_request_runs_exactly_once_at_any_concurrency(concurrency):
    agent = FakeAgent()
    workload = build_workload(default_cases(), 30)
    results, wall = run_workload(agent, workload, concurrency)
    assert agent.calls == 30
    assert [r.case_id for r in results] == [c.id for c in workload]  # order is preserved
    assert wall >= 0


# --- Summaries ----------------------------------------------------------------------------

def test_summary_computes_throughput_from_wall_time():
    results, _ = run_workload(FakeAgent(output_tokens=100), build_workload(default_cases(), 20), 1)
    summary = summarise_run(results, wall_s=10.0)
    assert summary["requests"] == 20 and summary["errors"] == 0
    assert summary["pass_rate"] == 1.0
    assert summary["output_tokens_per_s"] == 200.0  # 20 requests x 100 tokens / 10 s
    assert summary["requests_per_s"] == 2.0
    assert summary["latency_p50_s"] == 1.0 and summary["latency_p95_s"] == 1.0
    assert summary["avg_prompt_tokens"] == 50.0 and summary["avg_output_tokens"] == 100.0


def test_errors_are_counted_apart_and_excluded_from_quality_and_latency():
    failing = default_cases()[0].message
    agent = FakeAgent(fail_messages=[failing], latency_s=2.0)
    results, _ = run_workload(agent, build_workload(default_cases(), 24), 1)
    summary = summarise_run(results, wall_s=12.0)
    assert summary["errors"] == 2 and summary["answered"] == 22
    assert summary["pass_rate"] == 1.0  # the outage is not blamed on the model
    # The case that always failed has no answered runs, so it is absent, not counted as a model failure.
    assert default_cases()[0].id not in summary["per_case"]
    assert summary["output_tokens_per_s"] == pytest.approx(22 * 100 / 12.0, abs=0.1)


def test_summary_survives_a_run_where_nothing_answered():
    results, _ = run_workload(CrashingAgent(), build_workload(default_cases(), 4), 1)
    summary = summarise_run(results, wall_s=1.0)
    assert summary["answered"] == 0 and summary["errors"] == 4
    assert summary["pass_rate"] is None and summary["latency_p50_s"] is None
    assert summary["output_tokens_per_s"] == 0.0


def test_gpu_cost_per_million_tokens_comes_from_the_hourly_price():
    results, _ = run_workload(FakeAgent(output_tokens=100), build_workload(default_cases(), 36), 1)
    # 3,600 output tokens in 3.6 s = 1,000 tokens/s. At $3.60/hour the GPU costs $0.001 per second,
    # which is $0.001 / 1,000 tokens = $1.00 per million tokens.
    summary = summarise_run(results, wall_s=3.6, gpu_usd_per_hour=3.6)
    assert summary["gpu_usd_per_million_output_tokens"] == 1.0
    assert "gpu_usd_per_million_output_tokens" not in summarise_run(results, wall_s=3.6)


def test_api_cost_uses_prices_from_the_environment(monkeypatch):
    monkeypatch.setenv("LLM_PRICE_INPUT_PER_M", "1.0")
    monkeypatch.setenv("LLM_PRICE_OUTPUT_PER_M", "2.0")
    results, _ = run_workload(FakeAgent(output_tokens=100), build_workload(default_cases(), 12), 1)
    summary = summarise_run(results, wall_s=1.0)
    assert summary["avg_cost_usd"] == pytest.approx((50 * 1.0 + 100 * 2.0) / 1_000_000, abs=1e-9)


# --- The whole benchmark ------------------------------------------------------------------

def test_benchmark_warms_up_first_and_does_not_count_it():
    agent = FakeAgent()
    report = benchmark(agent, "fake", "openai", "toy-model", repeats=2,
                       concurrency_levels=(1, 3), requests_per_level=12, progress=lambda *_: None)
    cases = len(default_cases())
    assert agent.calls == 1 + 2 * cases + 12 + 12  # warm-up + quality + two load levels
    assert report["quality"]["requests"] == 2 * cases
    assert set(report["load"]) == {"1", "3"}
    assert report["load"]["3"]["requests"] == 12
    assert report["meta"]["label"] == "fake" and report["meta"]["model"] == "toy-model"


def test_compare_lines_two_runs_up_side_by_side():
    def run(label, tokens):
        return benchmark(FakeAgent(output_tokens=tokens), label, "openai", "m", repeats=1,
                         concurrency_levels=(1, 4), requests_per_level=8, progress=lambda *_: None)

    table = compare(run("gemini", 100), run("qwen", 200))
    lines = table.splitlines()
    assert lines[0] == "| metric | gemini | qwen |"
    assert any(line.startswith("| **Load: 4 at a time**") for line in lines)
    assert any(line.startswith("| output tokens/s |") for line in lines)
    assert "pass rate (answered)" in table


def test_compare_shows_the_gpu_cost_when_it_was_measured():
    with_gpu = benchmark(FakeAgent(), "qwen", "openai", "m", repeats=1, concurrency_levels=(2,),
                         requests_per_level=8, gpu_usd_per_hour=0.5, progress=lambda *_: None)
    without = benchmark(FakeAgent(), "gemini", "gemini", "m", repeats=1, concurrency_levels=(2,),
                        requests_per_level=8, progress=lambda *_: None)
    row = next(line for line in compare(without, with_gpu).splitlines() if line.startswith("| GPU $ per 1M"))
    cells = [c.strip() for c in row.strip("|").split("|")]
    assert cells[1] == "-"          # the API model has no GPU cost
    assert float(cells[2]) > 0      # the self-hosted model does
