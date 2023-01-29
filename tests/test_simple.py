from __future__ import annotations

from pathlib import Path

import pytest

from conftest import zfs
from snappy import entry_point


@pytest.fixture
def snappy_command(monkeypatch):
    def command(*args: str | Path):
        monkeypatch.setattr('sys.argv', ['snappy', *args])
        entry_point()

    return command


def test_temp_fs(temp_filesystem):
    (temp_filesystem.path / 'file').touch()


def test_create_snapshot(temp_filesystem, snappy_command):
    snappy_command(temp_filesystem.name)

    snapshots = zfs('list', '-Hp', '-r', '-t', 'snapshot', '-o', 'name', temp_filesystem.name)

    assert len(snapshots) == 1
    assert snapshots[0].split('@', 1)[1].startswith('snappy-')
