"""Benchmark an LLM backend through the real agent: quality, latency and throughput.

One run measures ONE backend (chosen by LLM_PROVIDER / LLM_BASE_URL / LLM_MODEL) and writes a
JSON file. `compare` then lines two such files up in a table, so Gemini and a self-hosted
open model are judged on exactly the same cases, the same checks and the same load.

What is measured, and why it is measured this way:
- A warm-up request runs first and is not counted. The first request to a model server is
  usually slower (caches, kernels, connections), and it would distort the numbers.
- Quality is a sequential run, repeated several times. Models are not perfectly repeatable,
  so one pass proves little.
- Latency is reported as p50 and p95, not an average. A few slow requests hide inside an
  average, but users feel them.
- Load runs the same requests at several concurrency levels. Throughput is the total output
  tokens the server produced per second of wall-clock time, across all requests.
- Provider errors (timeouts, 429, 503) are counted separately and excluded from quality and
  latency, so an outage is never mistaken for a bad model.
"""
from __future__ import annotations

import datetime
import statistics
import time
from concurrent.futures import ThreadPoolExecutor

from app.agent.evals import CANDIDATES, CaseResult, EvalCase, check_case, default_cases
from app.agent.tracing import AgentTrace


def percentile(values: list[float], p: float) -> float | None:
    """Nearest-rank percentile, the same method the agent evaluation uses."""
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(round(p / 100 * (len(ordered) - 1))))]


def _is_error(result: CaseResult) -> bool:
    return any(f.startswith("ERROR") for f in result.failures)


def run_one(agent, case: EvalCase) -> CaseResult:
    trace = AgentTrace()
    try:
        agent.run(case.message, {"user_id": 1, "candidates": CANDIDATES}, db=None, trace=trace)
    except Exception as exc:  # one bad request must not kill a whole benchmark run
        trace.error = f"{type(exc).__name__}: {exc}"[:200]
    return check_case(case, trace)


def build_workload(cases: list[EvalCase], n: int) -> list[EvalCase]:
    """n requests, cycling through the cases so every level sees the same mix."""
    return [cases[i % len(cases)] for i in range(n)]


def run_workload(agent, workload: list[EvalCase], concurrency: int) -> tuple[list[CaseResult], float]:
    """Run the requests with `concurrency` in flight at once. Returns results and wall-clock seconds."""
    started = time.perf_counter()
    if concurrency <= 1:
        results = [run_one(agent, case) for case in workload]
    else:
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            results = list(pool.map(lambda case: run_one(agent, case), workload))
    return results, time.perf_counter() - started


def _r(value, digits=3):
    return None if value is None else round(value, digits)


def summarise_run(results: list[CaseResult], wall_s: float, gpu_usd_per_hour: float | None = None) -> dict:
    answered = [r for r in results if not _is_error(r)]
    latencies = [r.trace.total_latency_s for r in answered]
    output_tokens = sum(r.trace.output_tokens for r in answered)
    costs = [r.trace.cost_usd() for r in answered]

    per_case: dict[str, dict] = {}
    for r in answered:
        entry = per_case.setdefault(r.case_id, {"passed": 0, "total": 0})
        entry["total"] += 1
        entry["passed"] += int(r.passed)

    tokens_per_s = output_tokens / wall_s if wall_s > 0 else 0.0
    summary = {
        "requests": len(results),
        "answered": len(answered),
        "errors": len(results) - len(answered),
        "pass_rate": _r(sum(r.passed for r in answered) / len(answered)) if answered else None,
        "budget_violations": sum(any("BUDGET VIOLATION" in f for f in r.failures) for r in answered),
        "latency_p50_s": _r(percentile(latencies, 50)),
        "latency_p95_s": _r(percentile(latencies, 95)),
        "latency_max_s": _r(max(latencies)) if latencies else None,
        "wall_s": _r(wall_s),
        "requests_per_s": _r(len(answered) / wall_s) if wall_s > 0 else None,
        "output_tokens_per_s": _r(tokens_per_s, 1),
        "avg_llm_calls": _r(statistics.mean(len(r.trace.llm_calls) for r in answered), 2) if answered else None,
        "avg_prompt_tokens": _r(statistics.mean(r.trace.prompt_tokens for r in answered), 1) if answered else None,
        "avg_output_tokens": _r(statistics.mean(r.trace.output_tokens for r in answered), 1) if answered else None,
        "avg_cost_usd": _r(statistics.mean(costs), 6) if answered and all(c is not None for c in costs) else None,
        "per_case": per_case,
    }
    if gpu_usd_per_hour is not None and tokens_per_s > 0:
        # Self-hosted cost: what the GPU costs per hour, spread over the tokens it produced.
        summary["gpu_usd_per_million_output_tokens"] = _r(gpu_usd_per_hour / 3600 / tokens_per_s * 1_000_000, 4)
    return summary


