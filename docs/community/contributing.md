# Contributing

1. Fork / branch from `main`
2. Install: `pip install -e ".[testing,linting,docs]"`
3. Run tests: `python -m pytest` or `tox`
4. Run hooks: `pre-commit run --all-files`
5. Add a towncrier news fragment under `news/` for user-visible changes
6. Open a pull request
