from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Dict

import pandas as pd
import structlog

from m365_billing.audit.drift import drift_audit
from m365_billing.connectors.odoo_rpc import OdooRPC
from m365_billing.settings import EnvSettings, load_config
from m365_billing.store.history_store import ParquetHistoryStore

log = structlog.get_logger()


def read_input(path: Path, required_cols: list[str]) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
    elif path.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(path)
    else:
        raise ValueError(f"Unsupported input extension: {path.suffix}")

    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = df.copy()
    df["Client_ID"] = df["Client_ID"].astype(str).str.strip()
    df["Subscription_ID"] = df["Subscription_ID"].astype(str).str.strip()
    df["SKU_Name"] = df["SKU_Name"].astype(str).str.strip()
    df["Quantity_Month_N"] = pd.to_numeric(df["Quantity_Month_N"], errors="coerce").fillna(0).astype(int)
    return df


def run_pipeline(
    input_path: Path,
    period: str,
    dry_run: bool,
    execution_id: str | None = None,
    no_odoo: bool = False,
) -> Dict[str, Any]:
    env = EnvSettings()
    cfg = load_config()
    execution_id = execution_id or f"exec_{uuid.uuid4().hex[:8]}_{period}"

    storage_root = Path(env.storage_root)
    store = ParquetHistoryStore(storage_root=storage_root)

    log.info("start", execution_id=execution_id, period=period, input=str(input_path), dry_run=dry_run, no_odoo=no_odoo)

    df = read_input(input_path, cfg.io.required_columns)

    # Odoo mapping index (optional)
    sol_index: dict[str, dict] = {}
    if not no_odoo:
        odoo = OdooRPC(url=env.odoo_url, db=env.odoo_db, user=env.odoo_user, password=env.odoo_password)
        domain = cfg.raw_base.get("odoo", {}).get("domain_active_sol", [])
        fields = ["id", cfg.app.join_field, cfg.app.qty_field, "product_id", "order_partner_id"]
        sol_rows = odoo.search_read(cfg.app.odoo_model, domain=domain, fields=fields)
        sol_index = {r[cfg.app.join_field]: r for r in sol_rows if r.get(cfg.app.join_field)}
    else:
        odoo = None  # type: ignore

    treated = ok = warning = critical = 0
    mapping_errors = write_errors = 0

    updates: list[tuple[int, dict]] = []
    report_rows: list[dict[str, Any]] = []

    for row in df.itertuples(index=False):
        treated += 1
        sub_id = str(row.Subscription_ID)
        qty_new = int(row.Quantity_Month_N)

        sol = sol_index.get(sub_id) if not no_odoo else None
        sol_id = int(sol["id"]) if sol else None

        if (not no_odoo) and sol is None:
            mapping_errors += 1
            # still report + still persist raw usage if you want; here we keep it for audit history
        qty_prev = store.get_last_qty(sub_id)

        audit = drift_audit(
            qty_new=qty_new,
            qty_prev=qty_prev,
            warn_thr=cfg.drift.pct_threshold_warning,
            crit_thr=cfg.drift.pct_threshold_critical,
        )
        status = audit["status"]
        if status == "ok":
            ok += 1
        elif status == "warning":
            warning += 1
        else:
            critical += 1

        # persist external history (Parquet + latest index)
        store.append_month(
            period=period,
            client_id=str(row.Client_ID),
            subscription_id=sub_id,
            sku=str(row.SKU_Name),
            qty=qty_new,
            execution_id=execution_id,
        )

        # prepare Odoo update only if we have a sol_id
        if sol_id is not None:
            values = {
                cfg.app.qty_field: qty_new,
                cfg.app.audit_status_field: status,
                cfg.app.audit_log_field: json.dumps(
                    {
                        "context": {"source": cfg.app.source, "period": period, "execution_id": execution_id},
                        "audit_ia": audit,
                    },
                    ensure_ascii=False,
                ),
            }
            updates.append((sol_id, values))

        report_rows.append(
            {
                "period": period,
                "client_id": str(row.Client_ID),
                "subscription_id": sub_id,
                "sku": str(row.SKU_Name),
                "qty_new": qty_new,
                "qty_prev": qty_prev,
                "status": status,
                "anomaly_score": audit.get("anomaly_score"),
                "reason": audit.get("reason"),
                "sol_id": sol_id,
            }
        )

    store.flush()

    # write report CSV artifact
    artifacts_dir = Path("artifacts") / "runs" / execution_id
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    report_path = artifacts_dir / "report.csv"
    pd.DataFrame(report_rows).to_csv(report_path, index=False)

    # write to Odoo unless dry_run or no_odoo
    if (not dry_run) and (not no_odoo) and updates:
        try:
            assert odoo is not None
            odoo.batch_write(cfg.app.odoo_model, updates)
        except Exception as e:
            write_errors = len(updates)
            log.exception("odoo_write_failed", err=str(e))

    res = {
        "execution_id": execution_id,
        "treated": treated,
        "ok": ok,
        "warning": warning,
        "critical": critical,
        "mapping_errors": mapping_errors,
        "write_errors": write_errors,
        "report_path": str(report_path),
    }
    log.info("done", **res)
    return res
