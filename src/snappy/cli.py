from __future__ import annotations

import argparse
import logging
import shlex
import sys
from argparse import Namespace
from pathlib import Path
from subprocess import CalledProcessError
from typing import TypeVar, Callable, Sequence

from snappy.config import get_default_config_path, parse_keep_spec, KeepSpec
from snappy.snappy import auto_command, cli_command, \
    default_snapshot_name_prefix, AutoAction
from snappy.utils import BetterHelpFormatter, UserError
from snappy.zfs import Dataset


T = TypeVar('T')


def list_arg(parse_fn: Callable[[str], T]) -> Callable[[str], list[T]]:
    def list_parse_fn(value: str) -> list[T]:
        return [parse_fn(i) for i in value.split(',')]

    return list_parse_fn


def _parse_args() -> Namespace:
    parser = argparse.ArgumentParser(
        formatter_class=BetterHelpFormatter,
        description='Create and/or prune snapshots on ZFS filesystems.')

    parser.add_argument(
        'datasets',
        nargs='*',
        type=Dataset,
        metavar='DATASETS',
        help='Datasets on which to create and prune snapshots.')

    parser.add_argument(
        '-r',
        '--recursive',
        action='store_true',
        help='Include children of the specified datasets when creating, '
             'sending, and/or pruning snapshots.')

    parser.add_argument(
        '-e',
        '--exclude',
        type=Dataset,
        action='append',
        default=[],
        help='Exclude a dataset and its children when enumerating datasets '
             'recursively.')

    parser.add_argument(
        '-p',
        '--prefix',
        default=None,
        help=f'Prefix of snapshot names of created and pruned snapshots. '
             f'Defaults to `{default_snapshot_name_prefix}\'.')

    parser.add_argument(
        '-S',
        '--no-snapshot',
        dest='take_snapshot',
        action='store_false',
        help='Disables creating snapshots. Instead, only prune and/or send '
             'snapshots.')

    prune_group = parser.add_argument_group('pruning')

    prune_group.add_argument(
        '-k',
        '--keep',
        type=list_arg(parse_keep_spec),
        dest='keep_specs',
        metavar='KEEP_SPECIFICATIONS',
        help='Prune snapshots according to this list of keep specifications.\n'
             'See https://github.com/Feuermurmel/snappy#pruning.')

    send_group = parser.add_argument_group('sending snapshots')

    send_group.add_argument(
        '-s',
        '--send-to',
        type=Dataset,
        dest='send_target',
        metavar='TARGET',
        help='Send the snapshots of the DATASETS into child filesystem of this '
             'target filesystem. If specified, pruning will happen on the '
             'target datasets instead of the source datasets.')

    send_group.add_argument(
        '-b',
        '--send-base',
        type=Dataset,
        help='The path prefix that is stripped from each of DATASETS and '
             'replaced with TARGET when sending snapshots to construct the '
             'names of the destination datasets. Without this option, only a '
             'single source dataset can be sent at a time, which is sent '
             'directly to TARGET.')

    auto_group = parser.add_argument_group('running from config file')

    auto_group.add_argument(
        '--auto',
        nargs='?',
        const=AutoAction,
        type=list_arg(AutoAction),
        dest='auto_actions',
        metavar='ACTIONS',
        help='Run the snapshot, send, and prune actions specified in the '
             'configuration file instead of on the command line.\n'
             '\n'
             'Use --auto=snapshot to only run snapshot and prune actions. '
             'In this mode, because snapshots are not sent, pruning on the '
             'send destinations is also skipped.\n'
             '\n'
             'Use --auto=send to only run send and prune actions. In this '
             'mode, only snapshots on send targets are pruned.')

    auto_group.add_argument(
        '--config',
        type=Path,
        dest='config_path',
        help=f'Path to the configuration file to use. Requires --auto. '
             f'Defaults to `{get_default_config_path()}\'.')

    args = parser.parse_args()

    def check(condition: bool, message: str) -> None:
        if not condition:
            parser.error(message)

    if args.auto_actions:
        check(not args.datasets and not args.recursive and args.prefix is None
              and args.take_snapshot and not args.keep_specs
              and args.send_target is None and args.send_base is None,
              '--auto conflicts with DATASETS, --recursive, --prefix, '
              '--no-snapshot, --keep, --send-to, and --send-base.')
    else:
        check(args.datasets,
              'DATASETS is required unless --auto is given.')

        check(args.recursive or not args.exclude,
              '--exclude requires --recursive.')

        check(args.config_path is None,
              '--config requires --auto, --auto-send, or --auto-snapshot.')

        check(args.take_snapshot or args.keep_specs is not None
              or args.send_target,
              '--no-snapshot requires at least one of --keep and --send-to.')

        if args.send_target is None:
            check(args.send_base is None,
                  '--send-base requires --send-to.')
        else:
            check(len(args.datasets) < 2 or args.send_base is not None,
                  '--send-to requires --send-base if more than one dataset is '
                  'specified')

    return args


# TODO: Gracefully handle non-existing source dataset (i.e. print warning and
#  skip).
def main(
        datasets: list[Dataset], recursive: bool, exclude: list[Dataset],
        prefix: str | None, take_snapshot: bool,
        keep_specs: list[KeepSpec] | None, send_target: Dataset | None,
        send_base: Dataset | None, auto_actions: Sequence[AutoAction] | None,
        config_path: Path | None) \
        -> None:
    if auto_actions is None:
        cli_command(
            datasets=datasets,
            recursive=recursive,
            exclude=exclude,
            prefix=prefix,
            take_snapshot=take_snapshot,
            pre_snapshot_script=None,
            keep_specs=keep_specs,
            send_target=send_target,
            send_base=send_base,
            do_snapshot=True,
            do_send=True)
    else:
        auto_command(config_path, auto_actions)


def entry_point() -> None:
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    try:
        main(**vars(_parse_args()))
    except UserError as e:
        logging.error(f'error: {e}')
        sys.exit(1)
    except CalledProcessError as e:
        cmdline_str = e.cmd

        if not isinstance(e.cmd, (str, bytes)):
            cmdline_str = shlex.join(cmdline_str)

        logging.error(f'error: Internal command failed: {cmdline_str}')
        sys.exit(1)
    except KeyboardInterrupt:
        logging.error('Operation interrupted.')
        sys.exit(130)
