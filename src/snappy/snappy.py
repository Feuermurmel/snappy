from __future__ import annotations

from datetime import datetime
from pathlib import Path

from snappy.config import load_config, get_default_config_path, KeepSpec
from snappy.snapshots import make_snapshot_name, get_snapshot_infos, \
    select_snapshots_to_keep
from snappy.zfs import crate_snapshot, destroy_snapshots


def _datetime_now():
    """
    Simple wrapper for `datetime.now()`. Allows the current time to be mocked
    from tests.
    """
    return datetime.now()


def _snapshot(recursive: bool, datasets: list[str]):
    snapshot_name = make_snapshot_name(_datetime_now())

    crate_snapshot([f'{i}@{snapshot_name}' for i in datasets], recursive)


def _prune(recursive: bool, keep_specs: list[KeepSpec], datasets: list[str]):
    for dataset in datasets:
        snapshots = get_snapshot_infos(dataset)

        selected_snapshots = select_snapshots_to_keep(snapshots, keep_specs)
        deleted_snapshot = set(snapshots) - selected_snapshots

        # The most recent snapshot should never be deleted by this tool.
        assert not snapshots or snapshots[-1] not in deleted_snapshot

        destroy_snapshots(dataset, [i.name for i in deleted_snapshot], recursive)


def cli_command(
        recursive: bool, keep_specs: list[KeepSpec] | None, take_snapshot: bool,
        datasets: list[str]):
    if take_snapshot:
        _snapshot(recursive, datasets)

    if keep_specs is not None:
        _prune(recursive, keep_specs, datasets)


def auto_command(config_path: Path | None):
    if config_path is None:
        config_path = get_default_config_path()

    config = load_config(config_path)

    for i in config.snapshot:
        cli_command(i.recursive, i.prune_keep, i.take_snapshot, i.datasets)
