import logging
import subprocess


def create_snapshots(datasets: list[str], snapshot_name: str, recursive: bool):
    recursive_arg = ['-r'] if recursive else []
    snapshots = [f'{i}@{snapshot_name}' for i in datasets]

    logging.info(f'Creating snapshots: {", ".join(snapshots)}')
    subprocess.check_call(['zfs', 'snapshot', *recursive_arg, '--', *snapshots])


def list_snapshots(dataset: str) -> list[str]:
    output = subprocess.check_output(
        ['zfs', 'list', '-Hd1', '-t', 'snapshot', '-o', 'name', '--', dataset],
        text=True)

    def get_snapshot_name(snapshot: str):
        dataset_part, snapshot_name = snapshot.split('@')

        assert dataset_part == dataset

        return snapshot_name

    return [get_snapshot_name(i) for i in output.splitlines()]


def destroy_snapshots(dataset: str, snapshot_names: list[str], recursive: bool):
    if not snapshot_names:
        # We cant call `zfs destroy` with an empty list of snapshots.
        return

    recursive_arg = ['-r'] if recursive else []
    snapshots_arg = f'{dataset}@{",".join(snapshot_names)}'

    logging.info(f'Destroying snapshots: {snapshots_arg}')
    subprocess.check_call(['zfs', 'destroy', *recursive_arg, '--', snapshots_arg])
