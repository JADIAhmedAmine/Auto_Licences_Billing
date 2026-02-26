from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


def make_synth(n_subs: int = 500, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    subs = [f"MS-{rng.integers(10_000, 99_999)}" for _ in range(n_subs)]
    clients = [str(rng.integers(1000, 9999)) for _ in range(n_subs)]
    skus = rng.choice(["O365_E3", "O365_E5", "BUS_PREMIUM", "F3"], size=n_subs)

    base = rng.poisson(lam=rng.uniform(5, 200, size=n_subs)).astype(int)
    spikes = rng.random(n_subs) < 0.02
    base[spikes] *= rng.integers(5, 25, size=spikes.sum())

    return pd.DataFrame(
        {
            "Client_ID": clients,
            "Subscription_ID": subs,
            "SKU_Name": skus,
            "Quantity_Month_N": base,
        }
    )


def train_model(out_dir: str = "artifacts/models", seed: int = 42) -> None:
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    df = make_synth(seed=seed)
    X = df[["Quantity_Month_N"]].values

    model = IsolationForest(n_estimators=200, contamination=0.02, random_state=seed)
    model.fit(X)

    model_path = Path(out_dir) / "iforest.joblib"
    joblib.dump(model, model_path)

    meta = {"model": "IsolationForest", "features": ["Quantity_Month_N"], "seed": seed}
    (Path(out_dir) / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(f"Saved model: {model_path}")


if __name__ == "__main__":
    train_model()
