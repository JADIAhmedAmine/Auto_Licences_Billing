from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone


def new_execution_id(period: str) -> str:
    return f"exec_{uuid.uuid4().hex[:8]}_{period}"


def model_version() -> str:
    # if you tag releases in git, you can inject GIT_SHA in CI
    sha = os.getenv("GIT_SHA")
    if sha:
        return sha[:8]
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
