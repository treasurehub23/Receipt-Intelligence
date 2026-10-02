"""Turn your real OCR text files into labeled training examples.

Reads every .txt file in --ocr-dir (same raw OCR text your eval harness
uses), runs it through parse_receipt(), shows you the merchant and
items, and asks you to pick a category. Writes to --out in the exact
format combine.py expects (text,category), using the SAME
receipt_to_text() function classify() will use later - so training and
inference features never drift apart.

Usage:
    python label_real_receipts.py --ocr-dir ../sample_eval/ocr --out data/real_labeled.csv

Safe to re-run: it skips receipts already in --out (by id), and you can
stop any time (Ctrl+C) - whatever you've labeled so far is saved.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # reach the parsing/ package

from parsing import parse_receipt
from features import parsed_receipt_to_text
from categories import CATEGORIES


def already_labeled(out_path: Path) -> set[str]:
    if not out_path.exists():
        return set()
    with open(out_path, newline="", encoding="utf-8") as fh:
        return {row["id"] for row in csv.DictReader(fh) if "id" in row}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ocr-dir", default="receipts_ocr", help="directory containing OCR text files")
    ap.add_argument("--out", default="data/real_labeled.csv")
    ap.add_argument("--default-currency", default="NGN")
    args = ap.parse_args()

    out_path = Path(args.out)
    done = already_labeled(out_path)
    is_new_file = not out_path.exists()

    files = sorted(Path(args.ocr_dir).glob("*.txt"))
    todo = [f for f in files if f.stem not in done]
    print(f"{len(files)} receipts found, {len(done)} already labeled, {len(todo)} to go.\n")

    menu = "  ".join(f"{i+1}={c}" for i, c in enumerate(CATEGORIES))

    with open(out_path, "a", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        if is_new_file:
            writer.writerow(["id", "text", "category"])

        for f in todo:
            raw_text = f.read_text(encoding="utf-8")
            parsed = parse_receipt(raw_text, default_currency=args.default_currency)
            text = parsed_receipt_to_text(parsed)

            print("=" * 60)
            print(f"[{f.stem}]  merchant={parsed.merchant!r}  total={parsed.total}")
            print(f"items: {[li.description for li in parsed.line_items]}")
            print(f"feature text -> {text!r}")
            print(menu)
            choice = input("category (number, 's' to skip, 'q' to quit): ").strip().lower()

            if choice == "q":
                break
            if choice == "s" or not choice:
                continue
            try:
                category = CATEGORIES[int(choice) - 1]
            except (ValueError, IndexError):
                print("  not a valid choice, skipping this one")
                continue

            writer.writerow([f.stem, text, category])
            fh.flush()
            print(f"  -> labeled {category}")

    print(f"\nDone. Labels saved to {out_path}")


if __name__ == "__main__":
    main()