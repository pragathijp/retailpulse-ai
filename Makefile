.PHONY: setup ingest dbt_build forecast rfm_check audit run_all clean

setup:
	pip install dbt-duckdb streamlit plotly duckdb pandas statsmodels pytest

ingest:
	python src/ingestion.py

dbt_build:
	cd dbt_project && dbt seed --profiles-dir . && dbt build --profiles-dir .

forecast:
	python src/forecasting.py

rfm_check:
	python src/rfm_check.py

audit:
	pytest tests/ -v

run_all: dbt_build forecast rfm_check audit

clean:
	Remove-Item -Force -ErrorAction SilentlyContinue data\duckdb\retail_analytics.duckdb
	Remove-Item -Recurse -Force -ErrorAction SilentlyContinue data\processed\*