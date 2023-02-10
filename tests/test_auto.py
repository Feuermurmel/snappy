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


def test_config_error_keep_spec(
        snappy_command, fails_with_message, mocked_config_file):
    # Just check one specific case to check that these kinds of errors are
    # correctly handled.
    mocked_config_file.write_text(
        f'[[snapshot]]\n'
        f'datasets = []\n'
        f'\n'
        f'prune_keep = ["1w:1w"]\n')

    with fails_with_message(
            'Invalid value in field "snapshot.prune.keep": Invalid count `1w\''):
        snappy_command('--auto')


def test_config_error_validation(
        snappy_command, fails_with_message, mocked_config_file):
    # Just check one specific case to check that these kinds of errors are
    # correctly handled.
    mocked_config_file.write_text(
        f'[[snapshot]]\n'
        f'datasets = []\n'
        f'take_snapshot = false\n')

    with fails_with_message(
            'Key `prune_keep\' is required if `take_snapshot\' is set to false'):
        snappy_command('--auto')


def test_config_error_dacite_deserialization(
        snappy_command, fails_with_message, mocked_config_file):
    # Just check one specific case to check that these kinds of errors are
    # correctly handled.
    mocked_config_file.write_text(
        f'[[snapshot]]\n'
        f'datasets = [123]\n')

    with fails_with_message(
            'wrong value type for field "snapshot.datasets" - should be "list"'):
        snappy_command('--auto')


def test_auto(snappy_command, mocked_config_file, temp_filesystem):
    child_filesystem = f'{temp_filesystem}/child'
    zfs('create', child_filesystem)

    mocked_config_file.write_text(
        f'[[snapshot]]\n'
        f'datasets = ["{temp_filesystem}"]\n'
        f'recursive = true\n'
        f'prune_keep = ["1h:2"]\n')

    snappy_command('--auto')
    snappy_command('--auto')
    snappy_command('--auto')

    expected_snapshots = ['snappy-2001-02-03-091500', 'snappy-2001-02-03-101500']
    assert get_snapshots(temp_filesystem) == expected_snapshots
    assert get_snapshots(child_filesystem) == expected_snapshots


def test_two_jobs(
        snappy_command, mocked_config_file, temp_filesystem,
        other_temp_filesystem):
    mocked_config_file.write_text(
        f'[[snapshot]]\n'
        f'datasets = ["{temp_filesystem}"]\n'
        f'[[snapshot]]\n'
        f'datasets = ["{other_temp_filesystem}"]\n'
        f'prefix = "foo"\n')

    snappy_command('--auto')

    assert get_snapshots(temp_filesystem) == ['snappy-2001-02-03-081500']
    assert get_snapshots(other_temp_filesystem) == ['foo-2001-02-03-091500']
