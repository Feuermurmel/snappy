from __future__ import annotations

import itertools
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest


temp_zpool_vdev_path = Path('/dev/shm/snappy-test-vdev')
temp_zpool_name = 'snappy-test-zpool'


def zpool(*args: str | Path) -> list[str]:
    return subprocess.check_output(['zpool', *args], text=True).splitlines()


def zfs(*args: str | Path) -> list[str]:
    return subprocess.check_output(['zfs', *args], text=True).splitlines()


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


temp_filesystem_counter = itertools.count(1)


@dataclass
class TempFilesystem:
    name: str
    path: Path


@pytest.fixture
def temp_filesystem(temp_zpool):
    seq = next(temp_filesystem_counter)
    name = f'{temp_zpool}/fs{seq}'

    zfs('create', name)
    mountpoint, = zfs('list', '-Hp', '-o', 'mountpoint', name)

    yield TempFilesystem(name, Path(mountpoint))

    zfs('destroy', '-r', name)
