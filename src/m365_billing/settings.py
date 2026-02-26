from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Odoo
    odoo_url: str
    odoo_db: str
    odoo_user: str
    odoo_password: str

    # Storage/config paths
    storage_root: str = "./storage"
    config_base: str = "./configs/base.yaml"
    config_thresholds: str = "./configs/thresholds.yaml"


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class AppConfig(BaseModel):
    source: str
    odoo_model: str
    join_field: str
    qty_field: str
    audit_log_field: str
    audit_status_field: str


class IOConfig(BaseModel):
    required_columns: List[str]


class DriftConfig(BaseModel):
    pct_threshold_warning: float = 0.5
    pct_threshold_critical: float = 2.0


class ConfigBundle(BaseModel):
    app: AppConfig
    io: IOConfig
    drift: DriftConfig
    raw_base: Dict[str, Any]
    raw_thresholds: Dict[str, Any]


def load_config() -> ConfigBundle:
    env = EnvSettings()

    base = _load_yaml(Path(env.config_base))
    thr = _load_yaml(Path(env.config_thresholds))

    return ConfigBundle(
        app=AppConfig(**base["app"]),
        io=IOConfig(**base["io"]),
        drift=DriftConfig(**thr.get("drift", {})),
        raw_base=base,
        raw_thresholds=thr,
    )
