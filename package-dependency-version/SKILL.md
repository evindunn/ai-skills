---
name: package-dependency-version
description: Find the next package version whose published dependency metadata satisfies a requested dependency version/specifier, such as locating the next fastapi~=0.141.1 release that allows anyio~=4.14.2.
metadata:
  short-description: Resolve package dependency compatibility by version
---

# Package Dependency Version

Use this skill when the user gives a package version specifier and asks for the next package release whose dependency metadata matches a dependency version or specifier.

Prefer the helper script for Python packages published on PyPI:

```shell
python ~/.codex/skills/package-dependency-version/scripts/find_next_dependency_match.py 'fastapi~=0.141.1' 'anyio~=4.14.2'
```

The first argument is the package requirement to start from. The second argument is the dependency requirement to match. By default, the script treats the package requirement's lower bound as the current/start version and searches later releases, even if the package specifier itself has an upper bound. This matches requests like "starting at `fastapi~=0.141.1`, find the next FastAPI release that allows `anyio~=4.14.2`."

The script treats the lower bound implied by the dependency requirement as the version that must be accepted by the package release's `Requires-Dist` constraint. For example, `anyio~=4.14.2` is tested as version `4.14.2` against each candidate FastAPI release's `anyio` requirement.

## Workflow

- If the package index or ecosystem is unclear, ask one concise question before acting.
- For PyPI packages, run the helper script rather than manually browsing release pages.
- Report the first matching package version, the dependency constraint found in its metadata, and any skipped versions with missing metadata when that affects confidence.
- If no version matches, say that directly and include the highest candidate inspected.
- Use live package metadata when answering; dependency constraints change across releases and should not be answered from memory.
- If the requested dependency is transitive rather than directly declared by the package, report the transitive path and ask before making project file changes that add the dependency explicitly or otherwise force that transitive version.
- Do not add a new direct dependency, narrow an unrelated dependency constraint, or update a lockfile to force the requested dependency version unless the user explicitly confirms that is the desired change.

## Notes

- The script requires the `packaging` Python package and network access to PyPI.
- Use `--include-current` when the user wants to know whether the currently pinned/lower-bound release already matches.
- Use `--respect-package-spec` only when the user explicitly wants candidates constrained to the original package requirement.
- Use `--index-url` only when the user specifies a non-default PyPI-compatible JSON endpoint.
