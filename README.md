# pytest-travis-fold

[Pytest][4] plugin that folds captured output sections in Travis CI build log.

![Travis CI build log view](https://cloud.githubusercontent.com/assets/530396/10524841/52ecb102-738a-11e5-83ab-f3cf1b3316fb.png)

In addition, pytest-travis-fold recognizes presence of the [pytest-cov][5]
plugin and folds coverage reports accordingly.

## Installation and Usage

Just install the [pytest-travis-fold][1] package
as part of your build.

When using [tox][6], add the package to the `deps` list in your `tox.ini`
and make sure the `TRAVIS` environment variable is passed:

```ini
[testenv]
deps =
    pytest-travis-fold
passenv = TRAVIS
```

If you **don't** use tox and invoke `py.test` directly from `.travis.yml`,
you may install the package as an additional `install` step:

```yaml
install:
  - pip install -e .
  - pip install pytest-travis-fold

script: py.test
```

Output folding is enabled automatically when running inside Travis CI. It is OK
to have the plugin installed also in your dev environment: it is only activated
by checking the presence of the `TRAVIS` environmental variable, unless the
`--travis-fold` command line switch is used.

## The `travis` fixture

The plugin by itself only makes the captured output sections appear folded.
If you wish to make the same thing with arbitrary lines, you can do it manually
by using the `travis` fixture.

It is possible to fold the output of a certain code block using the
`travis.folding_output()` context manager:

```python
def test_something(travis):
    with travis.folding_output():
        print("Lines, lines, lines...")
        print("Lots of them!")
        ...
```

Or you may want to use lower-level `travis.fold_string()` and
`travis.fold_lines()` functions and then output the result as usual.

## Contributing

Contributions are very welcome. Tests can be run with [tox][6], please ensure
the coverage at least stays the same before you submit a pull request.

## License

Distributed under the terms of the [MIT][2] license, "pytest-travis-fold" is
free and open source software.

## Issues

If you encounter any problems, please [file an issue][3] along with a detailed
description.

[1]: https://pypi.python.org/pypi/pytest-travis-fold
[2]: http://opensource.org/licenses/MIT
[3]: https://github.com/abusalimov/pytest-travis-fold/issues
[4]: https://github.com/pytest-dev/pytest
[5]: https://github.com/pytest-dev/pytest-cov
[6]: https://tox.readthedocs.org/en/latest
