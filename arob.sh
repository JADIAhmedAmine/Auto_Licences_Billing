#!/usr/bin/env bash

set -e


echo "📦 Creating project: $PROJECT_NAME"

touch pyproject.toml
touch .env.example
touch .gitignore

# Configs
mkdir -p configs
touch configs/base.yaml
touch configs/thresholds.yaml

# Storage
mkdir -p storage/parquet
mkdir -p storage/index

# Source tree
mkdir -p src/m365_billing/pipeline
mkdir -p src/m365_billing/connectors
mkdir -p src/m365_billing/store
mkdir -p src/m365_billing/audit

touch src/m365_billing/__init__.py
touch src/m365_billing/main.py
touch src/m365_billing/settings.py

touch src/m365_billing/pipeline/__init__.py
touch src/m365_billing/pipeline/run_pipeline.py

touch src/m365_billing/connectors/__init__.py
touch src/m365_billing/connectors/odoo_rpc.py

touch src/m365_billing/store/__init__.py
touch src/m365_billing/store/history_store.py

touch src/m365_billing/audit/__init__.py
touch src/m365_billing/audit/drift.py

# Tests
mkdir -p tests
touch tests/test_drift.py

echo "✅ Project structure created successfully."
echo ""
echo "Next steps:"
echo "1️⃣  cd $PROJECT_NAME"
echo "2️⃣  python -m venv .venv"
echo "3️⃣  source .venv/bin/activate"
echo "4️⃣  pip install -e ."
