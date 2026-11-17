"""Benchmark the agent's model backend, then compare two backends side by side.

Measure one backend (the one selected by LLM_PROVIDER / LLM_BASE_URL / LLM_MODEL):

    LLM_PROVIDER=openai LLM_BASE_URL=http://localhost:8000/v1 LLM_MODEL=Qwen/Qwen2.5-1.5B-Instruct \\
    python scripts/benchmark_llm.py run --label qwen-vllm --json-out qwen.json

    LLM_PROVIDER=gemini GEMINI_API_KEY=... \\
    python scripts/benchmark_llm.py run --label gemini --json-out gemini.json

Then compare:

    python scripts/benchmark_llm.py compare gemini.json qwen.json

For a cost estimate set LLM_PRICE_INPUT_PER_M and LLM_PRICE_OUTPUT_PER_M (USD per million tokens)
for API models, and --gpu-usd-per-hour for a self-hosted model. Prices are never hard-coded.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent.benchmark import benchmark, compare  # noqa: E402


def _levels(text: str) -> tuple[int, ...]:
    levels = tuple(int(part) for part in text.split(",") if part.strip())
    if not levels or any(level < 1 for level in levels):
        raise argparse.ArgumentTypeError("use positive whole numbers, e.g. 1,4,16")
    return levels


def run_command(args) -> None:
    from app.agent.agent import BudgetAgent
    from app.agent.evals import stub_tools
    from app.core.config import settings

    if settings.LLM_PROVIDER == "openai":
        if not settings.LLM_BASE_URL:
            sys.exit("LLM_PROVIDER=openai needs LLM_BASE_URL, e.g. http://localhost:8000/v1")
    elif not settings.GEMINI_API_KEY:
        sys.exit("GEMINI_API_KEY is not set; the Gemini benchmark needs the real model.")

    label = args.label or f"{settings.LLM_PROVIDER}:{settings.LLM_MODEL}"
    print(f"Benchmarking {label} (provider {settings.LLM_PROVIDER}, model {settings.LLM_MODEL})")
    report = benchmark(
        BudgetAgent(tool_registry=stub_tools()),
        label=label,
        provider=settings.LLM_PROVIDER,
        model=settings.LLM_MODEL,
        repeats=args.repeats,
        concurrency_levels=args.concurrency,
        requests_per_level=args.requests,
        gpu_usd_per_hour=args.gpu_usd_per_hour,
    )
    Path(args.json_out).write_text(json.dumps(report, indent=2))
    print(f"\nSaved {args.json_out}\n")
    print("| concurrency | output tokens/s | requests/s | p50 (s) | p95 (s) | errors |")
    print("|---|---|---|---|---|---|")
    for level, row in report["load"].items():
        print(f"| {level} | {row['output_tokens_per_s']} | {row['requests_per_s']} | "
              f"{row['latency_p50_s']} | {row['latency_p95_s']} | {row['errors']} |")
    quality = report["quality"]
    print(f"\nQuality: pass rate {quality['pass_rate']}, budget violations {quality['budget_violations']}, "
          f"provider errors {quality['errors']}")


def compare_command(args) -> None:
    a = json.loads(Path(args.first).read_text())
    b = json.loads(Path(args.second).read_text())
    print(compare(a, b))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("run", help="measure the backend selected by the environment")
    run.add_argument("--json-out", required=True)
    run.add_argument("--label", help="name shown in the comparison table")
    run.add_argument("--repeats", type=int, default=3, help="sequential passes over the eval cases")
    run.add_argument("--concurrency", type=_levels, default=(1, 4, 16), help="comma-separated, e.g. 1,4,16")
    run.add_argument("--requests", type=int, default=24, help="requests per concurrency level")
    run.add_argument("--gpu-usd-per-hour", type=float, default=None,
                     help="what the GPU costs per hour (self-hosted models only)")
    run.set_defaults(func=run_command)

    cmp = commands.add_parser("compare", help="put two result files side by side")
    cmp.add_argument("first")
    cmp.add_argument("second")
    cmp.set_defaults(func=compare_command)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
