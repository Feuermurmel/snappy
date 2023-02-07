from __future__ import annotations

import re
from argparse import ArgumentTypeError
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Union

import dacite
import toml
from typing_extensions import TypeAlias

from snappy.utils import UserError


@dataclass
class Config:
    snapshot: list[SnapshotConfig] = field(default_factory=list)


@dataclass
class SnapshotConfig:
    datasets: list[str]
    recursive: bool = False
    prune_only: bool = False
    prune: Union[PruneConfig, None] = None


@dataclass
class PruneConfig:
    keep: list[KeepSpec]


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

    def __str__(self):
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

        return MostRecentKeepSpec(number)
    else:
        unit = _units.get(unit_str)

        if unit is None:
            raise ValidationError(f'Unknown unit `{unit_str}\'.')

        if number == 0:
            raise ValidationError('Interval must be non-zero.')

        if count_str == '':
            raise ValidationError('Missing count after `:\'.')

        if count_str is None:
            count = None
        else:
            try:
                count = int(count_str)
            except ValueError:
                raise ValidationError(f'Invalid count `{count_str}\'.')

        return IntervalKeepSpec(number * unit, count)


_dacite_type_hooks = {KeepSpec: parse_keep_spec}


def get_default_config_path() -> Path:
    return Path('/etc/snappy/snappy.toml')


# Can be mocked from tests.
def _load_config(path: Path) -> Config:
    dacite_config = dacite.Config(type_hooks=_dacite_type_hooks)  # type: ignore

    return dacite.from_dict(Config, toml.load(path), dacite_config)


def load_config(path: Path) -> Config:
    try:
        return _load_config(path)
    except (FileNotFoundError, toml.TomlDecodeError, dacite.DaciteError) as e:
        raise UserError(f'Error loading config file `{path}\': {e}')
