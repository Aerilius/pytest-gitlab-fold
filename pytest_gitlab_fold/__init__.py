"""
Pytest plugin that folds captured output sections in GitLab CI build log.
"""

from __future__ import annotations

import os
import re
import sys
from collections import defaultdict
from collections.abc import Generator
from contextlib import contextmanager
from functools import update_wrapper
from io import IOBase
from typing import TYPE_CHECKING, Optional

import pytest

if TYPE_CHECKING:
    from _pytest.reports import TestReport
    from _pytest.terminal import TerminalReporter


__version__ = "0.1.0"


PUNCT_RE = re.compile(r"\W+")


def normalize_name(name: str) -> str:
    """Strip out any "exotic" chars and whitespaces."""
    return PUNCT_RE.sub("-", name.lower()).strip("-")


def get_and_increment(name: str, counter=defaultdict(int)) -> int:
    """Allocate a new unique number for the given name."""
    n = counter[name]
    counter[name] = n + 1
    return n


def section_name(name: str, n: int, prefix: str = f"py-{os.getpid()}") -> str:
    """Join arguments to get a GitLab section name, e.g. 'py-123.section.0'"""
    return ".".join(filter(bool, [prefix, name, str(n)]))


def section_marks(section: str, line_end: str = "") -> tuple[str, str]:
    """A pair of start/end GitLab fold marks."""
    return (
        f"gitlab_fold:start:{section}{line_end}",
        f"gitlab_fold:end:{section}{line_end}",
    )


def new_section(name: str) -> str:
    """Create a new GitLab fold section and return its name."""
    name = normalize_name(name)
    n = get_and_increment(name)
    return section_name(name, n)


def new_section_marks(name: str, line_end: str = "") -> tuple[str, str]:
    """Create a new GitLab fold section and return a pair of fold marks."""
    return section_marks(new_section(name), line_end)


def detect_line_end(string: str, line_end: str | None = None) -> str:
    """
    If needed, auto-detect line end using a given string or lines.
    """
    if line_end is None:
        if string and string.endswith("\n"):
            line_end = "\n"
        else:
            line_end = ""
    return line_end


class GitLabContext:
    """
    Provides folding methods and manages whether folding is active.

    The precedence is (from higher to lower):

        1. The 'force' argument of folding methods
        2. The 'fold_enabled' attribute set from constructor
        3. The --gitlab-fold command line switch
        4. The GITLAB_CI environmental variable
    """

    def __init__(self, fold_enabled: str = "auto"):
        super().__init__()
        self.fold_enabled = False
        self.setup_fold_enabled(fold_enabled)

    def setup_fold_enabled(self, value: str = "auto"):
        if isinstance(value, str):
            if value == "never":
                self.fold_enabled = False
            elif value == "always":
                self.fold_enabled = True
            else:  # auto
                self.fold_enabled = os.environ.get("GITLAB_CI") == "true"

    def is_fold_enabled(self, force=None) -> bool:
        if force is not None:
            return bool(force)
        return self.fold_enabled

    def fold_lines(
        self,
        lines: list[str],
        name: str = "",
        line_end: str | None = None,
        force=None,
    ) -> list[str]:
        """
        Return a list of given lines wrapped with fold marks.

        If 'line_end' is not specified it is determined from the last line
        given.

        It is designed to provide an adequate result by default. That is, the
        following two snippets:

            print('\\n'.join(fold_lines([
                'Some lines',
                'With no newlines at EOL',
            ]))

        and:

            print(''.join(fold_lines([
                'Some lines\\n',
                'With newlines at EOL\\n',
            ]))

        will both output a properly folded string:

            gitlab_fold:start:...\\n
            Some lines\\n
            ... newlines at EOL\\n
            gitlab_fold:end:...\\n

        """
        if not self.is_fold_enabled(force):
            return lines
        line_end = detect_line_end(lines[-1] if lines else "", line_end)
        start_mark, end_mark = new_section_marks(name, line_end)
        folded_lines = [start_mark, end_mark]
        folded_lines[1:1] = lines
        return folded_lines

    def fold_string(
        self,
        string: str,
        name: str = "",
        sep: str = "",
        line_end: str | None = None,
        force=None,
    ) -> str:
        """
        Return a string wrapped with fold marks.

        If 'line_end' is not specified it is determined in a similar way as
        described in docs for the fold_lines() function.
        """
        if not self.is_fold_enabled(force):
            return string
        line_end = detect_line_end(string, line_end)
        if not (sep or line_end and string.endswith(line_end)):
            sep = "\n"
        return sep.join(
            self.fold_lines([string], name, line_end=line_end, force=force)
        )

    @contextmanager
    def folding_output(
        self, name: str = "", file: IOBase | None = None, force=None
    ) -> Generator[str, None, None]:
        """
        Makes the output be folded by the GitLab CI build log view.

        Context manager that wraps the output with special 'gitlab_fold' marks
        recognized by GitLab CI build log view.

        The 'file' argument must be a file-like object with a 'write()' method;
        if not specified, it defaults to 'sys.stdout' (its current value at the
        moment of calling).
        """
        if not self.is_fold_enabled(force):
            yield
            return

        if file is None:
            file = sys.stdout

        start_mark, end_mark = new_section_marks(name, line_end="\n")

        file.write(start_mark)
        try:
            yield
        finally:
            file.write(end_mark)


