"""Combine site-level calibration summaries for a synthetic diabetes risk model."""

import argparse
from pathlib import Path

import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from study_fixture import HORIZON, build_cohort, generate, write_json

FEATURES = ("age_years", "latest_a1c", "a1c_change")
EDGES = (0.0, 0.1, 0.2, 0.3, 0.5, 1.0)
FIELDS = ("n", "events", "score_sum", "squared_error_sum")


def site_summary(labels, scores):
    """Compute the fields passed to the simulated evaluator."""
    labels, scores = np.asarray(labels), np.asarray(scores, dtype=float)
    if labels.ndim != 1 or labels.shape != scores.shape:
        raise ValueError("Expected matching one-dimensional label and score arrays")
    if not np.all(np.isin(labels, (0, 1))) or not np.all((0 <= scores) & (scores <= 1)):
        raise ValueError("Expected binary labels and probabilities in [0, 1]")
    bins = np.minimum(np.searchsorted(EDGES, scores, side="right") - 1, len(EDGES) - 2)
    payload = []
    for index in range(len(EDGES) - 1):
        selected = bins == index
        y, p = labels[selected], scores[selected]
        payload.append({
            "n": int(selected.sum()),
            "events": int(y.sum()),
            "score_sum": float(p.sum()),
            "squared_error_sum": float(np.square(p - y).sum()),
        })
    return payload


def combine(summaries):
    """Add each site's sufficient statistics using the common bin layout."""
    return [
        {field: sum(summary[index][field] for summary in summaries) for field in FIELDS}
        for index in range(len(EDGES) - 1)
    ]


def describe(summary):
    """Derive patient-weighted metrics from aggregate fields alone."""
    totals = {field: sum(bucket[field] for bucket in summary) for field in FIELDS}
    n = totals["n"]
    if not n:
        return {"n": 0, "events": 0, "bins": []}
    mean_score = totals["score_sum"] / n
    rate = totals["events"] / n
    bins = []
    for index, bucket in enumerate(summary):
        size = bucket["n"]
        if size:
            bins.append({
                "range": list(EDGES[index:index + 2]),
                "n": size,
                "events": bucket["events"],
                "observed_rate": bucket["events"] / size,
                "mean_score": bucket["score_sum"] / size,
            })
    return {
        "n": n, "events": totals["events"], "observed_rate": rate,
        "mean_score": mean_score, "calibration_gap": mean_score - rate,
        "brier": totals["squared_error_sum"] / n, "bins": bins,
    }


def matrix(rows):
    return np.asarray([[row[key] for key in FEATURES] for row in rows], dtype=float)


def run(seed):
    bundle, metadata = generate(seed)
    rows = build_cohort(bundle, metadata)
    training = [row for row in rows if row["split"] == "train"]
    model = make_pipeline(SimpleImputer(strategy="median", add_indicator=True),
                          StandardScaler(), LogisticRegression(max_iter=1000))
    model.fit(matrix(training), [row["outcome"] for row in training])
    payloads = {}
    for site in ("north", "south", "coastal"):
        local = [row for row in rows if row["site"] == site and row["split"] != "train"]
        scores = model.predict_proba(matrix(local))[:, 1]
        payloads[site] = site_summary([row["outcome"] for row in local], scores)
    return {
        "synthetic_only": True, "seed": seed, "horizon_days": HORIZON,
        "training_n": len(training), "score_bin_edges": list(EDGES),
        "site_payloads": payloads,
        "sites": {site: describe(payload) for site, payload in payloads.items()},
        "network": describe(combine(list(payloads.values()))),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=Path("build/evaluation.json"))
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.out, run(args.seed))
    print(f"Evaluation report: {args.out}")
