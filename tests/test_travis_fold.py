from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from _pytest.legacypath import Testdir
    from _pytest.pytester import RunResult

travis_mark_regexes = ["travis_fold:start:.*", "travis_fold:end:.*"]


@pytest.fixture
def failtest(testdir: Testdir) -> Callable[[str], RunResult]:
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
        pytest.param(
            [],
            marks=pytest.mark.xfail(strict=True, raises=pytest.fail.Exception),
        ),
        pytest.param(
            ["--travis-fold=auto"],
            marks=pytest.mark.xfail(strict=True, raises=pytest.fail.Exception),
        ),
        ["--travis-fold=always"],
        pytest.param(
            ["--travis-fold=never"],
            marks=pytest.mark.xfail(strict=True, raises=pytest.fail.Exception),
        ),
    ],
)
def test_no_travis_env(args, failtest, monkeypatch):
    """Check cmdline options on a dev env (no TRAVIS variable)."""
    monkeypatch.delenv("TRAVIS", raising=False)

    failtest(*args).stdout.re_match_lines(travis_mark_regexes)


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["--travis-fold=auto"],
        ["--travis-fold=always"],
        pytest.param(
            ["--travis-fold=never"],
            marks=pytest.mark.xfail(strict=True, raises=pytest.fail.Exception),
        ),
    ],
)
def test_travis_env(args, failtest, monkeypatch):
    """Set TRAVIS=true and check the stdout section is properly wrapped."""
    monkeypatch.setenv("TRAVIS", "true")

    failtest(*args).stdout.re_match_lines(travis_mark_regexes)
