# Checklist

Use this checklist when adding release automation to a Poetry project.

## Repository review

1. Read `pyproject.toml`.
2. Read existing files under `.github/workflows/`.
3. Read `README.md` for current release or installation guidance.
4. Check whether package-data includes, script targets, or version metadata need cleanup first.

## Workflow design

1. Trigger on pushed version tags such as `v*`.
2. Add `workflow_dispatch` when manual runs are useful.
3. Build once with `poetry build`.
4. Upload the `dist/` artifacts and reuse them in publish jobs.
5. Use GitHub Release upload for repository artifacts.
6. Use `pypa/gh-action-pypi-publish` for PyPI publishing.
7. Prefer `id-token: write` and PyPI trusted publishing over API tokens when possible.

## Permissions and environments

1. Give the GitHub release job `contents: write`.
2. Give the PyPI job `id-token: write`.
3. Use a `pypi` environment if the repository wants environment protection rules.

## Documentation

1. Explain the tag pattern that triggers publishing.
2. Show a sample tag such as `v0.1.0`.
3. Mention `poetry build` as a local sanity check.
4. Mention any required PyPI trusted publisher setup.

## Validation

1. Run `poetry build` when the environment allows it.
2. Check that the built artifacts include required package resources.
3. Confirm that the workflow reuses uploaded artifacts instead of rebuilding in each publish job.
