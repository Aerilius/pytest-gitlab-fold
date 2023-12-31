# pytest-gitlab-fold

[![Tests][badge-tests]][link-tests]
[![PyPI][badge-pypi]][link-pypi]

[Pytest] plugin that folds output sections in GitLab CI build log.

It is a port of Eldar Abusalimov's excellent [pytest-travis-fold] plugin,
all credits go to him and contributors.

![GitLab CI build log view](docs/screenshot.png)

In addition, pytest-gitlab-fold recognizes presence of the [pytest-cov]
plugin and folds coverage reports accordingly.

## Installation and Usage

Just install the \[pytest-gitlab-fold\]\[linnk-pypi\] package
as part of your build.

When using [tox], add the package to the `deps` list in your `tox.ini`
and make sure the `GITLAB_CI` environment variable is passed:

```ini
[testenv]
deps =
    pytest-gitlab-fold
passenv = GITLAB_CI
```

If you **don't** use tox and invoke `py.test` directly from `.gitlab-ci.yml`,
you may install the package as an additional `install` step:

```yaml
install:
  - pip install -e .
  - pip install pytest-gitlab-fold

script: py.test
```

Output folding is enabled automatically when running inside GitLab CI. It is OK
to have the plugin installed also in your dev environment: it is only activated
by checking the presence of the `GITLAB_CI` environmental variable, unless the
`--gitlab-fold` command line switch is used.

## The `gitlab` fixture

The plugin by itself only makes the captured output sections appear folded.
If you wish to make the same thing with arbitrary lines, you can do it manually
by using the `gitlab` fixture.

It is possible to fold the output of a certain code block using the
`gitlab.folding_output()` context manager:

```python
def test_something(gitlab):
    with gitlab.folding_output():
        print("Lines, lines, lines...")
        print("Lots of them!")
        ...
```

Or you may want to use lower-level `gitlab.fold_string()` and
`gitlab.fold_lines()` functions and then output the result as usual.

## Contributing

Contributions are very welcome. Tests can be run with [tox], please ensure
the coverage at least stays the same before you submit a pull request.

## License

Distributed under the terms of the [MIT][license] license, "pytest-gitlab-fold" is
free and open source software.

## Issues

If you encounter any problems, please [file an issue][issues] along with a detailed
description.

[badge-pypi]: https://img.shields.io/pypi/v/pytest-gitlab-fold
[badge-tests]: https://img.shields.io/github/actions/workflow/status/aerilius/pytest-gitlab-fold/tests.yml?branch=main&label=tests
[issues]: https://github.com/aerilius/pytest-gitlab-fold/issues
[license]: http://opensource.org/licenses/MIT
[link-pypi]: https://pypi.org/project/pytest-gitlab-fold/
[link-tests]: https://github.com/aerilius/pytest-gitlab-fold/actions/workflows/tests.yml
[pytest]: https://github.com/pytest-dev/pytest
[pytest-cov]: https://github.com/pytest-dev/pytest-cov
[pytest-travis-fold]: https://github.com/abusalimov/pytest-travis-fold
[tox]: https://tox.readthedocs.org/en/latest
