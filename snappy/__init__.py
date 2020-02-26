import argparse
import datetime
import subprocess

import sys


snapshot_name_prefix = 'snappy-'


def log(message, *args):
    print(message.format(*args), file=sys.stderr)


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '-r',
        '--recursive',
        action='store_true',
        help='Create and prune snapshots recursively on the specified '
             'datasets.')

    parser.add_argument(
        '-k',
        '--keep',
        type=int,
        help='Prune outdated snapshots after creating a new snapshot. Keep '
             'the specified number of most recent snapshots.')

    parser.add_argument(
        '-p',
        '--prune-only',
        action='store_true',
        help='Disables creating snapshots. Requires --keep.')

    parser.add_argument(
        'datasets',
        nargs='+',
        help='Datasets on which to create (and prune) snapshots.')

    args = parser.parse_args()

    if args.prune_only and args.keep is None:
        parser.error('--prune-only requires --keep.')

    return args


def crate_snapshot(snapshots, recursive):
    recursive_arg = ['-r'] if recursive else []

    log('Creating snapshots: {}', ', '.join(snapshots))
    subprocess.check_call(['zfs', 'snapshot', *recursive_arg, '--', *snapshots])


def list_snapshots(dataset):
    output = subprocess.check_output(['zfs', 'list', '-H', '-d', '1', '-t', 'snapshot', '-o', 'name', '--', dataset])

    return output.decode().splitlines()


def destroy_snapshot(snapshot, recursive):
    recursive_arg = ['-r'] if recursive else []

    log('Destroying snapshot: {}', snapshot)
    subprocess.check_call(['zfs', 'destroy', *recursive_arg, '--', snapshot])


def get_snapshot_name(timestamp):
    return snapshot_name_prefix + timestamp.strftime('%F-%H%M%S')


def is_snappy_snapshot(snapshot):
    dataset, snapshot_name = snapshot.split('@')

    return snapshot_name.startswith(snapshot_name_prefix)


def main(datasets, keep, prune_only, recursive):
    snapshot_name = get_snapshot_name(datetime.datetime.now())

    if not prune_only:
        crate_snapshot(['{}@{}'.format(i, snapshot_name) for i in datasets], recursive)

    if keep is not None:
        for dataset in datasets:
            snapshots = [i for i in list_snapshots(dataset) if is_snappy_snapshot(i)]

            # Make this work even with --keep=0.
            outdated_snapshots = list(reversed(snapshots))[keep:]

            for snapshot in outdated_snapshots:
                destroy_snapshot(snapshot, recursive)


def script_main():
    try:
        main(**vars(parse_args()))
    except KeyboardInterrupt:
        log('Operation interrupted.')
        sys.exit(1)
