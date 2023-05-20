from __future__ import annotations

import re
from argparse import ArgumentTypeError
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Union, Optional

import dacite
import toml
from typing_extensions import TypeAlias

from snappy.test_utils import mockable_fn
from snappy.utils import UserError
from snappy.zfs import Dataset


@dataclass
class Config:
    snapshot: list[SnapshotConfig] = field(default_factory=list)


@dataclass
class SnapshotConfig:
    datasets: list[Dataset]
    recursive: bool = False
    exclude: list[Dataset] = field(default_factory=list)
    prefix: Optional[str] = None
    take_snapshot: bool = True
    pre_snapshot_script: Optional[str] = None
    prune_keep: Optional[list[KeepSpec]] = None
    send_target: Optional[Dataset] = None
    send_base: Optional[Dataset] = None


@dataclass
class MostRecentKeepSpec:
    count: int


@dataclass
class IntervalKeepSpec:
    interval: timedelta
    count: int | None


KeepSpec: TypeAlias = Union[MostRecentKeepSpec, IntervalKeepSpec]


# A bit of a hack that works both with dacite and argparse to produce sensible
# error messages.
class ValidationError(ArgumentTypeError, dacite.DaciteFieldError):
    def __init__(self, message: str):
        super().__init__(None)

        self.message = message

    def __str__(self) -> str:
        if self.field_path is None:
            return self.message

        return f'Invalid value in field "{self.field_path}": {self.message}'


_units = {
    's': timedelta(seconds=1),
    'm': timedelta(minutes=1),
    'h': timedelta(hours=1),
    'd': timedelta(days=1),
    'w': timedelta(weeks=1)}


def parse_keep_spec(value: str) -> KeepSpec:
    match = re.fullmatch('([0-9]*)([^:]*?)(?::(.*))?', value)
    assert match
    number_str, unit_str, count_str = match.groups()

    if not number_str:
        raise ValidationError('Missing count or interval.')

    number = int(number_str)

    if unit_str == '':
        if count_str is not None:
            raise ValidationError(
                'Only a time interval can be followed by a `:\'.')

        if number <= 0:
            raise ValidationError('Count must be non-zero.')

        return MostRecentKeepSpec(number)
    else:
        unit = _units.get(unit_str)

        if unit is None:
            raise ValidationError(f'Unknown unit `{unit_str}\'.')

        if number <= 0:
            raise ValidationError('Interval must be non-zero.')

        if count_str is None:
            count = None
        else:
            if not count_str:
                raise ValidationError('Missing count after `:\'.')

            try:
                count = int(count_str)
            except ValueError:
                raise ValidationError(f'Invalid count `{count_str}\'.')

            if count <= 0:
                raise ValidationError('Count must be non-zero.')

        return IntervalKeepSpec(number * unit, count)


_dacite_type_hooks = {KeepSpec: parse_keep_spec}


def get_default_config_path() -> Path:
    return Path('/etc/snappy/snappy.toml')


def _validate_config(config: Config, config_path: Path) -> None:
    def check(condition: object, message: str) -> None:
        if not condition:
            raise UserError(f'Error in config file `{config_path}\': {message}')

    for i in config.snapshot:
        check(i.take_snapshot or i.prune_keep or i.send_target is not None,
              'At least one of keys `prune_keep\' or `send_target\' is '
              'required if `take_snapshot\' is set to false.')

        check(i.recursive or not i.exclude,
              'Key `exclude\' requires that `recursive\' is set to true.')

        check(i.prune_keep is None or i.prune_keep,
              '`prune_keep\' cannot be an empty list.')

        check(i.pre_snapshot_script is None or i.take_snapshot,
              'Key `pre_snapshot_script\' requires that `take_snapshot\' is '
              'set to true')

        if i.send_target is None:
            check(i.send_base is None,
                  'Key `send_target\' is required if `send_base\' is set.')
        else:
            check(len(i.datasets) < 2 or i.send_base is not None,
                  'Key `send_base\' is required if `send_target\' is set and '
                  'multiple datasets are specified.')


_dacite_config = dacite.Config(type_hooks=_dacite_type_hooks)  # type: ignore


@mockable_fn
def load_config(path: Path) -> Config:
    try:
        config = dacite.from_dict(Config, toml.load(path), _dacite_config)
    except (FileNotFoundError, toml.TomlDecodeError, dacite.DaciteError) as e:
        raise UserError(f'Error loading config file `{path}\': {e}')

    _validate_config(config, path)

    return config
