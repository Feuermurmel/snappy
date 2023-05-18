from conftest import get_snapshots, run_command


def test_create_snapshot(filesystem, snappy_command):
    snappy_command(f'{filesystem}')

    assert get_snapshots(filesystem) == ['snappy-2001-02-03-081500']


def test_multiple_keep(filesystem, snappy_command):
    for i in range(3):
        snappy_command(f'{filesystem}')

    snappy_command(f'-S -k 1,1d {filesystem}')

    assert get_snapshots(filesystem) == \
           ['snappy-2001-02-03-081500', 'snappy-2001-02-03-101500']


def test_recursive(filesystem, snappy_command):
    child_filesystem = f'{filesystem}/child'
    run_command('zfs', 'create', child_filesystem)

    # Should not create recursive snapshots.
    snappy_command(f'{filesystem}')

    assert get_snapshots(filesystem) == ['snappy-2001-02-03-081500']
    assert get_snapshots(child_filesystem) == []

    # Should create recursive snapshots.
    snappy_command(f'-k1 -r {filesystem}')

    assert get_snapshots(filesystem) == ['snappy-2001-02-03-091500']
    assert get_snapshots(filesystem) == ['snappy-2001-02-03-091500']


def test_exclude(filesystem, snappy_command):
    """
    Test that --exclude is correctly handled, including when children of
    excluded filesystems are included again.
    """
    included_filesystems = [
            f'{filesystem}',
            f'{filesystem}/child1/a',
            f'{filesystem}/child1/a/x',
            f'{filesystem}/child2']

    excluded_filesystems = [
        f'{filesystem}/child1',
        f'{filesystem}/child1/b']

    # Merge and sort two lists so that parents are created before children.
    # `filesystem` was already created by the fixture.
    for i in sorted((*included_filesystems[1:], *excluded_filesystems)):
        run_command('zfs', 'create', i)

    snappy_command(
        f'-r --exclude={filesystem}/child1 --exclude={filesystem}/child1/b '
        f'{filesystem} {filesystem}/child1/a')

    for i in included_filesystems:
        assert get_snapshots(i)

    for i in excluded_filesystems:
        assert not get_snapshots(i)


def test_multiple_filesystems(
        filesystem, other_filesystem, snappy_command):
    snappy_command(f'{filesystem} {other_filesystem}')
    snappy_command(f'-k1 {filesystem} {other_filesystem}')

    assert get_snapshots(filesystem) == ['snappy-2001-02-03-091500']
    assert get_snapshots(other_filesystem) == ['snappy-2001-02-03-091500']
