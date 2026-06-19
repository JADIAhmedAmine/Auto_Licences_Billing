# Auto Licences Billing — M365 Usage Billing Middleware

> **Middleware d'automatisation de la facturation à l'usage des licences Microsoft 365.**
> Ingestion des consommations mensuelles → audit des anomalies (règles + ML) → injection dans Odoo → observabilité.

> **EN — TL;DR:** A Python middleware that automates **usage-based billing for Microsoft 365 licenses**. It ingests monthly usage files (CSV/XLSX), audits each subscription for billing anomalies and consumption drift (threshold rules **+ machine-learning anomaly detection**), pushes validated quantities into **Odoo** via XML-RPC, and exposes the whole run through a FastAPI service with **Prometheus + Grafana** observability. Built with Python 3.10+, pydantic v2, pandas, scikit-learn and FastAPI; containerized with Docker.

---

> ℹ️ **Note** — Projet présenté à des fins de **portfolio**. Toutes les données (`data/samples`, `artifacts/runs`) sont **synthétiques** et les modèles ML sont entraînés sur des jeux générés aléatoirement. La configuration (`.env.example`, `configs/`) ne contient que des **valeurs d'exemple** — aucun secret ni donnée client réelle.
> *Portfolio project. All bundled data is synthetic, ML models are trained on randomly generated datasets, and configuration contains placeholder values only — no secrets or real client data.*

## Sommaire

