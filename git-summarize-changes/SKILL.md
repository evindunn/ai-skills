---
name: git-summarize-changes
description: Summarize current-branch changes vs an auto-discovered base branch for MR-style output. Use when the user asks to summarize git changes, draft an MR description, or compare against main/release.
---

# Git Summarize Changes

Produce a concise summary from `<base_branch>..HEAD` as the source of truth.

## Base branch

1. User-specified base branch, if given.
2. Else default remote branch:

```bash
BASE_BRANCH="$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|^origin/||')"
```

3. If empty, ask the user for a base branch.

## Workflow

1. Run from repo root; validate branch and range from git (do not trust stale chat).
2. Reuse chat context only if it matches current `<base_branch>..HEAD`.
3. Draft markdown; copy to clipboard when possible; paste the same in chat.

## Validate

```bash
git rev-parse --verify "$BASE_BRANCH" >/dev/null
git rev-parse --abbrev-ref HEAD
git log --oneline "$BASE_BRANCH"..HEAD
git diff --stat "$BASE_BRANCH"...HEAD
```

Empty range: say so; do not invent a summary.

## Output template

```markdown
## Summary
- <2-5 bullets on intent and impact>
```

## Clipboard (macOS)

```bash
cat <<'EOF' | pbcopy
## Summary
- <final bullets>
EOF
```

If `pbcopy` fails, retry with needed permissions and still paste the markdown in chat.
