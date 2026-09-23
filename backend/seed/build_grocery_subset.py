"""Build a small, deterministic development subset from the Australian grocery snapshot.

The raw Kaggle CSV stays outside the repository. This utility creates a roughly
10,000-row development file so Phase 1A can use the real dataset without
running the ORM importer against all 488k observations.

Sampling is stratified by Category × state, with a small minimum per stratum
and proportional allocation for the remaining rows. A fixed seed makes the
result reproducible.
"""

from __future__ import annotations

import argparse
import csv
import random
from collections import Counter, defaultdict
from pathlib import Path


DEFAULT_TARGET_ROWS = 10_000
DEFAULT_SEED = 42
STRATUM_MINIMUM = 10
STRATA = ("Category", "state")


def count_strata(csv_path: Path) -> tuple[list[str], Counter[tuple[str, str]]]:
    fieldnames: list[str] = []
    counts: Counter[tuple[str, str]] = Counter()

    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []

        missing = set(STRATA) - set(fieldnames)
        if missing:
            raise ValueError(f"Missing required columns: {sorted(missing)}")

        for row in reader:
            key = (row["Category"].strip(), row["state"].strip())
            counts[key] += 1

    return fieldnames, counts


def allocate_quotas(
    counts: Counter[tuple[str, str]],
    target_rows: int,
) -> dict[tuple[str, str], int]:
    if target_rows <= 0:
        raise ValueError("target_rows must be positive")

    total = sum(counts.values())
    if target_rows >= total:
        return dict(counts)

    # Give every non-empty stratum a small guaranteed representation first.
    quotas = {
        key: min(count, STRATUM_MINIMUM)
        for key, count in counts.items()
    }
    remaining = target_rows - sum(quotas.values())

    if remaining <= 0:
        # The target is smaller than the minimum allocation. Trim
        # deterministically from the largest strata.
        while sum(quotas.values()) > target_rows:
            key = max(
                quotas,
                key=lambda item: (quotas[item], item),
            )
            quotas[key] -= 1
        return quotas

    # Allocate the remainder proportionally to stratum size using largest
    # remainder rounding, which keeps the final total exactly at target_rows.
    fractional: list[tuple[float, tuple[str, str]]] = []
    allocated = 0

    for key, count in counts.items():
        available = count - quotas[key]
        share = remaining * available / max(1, total - sum(quotas.values()))
        whole = min(available, int(share))
        quotas[key] += whole
        allocated += whole
        fractional.append((share - whole, key))

    for _, key in sorted(fractional, reverse=True):
        if allocated >= remaining:
            break
        if quotas[key] < counts[key]:
            quotas[key] += 1
            allocated += 1

    return quotas


def reservoir_sample(
    csv_path: Path,
    quotas: dict[tuple[str, str], int],
    seed: int,
) -> dict[int, dict[str, str]]:
    rng = random.Random(seed)
    samples: dict[tuple[str, str], list[tuple[int, dict[str, str]]]] = defaultdict(list)
    seen: Counter[tuple[str, str]] = Counter()

    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)

        for row_number, row in enumerate(reader, start=2):
            key = (row["Category"].strip(), row["state"].strip())
            quota = quotas.get(key, 0)

            if quota == 0:
                continue

            seen[key] += 1
            bucket = samples[key]

            if len(bucket) < quota:
                bucket.append((row_number, row))
                continue

            replacement = rng.randrange(seen[key])
            if replacement < quota:
                bucket[replacement] = (row_number, row)

    selected: dict[int, dict[str, str]] = {}
    for bucket in samples.values():
        for row_number, row in bucket:
            selected[row_number] = row

    return selected


def build_subset(
    input_path: Path,
    output_path: Path,
    target_rows: int = DEFAULT_TARGET_ROWS,
    seed: int = DEFAULT_SEED,
) -> None:
    fieldnames, counts = count_strata(input_path)
    quotas = allocate_quotas(counts, target_rows)
    selected = reservoir_sample(input_path, quotas, seed)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()

        for row_number in sorted(selected):
            writer.writerow(selected[row_number])

    category_counts = Counter(row["Category"] for row in selected.values())
    state_counts = Counter(row["state"] for row in selected.values())

    print(f"Input rows:      {sum(counts.values()):,}")
    print(f"Target rows:     {target_rows:,}")
    print(f"Selected rows:   {len(selected):,}")
    print(f"Seed:            {seed}")
    print("\nCategories:")
    for name, count in category_counts.most_common():
        print(f"  {name}: {count:,}")
    print("\nStates:")
    for name, count in state_counts.most_common():
        print(f"  {name}: {count:,}")
    print(f"\nWrote: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_csv", type=Path)
    parser.add_argument("output_csv", type=Path)
    parser.add_argument(
        "--rows",
        type=int,
        default=DEFAULT_TARGET_ROWS,
        help=f"Target number of observations (default: {DEFAULT_TARGET_ROWS})",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Random seed (default: {DEFAULT_SEED})",
    )
    args = parser.parse_args()

    build_subset(
        args.input_csv,
        args.output_csv,
        target_rows=args.rows,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
