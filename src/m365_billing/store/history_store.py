from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd


@dataclass
class ParquetHistoryStore:
    storage_root: Path

    def __post_init__(self) -> None:
        self.parquet_root = self.storage_root / "parquet"
        self.index_root = self.storage_root / "index"
        self.parquet_root.mkdir(parents=True, exist_ok=True)
        self.index_root.mkdir(parents=True, exist_ok=True)
        self.latest_path = self.index_root / "latest.parquet"
        self._latest_df: Optional[pd.DataFrame] = None

    def _latest(self) -> pd.DataFrame:
        if self._latest_df is not None:
            return self._latest_df
        if self.latest_path.exists():
            self._latest_df = pd.read_parquet(self.latest_path)
        else:
            self._latest_df = pd.DataFrame(columns=["subscription_id", "last_period", "last_qty"])
        return self._latest_df

    def get_last_qty(self, subscription_id: str) -> Optional[int]:
        df = self._latest()
        m = df[df["subscription_id"] == subscription_id]
        if m.empty:
            return None
        return int(m.iloc[0]["last_qty"])

    def append_month(
        self,
        period: str,
        client_id: str,
        subscription_id: str,
        sku: str,
        qty: int,
        execution_id: str,
    ) -> None:
        part_dir = self.parquet_root / f"period={period}"
        part_dir.mkdir(parents=True, exist_ok=True)
        path = part_dir / "usage.parquet"

        row = pd.DataFrame([{
            "period": period,
            "client_id": client_id,
            "subscription_id": subscription_id,
            "sku": sku,
            "qty": int(qty),
            "execution_id": execution_id,
        }])

        if path.exists():
            old = pd.read_parquet(path)
            new = pd.concat([old, row], ignore_index=True)
        else:
            new = row

        new.to_parquet(path, index=False)

        latest = self._latest()
        latest = latest[latest["subscription_id"] != subscription_id]
        latest = pd.concat(
            [latest, pd.DataFrame([{
                "subscription_id": subscription_id,
                "last_period": period,
                "last_qty": int(qty),
            }])],
            ignore_index=True,
        )
        self._latest_df = latest

    def flush(self) -> None:
        df = self._latest()
        df.to_parquet(self.latest_path, index=False)
