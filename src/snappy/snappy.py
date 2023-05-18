from __future__ import annotations

import logging
import subprocess
from datetime import datetime
from pathlib import Path
from subprocess import CalledProcessError
from typing import Iterator

from snappy.config import load_config, get_default_config_path, KeepSpec, \
    MostRecentKeepSpec
from snappy.send import send_snapshots
from snappy.snapshots import make_snapshot_name, find_expired_snapshots
from snappy.utils import UserError
from snappy.zfs import create_snapshots, destroy_snapshots, Dataset, Snapshot, \
    list_snapshots, list_children

default_snapshot_name_prefix = 'snappy'


def _get_send_target(
        source: Dataset, send_target: Dataset, send_base: str | None) \
        -> Dataset:
    if send_base is None:
        return send_target

    # TODO: Is it a good idea that we allow send_base to end in a `/`?
    if not source.startswith(send_base):
        raise UserError(f'Name of source dataset `{source}\' is not located '
                        f'under the send base `{send_base}\'.')

    return Dataset(send_target + source.removeprefix(send_base))


def _get_selected_datasets(
        datasets: list[Dataset], recursive: bool) \
        -> list[Dataset]:
    res: list[Dataset] = []

    for i in datasets:
        if recursive:
            res.extend(list_children(i))
        else:
            res.append(i)

    return res


def _run_script(script: str) -> None:
    try:
        logging.info(f'Running pre-snapshot script: {script}')

        # TODO: Maybe start a new session here and wait for it.
        subprocess.check_call(script, shell=True)
    except CalledProcessError as e:
        raise UserError(
            f'Pre-snapshot script failed with exit code {e.returncode}.')


def _snapshot(datasets: list[Dataset], prefix: str) -> None:
    snapshot_name = make_snapshot_name(prefix, datetime.now())
    snapshots = [Snapshot(i, snapshot_name) for i in datasets]

    create_snapshots(snapshots)


def _send(
        datasets: list[Dataset], prefix: str, send_target: Dataset,
        send_base: str) \
        -> None:
    for dataset in datasets:
        target_dataset = _get_send_target(dataset, send_target, send_base)

        send_snapshots(dataset, target_dataset, prefix)


def _prune(
        datasets: list[Dataset], prefix: str, keep_specs: list[KeepSpec]) \
        -> None:
    # The most recent snapshot should never be deleted by this tool.
    keep_specs = keep_specs + [MostRecentKeepSpec(1)]

    for dataset in datasets:
        snapshots = list_snapshots(dataset)
        expired_snapshot = find_expired_snapshots(snapshots, keep_specs, prefix)

        destroy_snapshots(expired_snapshot)


def cli_command(
        datasets: list[Dataset], recursive: bool, prefix: str | None,
        take_snapshot: bool, pre_snapshot_script: str | None,
        keep_specs: list[KeepSpec] | None, send_target: Dataset | None,
        send_base: Dataset | None) \
        -> None:
    if prefix is None:
        prefix = default_snapshot_name_prefix

    if pre_snapshot_script is not None:
        _run_script(pre_snapshot_script)

    selected_datasets = _get_selected_datasets(datasets, recursive)

    if take_snapshot:
        _snapshot(selected_datasets, prefix)

    if send_target is not None:
        if send_base is None:
            # Effectively, when no send_base is specified, the full path of the
            # source dataset is used as the base.
            send_base, = datasets

        _send(selected_datasets, prefix, send_target, send_base)

        # We want to prune snapshots on the target datasets when sending
        # snapshots.
        datasets = [_get_send_target(i, send_target, send_base) for i in datasets]

    if keep_specs is not None:
        _prune(selected_datasets, prefix, keep_specs)


def auto_command(config_path: Path | None) -> None:
    if config_path is None:
        config_path = get_default_config_path()

    config = load_config(config_path)

    for i in config.snapshot:
        cli_command(
            i.datasets, i.recursive, i.prefix, i.take_snapshot,
            i.pre_snapshot_script, i.prune_keep, i.send_target, i.send_base)
