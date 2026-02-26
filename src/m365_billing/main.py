from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from m365_billing.observability.logging import setup_logging
from m365_billing.pipeline.run_pipeline import run_pipeline

app = typer.Typer(help="M365 Usage Billing middleware (ingestion + audit + Odoo push).")


@app.callback(invoke_without_command=True)
def main(
    input_path: Path = typer.Option(..., "--input", "-i", exists=True, readable=True),
    period: str = typer.Option(..., "--period", "-p", help="YYYY-MM (ex: 2025-10)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="No writes to Odoo"),
    no_odoo: bool = typer.Option(False, "--no-odoo", help="Test local: skip Odoo mapping/write"),
    execution_id: Optional[str] = typer.Option(None, "--execution-id"),
):
    setup_logging()
    res = run_pipeline(
        input_path=input_path,
        period=period,
        dry_run=dry_run,
        execution_id=execution_id,
        no_odoo=no_odoo,
    )

    typer.echo(f"execution_id={res['execution_id']}")
    typer.echo(f"treated={res['treated']} ok={res['ok']} warning={res['warning']} critical={res['critical']}")
    typer.echo(f"mapping_errors={res['mapping_errors']} write_errors={res['write_errors']}")
    if res.get("report_path"):
        typer.echo(f"report={res['report_path']}")
