from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel

from m365_billing.observability.logging import setup_logging
from m365_billing.pipeline.run_pipeline import run_pipeline

app = FastAPI(title="M365 Billing Audit API", version="0.1.0")


class AuditRequest(BaseModel):
    period: str
    input_path: Optional[str] = None
    rows: Optional[List[Dict[str, Any]]] = None
    dry_run: bool = True
    no_odoo: bool = True


@app.on_event("startup")
def _startup() -> None:
    setup_logging()


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/audit")
def audit(req: AuditRequest) -> Dict[str, Any]:
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

    return run_pipeline(
        input_path=input_path,
        period=req.period,
        dry_run=req.dry_run,
        no_odoo=req.no_odoo,
    )
