import re
import sys
from pathlib import Path

import pytest

from snappy.config import load_config


project_root_path = Path(__file__).parent.parent


def test_example_config_valid(monkeypatch):
    # Detect misspelled keys.
    monkeypatch.setattr('snappy.config._dacite_config.strict', True)

    # Simply check that loading the config file doesn't throw an exception.
    load_config(project_root_path / 'docs/example_config/snappy.toml')


def test_readme_contains_usage(capsys, monkeypatch, snappy_command):
    if sys.version_info <= (3, 10):
        # The output changed slightly in Python 3.10.
        # See https://github.com/python/cpython/issues/53903.
        pytest.skip()

    readme_path = project_root_path / 'readme.md'
    monkeypatch.setenv('COLUMNS', '80')

    try:
        snappy_command('--help')
    except SystemExit:
        pass

    # By accident, this will include `$ snappy --help` at the beginning. The
    # snappy_command fixture outputs this as part of logging, but I think it's
    # cute, and I'm keeping it. Wrapped paragraphs contain whitespace used for
    # indentation on empty lines, which I don't want to have in the markdown
    # file.
    help_output = re.sub(' +$', '', capsys.readouterr().out.strip(), flags=re.MULTILINE)

    usage_block = f'```\n' \
                  f'{help_output}\n' \
                  f'```'

    print(f'Expecting {readme_path} the following block:\n'
          f'\n'
          f'{usage_block}')

    assert usage_block in readme_path.read_text()
