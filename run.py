#!/usr/bin/env python3
"""RetailPulse AI pipeline runner (works in PowerShell, no `make` needed).

Usage:
    python run.py <command> [options]

Commands:
    setup       install requirements and dbt packages
    ingest      load the raw dataset from data/raw into DuckDB
    dbt_build   dbt deps + dbt build (models, seeds, tests, Parquet export)
    analyses    compile the dbt analyses and save results to reports/analysis_*.csv
    rfm_check   independent pandas check of the SQL RFM mart
    forecast    weekly revenue forecast
    export      verify the Parquet deliverables (added in Phase 3)
    ai_context  build the JSON context for the AI assistant (optional question, e.g. python run.py ai_context "top products")
    audit       run the pytest reconciliation suite
    run_all     ingest, dbt_build, analyses, rfm_check, forecast, export, ai_context, audit
    clean       delete generated databases, Parquet files and dbt target
"""
import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))
from common import DB_PATH, DBT_DIR, PROC, ROOT  # noqa: E402

SRC = ROOT / 'src'


def ensure_project_venv():
    """Re-launch under the project's .venv interpreter when run from another Python (e.g. system Python)."""
    scripts = 'Scripts' if os.name == 'nt' else 'bin'
    venv_python = ROOT / '.venv' / scripts / ('python.exe' if os.name == 'nt' else 'python')
    if not venv_python.exists() or os.environ.get('RP_VENV_REEXEC'):
        return
    if Path(sys.executable).absolute() == venv_python.absolute():
        return
    print(f'Using project environment: {venv_python}', flush=True)
    env = os.environ.copy()
    env['RP_VENV_REEXEC'] = '1'
    sys.exit(subprocess.run([str(venv_python), str(Path(__file__).resolve()), *sys.argv[1:]], env=env).returncode)


def pipeline_env():
    """Environment for dbt: absolute locations so views never depend on the working directory."""
    env = os.environ.copy()
    env['RP_PROCESSED_DIR'] = PROC.as_posix()
    env['RP_DB_PATH'] = DB_PATH.as_posix()
    return env


def dbt_exe():
    exe = Path(sys.executable).parent / ('dbt.exe' if os.name == 'nt' else 'dbt')
    if exe.exists():
        return str(exe)
    found = shutil.which('dbt')
    if found:
        return found
    sys.exit('dbt not found. Run: python run.py setup')


def run(cmd, cwd=ROOT, env=None):
    print(f'\n> {" ".join(str(c) for c in cmd)}', flush=True)
    result = subprocess.run([str(c) for c in cmd], cwd=str(cwd), env=env or pipeline_env())
    if result.returncode != 0:
        sys.exit(f'FAILED (exit code {result.returncode}): {" ".join(str(c) for c in cmd)}')


def script(name, *args, required=True):
    path = SRC / name
    if not path.exists():
        if required:
            sys.exit(f'Missing script: {path}')
        print(f'\n- SKIP {name}: not built yet')
        return False
    run([sys.executable, path, *args])
    return True


def cmd_setup(_):
    run([sys.executable, '-m', 'pip', 'install', '-r', ROOT / 'requirements.txt'])
    run([dbt_exe(), 'deps', '--profiles-dir', '.'], cwd=DBT_DIR)


def cmd_ingest(args):
    script('ingestion.py', *([args.file] if getattr(args, 'file', None) else []))


def ensure_dbt_packages():
    # dbt deps needs internet; skip it when the packages are already installed.
    if not (DBT_DIR / 'dbt_packages' / 'dbt_utils').exists():
        run([dbt_exe(), 'deps', '--profiles-dir', '.'], cwd=DBT_DIR)


def cmd_dbt_build(_):
    ensure_dbt_packages()
    run([dbt_exe(), 'build', '--profiles-dir', '.'], cwd=DBT_DIR)


def cmd_analyses(_):
    ensure_dbt_packages()
    run([dbt_exe(), 'compile', '--profiles-dir', '.'], cwd=DBT_DIR)
    script('run_analysis.py', '--all')


def cmd_rfm_check(_):
    script('rfm_check.py')


def cmd_forecast(_):
    script('forecasting.py')


def cmd_export(_):
    script('export_parquet.py', required=False)


def cmd_ai_context(args):
    script('context_builder.py', *(getattr(args, 'question', None) or []))


def cmd_audit(_):
    run([sys.executable, '-m', 'pytest', 'tests', '-v'])


def cmd_clean(_):
    targets = [DB_PATH, Path(str(DB_PATH) + '.wal'), PROC / '_manifest.json', DBT_DIR / 'target']
    targets += list(PROC.glob('*.parquet'))
    removed = 0
    for t in targets:
        if t.is_dir():
            shutil.rmtree(t)
            removed += 1
            print(f'removed folder {t}')
        elif t.exists():
            t.unlink()
            removed += 1
            print(f'removed {t}')
    print(f'Clean complete ({removed} items removed).')


def cmd_run_all(args):
    steps = [] if args.skip_ingest else [('ingest', cmd_ingest)]
    steps += [('dbt_build', cmd_dbt_build), ('analyses', cmd_analyses), ('rfm_check', cmd_rfm_check), ('forecast', cmd_forecast),
              ('export', cmd_export), ('ai_context', cmd_ai_context), ('audit', cmd_audit)]
    timings = []
    for name, fn in steps:
        start = time.time()
        fn(args)
        timings.append((name, time.time() - start))
    print('\nRUN_ALL COMPLETE')
    for name, secs in timings:
        print(f'  {name:<11} {secs:6.1f}s')


COMMANDS = {
    'setup': cmd_setup, 'ingest': cmd_ingest, 'dbt_build': cmd_dbt_build, 'analyses': cmd_analyses,
    'rfm_check': cmd_rfm_check,
    'forecast': cmd_forecast, 'export': cmd_export, 'ai_context': cmd_ai_context, 'audit': cmd_audit,
    'run_all': cmd_run_all, 'clean': cmd_clean,
}


def main():
    ensure_project_venv()
    ap = argparse.ArgumentParser(description='RetailPulse AI pipeline runner')
    ap.add_argument('command', choices=sorted(COMMANDS))
    ap.add_argument('question', nargs='*', help='ai_context only: the question the context is built for')
    ap.add_argument('--file', help='raw CSV/XLSX for ingest (default: first file in data/raw)')
    ap.add_argument('--skip-ingest', action='store_true', help='run_all: reuse the existing raw table')
    args = ap.parse_args()
    COMMANDS[args.command](args)


if __name__ == '__main__':
    main()
