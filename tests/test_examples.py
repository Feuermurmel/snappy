from pathlib import Path

from snappy.config import load_config


project_root_path = Path(__file__).parent.parent


def test_example_config_valid(monkeypatch):
    # Detect misspelled keys.
    monkeypatch.setattr('snappy.config._dacite_config.strict', True)

    # Simply check that loading the config file doesn't throw an exception.
    load_config(project_root_path / 'docs/example_config/snappy.toml')


def test_readme_contains_usage(capsys, monkeypatch, snappy_command):
    readme_path = project_root_path / 'readme.md'
    monkeypatch.setenv('COLUMNS', '80')

    try:
        snappy_command('--help')
    except SystemExit:
        pass

    usage_block = f'```\n' \
                  f'{capsys.readouterr().out.strip()}\n' \
                  f'```'

    print(f'Expecting {readme_path} the following block:\n'
          f'\n'
          f'{usage_block}')

    assert usage_block in readme_path.read_text()
