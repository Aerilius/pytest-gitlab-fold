from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from _pytest.legacypath import Testdir
    from _pytest.pytester import RunResult

gitlab_mark_regexes = ["gitlab_fold:start:.*", "gitlab_fold:end:.*"]


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
        pytest.param(
            [],
            marks=pytest.mark.xfail(strict=True, raises=pytest.fail.Exception),
        ),
        pytest.param(
            ["--gitlab-fold=auto"],
            marks=pytest.mark.xfail(strict=True, raises=pytest.fail.Exception),
        ),
        ["--gitlab-fold=always"],
        pytest.param(
            ["--gitlab-fold=never"],
            marks=pytest.mark.xfail(strict=True, raises=pytest.fail.Exception),
        ),
    ],
)
def test_no_gitlab_env(args, run_failing_test, monkeypatch):
    """Check cmdline options on a dev env (no GITLAB_CI variable)."""
    monkeypatch.delenv("GITLAB_CI", raising=False)

    run_failing_test(*args).stdout.re_match_lines(gitlab_mark_regexes)


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["--gitlab-fold=auto"],
        ["--gitlab-fold=always"],
        pytest.param(
            ["--gitlab-fold=never"],
            marks=pytest.mark.xfail(strict=True, raises=pytest.fail.Exception),
        ),
    ],
)
def test_gitlab_env(args, run_failing_test, monkeypatch):
    """Set GITLAB_CI=true and check the stdout section is properly wrapped."""
    monkeypatch.setenv("GITLAB_CI", "true")

    run_failing_test(*args).stdout.re_match_lines(gitlab_mark_regexes)
