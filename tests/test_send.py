import sys
from datetime import datetime
from functools import wraps
from subprocess import check_call, CalledProcessError

import pytest

from conftest import get_mount_point, get_snapshots, run_command


@pytest.fixture
def send_target(filesystems):
    return filesystems('target', create=False)


def test_send(snappy_command, filesystem, send_target):
    file_path = get_mount_point(filesystem) / 'file1'
    file_path.touch()

    snappy_command(f'-s {send_target} {filesystem}')

    # Make sure we're not mixing up the filesystems.
    file_path.unlink()

    assert not get_snapshots(filesystem)
    assert len(get_snapshots(send_target)) == 1
    assert (get_mount_point(send_target) / 'file1').exists()


def test_send_multiple_snapshots(snappy_command, filesystem, send_target):
    snappy_command(f'{filesystem}')
    snappy_command(f'{filesystem}')
    snappy_command(f'-S -s {send_target} {filesystem}')

    assert not get_snapshots(filesystem)
    assert len(get_snapshots(send_target)) == 2


def test_send_multiple_times(snappy_command, filesystem, send_target):
    snappy_command(f'-s {send_target} {filesystem}')
    assert not get_snapshots(filesystem)
    assert len(get_snapshots(send_target)) == 1

    snappy_command(f'-s {send_target} {filesystem}')
    assert not get_snapshots(filesystem)
    assert len(get_snapshots(send_target)) == 2


def test_prune_target(snappy_command, filesystem, send_target):
    snappy_command(f'-s {send_target} {filesystem}')
    snappy_command(f'-s {send_target} {filesystem}')
    snappy_command(f'-k 1 -s {send_target} {filesystem}')

    # The snapshots on the target are pruned.
    assert len(get_snapshots(send_target)) == 1


@pytest.mark.parametrize('create_snapshot', [True, False])
def test_target_modified(
        snappy_command, filesystem, send_target, create_snapshot):
    file_path = get_mount_point(filesystem) / 'file1'
    file_path.touch()

    snappy_command(f'-s {send_target} {filesystem}')

    file_on_target_path = get_mount_point(send_target) / 'file2'
    file_on_target_path.touch()

    if create_snapshot:
        # Additionally create a snapshot on the target filesystem.
        run_command('zfs', 'snapshot', f'{send_target}@foo')

    snappy_command(f'-s {send_target} {filesystem}')

    # TODO: This should probably be changed to result in an error.
    # The new data should simply be overwritten.
    assert not file_on_target_path.exists()


def test_recursive(snappy_command, filesystem, send_target):
    run_command('zfs', 'create', f'{filesystem}/child')
    (get_mount_point(filesystem) / 'file1').touch()
    (get_mount_point(filesystem) / 'child/file2').touch()

    snappy_command(f'-r -s {send_target} {filesystem}')

    assert len(get_snapshots(send_target)) == 1
    assert len(get_snapshots(f'{send_target}/child')) == 1

    # Make sure we're sending the right filesystems to the right targets.
    assert (get_mount_point(send_target) / 'file1').exists()
    assert (get_mount_point(send_target) / 'child/file2').exists()

    # Create an additional child filesystem and send again.
    run_command('zfs', 'create', f'{filesystem}/child2')
    (get_mount_point(filesystem) / 'child2/file3').touch()

    snappy_command(f'-r -s {send_target} {filesystem}')

    # Check that everything makes sense.
    assert len(get_snapshots(send_target)) == 2
    assert len(get_snapshots(f'{send_target}/child')) == 2
    assert len(get_snapshots(f'{send_target}/child2')) == 1
    assert (get_mount_point(send_target) / 'child2/file3').exists()

    # Destroy one of the children and send again.
    run_command('zfs', 'destroy', f'{filesystem}/child')
    snappy_command(f'-r -s {send_target} {filesystem}')

    # Check that everything makes sense. The deleted child should still exist on
    # the target.
    assert len(get_snapshots(send_target)) == 3
    assert len(get_snapshots(f'{send_target}/child')) == 2
    assert len(get_snapshots(f'{send_target}/child2')) == 2


@pytest.mark.parametrize('use_send', [True, False])
def test_target_already_exists(
        snappy_command, filesystem, other_filesystem, send_target, use_send,
        expect_message, mocked_datetime_now):
    # Try two different ways that the target filesystem is created before the
    # send command we want to test.
    if use_send:
        # Send a different filesystem to the same target.
        (get_mount_point(filesystem) / 'file1').touch()
        snappy_command(f'-s {send_target} {filesystem}')
    else:
        # Create a filesystem with the target name.
        run_command('zfs', 'create', send_target)
        run_command('zfs', 'snapshot', f'{send_target}@a')
        (get_mount_point(send_target) / 'file1').touch()

    (get_mount_point(other_filesystem) / 'file2').touch()

    mocked_datetime_now(datetime(2001, 2, 4, 10))

    # The name to which we expect the target filesystem to be moved to on the
    # next send.
    moved_target = f'{send_target}-snappy-moved-2001-02-04-110000'
    moved_target_name = moved_target.rsplit('/', 1)[1]

    with expect_message(f'has been renamed to {moved_target_name}'):
        snappy_command(f'-s {send_target} {other_filesystem}')

    assert len(get_snapshots(send_target)) == 1
    assert len(get_snapshots(moved_target)) == 1

    assert (get_mount_point(send_target) / 'file2').exists()
    assert (get_mount_point(moved_target) / 'file1').exists()


