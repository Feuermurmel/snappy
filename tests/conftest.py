from __future__ import annotations

import itertools
import re
import shlex
import subprocess
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from snappy import entry_point


temp_zpool_vdev_path = Path('/dev/shm/snappy-test-vdev')
temp_zpool_name = 'snappy-test-zpool'


def zpool(*args: str | Path) -> list[str]:
    return subprocess.check_output(['zpool', *args], text=True).splitlines()


def zfs(*args: str | Path) -> list[str]:
    return subprocess.check_output(['zfs', *args], text=True).splitlines()


def get_mount_point(filesystem: str) -> Path:
    mount_point, = zfs('list', '-Hp', '-o', 'mountpoint', filesystem)

    return Path(mount_point)


def get_snapshots(filesystem: str) -> list[str]:
    return [
        i.removeprefix(f'{filesystem}@')
        for i in zfs('list', '-Hpr', '-d', '1', '-t', 'snapshot', '-o', 'name', filesystem)]


def cleanup_temp_zpool():
    active_zpools = zpool('list', '-Hp', '-o', 'name')

    if temp_zpool_name in active_zpools:
        zpool('export', temp_zpool_name)

    if temp_zpool_vdev_path.exists():
        temp_zpool_vdev_path.unlink()


@pytest.fixture(scope='session')
def temp_zpool():
    cleanup_temp_zpool()

    subprocess.check_call(['truncate', '-s', '100M', temp_zpool_vdev_path])
    zpool('create', temp_zpool_name, temp_zpool_vdev_path)

    yield temp_zpool_name

    cleanup_temp_zpool()


@pytest.fixture
def temp_filesystems(temp_zpool):
    temp_filesystem_counter = itertools.count(1)

    @contextmanager
    def temp_filesystems_fixture():
        seq = next(temp_filesystem_counter)
        name = f'{temp_zpool}/fs{seq}'

        zfs('create', name)

        yield name

        zfs('destroy', '-r', name)

    return temp_filesystems_fixture


@pytest.fixture
def temp_filesystem(temp_filesystems):
    with temp_filesystems() as name:
        yield name


@pytest.fixture
def other_temp_filesystem(temp_filesystems):
    with temp_filesystems() as name:
        yield name


@pytest.fixture
def snappy_command(monkeypatch):
    def command(args: str):
        monkeypatch.setattr('sys.argv', shlex.split(f'snappy {args}'))
        entry_point()

    return command


@pytest.fixture
def fails_with_message(capsys):
    @contextmanager
    def fails_with_message_context(message_pattern: str):
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
