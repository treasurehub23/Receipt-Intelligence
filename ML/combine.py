"""Combine the synthetic dataset with your hand-labeled real receipts into
one training file. Keeps a 'source' column (synthetic/real) so you can
always split them back apart later - e.g. to hold real receipts out as
a pure test set instead of training on them.

Usage:
    python combine.py --synthetic data/synthetic.csv \
                       --real data/real_labeled.csv \
                       --out data/combined.csv
"""
from __future__ import annotations

import argparse
import csv


def load(path: str, source: str) -> list[dict]:
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            text = row["text"].strip()
            category = row["category"].strip().lower()
            if text and category:
                rows.append({"text": text, "category": category, "source": source})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", default="data/synthetic.csv")
    ap.add_argument("--real", default="data/real_labeled.csv")
    ap.add_argument("--out", default="data/combined.csv")
    args = ap.parse_args()

    rows = load(args.synthetic, "synthetic")
    try:
        real_rows = load(args.real, "real")
        rows.extend(real_rows)
        print(f"{len(real_rows)} real labeled receipts included")
    except FileNotFoundError:
        print(f"!! {args.real} not found yet - training on synthetic data only")

    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["text", "category", "source"])
        w.writeheader()
        w.writerows(rows)

    counts: dict[str, int] = {}
    for r in rows:
        counts[r["category"]] = counts.get(r["category"], 0) + 1
    print(f"\nWrote {len(rows)} total examples to {args.out}")
    for cat, n in sorted(counts.items()):
        print(f"  {cat:<14} {n}")


if __name__ == "__main__":
    main()