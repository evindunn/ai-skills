---
name: publish-poetry-project
description: Add or update build and publishing automation for Poetry-based Python projects. Use when Codex needs to configure GitHub Actions workflows for tagged releases, build wheels and sdists, publish artifacts to GitHub Releases, publish packages to PyPI, and document the release process in a Poetry project's repository.
---

# Publish Poetry Project

Set up release automation for Poetry projects using one build job and separate publish jobs for GitHub Releases and PyPI.

Before editing:

1. Read `pyproject.toml` to confirm the project name, build backend, console scripts, and any packaged resource includes.
2. Inspect the repository for existing GitHub Actions workflows and release documentation.
3. Check whether the package needs package-data fixes before a release workflow is useful.

When implementing the workflow:

1. Add a GitHub Actions workflow under `.github/workflows/` that triggers on version tags such as `v*`.
2. Build the distribution artifacts once with `poetry build`.
3. Upload the built artifacts so downstream jobs reuse the same wheel and sdist.
4. Publish the artifacts to a GitHub Release when the run was triggered by a tag.
5. Publish the same artifacts to PyPI, preferably with trusted publishing through GitHub OIDC.

When updating project files:

1. Fix any broken `tool.poetry.include` package-data paths that would make the build incomplete.
2. Keep `pyproject.toml` aligned with the workflow assumptions.
3. Update `README.md` with a short release section that explains local build checks, tag-based publishing, and any PyPI trusted-publisher requirement.

Validation steps:

1. Re-read the workflow file for trigger, artifact, and permission correctness.
2. Run `poetry build` locally when possible.
3. Call out any remaining manual setup, especially PyPI trusted publisher configuration and required GitHub permissions.

Read [references/checklist.md](references/checklist.md) before substantial publishing changes.
