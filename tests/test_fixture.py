import re
import sys

import pytest

gitlab_mark_regexes = ["gitlab_fold:start:.*", "gitlab_fold:end:.*"]


def test_gitlab_fixture_registered(testdir):
    testdir.runpytest("--fixtures").stdout.fnmatch_lines(["gitlab"])


@pytest.mark.parametrize("force", [True, False])
def test_is_fold_enabled(testdir, force):
    testdir.makepyfile(
        f"""
def test_something(gitlab):
    assert gitlab.is_fold_enabled(True) is True
    assert gitlab.is_fold_enabled(False) is False
    assert gitlab.is_fold_enabled() is {force}
"""
    )

    gitlab_fold = "always" if force else "never"
    result = testdir.runpytest(f"--gitlab-fold={gitlab_fold}")
    assert result.ret == 0


@pytest.fixture(scope="module")
def gitlab_force(request, gitlab):
    originally_fold_enabled = gitlab.fold_enabled

    @request.addfinalizer
    def restore_fold_enabled():
        gitlab.fold_enabled = originally_fold_enabled

    gitlab.fold_enabled = True
    return gitlab


def assert_lines_folded(lines, line_end=""):
    assert lines
    marks = lines[0], lines[-1]

    if line_end:
        assert all(mark.endswith(line_end) for mark in marks)
    else:
        assert all(not mark.endswith("\n") for mark in marks)

    assert all(
        re.match(regex, mark) for mark, regex in zip(marks, gitlab_mark_regexes)
    )


def assert_string_folded(string, line_end):
    assert string

    if line_end:
        assert string.endswith(line_end)
    else:
        assert not string.endswith("\n")

    string_lines = string.splitlines()
    if all(string_lines[1:-1]):
        assert "\n\n" not in string

    assert_lines_folded(string_lines, "")


@pytest.mark.parametrize(
    ("lines", "line_end"),
    [
        ([], "\n"),
        ([""], "\n"),
        (["\n"], ""),
        (["Aww!"], "\n"),
        (["Aww!\n"], ""),
    ],
)
def test_fold_lines(lines, line_end, gitlab_force):
    actual = gitlab_force.fold_lines(lines, line_end=line_end)
    assert_lines_folded(actual, line_end)


@pytest.mark.parametrize(
    ("lines", "line_end"),
    [([], ""), ([""], ""), (["\n"], "\n"), (["Aww!"], ""), (["Aww!\n"], "\n")],
)
def test_fold_lines_detect_line_end(lines, line_end, gitlab_force):
    actual = gitlab_force.fold_lines(lines)
    assert_lines_folded(actual, line_end)


@pytest.mark.parametrize(
    ("string", "line_end"),
    [("", "\n"), ("\n", ""), ("Woo!", "\n"), ("Woo!\n", "")],
)
def test_fold_string(string, line_end, gitlab_force):
    actual = gitlab_force.fold_string(string, line_end=line_end)
    assert_string_folded(actual, line_end)


@pytest.mark.parametrize(
    ("string", "line_end"),
    [("", ""), ("\n", "\n"), ("Woo!", ""), ("Woo!\n", "\n")],
)
def test_fold_string_detect_line_end(string, line_end, gitlab_force):
    actual = gitlab_force.fold_string(string)
    assert_string_folded(actual, line_end)


def test_folding_output(gitlab_force, capsys):
    with gitlab_force.folding_output():
        print("Ouu!")
    with gitlab_force.folding_output(file=sys.stderr):
        print("Errr!", file=sys.stderr)

    out, err = capsys.readouterr()

    assert_string_folded(out, "\n")
    assert_string_folded(err, "\n")
