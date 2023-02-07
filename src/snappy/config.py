from __future__ import annotations

import re
from argparse import ArgumentTypeError
from dataclasses import dataclass
from datetime import timedelta

from typing_extensions import TypeAlias


@dataclass
class MostRecentKeepSpec:
    count: int


@dataclass
class IntervalKeepSpec:
    interval: timedelta
    count: int | None


KeepSpec: TypeAlias = 'MostRecentKeepSpec | IntervalKeepSpec'


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
