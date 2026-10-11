"""The Power BI measure library and KPI export query stay in sync with the metrics contract."""
from common import ROOT
from helpers import CONTRACT

DAX = (ROOT / 'powerbi' / 'measures.dax').read_text()
EXPORT = (ROOT / 'powerbi' / 'kpi_export.dax').read_text()


def measure_lines():
    out = {}
    for line in DAX.splitlines():
        if ' = ' in line and not line.startswith(('//', ' ', '\t')):
            name, expr = line.split(' = ', 1)
            out[name.strip()] = expr.strip()
    return out


def test_every_contract_measure_is_defined_with_the_contract_expression():
    defined = measure_lines()
    for m in CONTRACT['metrics']:
        assert m['dax_measure'] in defined, f"measure missing in measures.dax: {m['dax_measure']}"
        assert defined[m['dax_measure']] == m['dax'], f"{m['dax_measure']} differs from the contract"


def test_kpi_export_covers_every_contract_metric():
    for m in CONTRACT['metrics']:
        assert f'"{m["name"]}"' in EXPORT and f'[{m["dax_measure"]}]' in EXPORT, m['name']


def test_dax_measure_names_are_unique():
    names = [line.split(' = ', 1)[0].strip() for line in DAX.splitlines()
             if ' = ' in line and not line.startswith(('//', ' ', '\t'))]
    assert len(names) == len(set(names))
