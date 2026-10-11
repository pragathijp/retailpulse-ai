"""Documentation stays honest: every runner command is documented and no unsupported claims appear."""
import re

from common import DOCS, ROOT

README = (ROOT / 'README.md').read_text()
FORBIDDEN = ['dataset-agnostic', 'audit-proof', 'production-ready', 'zero hallucination']


def runner_commands():
    text = (ROOT / 'run.py').read_text()
    block = re.search(r'COMMANDS = \{(.*?)\}', text, re.S).group(1)
    return re.findall(r"'([a-z_]+)':", block)


def test_every_runner_command_is_documented():
    for cmd in runner_commands():
        assert f'python run.py {cmd}' in README, cmd


def test_no_unsupported_claims_in_docs():
    for path in [ROOT / 'README.md', *DOCS.glob('*.md')]:
        text = path.read_text().lower()
        for phrase in FORBIDDEN:
            assert phrase not in text, f'{path.name} contains {phrase!r}'


def test_architecture_has_both_diagrams_and_airflow_is_conceptual():
    text = (DOCS / 'architecture.md').read_text()
    assert text.count('```mermaid') == 2 and 'documentation-only' in text


def test_readme_mentions_every_top_level_folder():
    for folder in ['src', 'dbt_project', 'tests', 'powerbi', 'docs', 'reports']:
        assert f'{folder}/' in README, folder
