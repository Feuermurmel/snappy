import logging
import subprocess
from dataclasses import dataclass
from typing import NewType, Iterable


# Sadly a misnomer as this is only used to refer to filesystems and volumes, but
# calling it just Filesystem seems even more confusing and would contradict the
# property names in config files.
Dataset = NewType('Dataset', str)


@dataclass(frozen=True)
class Snapshot:
    dataset: Dataset
    name: str

    def __str__(self):
        return f'{self.dataset}@{self.name}'


def create_snapshots(snapshots: list[Snapshot], recursive: bool):
    recursive_arg = ['-r'] if recursive else []
    snapshot_args = [str(i) for i in snapshots]

    logging.info(f'Creating snapshots: {", ".join(snapshot_args)}')
    subprocess.check_call(['zfs', 'snapshot', *recursive_arg, '--', *snapshot_args])


def list_snapshots(dataset: Dataset) -> list[Snapshot]:
    output = subprocess.check_output(
        ['zfs', 'list', '-Hd1', '-t', 'snapshot', '-o', 'name', '--', dataset],
        text=True)

    def parse_snapshot(snapshot: str):
        dataset_name, name = snapshot.split('@')

        assert dataset_name == dataset

        return Snapshot(Dataset(dataset_name), name)

    return [parse_snapshot(i) for i in output.splitlines()]


def destroy_snapshots(snapshots: Iterable[Snapshot], recursive: bool):
    if not snapshots:
        # We can't call `zfs destroy` with an empty list of snapshots.
        return

    recursive_arg = ['-r'] if recursive else []
    dataset, = {i.dataset for i in snapshots}
    snapshots_arg = f'{dataset}@{",".join(i.name for i in snapshots)}'

    logging.info(f'Destroying snapshots: {snapshots_arg}')
    subprocess.check_call(['zfs', 'destroy', *recursive_arg, '--', snapshots_arg])
