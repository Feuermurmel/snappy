from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from snappy.config import KeepSpec, IntervalKeepSpec
from snappy.zfs import list_snapshots, Snapshot, Dataset


_timestamp_format = '%Y-%m-%d-%H%M%S'

# Using this day, because that year incidentally starts with a monday.
_keep_interval_time_base = datetime(2001, 1, 1)


@dataclass(frozen=True)
class SnapshotInfo:
    snapshot: Snapshot
    timestamp: datetime


def make_snapshot_name(prefix: str, timestamp: datetime) -> str:
    return f'{prefix}-{timestamp.strftime(_timestamp_format)}'


def _info_from_snapshot(snapshot: Snapshot, prefix: str) -> SnapshotInfo | None:
    full_prefix = f'{prefix}-'

    if not snapshot.name.startswith(full_prefix):
        return None

    try:
        timestamp = datetime.strptime(
            snapshot.name.removeprefix(full_prefix), _timestamp_format)

        return SnapshotInfo(snapshot, timestamp)
    except ValueError:
        return None


def get_snapshot_infos(dataset: Dataset, prefix: str) -> list[SnapshotInfo]:
    snapshots = list[SnapshotInfo]()

    for i in list_snapshots(dataset):
        snapshot = _info_from_snapshot(i, prefix)

        if snapshot is not None:
            snapshots.append(snapshot)

    return snapshots


def select_snapshots_to_keep(
        snapshots: list[SnapshotInfo], keep_specs: list[KeepSpec]) \
        -> set[SnapshotInfo]:
    def get_selected_snapshots(spec: KeepSpec) -> list[SnapshotInfo]:
        # The list of snapshots returned by `zfs list` is from oldest to
        # newest, but we want to keep newer rather than older snapshots.
        selected_snapshots: Iterable[SnapshotInfo] = reversed(snapshots)

        # Select a subset of snapshots unless we're using a
        # MostRecentKeepSpec.
        if isinstance(spec, IntervalKeepSpec):
            # Because we're iterating form newest to the oldest snapshot,
            # this will overwrite keep the oldest snapshot within each
            # bucket defined by the keep specification.
            first_in_bucket = {
                (i.timestamp - _keep_interval_time_base) // spec.interval: i
                for i in selected_snapshots}

            selected_snapshots = first_in_bucket.values()

        return list(selected_snapshots)[:spec.count]

    return {
        snapshot for keep_spec in keep_specs
        for snapshot in get_selected_snapshots(keep_spec)}
