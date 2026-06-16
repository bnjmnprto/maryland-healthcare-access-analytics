.PHONY: setup live-data live-pipeline data validate model summaries dashboard test all

PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
PIP ?= $(PYTHON) -m pip
STREAMLIT ?= $(if $(wildcard .venv/bin/streamlit),.venv/bin/streamlit,$(PYTHON) -m streamlit)

setup:
	$(PIP) install -r requirements.txt

live-data:
	$(PYTHON) src/public_data_ingestion.py --output data/raw/maryland_county_health_access_public.csv

live-pipeline: live-data
	$(PYTHON) src/data_pipeline.py --raw-path data/raw/maryland_county_health_access_public.csv

data:
	$(PYTHON) src/data_pipeline.py

validate:
	$(PYTHON) src/validate_data.py

model:
	$(PYTHON) src/risk_model.py

summaries:
	$(PYTHON) src/ai_summary.py

dashboard:
	$(STREAMLIT) run dashboard/app.py

test:
	$(PYTHON) -m pytest

all: data validate model summaries test
