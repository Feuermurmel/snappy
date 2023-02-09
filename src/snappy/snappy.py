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
        obsolete_snapshot_names = \
            [i.name for i in set(snapshots) - selected_snapshots]

        destroy_snapshots(dataset, obsolete_snapshot_names, recursive)


def _process_datasets(
        recursive: bool, keep_specs: list[KeepSpec], take_snapshot: bool,
        datasets: list[str]):
    if take_snapshot:
        _snapshot(recursive, datasets)

    if keep_specs:
        _prune(recursive, keep_specs, datasets)


def _auto_command(config_path: Path | None):
    if config_path is None:
        config_path = get_default_config_path()

    config = load_config(config_path)

    for i in config.snapshot:
        if i.prune:
            keep_specs = i.prune.keep
        else:
            keep_specs = []

        _process_datasets(i.recursive, keep_specs, i.take_snapshot, i.datasets)


def main(
        recursive: bool, keep_specs: list[KeepSpec], take_snapshot: bool,
        datasets: list[str], auto: bool, config_path: Path | None):
    if auto:
        _auto_command(config_path)
    else:
        _process_datasets(recursive, keep_specs, take_snapshot, datasets)
