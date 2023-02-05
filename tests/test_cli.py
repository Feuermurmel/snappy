import re
from contextlib import contextmanager

import pytest

from conftest import list_snapshots


def test_create_snapshot(temp_filesystem, snappy_command):
    snappy_command(temp_filesystem)

    assert list_snapshots(temp_filesystem) == [
        f'{temp_filesystem}@snappy-2001-02-03-081500']


def test_prune(temp_filesystem, snappy_command):
    for i in range(3):
        snappy_command(temp_filesystem)

    assert len(list_snapshots(temp_filesystem)) == 3

    snappy_command(f'-p -k 1 {temp_filesystem}')

    assert len(list_snapshots(temp_filesystem)) == 1

    snappy_command(f'-p -k 0 {temp_filesystem}')

    assert len(list_snapshots(temp_filesystem)) == 0


def test_create_and_prune_snapshot(temp_filesystem, snappy_command):
    snappy_command(temp_filesystem)
    snappy_command(temp_filesystem)
    snappy_command(f'-k1 {temp_filesystem}')

    assert list_snapshots(temp_filesystem) == [
        f'{temp_filesystem}@snappy-2001-02-03-101500']


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
