from conftest import get_snapshots


def test_create_snapshot(filesystem, snappy_command):
    snappy_command(f'{filesystem} -p foo')

    assert get_snapshots(filesystem) == ['foo-2001-02-03-081500']


def test_prune(filesystem, snappy_command):
    snappy_command(f'{filesystem}')
    snappy_command(f'{filesystem} -p foo')
    snappy_command(f'{filesystem}')
    snappy_command(f'{filesystem} -p foo')

    snappy_command(f'-S -k 1 {filesystem} -p foo')

    assert get_snapshots(filesystem) == ['snappy-2001-02-03-081500', 'snappy-2001-02-03-101500', 'foo-2001-02-03-111500']