- [Le problème](#le-problème)
- [Ce que fait le middleware](#ce-que-fait-le-middleware)
- [Architecture](#architecture)
- [Le pipeline en détail](#le-pipeline-en-détail)
- [Détection d'anomalies (ML + règles)](#détection-danomalies-ml--règles)
- [Démarrage rapide](#démarrage-rapide)
- [Utilisation](#utilisation)
- [Observabilité](#observabilité)
- [Configuration](#configuration)
- [Stack technique](#stack-technique)
- [Structure du projet](#structure-du-projet)

## Le problème

Facturer les licences Microsoft 365 « à l'usage » suppose de relever chaque mois la consommation par abonnement, de la comparer au mois précédent, de repérer les écarts suspects (erreur d'export, pic anormal, abonnement fantôme) **avant** de facturer, puis de reporter les quantités validées dans l'ERP (Odoo). Fait à la main, ce processus est lent, peu traçable et risqué : une quantité erronée se traduit directement en facture fausse.

Ce middleware **industrialise et fiabilise** cette chaîne de bout en bout, avec un audit automatique et une traçabilité complète de chaque exécution.

## Ce que fait le middleware

- **Ingestion** de fichiers de consommation mensuels (CSV / XLSX), avec validation des colonnes attendues.
- **Historisation** des consommations par abonnement dans un *history store* Parquet (partitionné par période + index « dernier mois connu »).
- **Audit de dérive (drift)** mois N vs mois N-1 : classement `ok` / `warning` / `critical` selon des seuils configurables, avec score d'anomalie et explication lisible.
- **Détection d'anomalies par ML** : modèles `RandomForestClassifier` (supervisé) et `IsolationForest` (non supervisé) entraînés sur données synthétiques.
- **Injection Odoo** : mapping des abonnements vers les lignes de commande (`sale.order.line`) via un identifiant d'abonnement Microsoft, puis écriture en lot des quantités + journal d'audit.
- **Modes sûrs** : `--dry-run` (aucune écriture Odoo) et `--no-odoo` (exécution 100 % locale, sans ERP).
- **API & observabilité** : service FastAPI, métriques Prometheus, tableau de bord Grafana, logs structurés (`structlog`).
- **Artefacts d'exécution** : un rapport CSV par run (`artifacts/runs/<execution_id>/report.csv`).

## Architecture

```text
   Fichier usage (CSV/XLSX)                         ┌──────────────┐
            │                                        │  Prometheus  │◄── /metrics
            ▼                                        └──────┬───────┘
   ┌─────────────────────┐                                  │
   │  CLI (Typer)         │     ┌──────────────────┐        ▼
   │  ou API (FastAPI)    │────►│   run_pipeline    │   ┌──────────┐
   └─────────────────────┘     │                   │   │ Grafana  │
                                │  1. read_input    │   └──────────┘
   ┌─────────────────────┐     │  2. history store │
   │ Parquet history store│◄───►│  3. drift audit   │
   │ (qty M-1, index)     │     │  4. ML scoring    │
   └─────────────────────┘     │  5. Odoo mapping  │     ┌──────────────┐
                                │  6. batch write   │────►│   Odoo ERP   │
   ┌─────────────────────┐     │  7. report.csv    │     │ (XML-RPC)    │
   │ report.csv (artifact)│◄───│                   │     └──────────────┘
   └─────────────────────┘     └──────────────────┘
```

## Le pipeline en détail

| Étape | Description |
| --- | --- |
| **1. Lecture** | Lecture du CSV/XLSX, normalisation des types, contrôle des colonnes requises (`Client_ID`, `Subscription_ID`, `SKU_Name`, `Quantity_Month_N`). |
| **2. Historique** | Récupération de la quantité du mois précédent depuis le store Parquet (`get_last_qty`). |
| **3. Audit drift** | Calcul du % d'écart vs M-1 → statut `ok`/`warning`/`critical` + score + raison. |
| **4. Persistance** | Ajout de la consommation du mois à l'historique partitionné + mise à jour de l'index. |
| **5. Mapping Odoo** | Recherche des lignes de commande actives par identifiant d'abonnement (sauf `--no-odoo`). |
| **6. Écriture** | Écriture en lot des quantités validées + journal d'audit JSON dans Odoo (sauf `--dry-run`). |
| **7. Rapport** | Génération d'un `report.csv` par exécution, traçant chaque ligne et son verdict. |

## Détection d'anomalies (ML + règles)

Deux niveaux complémentaires :

1. **Règles de dérive** (`audit/drift.py`) — déterministes et explicables : l'écart relatif vs le mois précédent est comparé à deux seuils (`warning`, `critical`). Chaque verdict porte une raison en clair (ex. *« Augmentation critique : 400 % vs M-1 (850 vs 170) »*).
2. **Modèles ML** (`ml/`) — entraînés sur des séries synthétiques labellisées :
   - `RandomForestClassifier` sur les *features* `qty_prev`, `qty_new`, `pct_change` (classification anomalie / normal) ;
   - `IsolationForest` pour la détection non supervisée de points aberrants.
   Les modèles et leurs métadonnées (features, F1, seed) sont sauvegardés dans `artifacts/models/`.

## Démarrage rapide

```bash
# 1. Installer (mode éditable)
make install            # ou: pip install -e .

# 2. Configurer
cp .env.example .env    # puis renseigner les accès Odoo

# 3. Lancer un audit en local (sans Odoo)
m365-billing --input data/samples/usage_2025-10.xlsx --period 2025-10 --no-odoo
```

> Python **3.10+** requis.

## Utilisation

### En ligne de commande (Typer)

```bash
m365-billing --input <fichier.csv|xlsx> --period 2025-10 [--dry-run] [--no-odoo]
```

- `--no-odoo` : exécution locale, aucun appel ERP (idéal pour tester l'audit).
- `--dry-run` : mapping Odoo effectué mais **aucune écriture**.
- Sortie : `execution_id`, compteurs `treated / ok / warning / critical`, erreurs de mapping/écriture, chemin du rapport.

### Via l'API (FastAPI)

```bash
make api     # uvicorn services.api.app:app --port 8000
```

| Endpoint | Rôle |
| --- | --- |
| `GET /health` | Vérification de vie. |
| `GET /metrics` | Métriques Prometheus. |
| `POST /audit` | Lance le pipeline à partir de `rows` (JSON) ou d'un `input_path`, modes `dry_run` / `no_odoo`. |

```bash
curl -X POST localhost:8000/audit -H "Content-Type: application/json" -d '{
  "period": "2025-10",
  "rows": [{"Client_ID":"1792","Subscription_ID":"MS-365-99821","SKU_Name":"O365_BUSINESS_PREMIUM","Quantity_Month_N":850}],
  "no_odoo": true
}'
```

## Observabilité

- **Métriques Prometheus** exposées sur `/metrics` : `pipeline_runs_total`, `pipeline_lines_treated_total{status}`, `pipeline_mapping_errors_total`, `pipeline_write_errors_total`, `pipeline_latency_seconds`.
- **Tableau de bord Grafana** prêt à l'emploi (`monitoring/grafana/dashboards/`), avec provisioning automatique de la datasource et du dashboard.
- **Logs structurés** JSON via `structlog`.
- Stack complète d'un `docker compose up` : **API + Prometheus + Grafana**.

```bash
cd docker && docker compose up --build
```

## Configuration

Tout est piloté par `.env` + deux fichiers YAML :

- **`.env`** — accès Odoo (`ODOO_URL`, `ODOO_DB`, `ODOO_USER`, `ODOO_PASSWORD`) et chemins. Voir `.env.example`.
- **`configs/base.yaml`** — mapping métier : modèle Odoo, champs de jointure/quantité/audit, colonnes d'entrée requises.
- **`configs/thresholds.yaml`** — seuils de dérive (`warning`, `critical`).

> Le mapping Odoo est entièrement déclaratif : changer de modèle ou de champs ne demande aucune modification de code.

## Stack technique

**Cœur** — Python 3.10+ · Typer (CLI) · Pydantic v2 / pydantic-settings · pandas · PyArrow (Parquet)
**ML** — scikit-learn (RandomForest, IsolationForest) · joblib
**API & observabilité** — FastAPI · Uvicorn · prometheus-client · structlog · Grafana
**Intégration** — Odoo via XML-RPC
**Outillage** — Docker / docker-compose · Makefile · Ruff · pre-commit · pytest · GitHub Actions (CI)

## Structure du projet

```
src/m365_billing/
├── main.py                  # CLI Typer
├── settings.py              # env + chargement YAML (pydantic)
├── pipeline/run_pipeline.py # orchestration du pipeline
├── audit/drift.py           # règles de dérive M vs M-1
├── ml/                      # train_rf.py, train_iforest.py
├── connectors/odoo_rpc.py   # client Odoo XML-RPC
├── store/history_store.py   # history store Parquet + index
└── observability/           # logging structuré + métriques Prometheus
services/api/app.py          # API FastAPI (/health, /metrics, /audit)
configs/                     # base.yaml, thresholds.yaml
docker/                      # Dockerfile.api + docker-compose (API/Prometheus/Grafana)
monitoring/                  # config Prometheus + dashboards Grafana
data/samples/ · artifacts/   # données et sorties d'exemple (synthétiques)
tests/                       # pytest
```

---

*Réalisé par **Ahmed-Amine Jadi**. Données et configuration d'exemple — aucun secret ni donnée réelle.*
