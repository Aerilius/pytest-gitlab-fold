import re
import sys

import pytest

travis_mark_regexes = ["travis_fold:start:.*", "travis_fold:end:.*"]


def test_travis_fixture_registered(testdir):
    testdir.runpytest("--fixtures").stdout.fnmatch_lines(["travis"])


@pytest.mark.parametrize("force", [True, False])
def test_is_fold_enabled(testdir, force):
    testdir.makepyfile(
        f"""
def test_something(travis):
    assert travis.is_fold_enabled(True) is True
    assert travis.is_fold_enabled(False) is False
    assert travis.is_fold_enabled() is {force}
"""
    )

    travis_fold = "always" if force else "never"
    result = testdir.runpytest(f"--travis-fold={travis_fold}")
    assert result.ret == 0


@pytest.fixture(scope="module")
def travis_force(request, travis):
    originally_fold_enabled = travis.fold_enabled

    @request.addfinalizer
    def restore_fold_enabled():
        travis.fold_enabled = originally_fold_enabled

    travis.fold_enabled = True
    return travis


def assert_lines_folded(lines, line_end):
    assert lines
    marks = lines[0], lines[-1]

    if line_end:
        assert all(mark.endswith(line_end) for mark in marks)
    else:
        assert all(not mark.endswith("\n") for mark in marks)

    assert all(
        re.match(regex, mark) for mark, regex in zip(marks, travis_mark_regexes)
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
def test_fold_lines(lines, line_end, travis_force):
    actual = travis_force.fold_lines(lines, line_end=line_end)
    assert_lines_folded(actual, line_end)


@pytest.mark.parametrize(
    ("lines", "line_end"),
    [([], ""), ([""], ""), (["\n"], "\n"), (["Aww!"], ""), (["Aww!\n"], "\n")],
)
def test_fold_lines_detect_line_end(lines, line_end, travis_force):
    actual = travis_force.fold_lines(lines)
    assert_lines_folded(actual, line_end)


@pytest.mark.parametrize(
    ("string", "line_end"),
    [("", "\n"), ("\n", ""), ("Woo!", "\n"), ("Woo!\n", "")],
)
def test_fold_string(string, line_end, travis_force):
    actual = travis_force.fold_string(string, line_end=line_end)
    assert_string_folded(actual, line_end)


@pytest.mark.parametrize(
    ("string", "line_end"),
    [("", ""), ("\n", "\n"), ("Woo!", ""), ("Woo!\n", "\n")],
)
def test_fold_string_detect_line_end(string, line_end, travis_force):
    actual = travis_force.fold_string(string)
    assert_string_folded(actual, line_end)


def test_folding_output(travis_force, capsys):
    with travis_force.folding_output():
        print("Ouu!")
    with travis_force.folding_output(file=sys.stderr):
        print("Errr!", file=sys.stderr)

    out, err = capsys.readouterr()

    assert_string_folded(out, "\n")
    assert_string_folded(err, "\n")
