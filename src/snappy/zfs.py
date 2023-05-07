from __future__ import annotations

import logging
from dataclasses import dataclass
from subprocess import check_call, check_output
from typing import NewType, Iterable, TypeAlias, TypeVar, Generic, Sequence

from snappy.utils import check_call_pipeline


# Sadly a misnomer as this is only used to refer to filesystems and volumes, but
# calling it just Filesystem seems even more confusing and would contradict the
# property names in config files.
Dataset = NewType('Dataset', str)


@dataclass(frozen=True)
class Snapshot:
    dataset: Dataset
    name: str

    def __str__(self) -> str:
        return f'{self.dataset}@{self.name}'


@dataclass(frozen=True)
class Bookmark:
    dataset: Dataset
    name: str

    def __str__(self) -> str:
        return f'{self.dataset}#{self.name}'


SnapshotOrBookmarkT = \
    TypeVar('SnapshotOrBookmarkT', Snapshot, Bookmark, covariant=True)


@dataclass(frozen=True)
class _Info(Generic[SnapshotOrBookmarkT]):
    ref: SnapshotOrBookmarkT
    guid: int
    createtxg: int


SnapshotInfo: TypeAlias = _Info[Snapshot]
BookmarkInfo: TypeAlias = _Info[Bookmark]


def create_snapshots(snapshots: list[Snapshot], recursive: bool) -> None:
    recursive_arg = ['-r'] if recursive else []
    snapshot_args = [str(i) for i in snapshots]

    logging.info(f'Creating snapshots: {", ".join(snapshot_args)}')
    check_call(['zfs', 'snapshot', *recursive_arg, '--', *snapshot_args])


def create_bookmark(snapshot: Snapshot, bookmark: Bookmark) -> None:
    logging.info(f'Creating bookmark: {bookmark}')
    check_call(['zfs', 'bookmark', f'{snapshot}', f'{bookmark}'])


def list_children(dataset: Dataset) -> list[Dataset]:
    output = check_output(
        ['zfs', 'list', '-H', '-r', '-t', 'filesystem,volume', '-o', 'name',
         '--', dataset],
        text=True)

    return [Dataset(i) for i in output.splitlines()]


def _list_snapshots_and_bookmarks(
        dataset: Dataset, types: str) \
        -> tuple[Sequence[SnapshotInfo], Sequence[BookmarkInfo]]:
    """
    Return a list of snapshots of the specified dataset, ordered by createtxg.
    """
    output = check_output(
        ['zfs', 'list', '-Hpd1', '-t', types, '-o', 'name,guid,createtxg',
         '-s', 'createtxg', '--', dataset],
        text=True)

    snapshots: list[SnapshotInfo] = []
    bookmarks: list[BookmarkInfo] = []

    for line in output.splitlines():
        full_name, guid_str, createtxg_str = line.split('\t')
        guid = int(guid_str)
        createtxg = int(createtxg_str)

        if '@' in full_name:
            dataset_name, name = full_name.split('@')

            snapshots.append(_Info(Snapshot(dataset, name), guid, createtxg))
        else:
            dataset_name, name = full_name.split('#')

            bookmarks.append(_Info(Bookmark(dataset, name), guid, createtxg))

    return snapshots, bookmarks


def list_snapshots_and_bookmarks(
        dataset: Dataset) \
        -> tuple[Sequence[SnapshotInfo], Sequence[BookmarkInfo]]:
    return _list_snapshots_and_bookmarks(dataset, 'snapshot,bookmark')


def list_snapshots(dataset: Dataset) -> Sequence[SnapshotInfo]:
    return _list_snapshots_and_bookmarks(dataset, 'snapshot')[0]


def list_bookmarks(dataset: Dataset) -> Sequence[BookmarkInfo]:
    return _list_snapshots_and_bookmarks(dataset, 'bookmark')[1]


def destroy_snapshots(snapshots: Iterable[Snapshot], recursive: bool) -> None:
    if not snapshots:
        # We can't call `zfs destroy` with an empty list of snapshots.
        return

    recursive_arg = ['-r'] if recursive else []
    dataset, = {i.dataset for i in snapshots}
    snapshots_arg = f'{dataset}@{",".join(i.name for i in snapshots)}'

    logging.info(f'Destroying snapshots: {snapshots_arg}')
    check_call(['zfs', 'destroy', *recursive_arg, '--', snapshots_arg])


def destroy_bookmark(bookmark: Bookmark) -> None:
    logging.info(f'Destroying bookmark: {bookmark}')
    check_call(['zfs', 'destroy', '--', f'{bookmark}'])


def send_receive_snapshot(
        incremental_base_snapshot: Bookmark | Snapshot | None, source: Snapshot,
        target: Snapshot) -> None:
    if incremental_base_snapshot is None:
        incremental_args = []
    else:
        incremental_args = ['-i', f'{incremental_base_snapshot}']

    # Using -F on the receive side to prevent receiving to fail if the target
    # filesystem has been modified since the last receive. This will only make a
    # difference for incremental sends, i.e. when we know that the target
    # filesystem has actually been created as a back of the source we're
    # sending. If the target filesystem is unrelated, it won't be overwritten.
    check_call_pipeline(
        ['zfs', 'send', '-wp', *incremental_args, f'{source}'],
        ['zfs', 'receive', '-F', f'{target}'])
