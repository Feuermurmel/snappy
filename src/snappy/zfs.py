import logging
import subprocess
from dataclasses import dataclass
from subprocess import check_output
from typing import NewType, Iterable, TypeAlias, TypeVar, Generic, Literal, \
    overload, Sequence


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


SnapshotLike: TypeAlias = Snapshot | Bookmark

SnapshotLikeT = TypeVar('SnapshotLikeT', bound=SnapshotLike, covariant=True)


@dataclass(frozen=True)
class SnapshotInfo(Generic[SnapshotLikeT]):
    snapshot: SnapshotLikeT
    guid: int
    createtxg: int


SnapshotInfoT = TypeVar('SnapshotInfoT', bound=SnapshotInfo[SnapshotLike])


def create_snapshots(snapshots: list[Snapshot], recursive: bool) -> None:
    recursive_arg = ['-r'] if recursive else []
    snapshot_args = [str(i) for i in snapshots]

    logging.info(f'Creating snapshots: {", ".join(snapshot_args)}')
    subprocess.check_call(['zfs', 'snapshot', *recursive_arg, '--', *snapshot_args])


@overload
def list_snapshot_like(
        dataset: Dataset, types: Iterable[Literal['snapshot']]) \
        -> Sequence[SnapshotInfo[Snapshot]]: ...
@overload
def list_snapshot_like(
        dataset: Dataset, types: Iterable[Literal['bookmark']]) \
        -> Sequence[SnapshotInfo[Bookmark]]: ...
@overload
def list_snapshot_like(
        dataset: Dataset, types: Iterable[Literal['snapshot', 'bookmark']]) \
        -> Sequence[SnapshotInfo[SnapshotLike]]: ...


def list_snapshot_like(
        dataset: Dataset, types: Iterable[Literal['snapshot', 'bookmark']]) \
        -> Sequence[SnapshotInfo[SnapshotLike]]:
    """
    Return a list of snapshots of the specified dataset.
    """
    output = check_output(
        ['zfs', 'list', '-Hpd1', '-t', ','.join(types),
         '-o', 'name,guid,createtxg', '--', dataset],
        text=True)

    def parse_line(line: str) -> SnapshotInfo[SnapshotLike]:
        full_name, guid_str, createtxg_str = line.split('\t')
        snapshot_like: SnapshotLike

        if '@' in full_name:
            dataset_name, name = full_name.split('@')
            snapshot_like = Snapshot(dataset, name)
        else:
            dataset_name, name = full_name.split('#')
            snapshot_like = Bookmark(dataset, name)

        assert dataset_name == dataset

        guid = int(guid_str)
        createtxg = int(createtxg_str)

        return SnapshotInfo(snapshot_like, guid, createtxg)

    return [parse_line(i) for i in output.splitlines()]


def destroy_snapshots(snapshots: Iterable[Snapshot], recursive: bool) -> None:
    if not snapshots:
        # We can't call `zfs destroy` with an empty list of snapshots.
        return

    recursive_arg = ['-r'] if recursive else []
    dataset, = {i.dataset for i in snapshots}
    snapshots_arg = f'{dataset}@{",".join(i.name for i in snapshots)}'

    logging.info(f'Destroying snapshots: {snapshots_arg}')
    subprocess.check_call(['zfs', 'destroy', *recursive_arg, '--', snapshots_arg])
