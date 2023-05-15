from __future__ import annotations

import logging
from datetime import datetime
from subprocess import CalledProcessError
from typing import Iterable, TypeVar, Callable

from snappy.snapshots import parse_snapshot_name
from snappy.utils import timestamp_format
from snappy.zfs import send_receive_snapshot, Snapshot, Bookmark, \
    list_snapshots, Dataset, list_snapshots_and_bookmarks, create_bookmark, \
    destroy_bookmark, destroy_snapshots, rename_dataset


class CannotMoveRootOfPoolException(Exception):
    pass


def _move_target_away(dataset: Dataset) -> None:
    parent_name, sep, base_name = dataset.rpartition('/')
    new_base_name = \
        f'{base_name}-snappy-moved-{datetime.now():{timestamp_format}}'

    # The root filesystem of a pool cannot be moved to somewhere else in the
    # hierarchy.
    if not parent_name:
        raise CannotMoveRootOfPoolException

    new_dataset = Dataset(f'{parent_name}{sep}{new_base_name}')

    rename_dataset(dataset, new_dataset)

    logging.warning(
        f'Warning: Dataset at send target {dataset} has been renamed '
        f'to {new_base_name}.')


T = TypeVar('T')


def _get_first(seq: Iterable[T], predicate: Callable[[T], bool]) -> T | None:
    for i in seq:
        if predicate(i):
            return i

    return None


def send_snapshots(source: Dataset, target: Dataset, prefix: str) -> None:
    source_snapshots, source_bookmarks = list_snapshots_and_bookmarks(source)

    try:
        target_snapshots = list_snapshots(target, quiet=True)
        target_exists = True
    except CalledProcessError:
        # We assume that if listing snapshots fails, that the target filesystem
        # does not exist. It will be created later.
        target_snapshots = []
        target_exists = False

    if target_snapshots:
        # Target snapshot that will be the basis of the next incremental send.
        most_recent_target_snapshot_guid = target_snapshots[-1].guid

        # The bookmark on the source that corresponds to the most recent
        # snapshot on the target.
        incremental_bookmark_info = _get_first(
            source_bookmarks,
            lambda x: x.guid == most_recent_target_snapshot_guid)

        if incremental_bookmark_info is None:
            incremental_bookmark = None
        else:
            incremental_bookmark = incremental_bookmark_info.ref
    else:
        most_recent_target_snapshot_guid = None
        incremental_bookmark = None

    if incremental_bookmark is None and target_exists:
        # The target filesystem exist, but has no snapshot/bookmark in common
        # with the source. We assume that this is a filesystem unrelated to the
        # source and thus rename it. This could e.g. happen if the source
        # filesystem has been destroyed and re-created.
        _move_target_away(target)

    # Clean up left-over bookmarks. This might happen if the process was aborted
    # after sending a snapshot but before removing the incremental source
    # bookmark.
    for i in source_bookmarks:
        # Delete all bookmarks with the right prefix, except for the incremental
        # source bookmark we're going to use.
        if parse_snapshot_name(i.ref.name, prefix) is not None \
                and i.ref != incremental_bookmark:
            destroy_bookmark(i.ref)

    for snapshot in source_snapshots:
        # Ignore snapshots without the specified prefix.
        if parse_snapshot_name(snapshot.ref.name, prefix) is None:
            continue

        # We can skip everything and just delete the snapshot if that snapshot
        # has already been sent to the target but not yet deleted from the
        # source.
        if snapshot.guid != most_recent_target_snapshot_guid:
            # Create a bookmark of the snapshot we're going to send. For the
            # logic above to work, this bookmark needs to exist before receiving
            # the snapshot completes.
            new_incremental_bookmark = Bookmark(source, snapshot.ref.name)
            create_bookmark(snapshot.ref, new_incremental_bookmark)

            # Send the snapshot.
            target_snapshot = Snapshot(target, snapshot.ref.name)
            send_receive_snapshot(incremental_bookmark, snapshot.ref, target_snapshot)

            # Destroy the old bookmark that we used for the incremental send.
            if incremental_bookmark is not None:
                destroy_bookmark(incremental_bookmark)

            incremental_bookmark = new_incremental_bookmark

        destroy_snapshots([snapshot.ref])
