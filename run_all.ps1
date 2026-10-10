# Primary Windows entry point: runs the whole pipeline.
# Usage (PowerShell):  .\run_all.ps1            or   .\run_all.ps1 --skip-ingest
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$py = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) { $py = 'python' }
& $py run.py run_all @args
exit $LASTEXITCODE
