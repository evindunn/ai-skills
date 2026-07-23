---
name: refactor-testing
description: Find, propose, cache, and implement high-value tests in a local code repository with a target-selection checkpoint. Use when Codex is asked to refactor testing, add missing tests, improve coverage, search a repo for modules that would benefit from tests, identify the best test target, confirm or choose alternatives, cache candidates and completed refactors for about one hour, implement tests with locally available tooling, and mark completed targets after implementation.
---

# Refactor Testing

## Workflow

1. Inspect the repository shape before changing files:
   - Run `rg --files` to identify source files, tests, package manifests, lockfiles, and CI config.
   - Read existing test files and project docs to learn naming, style, fixtures, and commands.
   - Check git status and avoid reverting unrelated work.

2. Produce or reuse a deterministic test-target shortlist:
   - Prefer running `python3 scripts/rank_test_targets.py <repo-root>` from this skill.
   - Reuse the scanner cache when it is fresh; it stores candidates and completed refactors for about one hour.
   - Do not re-evaluate the repo while the cache is fresh unless the user explicitly asks for a rescan.
   - If Python is unavailable, approximate the same scoring with `rg`, manifests, and existing tests.
   - Treat the ranking as a triage aid, not a substitute for reading the highest-scoring files.

3. Choose the next unimplemented highest-value target:
   - Select the first `next` candidate from the cached scanner output.
   - If every cached candidate is completed, tell the user all cached refactors are done and ask whether to refresh the cache.
   - Favor modules that are user-facing, parsing or transforming data, branching heavily, touching I/O boundaries, or fixing behavior that could regress.
   - Prefer files without direct tests, files with nearby test patterns, and files whose behavior can be tested deterministically.
   - Avoid generated files, vendored code, build outputs, migrations, and files where meaningful tests require external services unless suitable mocks already exist.

4. Tell the user which target was chosen and pause for direction:
   - Name the chosen target and give a concise reason based on the shortlist and source inspection.
   - Include one or two strong alternatives when they are meaningfully close in value.
   - Ask whether to continue with the chosen target or use an alternative.
   - Continue only after the user confirms, chooses an alternative, or gives equivalent direction.

5. Implement focused tests using local tooling:
   - Use the test framework already present in the repo.
   - Reuse existing fixtures, helpers, factories, and command style.
   - Add only the minimum production-code changes needed to make the module testable.
   - Keep tests deterministic: freeze time, seed randomness, mock network/filesystem boundaries, and assert stable behavior.
   - Follow repository and user coding standards, including docstring and import conventions.

6. Validate:
   - Run the narrowest relevant test command first.
   - If reasonable, run the broader local test command from the project docs or manifest.
   - If a command fails because required dependencies are unavailable, report that clearly and still summarize the implemented tests.

7. Mark complete and summarize:
   - Mark the selected target complete in the cache after the tests are implemented and validation has been attempted: `python3 scripts/rank_test_targets.py <repo-root> --complete <target-path>`.
   - Name the selected target and why it was highest value.
   - List the tests added and the behavior covered.
   - Include validation commands and outcomes.
   - Mention any residual risk or follow-up targets from the shortlist.
   - Stop after the summary unless the user explicitly asks for additional changes or another target.

## Scanner

Use:

```bash
python3 /path/to/refactor-testing/scripts/rank_test_targets.py <repo-root>
python3 /path/to/refactor-testing/scripts/rank_test_targets.py <repo-root> --complete <target-path>
python3 /path/to/refactor-testing/scripts/rank_test_targets.py <repo-root> --refresh-cache
```

The scanner prints a ranked table of source files that appear to have weak or missing direct tests. The first uncompleted candidate is marked `next`. Scores are intentionally simple and deterministic so another Codex run reaches similar candidates with minimal context.

The scanner supports Python, JavaScript, TypeScript, JSX, and TSX source files. It ignores common dependency, cache, generated, and build directories.

Cache behavior:

- Cache files live under the system temp directory and are keyed by resolved repo path.
- The default cache TTL is 3,600 seconds.
- Fresh cache output must be reused to choose the next target without rescanning the repo.
- Use `--complete <target-path>` to add completed refactors to the cache.
- Use `--show-completed` when the completed list is useful for the summary.
- Use `--refresh-cache` only when the cache expired, all cached candidates are completed, or the user asks to rescan.
