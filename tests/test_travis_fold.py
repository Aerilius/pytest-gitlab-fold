from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from _pytest.legacypath import Testdir
    from _pytest.pytester import RunResult

travis_mark_regexes = ["travis_fold:start:.*", "travis_fold:end:.*"]


@pytest.fixture
def failtest(testdir: Testdir) -> Callable[[], RunResult]:
    testdir.makepyfile(
        """
def test_something():
    print("boo!")
    assert False
"""
    )
    return testdir.runpytest


def test_no_travis_env(failtest, monkeypatch):
    """Check cmdline options on a dev env (no TRAVIS variable)."""
    monkeypatch.delenv("TRAVIS", raising=False)

    with pytest.raises(pytest.fail.Exception):
        failtest().stdout.re_match_lines(travis_mark_regexes)
    with pytest.raises(pytest.fail.Exception):
        failtest("--travis-fold=auto").stdout.re_match_lines(
            travis_mark_regexes
        )

    failtest("--travis-fold=always").stdout.re_match_lines(travis_mark_regexes)

    with pytest.raises(pytest.fail.Exception):
        failtest("--travis-fold=never").stdout.re_match_lines(
            travis_mark_regexes
        )


def test_travis_env(failtest, monkeypatch):
    """Set TRAVIS=true and check the stdout section is properly wrapped."""
    monkeypatch.setenv("TRAVIS", "true")

    failtest().stdout.re_match_lines(travis_mark_regexes)
    failtest("--travis-fold=auto").stdout.re_match_lines(travis_mark_regexes)

    failtest("--travis-fold=always").stdout.re_match_lines(travis_mark_regexes)

    with pytest.raises(pytest.fail.Exception):
        failtest("--travis-fold=never").stdout.re_match_lines(
            travis_mark_regexes
        )
