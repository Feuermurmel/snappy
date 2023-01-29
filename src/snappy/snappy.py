from __future__ import annotations

from datetime import datetime

from snappy.snapshots import make_snapshot_name, get_snapshot_infos, \
    select_snapshots_to_keep, KeepSpec
from snappy.zfs import crate_snapshot, destroy_snapshots


def _datetime_now():
    """
    Simple wrapper for `datetime.now()`. Allows the current time to be mocked
    from tests.
    """
    return datetime.now()


def main(
        datasets: list[str], keep_specs: list[KeepSpec] | None,
        prune_only: bool, recursive: bool):
    snapshot_name = make_snapshot_name(_datetime_now())

    if not prune_only:
        crate_snapshot([f'{i}@{snapshot_name}' for i in datasets], recursive)

    if keep_specs:
        for dataset in datasets:
            snapshots = get_snapshot_infos(dataset)

            pruned_snapshots = \
                set(snapshots) - select_snapshots_to_keep(snapshots, keep_specs)
            pruned_snapshot_names = [i.name for i in pruned_snapshots]

            destroy_snapshots(dataset, pruned_snapshot_names, recursive)
