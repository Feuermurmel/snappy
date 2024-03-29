from __future__ import annotations

import logging
import subprocess
from datetime import datetime
from enum import Enum
from pathlib import Path
from subprocess import CalledProcessError
from typing import Iterator, Sequence

from snappy.config import load_config, get_default_config_path, KeepSpec, \
    MostRecentKeepSpec
from snappy.send import send_snapshots
from snappy.snapshots import make_snapshot_name, find_expired_snapshots
from snappy.utils import UserError
from snappy.zfs import create_snapshots, destroy_snapshots, Dataset, Snapshot, \
    list_snapshots, list_children


default_snapshot_name_prefix = 'snappy'


class AutoAction(Enum):
    snapshot = 'snapshot'
    send = 'send'


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


def _get_pool_name(dataset: Dataset) -> Dataset:
    return Dataset(dataset.split('/', 1)[0])


def _iter_parents(dataset: Dataset) -> Iterator[Dataset]:
    while True:
        yield dataset

        if '/' not in dataset:
            break

        dataset = Dataset(dataset.rsplit('/', 1)[0])


def _get_selected_datasets(
        datasets: list[Dataset], recursive: bool, exclude: list[Dataset]) \
        -> list[Dataset]:
    if not recursive:
        # Input validation should make sure that `exclude` is only set if
        # recursive is true.
        assert not exclude

        return datasets

    processed_datasets: set[Dataset] = set()
    res: list[Dataset] = []

    # Sort so that we get parents before children.
    for i in sorted(datasets):
        if i not in processed_datasets:
            for j in list_children(i):
                # Add all children to this set to that we won't call
                # `list_children()` again even if they occur in `datasets`.
                processed_datasets.add(j)

                # Figure out if a dataset should be included by iterating
                # looking up each prefix in `datasets` and `exclude`.
                for k in _iter_parents(j):
                    if k in exclude:
                        break
                    elif k in datasets:
                        res.append(j)
                        break

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
        *, datasets: list[Dataset], recursive: bool, exclude: list[Dataset],
        prefix: str | None, take_snapshot: bool,
        pre_snapshot_script: str | None, keep_specs: list[KeepSpec] | None,
        send_target: Dataset | None, send_base: Dataset | None,
        do_snapshot: bool, do_send: bool) \
        -> None:
    if prefix is None:
        prefix = default_snapshot_name_prefix

    if do_snapshot and pre_snapshot_script is not None:
        _run_script(pre_snapshot_script)

    selected_datasets = _get_selected_datasets(datasets, recursive, exclude)

    if do_snapshot and take_snapshot:
        _snapshot(selected_datasets, prefix)

    # Depending on whether we have a send target or not, pruning is disabled by
    # setting one of the `do_*` flags to False.
    if send_target is None:
        do_prune = do_snapshot
    else:
        do_prune = do_send

        if send_base is None:
            # Effectively, when no send_base is specified, the full path of the
            # source dataset is used as the base.
            send_base, = datasets

        if do_send:
            _send(selected_datasets, prefix, send_target, send_base)

        # We want to prune snapshots on the target datasets when sending
        # snapshots.
        selected_datasets = [
            _get_send_target(i, send_target, send_base)
            for i in selected_datasets]

    if do_prune and keep_specs is not None:
        _prune(selected_datasets, prefix, keep_specs)


def auto_command(
        config_path: Path | None, auto_actions: Sequence[AutoAction]) \
        -> None:
    if config_path is None:
        config_path = get_default_config_path()

    config = load_config(config_path)

    for i in config.snapshot:
        cli_command(
            datasets=i.datasets,
            recursive=i.recursive,
            exclude=i.exclude,
            prefix=i.prefix,
            take_snapshot=i.take_snapshot,
            pre_snapshot_script=i.pre_snapshot_script,
            keep_specs=i.prune_keep,
            send_target=i.send_target,
            send_base=i.send_base,
            do_snapshot=AutoAction.snapshot in auto_actions,
            do_send=AutoAction.send in auto_actions)
