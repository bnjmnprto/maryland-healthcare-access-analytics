.PHONY: setup fetch-data live-data live-pipeline data validate model summaries dashboard test all

PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
PIP ?= $(PYTHON) -m pip
STREAMLIT ?= $(if $(wildcard .venv/bin/streamlit),.venv/bin/streamlit,$(PYTHON) -m streamlit)

setup:
	$(PIP) install -r requirements.txt

fetch-data:
	$(PYTHON) src/fetch_acs.py --refresh
	$(PYTHON) src/fetch_cdc_places.py --refresh
	$(PYTHON) src/fetch_hrsa_hpsa.py --refresh
	$(PYTHON) src/fetch_cms_hospital_quality.py --refresh

live-data: fetch-data

live-pipeline: fetch-data
	$(PYTHON) src/data_pipeline.py --refresh-public

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
