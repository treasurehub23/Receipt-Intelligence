
from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path

from categories import CATEGORIES


# These templates increase variation, but do not add new meaning.
# Real item synonyms are still needed for stronger generalization.
ITEM_TEMPLATES = [
    "{item}",
    "purchase of {item}",
    "{item} purchase",
    "payment for {item}",
    "{item} payment",
    "one {item}",
    "purchase {item}",
    "{item} x1",
]


def normalize(text: str) -> str:
    """Normalize whitespace and case for consistent deduplication."""
    return " ".join(text.upper().split())


def generate_item_variations(
    rng: random.Random,
    items: list[str],
    target: int,
) -> list[str]:
    """Create a bounded set of unique text variations for one category."""
    candidates: set[str] = set()

    for item in items:
        item = normalize(item)

        for template in ITEM_TEMPLATES:
            candidates.add(normalize(template.format(item=item)))

    candidates_list = sorted(candidates)
    rng.shuffle(candidates_list)

    return candidates_list[:target]


def generate(
    per_category: int = 200,
    seed: int = 42,
) -> list[tuple[str, str]]:
    """Generate (text, category) examples without conflicting exact labels."""
    if per_category < 1:
        raise ValueError("per_category must be at least 1")

    rng = random.Random(seed)
    rows: list[tuple[str, str]] = []
    assigned_labels: dict[str, str] = {}

    for category, details in CATEGORIES.items():
        items = details["items"]

        candidates = generate_item_variations(
            rng=rng,
            items=items,
            target=per_category * 3,
        )

        category_count = 0

        for text in candidates:
            existing_category = assigned_labels.get(text)

            # Never assign identical text to different categories.
            if existing_category is not None:
                if existing_category != category:
                    continue
                continue

            assigned_labels[text] = category
            rows.append((text, category))
            category_count += 1

            if category_count >= per_category:
                break

        if category_count < per_category:
            print(
                f"Warning: {category} produced {category_count} "
                f"unique examples; requested {per_category}. "
                "Add more meaningful item descriptions or synonyms."
            )

    rng.shuffle(rows)
    return rows


def save_csv(
    rows: list[tuple[str, str]],
    output_path: str = "ML/synthetic_expenses.csv",
) -> None:
    """Save generated examples to a CSV file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["text", "category"])
        writer.writerows(rows)

    print(f"Saved {len(rows)} examples to {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-category", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--output",
        default="ML/synthetic_expenses.csv",
    )
    args = parser.parse_args()

    data = generate(
        per_category=args.per_category,
        seed=args.seed,
    )
    save_csv(data, args.output)

    print(f"Total examples: {len(data)}")
    print(f"Categories represented: {len(set(label for _, label in data))}")
