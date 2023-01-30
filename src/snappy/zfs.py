import logging
import subprocess
from typing import Iterator


def crate_snapshot(snapshots: list[str], recursive: bool):
    recursive_arg = ['-r'] if recursive else []

    logging.info(f'Creating snapshots: {", ".join(snapshots)}')
    subprocess.check_call(['zfs', 'snapshot', *recursive_arg, '--', *snapshots])


def list_snapshots(dataset: str) -> list[str]:
    output = subprocess.check_output(
        ['zfs', 'list', '-H', '-d', '1', '-t', 'snapshot', '-o', 'name', '--', dataset])

    def iter_snapshots() -> Iterator[str]:
        for i in output.decode().splitlines():
            dataset_part, snapshot_name = i.split('@')

            assert dataset_part == dataset

            yield snapshot_name

    return list(iter_snapshots())


def destroy_snapshots(dataset: str, snapshot_names: list[str], recursive: bool):
    if not snapshot_names:
        # Nothing to do.
        return

    recursive_arg = ['-r'] if recursive else []

    snapshot_arg = f'{dataset}@{",".join(snapshot_names)}'

    logging.info(f'Destroying snapshots: {snapshot_arg}')
    subprocess.check_call(['zfs', 'destroy', *recursive_arg, '--', snapshot_arg])
