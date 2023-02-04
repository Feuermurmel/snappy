import argparse
import logging
import sys
from argparse import Namespace

from snappy.snappy import main
from snappy.utils import BetterHelpFormatter


def _parse_args() -> Namespace:
    parser = argparse.ArgumentParser(formatter_class=BetterHelpFormatter)

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


def entry_point():
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    try:
        main(**vars(_parse_args()))
    except KeyboardInterrupt:
        logging.error('Operation interrupted.')
        sys.exit(130)
