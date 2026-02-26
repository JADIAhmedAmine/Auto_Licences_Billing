from __future__ import annotations

from prometheus_client import Counter, Histogram

PIPELINE_RUNS = Counter("pipeline_runs_total", "Number of pipeline runs", ["mode"])
LINES_TREATED = Counter("pipeline_lines_treated_total", "Lines treated", ["status"])
MAPPING_ERRORS = Counter("pipeline_mapping_errors_total", "Mapping errors")
WRITE_ERRORS = Counter("pipeline_write_errors_total", "Write errors")
PIPELINE_LATENCY = Histogram("pipeline_latency_seconds", "Pipeline latency in seconds")
