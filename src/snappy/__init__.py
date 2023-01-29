import argparse
import datetime
import subprocess
import logging

import sys


snapshot_name_prefix = 'snappy-'


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

    logging.info(f'Creating snapshots: {", ".join(snapshots)}')
    subprocess.check_call(['zfs', 'snapshot', *recursive_arg, '--', *snapshots])


def list_snapshots(dataset):
    output = subprocess.check_output(['zfs', 'list', '-H', '-d', '1', '-t', 'snapshot', '-o', 'name', '--', dataset])

    def iter_snapshots():
        for i in output.decode().splitlines():
            dataset_part, snapshot_name = i.split('@')

            assert dataset_part == dataset

            yield snapshot_name

    return list(iter_snapshots())


def destroy_snapshots(dataset, snapshot_names, recursive):
    if not snapshot_names:
        # Nothing to do.
        return

    recursive_arg = ['-r'] if recursive else []

    snapshot_arg = '{}@{}'.format(dataset, ','.join(snapshot_names))

    logging.info('Destroying snapshots: {}', snapshot_arg)
    subprocess.check_call(['zfs', 'destroy', *recursive_arg, '--', snapshot_arg])


def get_snapshot_name(timestamp):
    return snapshot_name_prefix + timestamp.strftime('%F-%H%M%S')


def is_snappy_snapshot(snapshot_name):
    return snapshot_name.startswith(snapshot_name_prefix)


def main(datasets, keep, prune_only, recursive):
    snapshot_name = get_snapshot_name(datetime.datetime.now())

    if not prune_only:
        crate_snapshot(['{}@{}'.format(i, snapshot_name) for i in datasets], recursive)

    if keep is not None:
        for dataset in datasets:
            snapshot_names = list(filter(is_snappy_snapshot, list_snapshots(dataset)))

            # Make this work even with --keep=0.
            outdated_snapshot_names = list(reversed(snapshot_names))[keep:]

            destroy_snapshots(dataset, outdated_snapshot_names, recursive)


def entry_point():
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    try:
        main(**vars(parse_args()))
    except KeyboardInterrupt:
        logging.error('Operation interrupted.')
        sys.exit(1)
