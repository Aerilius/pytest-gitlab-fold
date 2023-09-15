from __future__ import annotations

import re
from collections.abc import Callable
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from _pytest.legacypath import Testdir
    from _pytest.pytester import RunResult


gitlab_mark_regexes = [
    r"\x1b\[0Ksection_start:\d+:[^:\r]+[\r\n]\x1b\[0K",
    r"\x1b\[0Ksection_end:\d+:[^:\r]+[\r\n]\x1b\[0K",
]


@pytest.fixture
def run_failing_test(testdir: Testdir) -> Callable[[str], RunResult]:
    testdir.makepyfile(
        """
def test_something():
    print("boo!")
    assert False
"""
    )
    return testdir.runpytest


@pytest.mark.parametrize(
    "args",
    [
        pytest.param([], marks=pytest.mark.xfail(strict=True)),
        pytest.param(
            ["--gitlab-fold=auto"], marks=pytest.mark.xfail(strict=True)
        ),
        ["--gitlab-fold=always"],
        pytest.param(
            ["--gitlab-fold=never"], marks=pytest.mark.xfail(strict=True)
        ),
    ],
)
def test_no_gitlab_env(args, run_failing_test, monkeypatch):
    """Check cmdline options on a dev env (no GITLAB_CI variable)."""
    monkeypatch.delenv("GITLAB_CI", raising=False)
    # Here, run_failing_test returns a RunResult through
    # `Pytester.runpytest_inprocess` which uses str.splitlines which breaks
    # on \r. Thus we cannot use `RunResult.stdout.re_match_lines`, but join
    # `RunResult.outlines` and allow the separator \n in place of expected \r.
    # This should only affect the way how to do assertions, not the desired
    # pytest terminal output.

    actual = run_failing_test(*args)
    actual_stdout_str = "\n".join(actual.outlines)
    assert all(
        re.search(r"\n" + regex, actual_stdout_str)
        for regex in gitlab_mark_regexes
    )


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["--gitlab-fold=auto"],
        ["--gitlab-fold=always"],
        pytest.param(
            ["--gitlab-fold=never"], marks=pytest.mark.xfail(strict=True)
        ),
    ],
)
def test_gitlab_env(args, run_failing_test, monkeypatch):
    """Set GITLAB_CI=true and check the stdout section is properly wrapped."""
    monkeypatch.setenv("GITLAB_CI", "true")

    actual = run_failing_test(*args)
    actual_stdout_str = "\n".join(actual.outlines)
    assert all(
        re.search(r"\n" + regex, actual_stdout_str)
        for regex in gitlab_mark_regexes
    )
