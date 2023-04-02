from __future__ import annotations

import re
import shlex
import subprocess
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from pytest import MonkeyPatch

import snappy.config
from snappy.cli import entry_point
from snappy.config import Config


temp_zpool_vdev_path = Path('/dev/shm/snappy-test-vdev')
temp_zpool_name = 'snappy-test-zpool'


def run_command(*cmdline: str | Path) -> list[str]:
    return subprocess.check_output(cmdline, text=True).splitlines()


def get_mount_point(filesystem: str) -> Path:
    mount_point, = run_command('zfs', 'list', '-Hp', '-o', 'mountpoint', filesystem)

    return Path(mount_point)


def get_snapshots(filesystem: str) -> list[str]:
    return [
        i.removeprefix(f'{filesystem}@')
        for i in run_command('zfs', 'list', '-Hpr', '-d', '1', '-t', 'snapshot', '-o', 'name', filesystem)]


def cleanup_temp_zpool():
    active_zpools = run_command('zpool', 'list', '-Hp', '-o', 'name')

    if temp_zpool_name in active_zpools:
        run_command('zpool', 'export', temp_zpool_name)

    if temp_zpool_vdev_path.exists():
        temp_zpool_vdev_path.unlink()


@pytest.fixture(scope='session')
def zpool():
    cleanup_temp_zpool()

    run_command('truncate', '-s', '100M', temp_zpool_vdev_path)
    run_command('zpool', 'create', temp_zpool_name, temp_zpool_vdev_path)

    yield temp_zpool_name

    cleanup_temp_zpool()


@pytest.fixture
def filesystems(zpool):
    root_temp_filesystem = f'{zpool}/t'

    run_command('zfs', 'create', root_temp_filesystem)

    def temp_filesystems_fixture(basename: str, create: bool = True) -> str:
        name = f'{root_temp_filesystem}/{basename}'

        if create:
            run_command('zfs', 'create', name)

        return name

    yield temp_filesystems_fixture

    run_command('zfs', 'destroy', '-R', root_temp_filesystem)


@pytest.fixture
def filesystem(filesystems):
    return filesystems('temp')


@pytest.fixture
def other_filesystem(filesystems):
    return filesystems('other')


@pytest.fixture
def snappy_command(monkeypatch):
    def snappy_command_fixture(args: str) -> None:
        monkeypatch.setattr('sys.argv', shlex.split(f'snappy {args}'))
        entry_point()

    return snappy_command_fixture


@pytest.fixture
def fails_with_message(capsys):
    @contextmanager
    def fails_with_message_context(message_pattern):
        with pytest.raises(SystemExit):
            yield

        assert re.search(message_pattern, capsys.readouterr().err)

    return fails_with_message_context


@pytest.fixture(autouse=True)
def mocked_datetime_now(monkeypatch):
    """
    Mock datetime_now() used to generate snapshot names so that we can have
    consistent snapshot names during tests.
    """
    now = datetime(2001, 2, 3, 7, 15, 0)

    def mock_datetime_now():
        nonlocal now

        now += timedelta(hours=1)

        return now

    monkeypatch.setattr('snappy.snappy._datetime_now', mock_datetime_now)


@pytest.fixture
def mocked_config_file(monkeypatch: MonkeyPatch, tmp_path: Path) -> Path:
    config_path = tmp_path / 'mocked_config_file.toml'

    def mock_load_config(path: Path) -> Config:
        return orig_load_config(config_path)

    orig_load_config = snappy.config._load_config
    monkeypatch.setattr('snappy.config._load_config', mock_load_config)

    return config_path
