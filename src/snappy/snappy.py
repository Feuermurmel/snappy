from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path
from subprocess import CalledProcessError

from snappy.utils import UserError
from snappy.config import load_config, get_default_config_path, KeepSpec, MostRecentKeepSpec
from snappy.snapshots import make_snapshot_name, get_snapshot_infos, \
    select_snapshots_to_keep
from snappy.zfs import create_snapshots, destroy_snapshots


default_snapshot_name_prefix = 'snappy'


def _datetime_now():
    """
    Simple wrapper for `datetime.now()`. Allows the current time to be mocked
    from tests.
    """
    return datetime.now()


def _run_script(script: str):
    try:
        subprocess.check_call(script, shell=True)
    except CalledProcessError as e:
        raise UserError(
            f'Pre-snapshot script failed with exit code {e.returncode}.')


def _snapshot(datasets: list[str], recursive: bool, prefix: str):
    snapshot_name = make_snapshot_name(prefix, _datetime_now())

    create_snapshots(datasets, snapshot_name, recursive)


def _prune(
        datasets: list[str], recursive: bool, prefix: str,
        keep_specs: list[KeepSpec]):
    for dataset in datasets:
        # The most recent snapshot should never be deleted by this tool.
        keep_specs = keep_specs + [MostRecentKeepSpec(1)]
        snapshots = get_snapshot_infos(dataset, prefix)

        selected_snapshots = select_snapshots_to_keep(snapshots, keep_specs)
        deleted_snapshot = set(snapshots) - selected_snapshots

        destroy_snapshots(dataset, [i.name for i in deleted_snapshot], recursive)


def cli_command(
        datasets: list[str], recursive: bool, prefix: str | None,
        keep_specs: list[KeepSpec] | None, take_snapshot: bool,
        pre_snapshot_script: str | None = None):
    if prefix is None:
        prefix = default_snapshot_name_prefix

    if pre_snapshot_script is not None:
        _run_script(pre_snapshot_script)

    if take_snapshot:
        _snapshot(datasets, recursive, prefix)

    if keep_specs is not None:
        _prune(datasets, recursive, prefix, keep_specs)


def auto_command(config_path: Path | None):
    if config_path is None:
        config_path = get_default_config_path()

    config = load_config(config_path)

    for i in config.snapshot:
        cli_command(
            i.datasets, i.recursive, i.prefix, i.prune_keep, i.take_snapshot,
            i.pre_snapshot_script)
