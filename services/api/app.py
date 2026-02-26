from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel

from m365_billing.observability.logging import setup_logging
from m365_billing.observability.metrics import (
    LINES_TREATED,
    MAPPING_ERRORS,
    PIPELINE_LATENCY,
    PIPELINE_RUNS,
    WRITE_ERRORS,
)
from m365_billing.pipeline.run_pipeline import run_pipeline

app = FastAPI(title="M365 Billing Audit API", version="0.1.0")


class AuditRequest(BaseModel):
    period: str
    input_path: str | None = None
    rows: list[dict[str, Any]] | None = None
    dry_run: bool = True
    no_odoo: bool = True


@app.on_event("startup")
def _startup() -> None:
    setup_logging()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/audit")
def audit(req: AuditRequest) -> dict[str, Any]:
    t0 = time.time()
    mode = "no_odoo" if req.no_odoo else "odoo"
    PIPELINE_RUNS.labels(mode=mode).inc()

    if req.rows is not None:
        tmp_dir = Path("artifacts/tmp")
        tmp_dir.mkdir(parents=True, exist_ok=True)
        tmp = tmp_dir / f"input_{req.period}.csv"
        pd.DataFrame(req.rows).to_csv(tmp, index=False)
        input_path = tmp
    elif req.input_path is not None:
        input_path = Path(req.input_path)
        if not input_path.exists():
            return {"error": f"input_path not found: {req.input_path}"}
    else:
        return {"error": "Provide either rows or input_path"}

    with PIPELINE_LATENCY.time():
        res = run_pipeline(
            input_path=input_path,
            period=req.period,
            dry_run=req.dry_run,
            no_odoo=req.no_odoo,
        )

    # counters
    LINES_TREATED.labels(status="treated").inc(res["treated"])
    LINES_TREATED.labels(status="ok").inc(res["ok"])
    LINES_TREATED.labels(status="warning").inc(res["warning"])
    LINES_TREATED.labels(status="critical").inc(res["critical"])
    MAPPING_ERRORS.inc(res["mapping_errors"])
    WRITE_ERRORS.inc(res["write_errors"])

    res["latency_sec"] = round(time.time() - t0, 4)
    return res
