import re
from contextlib import contextmanager

import pytest

from conftest import get_snapshots, zfs


def test_create_snapshot(temp_filesystem, snappy_command):
    snappy_command(f'{temp_filesystem}')

    assert get_snapshots(temp_filesystem) == ['snappy-2001-02-03-081500']


def test_prune(temp_filesystem, snappy_command):
    for i in range(3):
        snappy_command(f'{temp_filesystem}')

    assert len(get_snapshots(temp_filesystem)) == 3

    snappy_command(f'-p -k 1 {temp_filesystem}')

    assert len(get_snapshots(temp_filesystem)) == 1

    snappy_command(f'-p -k 0 {temp_filesystem}')

    assert len(get_snapshots(temp_filesystem)) == 0


def test_create_and_prune_snapshot(temp_filesystem, snappy_command):
    snappy_command(f'{temp_filesystem}')
    snappy_command(f'{temp_filesystem}')
    snappy_command(f'-k1 {temp_filesystem}')

    assert get_snapshots(temp_filesystem) == ['snappy-2001-02-03-101500']


def test_recursive(temp_filesystem, snappy_command):
    child_filesystem = f'{temp_filesystem}/child'
    zfs('create', child_filesystem)

    # Should not create recursive snapshots.
    snappy_command(f'{temp_filesystem}')

    assert get_snapshots(temp_filesystem) == ['snappy-2001-02-03-081500']
    assert get_snapshots(child_filesystem) == []

    # Should create recursive snapshots.
    snappy_command(f'-k1 -r {temp_filesystem}')

    assert get_snapshots(temp_filesystem) == ['snappy-2001-02-03-091500']
    assert get_snapshots(temp_filesystem) == ['snappy-2001-02-03-091500']


def test_multiple_filesystems(
        temp_filesystem, other_temp_filesystem, snappy_command):
    snappy_command(f'{temp_filesystem} {other_temp_filesystem}')
    snappy_command(f'-k1 {temp_filesystem} {other_temp_filesystem}')

    assert get_snapshots(temp_filesystem) == ['snappy-2001-02-03-091500']
    assert get_snapshots(other_temp_filesystem) == ['snappy-2001-02-03-091500']


def test_invalid_argument_combinations(snappy_command, capsys):
    @contextmanager
    def fails_with_message(message_pattern: str):
        with pytest.raises(SystemExit):
            yield

        assert re.search(message_pattern, capsys.readouterr().err)

    with fails_with_message('required: datasets'):
        snappy_command('')

    with fails_with_message('--prune-only requires --keep'):
        snappy_command('-p foo')
