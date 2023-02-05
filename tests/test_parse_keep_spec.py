from argparse import ArgumentTypeError
from datetime import timedelta

import pytest

from snappy import _keep_spec, MostRecentKeepSpec, IntervalKeepSpec


@pytest.mark.parametrize(
    'value, result',
    [
        ('', 'Missing count or interval'),
        (':', 'Missing count or interval'),
        ('h', 'Missing count or interval'),
        (':5', 'Missing count or interval'),
        ('-1', 'Missing count or interval'),
        ('0', MostRecentKeepSpec(0)),
        ('5', MostRecentKeepSpec(5)),
        ('5m', IntervalKeepSpec(timedelta(minutes=5), None)),
        ('5w', IntervalKeepSpec(timedelta(weeks=5), None)),
        ('5:', 'Only a time interval can be followed by a `:\''),
        ('5:7', 'Only a time interval can be followed by a `:\''),
        ('5d:7', IntervalKeepSpec(timedelta(days=5), 7)),
        ('5d::', 'Invalid count `:\''),
        ('5d:1w', 'Invalid count `1w\''),
        ('5d:', 'Missing count after `:\''),
        ('5d7', 'Unknown unit `d7\''),
        ('5y', 'Unknown unit `y\'')])
def test_parse_keep_spec(value, result):
    if isinstance(result, str):
        with pytest.raises(ArgumentTypeError, match=result):
            _keep_spec(value)
    else:
        assert _keep_spec(value) == result
