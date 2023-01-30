from datetime import datetime

from snappy.zfs import crate_snapshot, list_snapshots, destroy_snapshots


_snapshot_name_prefix = 'snappy-'


def _datetime_now():
    """
    Simple wrapper for `datetime.now()`. Allows the current time to be mocked
    from tests.
    """
    return datetime.now()


def _make_snapshot_name(timestamp: datetime) -> str:
    return _snapshot_name_prefix + timestamp.strftime('%F-%H%M%S')


def _is_snappy_snapshot(snapshot_name) -> bool:
    return snapshot_name.startswith(_snapshot_name_prefix)


def main(datasets: list[str], keep: bool, prune_only: bool, recursive: bool):
    snapshot_name = _make_snapshot_name(_datetime_now())

    if not prune_only:
        crate_snapshot([f'{i}@{snapshot_name}' for i in datasets], recursive)

    if keep is not None:
        for dataset in datasets:
            snapshot_names = list(filter(_is_snappy_snapshot, list_snapshots(dataset)))

            # Make this work even with --keep=0.
            outdated_snapshot_names = list(reversed(snapshot_names))[keep:]

            destroy_snapshots(dataset, outdated_snapshot_names, recursive)
