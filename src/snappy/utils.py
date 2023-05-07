import shlex
import sys
import textwrap
from argparse import HelpFormatter
from functools import wraps
from subprocess import check_call
from typing import ParamSpec, TypeVar, Callable, Any


T = TypeVar('T')
P = ParamSpec('P')


timestamp_format = '%Y-%m-%d-%H%M%S'


class UserError(Exception):
    pass


def _wrap_paragraphs(text: str, width: int, indent: str) -> list[str]:
    """
    Wrapper around `textwrap.wrap()` which keeps newlines in the input string
    intact.
    """
    lines = list[str]()

    for i in text.splitlines():
        paragraph_lines = \
            textwrap.wrap(i, width, initial_indent=indent, subsequent_indent=indent)

        # `textwrap.wrap()` will return an empty list when passed an empty
        # string (which happens when there are two consecutive line breaks in
        # the input string). This would lead to those line breaks being
        # collapsed into a single line break, effectively removing empty lines
        # from the input. Thus, we add an empty line in that case.
        lines.extend(paragraph_lines or [''])

    return lines


class BetterHelpFormatter(HelpFormatter):
    def _split_lines(self, text: str, width: int) -> list[str]:
        return _wrap_paragraphs(text, width, '')

    def _fill_text(self, text: str, width: int, indent: str) -> str:
        return '\n'.join(_wrap_paragraphs(text, width, indent))


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


def check_call_pipeline(*cmdlines: list[str], **kwargs: Any) -> None:
    """
    subprocess.check_call() for pipelines. Each element of cmdlines is a list
    representing a command line of separate processes to be started. All started
    processes are joined in a pipeline.
    """
    check_call(' | '.join(shlex.join(i) for i in cmdlines), shell=True, **kwargs)