def benchmark(
    agent,
    label: str,
    provider: str,
    model: str,
    cases: list[EvalCase] | None = None,
    repeats: int = 3,
    concurrency_levels: tuple[int, ...] = (1, 4, 16),
    requests_per_level: int = 24,
    gpu_usd_per_hour: float | None = None,
    progress=print,
) -> dict:
    cases = cases or default_cases()

    progress("Warm-up request (not counted)...")
    run_one(agent, cases[0])

    progress(f"Quality: {repeats} sequential passes over {len(cases)} cases...")
    quality_workload = [case for _ in range(repeats) for case in cases]
    results, wall = run_workload(agent, quality_workload, 1)
    quality = summarise_run(results, wall, gpu_usd_per_hour)

    load = {}
    for level in concurrency_levels:
        progress(f"Load: {requests_per_level} requests, {level} at a time...")
        results, wall = run_workload(agent, build_workload(cases, requests_per_level), level)
        load[str(level)] = summarise_run(results, wall, gpu_usd_per_hour)

    return {
        "meta": {
            "label": label,
            "provider": provider,
            "model": model,
            "repeats": repeats,
            "concurrency_levels": list(concurrency_levels),
            "requests_per_level": requests_per_level,
            "gpu_usd_per_hour": gpu_usd_per_hour,
            "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        },
        "quality": quality,
        "load": load,
    }


def _fmt(value) -> str:
    return "-" if value is None else str(value)


def compare(a: dict, b: dict) -> str:
    """A Markdown table with both runs side by side."""
    label_a, label_b = a["meta"]["label"], b["meta"]["label"]
    rows = [
        ("**Quality (sequential)**", "", ""),
        ("pass rate (answered)", _fmt(a["quality"]["pass_rate"]), _fmt(b["quality"]["pass_rate"])),
        ("budget violations", _fmt(a["quality"]["budget_violations"]), _fmt(b["quality"]["budget_violations"])),
        ("provider errors", _fmt(a["quality"]["errors"]), _fmt(b["quality"]["errors"])),
        ("latency p50 (s)", _fmt(a["quality"]["latency_p50_s"]), _fmt(b["quality"]["latency_p50_s"])),
        ("latency p95 (s)", _fmt(a["quality"]["latency_p95_s"]), _fmt(b["quality"]["latency_p95_s"])),
        ("avg tokens per request (in / out)",
         f"{_fmt(a['quality']['avg_prompt_tokens'])} / {_fmt(a['quality']['avg_output_tokens'])}",
         f"{_fmt(b['quality']['avg_prompt_tokens'])} / {_fmt(b['quality']['avg_output_tokens'])}"),
        ("avg cost per request (USD)", _fmt(a["quality"]["avg_cost_usd"]), _fmt(b["quality"]["avg_cost_usd"])),
    ]
    levels = sorted({int(k) for k in a["load"]} | {int(k) for k in b["load"]})
    for level in levels:
        la, lb = a["load"].get(str(level), {}), b["load"].get(str(level), {})
        rows.append((f"**Load: {level} at a time**", "", ""))
        for name, key in (("output tokens/s", "output_tokens_per_s"), ("requests/s", "requests_per_s"),
                          ("latency p50 (s)", "latency_p50_s"), ("latency p95 (s)", "latency_p95_s"),
                          ("provider errors", "errors"),
                          ("GPU $ per 1M output tokens", "gpu_usd_per_million_output_tokens")):
            rows.append((name, _fmt(la.get(key)), _fmt(lb.get(key))))
    lines = [f"| metric | {label_a} | {label_b} |", "|---|---|---|"]
    lines += [f"| {name} | {va} | {vb} |" for name, va, vb in rows]
    return "\n".join(lines)
