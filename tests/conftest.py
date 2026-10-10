import sys
from pathlib import Path

# Make src/common.py importable from every test, regardless of the working directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
