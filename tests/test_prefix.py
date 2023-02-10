from conftest import get_snapshots, zfs


def test_create_snapshot(temp_filesystem, snappy_command):
    snappy_command(f'{temp_filesystem} -p foo')

    assert get_snapshots(temp_filesystem) == ['foo-2001-02-03-081500']


def test_prune(temp_filesystem, snappy_command):
    snappy_command(f'{temp_filesystem}')
    snappy_command(f'{temp_filesystem} -p foo')
    snappy_command(f'{temp_filesystem}')
    snappy_command(f'{temp_filesystem} -p foo')

    snappy_command(f'-S -k 1 {temp_filesystem} -p foo')

    assert get_snapshots(temp_filesystem) == ['snappy-2001-02-03-081500', 'snappy-2001-02-03-101500', 'foo-2001-02-03-111500']
