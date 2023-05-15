from __future__ import annotations

import datetime
import re
import shlex
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator, ContextManager

import pytest
import toml
from _pytest.capture import CaptureFixture
from pytest import MonkeyPatch

from snappy.test_utils import mockable_fn


temp_zpool_vdev_path = Path('/dev/shm/snappy-test-vdev')
temp_zpool_name = 'snappy-test-zpool'


def pytest_sessionstart(session):
    # Allow mocking of the current time.
    class MockableDatetime(datetime.datetime):
        now = mockable_fn(datetime.datetime.now)

    datetime.datetime = MockableDatetime
    toml.load = mockable_fn(toml.load)
    subprocess.check_call = mockable_fn(subprocess.check_call)


def run_command(*cmdline: str | Path) -> list[str]:
    return subprocess.check_output(cmdline, text=True).splitlines()


def get_mount_point(filesystem: str) -> Path:
    mount_point, = run_command('zfs', 'list', '-Hp', '-o', 'mountpoint', filesystem)

    return Path(mount_point)


def _zfs_list(filesystem: str, type: str) -> list[str]:
    output_lines = \
        run_command('zfs', 'list', '-Hpr', '-d', '1', '-t', type, '-o', 'name', filesystem)

    # Strip fs@ or fs# prefix from each returned entry.
    return [i[len(filesystem) + 1:] for i in output_lines]


def get_snapshots(filesystem: str) -> list[str]:
    return _zfs_list(filesystem, 'snapshot')


def get_bookmarks(filesystem: str) -> list[str]:
    return _zfs_list(filesystem, 'bookmark')


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
    return filesystems('fs')


@pytest.fixture
def other_filesystem(filesystems):
    return filesystems('other')


@pytest.fixture
def snappy_command(monkeypatch):
    from snappy.cli import entry_point

    def snappy_command_fixture(args: str) -> None:
        cmdline = f'snappy {args}'

        print(f'$ {cmdline}', file=sys.stderr)

        monkeypatch.setattr('sys.argv', shlex.split(cmdline))
        entry_point()

    return snappy_command_fixture


@pytest.fixture
def expect_message(
        capsys: CaptureFixture[str]) \
        -> Callable[[str], ContextManager[None]]:
    @contextmanager
    def expect_message_context(message_pattern: str) -> Iterator[None]:
        yield

        output = capsys.readouterr().err

        assert re.search(message_pattern, output), \
               f'Output did not contain the expected pattern "{message_pattern}":\n' \
               f'\n' \
               f'{output}'

    return expect_message_context


@pytest.fixture
def fails_with_message(expect_message):
    @contextmanager
    def fails_with_message_context(message_pattern):
        with pytest.raises(SystemExit), expect_message(message_pattern):
            yield

    return fails_with_message_context


@pytest.fixture(autouse=True)
def mocked_datetime_now(monkeypatch):
    """
    Mock datetime.datetime.now() used to generate snapshot names so that we can
    have consistent snapshot names during tests.
    """
    current_time = datetime.datetime(2001, 2, 3, 8, 15, 0)

    def mock_datetime_now(tz=None):
        nonlocal current_time

        now = current_time
        current_time += datetime.timedelta(hours=1)

        return now

    def set_current_time(time):
        nonlocal current_time

        current_time = time

    monkeypatch.setattr(datetime.datetime.now, '__wrapped__', mock_datetime_now)

    return set_current_time


@pytest.fixture
def mocked_config_file(monkeypatch: MonkeyPatch, tmp_path: Path) -> Path:
    import snappy
    from snappy.config import Config

    config_path = tmp_path / 'mocked_config_file.toml'

    def mock_load_config(path: Path) -> Config:
        return orig_load_config(config_path)

    orig_load_config: Callable[[Path], Config] = \
        snappy.config.load_config.__wrapped__  # type: ignore

    monkeypatch.setattr(snappy.config.load_config, '__wrapped__', mock_load_config)

    return config_path
