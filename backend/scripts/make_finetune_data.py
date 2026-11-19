"""Write the fine-tuning training set (JSONL) and show what is in it.

    python scripts/make_finetune_data.py --out train.jsonl

The held-out test set is built in code (`heldout_cases`) and run with
`python scripts/benchmark_llm.py run --cases heldout ...`, so it never needs a file.
"""
import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent.finetune_data import build_training_records, heldout_cases  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default="train.jsonl")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--per-family", type=int, default=40, help="distinct requests per kind of request")
    args = parser.parse_args()

    records = build_training_records(seed=args.seed, per_family=args.per_family)
    with open(args.out, "w") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")

    by_family = collections.Counter(r["family"] for r in records)
    by_turn = collections.Counter(r["turn"] for r in records)
    print(f"Wrote {len(records)} training records to {args.out}")
    print("  by turn:  ", dict(by_turn))
    print("  by family:", dict(sorted(by_family.items())))
    print(f"Held-out test cases (built in code, never trained on): {len(heldout_cases())}")

    sample = next(r for r in records if r["family"] == "named_decision" and r["turn"] == "tool_call"
                  and len(r["prompt"]) > 2)
    print("\nOne example, a follow-up turn (the model must copy the product_id from the tool result):")
    for message in sample["prompt"][1:]:
        print(f"  {message['role']:9} {str(message.get('content') or message.get('tool_calls'))[:150]}")
    print(f"  -> TARGET  {sample['completion'][0]['tool_calls']}")


if __name__ == "__main__":
    main()
