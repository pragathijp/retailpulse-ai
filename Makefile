# Optional convenience wrapper. On Windows PowerShell use `python run.py <command>` or `.\run_all.ps1`.
PY ?= python

.PHONY: setup ingest dbt_build analyses export forecast rfm_check audit ai_context run_all clean

setup ingest dbt_build analyses export forecast rfm_check audit ai_context run_all clean:
	$(PY) run.py $@
