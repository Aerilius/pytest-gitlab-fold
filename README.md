# pytest-gitlab-fold

[Pytest][4] plugin that folds output sections in GitLab CI build log.

It is a port of Eldar Abusalimov's excellent [pytest-travis-fold][7] plugin,
all credits go to him and contributors.

![GitLab CI build log view](<>)

In addition, pytest-gitlab-fold recognizes presence of the [pytest-cov][5]
plugin and folds coverage reports accordingly.

## Installation and Usage

Just install the [pytest-gitlab-fold][1] package
as part of your build.

When using [tox][6], add the package to the `deps` list in your `tox.ini`
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

Contributions are very welcome. Tests can be run with [tox][6], please ensure
the coverage at least stays the same before you submit a pull request.

## License

Distributed under the terms of the [MIT][2] license, "pytest-gitlab-fold" is
free and open source software.

## Issues

If you encounter any problems, please [file an issue][3] along with a detailed
description.

[1]: https://pypi.python.org/pypi/pytest-gitlab-fold
[2]: http://opensource.org/licenses/MIT
[3]: https://github.com/aerilius/pytest-gitlab-fold/issues
[4]: https://github.com/pytest-dev/pytest
[5]: https://github.com/pytest-dev/pytest-cov
[6]: https://tox.readthedocs.org/en/latest
[7]: https://github.com/abusalimov/pytest-travis-fold
