"""
Contains stuff used for testing, that needs to be also available to the
application. It's important that this module can be imported without importing
any of the application's code.
"""

import sys
from functools import wraps
from typing import ParamSpec, TypeVar, Callable


T = TypeVar('T')
P = ParamSpec('P')


def mockable_fn(fn: Callable[P, T]) -> Callable[P, T]:
    """
    Decorator for functions that allows them to be mocked even after they've
    been imported with a `from` import.
    """
    if 'pytest' not in sys.modules:
        return fn

    @wraps(fn)
    def wrapped_fn(*args: P.args, **kwargs: P.kwargs) -> T:
        return wrapped_fn.__wrapped__(*args, **kwargs)  # type: ignore

    return wrapped_fn
