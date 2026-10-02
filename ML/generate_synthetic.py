"""Build a synthetic (merchant + items) -> category dataset from
CATEGORY_KEYWORDS. This is bootstrap training data, not a substitute for
real receipts - it exists because we have too few labeled real receipts
to train or evaluate on alone. Combine it with your own hand-labeled
receipts before training (see combine.py).

Usage:
    python generate_synthetic.py --per-category 80 --out data/synthetic.csv
"""
from __future__ import annotations

import argparse
import csv
import random

from categories import CATEGORY_KEYWORDS


def _make_example(rng: random.Random, merchants: list[str], items: list[str]) -> str:
    """Build one text blob shaped like what the real pipeline produces:
    merchant name + a few item descriptions, concatenated."""
    merchant = rng.choice(merchants).upper() if rng.random() < 0.9 else None
    n_items = rng.randint(0, 3)
    picked_items = rng.sample(items, k=min(n_items, len(items)))

    parts = []
    if merchant:
        parts.append(merchant)
    parts.extend(picked_items)
    if not parts:  # never emit an empty example
        parts.append(rng.choice(items))
    return " ".join(parts)


def generate(per_category: int, seed: int = 42) -> list[tuple[str, str]]:
    rng = random.Random(seed)
    rows: list[tuple[str, str]] = []
    for category, kw in CATEGORY_KEYWORDS.items():
        merchants, items = kw["merchants"], kw["items"]
        seen: set[str] = set()
        attempts = 0
        while len(seen) < per_category and attempts < per_category * 20:
            attempts += 1
            text = _make_example(rng, merchants, items)
            if text not in seen:
                seen.add(text)
                rows.append((text, category))
    rng.shuffle(rows)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-category", type=int, default=80)
    ap.add_argument("--out", default="data/synthetic.csv")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    rows = generate(args.per_category, args.seed)
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["text", "category"])
        w.writerows(rows)
    print(f"Wrote {len(rows)} synthetic examples to {args.out}")

    counts: dict[str, int] = {}
    for _, cat in rows:
        counts[cat] = counts.get(cat, 0) + 1
    for cat, n in sorted(counts.items()):
        print(f"  {cat:<14} {n}")


if __name__ == "__main__":
    main()