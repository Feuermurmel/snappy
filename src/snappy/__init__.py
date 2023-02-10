from __future__ import annotations

import argparse
import logging
import sys
from argparse import Namespace
from pathlib import Path
from typing import TypeVar, Callable

from snappy.config import get_default_config_path, parse_keep_spec, KeepSpec
from snappy.snappy import auto_command, cli_command, default_snapshot_name_prefix
from snappy.utils import BetterHelpFormatter, UserError


T = TypeVar('T')


def list_arg(parse_fn: Callable[[str], T]) -> Callable[[str], list[T]]:
    def list_parse_fn(value: str) -> list[T]:
        return [parse_fn(i) for i in value.split(',')]

    return list_parse_fn


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
        '-p',
        '--prefix',
        help=f'Prefix of snapshot names of created and pruned snapshots. '
             f'Defaults to `{default_snapshot_name_prefix}\'.')

    parser.add_argument(
        '-S',
        '--no-snapshot',
        dest='take_snapshot',
        action='store_false',
        help='Disables creating snapshots. Instead, only prune snapshots.')

    parser.add_argument(
        'datasets',
        nargs='*',
        metavar='DATASETS',
        help='Datasets on which to create (and prune) snapshots.')

    pruning_group = parser.add_argument_group('pruning')

    pruning_group.add_argument(
        '-k',
        '--keep',
        type=list_arg(parse_keep_spec),
        dest='keep_specs',
        metavar='KEEP_SPECIFICATION',
        help='Comma-separated list of keep specifications that specify how '
             'many snapshots to keep in what intervals.')

    auto_group = parser.add_argument_group('running from config file')

    auto_group.add_argument(
        '--auto',
        action='store_true',
        help='Run the snapshot and prune actions specified in the '
             'configuration file instead of on the command line.')

    auto_group.add_argument(
        '--config',
        type=Path,
        dest='config_path',
        help=f'Path to the configuration file to use. Requires --auto. '
             f'Defaults to `{get_default_config_path()}\'.')

    args = parser.parse_args()

    if args.auto:
        if args.recursive or args.prefix is not None or args.keep_specs \
                or not args.take_snapshot or args.datasets:
            parser.error('--auto conflicts with --recursive, --prefix, --keep, '
                         '--no-snapshot and DATASETS.')
    else:
        if not args.datasets:
            parser.error('DATASETS is required unless --auto is given.')

        if args.config_path is not None:
            parser.error('--config requires --auto.')

        if not args.take_snapshot and args.keep_specs is None:
            parser.error('--no-snapshot requires --keep.')

    return args


def main(
        datasets: list[str], recursive: bool, prefix: str | None,
        keep_specs: list[KeepSpec] | None, take_snapshot: bool, auto: bool,
        config_path: Path | None):
    if auto:
        auto_command(config_path)
    else:
        cli_command(datasets, recursive, prefix, keep_specs, take_snapshot)


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
