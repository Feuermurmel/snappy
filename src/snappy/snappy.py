from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path
from subprocess import CalledProcessError
from typing import Iterator

from snappy.utils import UserError
from snappy.config import load_config, get_default_config_path, KeepSpec, \
    MostRecentKeepSpec
from snappy.snapshots import make_snapshot_name, find_expired_snapshots
from snappy.zfs import create_snapshots, destroy_snapshots, Dataset, Snapshot, \
    list_snapshots, list_children

default_snapshot_name_prefix = 'snappy'


def _run_script(script: str) -> None:
    try:
        subprocess.check_call(script, shell=True)
    except CalledProcessError as e:
        raise UserError(
            f'Pre-snapshot script failed with exit code {e.returncode}.')


def _snapshot(datasets: list[Dataset], recursive: bool, prefix: str) -> None:
    snapshot_name = make_snapshot_name(prefix, datetime.now())
    snapshots = [Snapshot(i, snapshot_name) for i in datasets]

    create_snapshots(snapshots, recursive)


def _prune(
        datasets: list[Dataset], recursive: bool, prefix: str,
        keep_specs: list[KeepSpec]) -> None:
    # The most recent snapshot should never be deleted by this tool.
    keep_specs = keep_specs + [MostRecentKeepSpec(1)]

    def iter_child_datasets() -> Iterator[Dataset]:
        for dataset in datasets:
            if recursive:
                yield from list_children(dataset)
            else:
                yield dataset

    for dataset in iter_child_datasets():
        snapshots = list_snapshots(dataset)
        expired_snapshot = find_expired_snapshots(snapshots, keep_specs, prefix)

        destroy_snapshots(expired_snapshot)


def cli_command(
        datasets: list[Dataset], recursive: bool, prefix: str | None,
        keep_specs: list[KeepSpec] | None, take_snapshot: bool,
        pre_snapshot_script: str | None = None) -> None:
    if prefix is None:
        prefix = default_snapshot_name_prefix

    if pre_snapshot_script is not None:
        _run_script(pre_snapshot_script)

    if take_snapshot:
        _snapshot(datasets, recursive, prefix)

    if keep_specs is not None:
        _prune(datasets, recursive, prefix, keep_specs)


def auto_command(config_path: Path | None) -> None:
    if config_path is None:
        config_path = get_default_config_path()

    config = load_config(config_path)

    for i in config.snapshot:
        cli_command(
            i.datasets, i.recursive, i.prefix, i.prune_keep, i.take_snapshot,
            i.pre_snapshot_script)
