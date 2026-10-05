
from __future__ import annotations

import argparse

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

# One Pipeline per model: TF-IDF is refit INSIDE each fold, not once on the
# whole dataset beforehand. Fitting the vectorizer first would leak each
# fold's vocabulary into the others - every fold needs its own vectorizer.
df = pd.read_csv("data/combined.csv")

MODELS: dict[str, tuple[Pipeline, dict]] = {
    "LogisticRegression": (
        Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2))),
            ("clf", LogisticRegression(max_iter=1000)),
        ]),
        {"clf__C": [0.1, 1, 10], "clf__class_weight": [None, "balanced"]},
    ),
    "MultinomialNB": (
        Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2))),
            ("clf", MultinomialNB()),
        ]),
        {"clf__alpha": [0.1, 0.5, 1.0]},
    ),
    "LinearSVC": (
        Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2))),
            ("clf", LinearSVC(max_iter=5000)),
        ]),
        {"clf__C": [0.1, 1, 10], "clf__class_weight": [None, "balanced"]},
    ),
    "RandomForest": (
        Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2))),
            ("clf", RandomForestClassifier(random_state=42)),
        ]),
        {
            "clf__n_estimators": [100, 300],
            "clf__max_depth": [None, 20],
            "clf__class_weight": [None, "balanced"],
        },
    ),
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/synthetic.csv")
    ap.add_argument("--folds", type=int, default=5)
    args = ap.parse_args()

    df = pd.read_csv(args.data)
    X, y = df["text"], df["category"]

    # SAME folds for every model - this is what makes the comparison fair.
    # shuffle=True + a fixed random_state: the split is randomized once,
    # then identical across every model/grid-search call below.
    cv = StratifiedKFold(n_splits=args.folds, shuffle=True, random_state=42)

    print(f"Dataset: {args.data}  ({len(df)} rows, {y.nunique()} categories)")
    print(f"Folds: {args.folds} (stratified, same split reused for every model)\n")

    results = []
    for name, (pipeline, param_grid) in MODELS.items():
        grid = GridSearchCV(
            pipeline, param_grid,
            cv=cv, scoring="f1_macro", n_jobs=-1,
        )
        grid.fit(X, y)

        best_idx = grid.best_index_
        mean_f1 = grid.cv_results_["mean_test_score"][best_idx]
        std_f1 = grid.cv_results_["std_test_score"][best_idx]
        results.append((name, mean_f1, std_f1, grid.best_params_))

        print(f"{name:<20} macro-F1 = {mean_f1:.3f} ± {std_f1:.3f}   best params: {grid.best_params_}")

    print("\nRanked by macro-F1:")
    for name, mean_f1, std_f1, _ in sorted(results, key=lambda r: -r[1]):
        print(f"  {name:<20} {mean_f1:.3f} ± {std_f1:.3f}")


if __name__ == "__main__":
    main()