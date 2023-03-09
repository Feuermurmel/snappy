from conftest import get_snapshots


def test_prune(filesystem, snappy_command):
    for i in range(3):
        snappy_command(f'{filesystem}')

    assert len(get_snapshots(filesystem)) == 3

    snappy_command(f'-S -k 1 {filesystem}')

    assert len(get_snapshots(filesystem)) == 1


def test_create_and_prune_snapshot(filesystem, snappy_command):
    snappy_command(f'{filesystem}')
    snappy_command(f'{filesystem}')
    snappy_command(f'-k1 {filesystem}')

    assert get_snapshots(filesystem) == ['snappy-2001-02-03-101500']


def test_last_snapshot_kept(filesystem, snappy_command):
    snappy_command(f'{filesystem}')
    snappy_command(f'{filesystem}')
    snappy_command(f'-k 1d {filesystem}')

    # Check that the most recent snapshot is always kept. This is necessary to
    # prevent losing the most recent snapshot on a received dataset.
    assert get_snapshots(filesystem) == \
           ['snappy-2001-02-03-081500', 'snappy-2001-02-03-101500']