def pytest_addoption(parser):
    group = parser.getgroup("GitLab CI")
    group.addoption(
        "--gitlab-fold",
        action="store",
        dest="gitlab_fold",
        choices=["never", "auto", "always"],
        nargs="?",
        default="auto",
        const="always",
        help="Fold captured output sections in GitLab CI build log",
    )


@pytest.hookimpl(trylast=True)  # to let 'terminalreporter' be registered first
def pytest_configure(config):
    gitlab = GitLabContext(config.option.gitlab_fold)
    if not gitlab.fold_enabled:
        return

    reporter: TerminalReporter = config.pluginmanager.getplugin(
        "terminalreporter"
    )
    if hasattr(reporter, "_outrep_summary"):

        def patched_outrep_summary(rep: TestReport):
            """
            Patched _pytest.terminal.TerminalReporter._outrep_summary().
            """
            rep.toterminal(reporter._tw)
            for secname, content in rep.sections:
                name = secname

                # Shorten the most common case:
                # 'Captured stdout call' -> 'stdout'.
                if name.startswith("Captured "):
                    name = name[len("Captured ") :]
                if name.endswith(" call"):
                    name = name[: -len(" call")]

                if content[-1:] == "\n":
                    content = content[:-1]

                with gitlab.folding_output(
                    name,
                    file=reporter._tw,
                    # Don't fold if there's nothing to fold.
                    force=(False if not content else None),
                ):
                    reporter._tw.sep("-", secname)
                    reporter._tw.line(content)

        reporter._outrep_summary = update_wrapper(
            patched_outrep_summary, reporter._outrep_summary
        )

    cov = config.pluginmanager.getplugin("_cov")
    # We can't patch CovPlugin.pytest_terminal_summary() (which would fit
    # perfectly), since it is already registered by the plugin manager and
    # stored somewhere. Hook into a 'cov_controller' instance instead.
    cov_controller = getattr(cov, "cov_controller", None)
    if cov_controller is not None:
        orig_summary = cov_controller.summary

        def patched_summary(writer):
            with gitlab.folding_output("cov", file=writer):
                return orig_summary(writer)

        cov_controller.summary = update_wrapper(patched_summary, orig_summary)


@pytest.fixture(scope="session")
def gitlab(pytestconfig):
    """
    Methods for folding the output on GitLab CI.

    * gitlab.fold_string()     -> string that will appear folded in the GitLab
                                  build log
    * gitlab.fold_lines()      -> list of lines wrapped with the proper GitLab
                                  fold marks
    * gitlab.folding_output()  -> context manager that makes the output folded
    """
    return GitLabContext(pytestconfig.option.gitlab_fold)
