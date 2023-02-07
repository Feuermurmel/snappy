from __future__ import annotations

from datetime import datetime
from pathlib import Path

from typing_extensions import Never

from snappy.utils import UserError
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
        recursive: bool, keep_specs: list[KeepSpec], prune_only: bool,
        datasets: list[str]):
    if not prune_only:
        _snapshot(recursive, datasets)

    if keep_specs:
        _prune(recursive, keep_specs, datasets)


def _auto_command(config_path: Path | None):
    if config_path is None:
        config_path = get_default_config_path()

    config = load_config(config_path)

    def raise_config_error(message: str) -> Never:
        raise UserError(f'Error in config file `{config_path}\': {message}')

    for i in config.snapshot:
        if i.prune:
            keep_specs = i.prune.keep

            # TODO: Move validation logic into config module.
            if not keep_specs:
                raise raise_config_error(
                    f'`keep_specs\' cannot be empty. Set `keep_specs\' to '
                    f'["0"] to explicitly prune all snapshots.')
        else:
            keep_specs = []

            if i.prune_only:
                raise raise_config_error(
                    f'Key `prune\' is required if `prune_only\' is set to true.')

        _process_datasets(i.recursive, keep_specs, i.prune_only, i.datasets)


def main(
        recursive: bool, keep_specs: list[KeepSpec], prune_only: bool,
        datasets: list[str], auto: bool, config_path: Path | None):
    if auto:
        _auto_command(config_path)
    else:
        _process_datasets(recursive, keep_specs, prune_only, datasets)
