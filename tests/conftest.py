import itertools
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

temp_zpool_vdev_path = Path('/dev/shm/snappy-test-vdev')
temp_zpool_name = 'snappy-test-zpool'


def cleanup_temp_zpool():
    active_zpools = subprocess \
        .check_output(['zpool', 'list', '-Hp', '-o', 'name'], text=True) \
        .splitlines()

    if temp_zpool_name in active_zpools:
        subprocess.check_call(['zpool', 'export', temp_zpool_name])

    if temp_zpool_vdev_path.exists():
        temp_zpool_vdev_path.unlink()


@pytest.fixture(scope='session')
def temp_zpool():
    cleanup_temp_zpool()

    subprocess \
        .check_call(['truncate', '-s', '100M', temp_zpool_vdev_path])

    subprocess \
        .check_call(['zpool', 'create', temp_zpool_name, temp_zpool_vdev_path])

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

    subprocess.check_call(['zfs', 'create', name])
    mountpoint, = subprocess \
        .check_output(['zfs', 'list', '-Hp', '-o', 'mountpoint', name], text=True) \
        .splitlines()

    yield TempFilesystem(name, Path(mountpoint))

    subprocess.check_call(['zfs', 'destroy', '-r', name])
