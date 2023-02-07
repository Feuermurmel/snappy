import argparse
import logging
import sys
from argparse import Namespace
from pathlib import Path

from snappy.config import get_default_config_path, parse_keep_spec
from snappy.snappy import main
from snappy.utils import BetterHelpFormatter, UserError


def _parse_args() -> Namespace:
    parser = argparse.ArgumentParser(
        formatter_class=BetterHelpFormatter,
        description='Create and/or prune snapshots on ZFS filesystems.',
        epilog='KEEP SPECIFICATION\n'
               '\n'
               'Either a number or a TIME INTERVAL. When a number is given, it '
               'specifies to keep that many most recent snapshots.\n'
               '\n'
               'If a time interval is given, it specifies to keep one snapshot '
               'per that interval. The interval can be followed by a `:\' and '
               'a number, which specifies to keep only that many most recent '
               'snapshots taken in that interval.\n'
               '\n'
               'TIME INTERVAL\n'
               '\n'
               'A number followed by one of the time units `s\', `m\', `h\', '
               '`d\', or `w\', specifying an interval of that many seconds, '
               'minutes, hours, days, or weeks respectively.')

    parser.add_argument(
        '-r',
        '--recursive',
        action='store_true',
        help='Create and prune snapshots recursively on the specified '
             'datasets.')

    parser.add_argument(
        '-k',
        '--keep',
        type=parse_keep_spec,
        dest='keep_specs',
        action='append',
        default=[],
        metavar='KEEP SPECIFICATION',
        help='Prune old snapshots after creating a new one. This option can be '
             'given multiple times to keep additional snapshots in different '
             'time intervals.')

    parser.add_argument(
        '-p',
        '--prune-only',
        action='store_true',
        help='Disables creating snapshots. Requires --keep.')

    parser.add_argument(
        '--auto',
        action='store_true',
        help='Run the snapshot and prune actions specified in the '
             'configuration file instead of on the command line.')

    parser.add_argument(
        '--config',
        type=Path,
        dest='config_path',
        help=f'Path to the configuration file to use. Requires --auto. '
             f'Defaults to `{get_default_config_path()}\'.')

    parser.add_argument(
        'datasets',
        nargs='*',
        metavar='DATASETS',
        help='Datasets on which to create (and prune) snapshots.')

    args = parser.parse_args()

    if args.auto:
        if args.recursive or args.keep_specs or args.prune_only or args.datasets:
            parser.error('--auto conflicts with --recursive, --keep, '
                         '--prune-only and DATASETS.')
    else:
        if not args.datasets:
            parser.error('DATASETS is required unless --auto is given.')

        if args.config_path is not None:
            parser.error('--config requires --auto.')

        if args.prune_only and not args.keep_specs:
            parser.error('--prune-only requires --keep.')

    return args


def entry_point():
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    try:
        main(**vars(_parse_args()))
    except UserError as e:
        logging.error(f'error: {e}')
        sys.exit(1)
    except KeyboardInterrupt:
        logging.error('Operation interrupted.')
        sys.exit(130)
