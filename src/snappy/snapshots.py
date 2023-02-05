from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from itertools import groupby, islice
from typing import Iterator

from typing_extensions import TypeAlias

from snappy.zfs import list_snapshots


_snapshot_name_prefix = 'snappy-'
_timestamp_format = '%Y-%m-%d-%H%M%S'

# Using this day, because that year incidentally starts with a monday.
_keep_interval_time_base = datetime(2001, 1, 1)


@dataclass
class MostRecentKeepSpec:
    count: int


@dataclass
class IntervalKeepSpec:
    interval: timedelta
    count: int | None


KeepSpec: TypeAlias = 'MostRecentKeepSpec | IntervalKeepSpec'


@dataclass(frozen=True)
class SnapshotInfo:
    name: str
    timestamp: datetime


def make_snapshot_name(timestamp: datetime) -> str:
    return _snapshot_name_prefix + timestamp.strftime(_timestamp_format)


def parse_snapshot_name(name: str) -> SnapshotInfo | None:
    if not name.startswith(_snapshot_name_prefix):
        return None

    try:
        timestamp = datetime.strptime(
            name.removeprefix(_snapshot_name_prefix), _timestamp_format)

        return SnapshotInfo(name, timestamp)
    except ValueError:
        return None


def get_snapshot_infos(dataset: str) -> list[SnapshotInfo]:
    snapshots = list[SnapshotInfo]()

    for i in list_snapshots(dataset):
        snapshot = parse_snapshot_name(i)

        if snapshot is not None:
            snapshots.append(snapshot)

    return snapshots


def select_snapshots_to_keep(
        snapshots: list[SnapshotInfo], keep_specs: list[KeepSpec]) \
        -> set[SnapshotInfo]:
    # Process most recent snapshots first to keep those rather than older ones.
    snapshots = sorted(snapshots, key=lambda x: x.timestamp, reverse=True)

    def iter_kept_snapshots(spec: KeepSpec) -> Iterator[SnapshotInfo]:
        if isinstance(spec, MostRecentKeepSpec):
            return iter(snapshots)
        else:
            def get_bucket(snapshot: SnapshotInfo) -> int:
                return (snapshot.timestamp - _keep_interval_time_base) \
                       // spec.interval  # type: ignore

            # Get the last (i.e. least recent) snapshot in each bucket.
            return (j for _, (*_, j) in groupby(snapshots, get_bucket))

    return {
        snapshot
        for spec in keep_specs
        for snapshot in islice(iter_kept_snapshots(spec), spec.count)}
