"""Run the agent evaluation against the real Gemini API (needs GEMINI_API_KEY).

    python scripts/run_agent_eval.py --json-out agent_eval.json

Optional cost estimate: set LLM_PRICE_INPUT_PER_M and LLM_PRICE_OUTPUT_PER_M (USD per million tokens)
to your model's current prices. Exits with code 1 if the release gate fails, so CI can block on it.
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent.agent import BudgetAgent  # noqa: E402
from app.agent.evals import run_eval, stub_tools, summarise, verdict  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--json-out")
    ap.add_argument("--min-pass-rate", type=float, default=0.9)
    ap.add_argument("--pause", type=float, default=0.0, help="seconds between cases, to respect rate limits")
    ap.add_argument("--retry-errors-after", type=float, default=None,
                    help="re-run cases that hit provider errors once, after this many seconds")
    a = ap.parse_args()
    if not os.getenv("GEMINI_API_KEY"):
        sys.exit("GEMINI_API_KEY is not set; the live evaluation needs the real model.")

    print(f"Model: {os.getenv('LLM_MODEL', '(config default)')}")
    results = run_eval(BudgetAgent(tool_registry=stub_tools()), pause_s=a.pause,
                       retry_errors_after_s=a.retry_errors_after)
    summary = summarise(results)
    print("| case | passed | tools called | latency (s) | tokens | failures |")
    print("|---|---|---|---|---|---|")
    for r in results:
        t = r.trace
        print(f"| {r.case_id} | {'yes' if r.passed else 'NO'} | {', '.join(t.tools_called) or '-'} | "
              f"{t.total_latency_s} | {t.prompt_tokens + t.output_tokens} | {'; '.join(r.failures) or '-'} |")
    print("\n" + json.dumps({k: v for k, v in summary.items() if k != "failed_cases"}, indent=2))
    if a.json_out:
        Path(a.json_out).write_text(json.dumps(
            {"summary": summary, "traces": {r.case_id: r.trace.to_dict() for r in results}}, indent=2))
    status, problems = verdict(summary, a.min_pass_rate)
    if status == "fail":
        print("\nGATE FAILED: " + "; ".join(problems))
        sys.exit(1)
    if status == "inconclusive":
        # A provider outage is not a product failure: warn loudly, but don't fail the build.
        print("\n::warning::Evaluation inconclusive: " + "; ".join(problems))
        sys.exit(0)
    print("\nGate passed.")
