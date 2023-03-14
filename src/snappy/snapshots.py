from __future__ import annotations

from datetime import datetime

from snappy.config import KeepSpec, IntervalKeepSpec
from snappy.zfs import Snapshot


_timestamp_format = '%Y-%m-%d-%H%M%S'

# Using this day, because that year incidentally starts with a monday.
_keep_interval_time_base = datetime(2001, 1, 1)


def make_snapshot_name(prefix: str, timestamp: datetime) -> str:
    return f'{prefix}-{timestamp.strftime(_timestamp_format)}'


def _parse_snapshot_name(name: str, prefix: str) -> datetime | None:
    full_prefix = f'{prefix}-'

    if not name.startswith(full_prefix):
        return None

    timestamp_str = name.removeprefix(full_prefix)

    try:
        return datetime.strptime(timestamp_str, _timestamp_format)
    except ValueError:
        return None


def find_expired_snapshots(
        snapshots: list[Snapshot], keep_specs: list[KeepSpec], prefix: str) \
        -> set[Snapshot]:
    snapshots_with_timestamps: list[tuple[Snapshot, datetime]] = []

    # The list of snapshots returned by `zfs list` is from oldest to newest, but
    # we want to keep newer rather than older snapshots.
    for i in reversed(snapshots):
        timestamp = _parse_snapshot_name(i.name, prefix)

        if timestamp is not None:
            snapshots_with_timestamps.append((i, timestamp))

    def get_selected_snapshots(spec: KeepSpec) -> list[Snapshot]:
        # Select a subset of snapshots unless we're using a
        # MostRecentKeepSpec.
        if isinstance(spec, IntervalKeepSpec):
            # Because we're iterating form newest to the oldest snapshot, this
            # will keep the oldest snapshot within each bucket defined by the
            # keep specification.
            first_in_bucket = {
                (t - _keep_interval_time_base) // spec.interval: s
                for s, t in snapshots_with_timestamps}

            selected_snapshots = list(first_in_bucket.values())
        else:
            selected_snapshots = [s for s, _ in snapshots_with_timestamps]

        return selected_snapshots[:spec.count]

    return set(snapshots) - {
        snapshot for keep_spec in keep_specs
        for snapshot in get_selected_snapshots(keep_spec)}
