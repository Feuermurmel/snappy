from conftest import get_snapshots


def test_prune(temp_filesystem, snappy_command):
    for i in range(3):
        snappy_command(f'{temp_filesystem}')

    assert len(get_snapshots(temp_filesystem)) == 3

    snappy_command(f'-S -k 1 {temp_filesystem}')

    assert len(get_snapshots(temp_filesystem)) == 1


def test_create_and_prune_snapshot(temp_filesystem, snappy_command):
    snappy_command(f'{temp_filesystem}')
    snappy_command(f'{temp_filesystem}')
    snappy_command(f'-k1 {temp_filesystem}')

    assert get_snapshots(temp_filesystem) == ['snappy-2001-02-03-101500']
