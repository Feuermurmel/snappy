from pathlib import Path

import pytest

import snappy.config
from conftest import get_snapshots, zfs
from snappy.config import Config


@pytest.fixture
def mocked_config_file(monkeypatch, tmp_path):
    config_path = tmp_path / 'mocked_config_file.toml'

    def mock_load_config(path: Path) -> Config:
        return orig_load_config(config_path)

    orig_load_config = snappy.config._load_config
    monkeypatch.setattr('snappy.config._load_config', mock_load_config)

    return config_path


def test_error_no_config_file_found(
        snappy_command, fails_with_message, mocked_config_file):
    with fails_with_message(
            'Error loading config file `/etc/snappy/snappy.toml\': .* No such '
            'file'):
        snappy_command('--auto')


def test_error_config_file_invalid_syntax(
        snappy_command, fails_with_message, mocked_config_file):
    mocked_config_file.write_text('bla bla')

    with fails_with_message(
            'Error loading config file `/etc/snappy/snappy.toml\': Found '
            'invalid character'):
        snappy_command('--auto')


def test_auto(snappy_command, mocked_config_file, temp_filesystem):
    child_filesystem = f'{temp_filesystem}/child'
    zfs('create', child_filesystem)

    mocked_config_file.write_text(
        f'[[snapshot]]\n'
        f'datasets = ["{temp_filesystem}"]\n'
        f'recursive = true\n'
        f'\n'
        f'[snapshot.prune]\n'
        f'keep = ["1h:2"]\n')

    snappy_command('--auto')
    snappy_command('--auto')
    snappy_command('--auto')

    expected_snapshots = ['snappy-2001-02-03-091500', 'snappy-2001-02-03-101500']
    assert get_snapshots(temp_filesystem) == expected_snapshots
    assert get_snapshots(child_filesystem) == expected_snapshots
