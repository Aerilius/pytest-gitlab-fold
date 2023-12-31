"""
Pytest plugin that folds captured output sections in GitLab CI build log.
"""

from __future__ import annotations

import os
import re
import sys
import time
from collections import Counter
from collections.abc import Generator
from contextlib import contextmanager
from functools import update_wrapper
from io import IOBase
from typing import TYPE_CHECKING, Optional

import pytest

if TYPE_CHECKING:
    from _pytest.reports import TestReport
    from _pytest.terminal import TerminalReporter


__version__ = "0.3.1"


SECTION_COUNTER = Counter()
SECTION_NAME_MAX_LEN = 30


def create_unique_section_name(name: str = "section") -> str:
    name = re.sub(r"[^A-Za-z0-9]+", "_", name)[:SECTION_NAME_MAX_LEN].lower()
    SECTION_COUNTER[name] += 1
    count = SECTION_COUNTER[name]
    if name == "" or count != 1:
        name += str(count)
    return name


def gitlab_supports_collapsed() -> bool:
    major = int(os.environ.get("CI_SERVER_VERSION_MAJOR", -1))
    minor = int(os.environ.get("CI_SERVER_VERSION_MINOR", -1))
    return (major, minor) >= (13, 5)


def start_section(
    name: str,
    header: str,
    timestamp: int | None = None,
    collapsed: bool = False,
    line_end: str = "",
) -> str:
    if timestamp is None:
        timestamp = int(time.time())
    if gitlab_supports_collapsed():
        collapsed_option = f"[collapsed={str(collapsed).lower()}]"
    else:
        collapsed_option = ""
    # Note: ASCII control escape sequences are not guaranteed to work in all
    # languages. It is recommended to use the decimal, octal or hex
    # representation as escape code.
    # Contrary to the example in GitLab documentation at
    # https://docs.gitlab.com/ee/ci/jobs/#custom-collapsible-sections
    # we need to use \033 instead of \e to make it work in Python.
    return f"\033[0Ksection_start:{timestamp}:{name}{collapsed_option}\r\033[0K{header}{line_end}"


def end_section(
    name: str, timestamp: int | None = None, line_end: str = ""
) -> str:
    if timestamp is None:
        timestamp = int(time.time())
    return f"\033[0Ksection_end:{timestamp}:{name}\r\033[0K{line_end}"


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
        title: str = "",
        timestamp_start: int | None = None,
        timestamp_end: int | None = None,
        collapsed: bool = False,
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
        name = create_unique_section_name(title)
        start_mark = start_section(
            name,
            header=title,
            timestamp=timestamp_start,
            collapsed=collapsed,
            line_end=line_end,
        )
        end_mark = end_section(name, timestamp=timestamp_end, line_end=line_end)
        folded_lines = [start_mark, end_mark]
        folded_lines[1:1] = lines
        return folded_lines

    def fold_string(
        self,
        string: str,
        title: str = "",
        timestamp_start: int | None = None,
        timestamp_end: int | None = None,
        collapsed: bool = False,
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
            self.fold_lines(
                [string],
                title,
                timestamp_start=timestamp_start,
                timestamp_end=timestamp_end,
                collapsed=collapsed,
                line_end=line_end,
                force=force,
            )
        )

    @contextmanager
    def folding_output(
        self,
        title: str = "",
        timestamp_start: int | None = None,
        timestamp_end: int | None = None,
        collapsed: bool = False,
        file: IOBase | None = None,
        force=None,
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

        # Unfortunately, collapsed can only be set in the section start, so we
        # can not set it depending on the outcome of yield.
        name = create_unique_section_name(title)
        start_mark = start_section(
            name,
            header=title,
            timestamp=timestamp_start,
            collapsed=collapsed,
            line_end="\n",
        )
        file.write(start_mark)
        try:
            yield
        finally:
            end_mark = end_section(name, timestamp=timestamp_end, line_end="\n")
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
            # Report of an individual test case (failed, passed, skipped)
            has_content = rep.longrepr
            start = int(getattr(rep, "start", 0))
            stop = int(getattr(rep, "stop", getattr(rep, "duration", 0)))
            with gitlab.folding_output(
                title=rep.head_line,
                timestamp_start=start,
                timestamp_end=stop,
                collapsed=not rep.failed,
                file=reporter._tw,
                # Don't fold if there's nothing to fold.
                force=(False if not has_content else None),
            ):
                rep.toterminal(reporter._tw)

            # Optional sections like stdout, stderr, log
            for secname, content in rep.sections:
                title = secname

                if content[-1:] == "\n":
                    content = content[:-1]

                with gitlab.folding_output(
                    title=title,
                    collapsed=True,
                    file=reporter._tw,
                    # Don't fold if there's nothing to fold.
                    force=(False if not content else None),
                ):
                    reporter._tw.sep("-", secname)
                    reporter._tw.line(content)

        reporter._outrep_summary = update_wrapper(
            patched_outrep_summary, reporter._outrep_summary
        )

    if hasattr(reporter, "summary_warnings"):
        orig_summary_warnings = reporter.summary_warnings

        def patched_summary_warnings():
            final = reporter._already_displayed_warnings is not None
            title = "warnings summary (final)" if final else "warnings summary"
            n_warnings = len(reporter.stats.get("warnings") or [])
            n_displayed: int = reporter._already_displayed_warnings or 0
            has_warnings = reporter.hasopt("w") and n_warnings - n_displayed > 0
            with gitlab.folding_output(
                title=title,
                collapsed=True,
                file=reporter._tw,
                # Don't fold if there's nothing to fold.
                force=(False if not has_warnings else None),
            ):
                orig_summary_warnings()

        reporter.summary_warnings = update_wrapper(
            patched_summary_warnings, reporter.summary_warnings
        )

    if hasattr(reporter, "short_test_summary"):
        orig_short_test_summary = reporter.short_test_summary

        def patched_short_test_summary():
            has_summaries = reporter.reportchars
            with gitlab.folding_output(
                title="short test summary info",
                collapsed=False,
                file=reporter._tw,
                # Don't fold if there's nothing to fold.
                force=(False if not has_summaries else None),
            ):
                orig_short_test_summary()

        reporter.short_test_summary = update_wrapper(
            patched_short_test_summary, reporter.short_test_summary
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
