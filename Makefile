.PHONY: help venv install lint format test api train docker-build docker-run

help:
	@echo "Targets:"
	@echo "  install       Install project in editable mode"
	@echo "  lint          Ruff check"
	@echo "  format        Ruff format"
	@echo "  test          Pytest"
	@echo "  api           Run FastAPI locally"
	@echo "  train         Train RandomForest model"
	@echo "  docker-build  Build API docker image"
	@echo "  docker-run    Run API docker container on port 8001"

install:
	pip install -e .

lint:
	python -m ruff check .

format:
	python -m ruff format .

test:
	python -m pytest

api:
	uvicorn services.api.app:app --host 0.0.0.0 --port 8000

train:
	python src/m365_billing/ml/train_rf.py

docker-build:
	docker build -f docker/Dockerfile.api -t m365-billing-api:dev .

docker-run:
	docker run --rm -p 8001:8000 \
		-v "$(PWD)/storage:/app/storage" \
		-v "$(PWD)/artifacts:/app/artifacts" \
		-v "$(PWD)/configs:/app/configs" \
		--env-file .env \
		m365-billing-api:dev