@pytest.mark.parametrize('what', ['snapshot', 'bookmark'])
def test_snapshot_bookmark_lost(
        snappy_command, filesystem, send_target, expect_message, what):
    (get_mount_point(filesystem) / 'file1').touch()

    snappy_command(f'-s {send_target} {filesystem}')

    if what == 'snapshot':
        # Remove the snapshot that we just sent.
        run_command('zfs', 'destroy', f'{send_target}@snappy-2001-02-03-081500')
    else:
        assert what == 'bookmark'

        # Remove the bookmark that was created as part of sending.
        run_command('zfs', 'destroy', f'{filesystem}#snappy-2001-02-03-081500')

    # The name to which we expect the target filesystem to be moved to on the
    # next send.
    moved_target = f'{send_target}-snappy-moved-2001-02-03-101500'
    moved_target_name = moved_target.rsplit('/', 1)[1]

    with expect_message(f'has been renamed to {moved_target_name}'):
        snappy_command(f'-s {send_target} {filesystem}')

    # The same file should exist in both filesystems as both are a result of
    # sending the same source filesystem.
    assert (get_mount_point(send_target) / 'file1').exists()
    assert (get_mount_point(moved_target) / 'file1').exists()


class Aborted(Exception):
    pass


def abort_after_n_calls(num_calls, fn):
    """
    Wraps a function so that it will allow the specified number of call to
    happen and raise `Aborted` on each call afterward.
    """
    @wraps(fn)
    def wrapped_fn(*args, **kwargs):
        nonlocal num_calls

        if not num_calls:
            raise Aborted

        num_calls -= 1

        return fn(*args, **kwargs)

    return wrapped_fn


# Number of calls to `subprocess.check_call()` it takes to complete the send
# operation below. This is used to generate test cases that abort the send after
# each of those operations.
_num_operations = 10


@pytest.mark.parametrize('allowed_operations', range(1, _num_operations + 1))
@pytest.mark.parametrize('interference', [True, False])
def test_interrupted(
        snappy_command, filesystem, send_target, allowed_operations,
        interference, monkeypatch, mocked_datetime_now):
    child_filesystem = f'{filesystem}/child'
    send_target_child = f'{send_target}/child'

    # Two filesystems and two snapshots.
    run_command('zfs', 'create', child_filesystem)
    snappy_command(f'-r {filesystem}')
    snappy_command(f'-r {filesystem}')

    # Add 1, because we want to allow `allowed_operations` operations and abort
    # _after_ that.
    original_check_call = check_call.__wrapped__
    monkeypatch.setattr(
        check_call,
        '__wrapped__',
        abort_after_n_calls(allowed_operations, original_check_call))

    try:
        snappy_command(f'-rS -s {send_target} {filesystem}')
        aborted = False
    except Aborted as e:
        print('>> Command aborted <<', file=sys.stderr)
        aborted = True

    # Check that the operation _only_ completes after `_num_operations`
    # operations, otherwise that value needs to adjusted to make sure we're
    # testing every case.
    assert (allowed_operations < _num_operations) == aborted

    if interference:
        # Remove all snapshots on the target filesystem. The filesystem might
        # not yet exist or not yet have snapshot.
        run_command('zfs', 'create', '-p', send_target)
        run_command('zfs', 'snapshot', f'{send_target}@foo')
        run_command('zfs', 'destroy', f'{send_target}@%')

    # Replace the original function, all calls should work again from now on.
    monkeypatch.setattr(check_call, '__wrapped__', original_check_call)

    mocked_datetime_now(datetime(2001, 2, 4, 10))

    # Create another snapshot on the source and then try to complete the send
    # operation.
    snappy_command(f'-r {filesystem}')
    snappy_command(f'-rS -s {send_target} {filesystem}')

    # All (remaining) snapshots should be gone from the source filesystems.
    assert not get_snapshots(filesystem)
    assert not get_snapshots(child_filesystem)

    # We can only guarantee that the last snapshot will remain, the others could
    # be lost due to us replacing the target filesystems after some snapshots
    # have already been sent.
    assert 'snappy-2001-02-04-100000' in get_snapshots(send_target)
    assert 'snappy-2001-02-04-100000' in get_snapshots(send_target_child)

    if not interference:
        # If we did nothing to the send target, so we should get all three
        # snapshots.
        assert len(get_snapshots(send_target)) == 3
        assert len(get_snapshots(send_target_child)) == 3


# TODO: Add test: Replace child filesystem with file.
# TODO: Add test: Have unrelated snapshots on source.
# TODO: Add test: Change prefix while sending snapshots.
# TODO: Add test: Using root of pool as send target.
