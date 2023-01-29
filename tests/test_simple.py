from __future__ import annotations

from conftest import list_snapshots


def test_create_snapshot(temp_filesystem, snappy_command):
    snappy_command(temp_filesystem)

    assert list_snapshots(temp_filesystem) == [
        f'{temp_filesystem}@snappy-2001-02-03-081500']


def test_prune(temp_filesystem, snappy_command):
    for i in range(3):
        snappy_command(temp_filesystem)

    assert len(list_snapshots(temp_filesystem)) == 3

    snappy_command('-p', '-k', '1', temp_filesystem)

    assert len(list_snapshots(temp_filesystem)) == 1
