---
name: publish-poetry-project
description: Add or update build and publishing automation for Poetry-based Python projects. Use when an agent needs to configure GitHub Actions workflows for tagged releases, build wheels and sdists, publish artifacts to GitHub Releases, publish packages to PyPI, and document the release process in a Poetry project's repository.
---

# Publish Poetry Project

Set up release automation for Poetry projects using one build job and separate publish jobs for GitHub Releases and PyPI.

Before editing:

1. Read `pyproject.toml` to confirm the project name, build backend, console scripts, and any packaged resource includes.
2. Inspect the repository for existing GitHub Actions workflows and release documentation.
3. Check whether the package needs package-data fixes before a release workflow is useful.

When implementing the workflow:

1. Start from [templates/workflow.yml.tmpl](templates/workflow.yml.tmpl) instead of drafting the GitHub Actions workflow from scratch.
2. Render the template into a `.github/workflows/*.yml` workflow with [scripts/render_template.py](scripts/render_template.py), passing template values such as `workflow_name`, `tag_pattern`, `artifact_name`, and `pypi_environment`.
   Example: `python3 scripts/render_template.py templates/workflow.yml.tmpl workflow_name=Release 'tag_pattern=v*' artifact_name=python-package pypi_environment=pypi`

When updating project files:

1. Fix any broken `tool.poetry.include` package-data paths that would make the build incomplete.
2. Keep `pyproject.toml` aligned with the workflow assumptions.
3. Update `README.md` with a short release section that explains local build checks, tag-based publishing, and any PyPI trusted-publisher requirement.

Validation steps:

1. Re-read the rendered workflow file for trigger, container image, artifact, and permission correctness.
2. Confirm that the rendered workflow still matches the structure in [templates/workflow.yml.tmpl](templates/workflow.yml.tmpl) unless the project needed a deliberate deviation.
3. Run `poetry build` locally when possible.
4. Call out any remaining manual setup, especially PyPI trusted publisher configuration and required GitHub permissions.

Read [references/checklist.md](references/checklist.md) before substantial publishing changes.
