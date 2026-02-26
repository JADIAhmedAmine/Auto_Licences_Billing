from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split


def make_synth_timeseries(n_subs: int = 800, seed: int = 42) -> pd.DataFrame:
    """
    Generates synthetic labeled data for anomaly detection.
    Features:
      - qty_new, qty_prev, pct_change
    Label:
      - y (0 normal, 1 anomaly)
    """
    rng = np.random.default_rng(seed)

    qty_prev = rng.integers(1, 250, size=n_subs)
    # Most are stable-ish
    noise = rng.normal(0, 0.1, size=n_subs)
    qty_new = (qty_prev * (1 + noise)).clip(0, None).astype(int)

    # Inject anomalies (spikes)
    y = np.zeros(n_subs, dtype=int)
    anomaly_idx = rng.random(n_subs) < 0.05
    qty_new[anomaly_idx] = (
        qty_prev[anomaly_idx] * rng.integers(4, 20, size=anomaly_idx.sum())
    ).astype(int)
    y[anomaly_idx] = 1

    df = pd.DataFrame({"qty_prev": qty_prev, "qty_new": qty_new, "y": y})
    df["pct_change"] = np.where(
        df["qty_prev"] == 0, np.inf, np.abs(df["qty_new"] - df["qty_prev"]) / df["qty_prev"]
    )
    df.replace([np.inf, -np.inf], 999.0, inplace=True)
    return df


def train(out_dir: str = "artifacts/models", seed: int = 42) -> None:
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    df = make_synth_timeseries(seed=seed)
    X = df[["qty_prev", "qty_new", "pct_change"]]
    y = df["y"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=seed, stratify=y
    )

    clf = RandomForestClassifier(
        n_estimators=300,
        max_depth=None,
        min_samples_leaf=2,
        random_state=seed,
        n_jobs=-1,
    )
    clf.fit(X_train, y_train)

    pred = clf.predict(X_test)
    report = classification_report(y_test, pred, output_dict=True)

    model_path = Path(out_dir) / "rf_anomaly.joblib"
    joblib.dump(clf, model_path)

    meta = {
        "model": "RandomForestClassifier",
        "features": ["qty_prev", "qty_new", "pct_change"],
        "seed": seed,
        "report": report,
    }
    (Path(out_dir) / "rf_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(f"Saved: {model_path}")
    print("F1 anomaly:", report["1"]["f1-score"])


if __name__ == "__main__":
    train()
