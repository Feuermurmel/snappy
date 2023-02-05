import argparse
import logging
import re
import sys
from argparse import Namespace, ArgumentTypeError
from datetime import timedelta

from snappy.snappy import main
from snappy.snapshots import KeepSpec, MostRecentKeepSpec, IntervalKeepSpec
from snappy.utils import BetterHelpFormatter


_units = {
    's': timedelta(seconds=1),
    'm': timedelta(minutes=1),
    'h': timedelta(hours=1),
    'd': timedelta(days=1),
    'w': timedelta(weeks=1)}


def _keep_spec(value: str) -> KeepSpec:
    match = re.fullmatch('([0-9]*)([^:]*?)(?::(.*))?', value)
    assert match
    number_str, unit_str, count_str = match.groups()

    if not number_str:
        raise ArgumentTypeError('Missing count or interval.')

    number = int(number_str)

    if unit_str == '':
        if count_str is not None:
            raise ArgumentTypeError(
                'Only a time interval can be followed by a `:\'.')

        return MostRecentKeepSpec(number)
    else:
        unit = _units.get(unit_str)

        if unit is None:
            raise ArgumentTypeError(f'Unknown unit `{unit_str}\'.')

        if number == 0:
            raise ArgumentTypeError('Interval must be non-zero.')

        if count_str == '':
            raise ArgumentTypeError('Missing count after `:\'.')

        if count_str is None:
            count = None
        else:
            try:
                count = int(count_str)
            except ValueError:
                raise ArgumentTypeError(f'Invalid count `{count_str}\'.')

        return IntervalKeepSpec(number * unit, count)


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
        type=_keep_spec,
        dest='keep_specs',
        action='append',
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
        'datasets',
        nargs='+',
        help='Datasets on which to create (and prune) snapshots.')

    args = parser.parse_args()

    if args.prune_only and args.keep_specs is None:
        parser.error('--prune-only requires --keep.')

    return args


def entry_point():
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    try:
        main(**vars(_parse_args()))
    except KeyboardInterrupt:
        logging.error('Operation interrupted.')
        sys.exit(130)
