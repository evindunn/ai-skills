---
name: document-code
description: Improve code documentation by adding useful logical block comments, docstring-style comments for functions/classes/modules, and top-level file comments. Use when asked to document code, add comments, improve docstrings, explain entrypoints, make code easier for engineers or future AI agents to scan, or perform documentation passes across source files in any programming language.
---

# Document Code

## Overview

Use this skill to document existing code without changing behavior. The output should help both human engineers and future AI agents answer:

- What does this file do?
- Where are the main entrypoints?
- What does this subroutine own?
- What are the logical phases inside long or dense code?

## Workflow

### 1. Read Before Writing

Inspect the target files and identify:

- Public entrypoints, CLI commands, handlers, exported APIs, tasks, jobs, or main functions.
- Long or dense subroutines with multiple logical phases.
- Data flow between helpers, especially inputs, intermediate structures, and outputs.
- Existing project comment/docstring style.
- Generated, vendored, or external files that should not be edited.

Prefer structural tools when available:

- Search for definitions/classes/modules with the language's parser or fast text search.
- Sort subroutines by length/complexity to find the best targets for block comments.
- Use tests, validators, or linters already present in the repo after edits.

### 2. Add Logical Block Comments First

For longer functions or dense code, add sparse comments at phase boundaries. Comment the why/shape of the block, not each line.

Good block comments:

- Name the phase: collect inputs, normalize data, group evidence, infer rules, render output, persist artifacts.
- Explain a non-obvious heuristic or safety choice.
- Mark fallback behavior or intentionally approximate logic.
- Help a reader resume scanning after a large conditional or loop.

Avoid:

- Repeating the next line in English.
- Decorating obvious code.
- Adding comments to every branch just for coverage.
- Explaining syntax that any engineer knows.

### 3. Upgrade Subroutine Docstrings From What You Learned

After block comments clarify the structure, update docstring-style comments for functions, classes, methods, modules, commands, or equivalent language constructs.

Docstrings should usually be one concise sentence. Include more only when the API is broad, risky, or externally consumed.

Prefer docstrings that state:

- Purpose: what the routine is responsible for.
- Inputs/outputs when not obvious from the signature.
- Contract or side effect: writes files, mutates state, calls network, shells out, returns findings, yields nodes.
- Important approximation or safety boundary.

Use the project's native convention:

- Python: module/function/class docstrings.
- JavaScript/TypeScript: JSDoc/TSDoc for exported or complex functions.
- Java/Kotlin/Scala: Javadoc/KDoc/Scaladoc for public APIs and complex internals.
- Go/Rust/C/C++/Shell/YAML/etc.: idiomatic leading comments.

Avoid generic generated phrasing such as:

- `Return foo data.`
- `Check bar.`
- `Handle item.`
- `Run the requested workflow.`

Make it specific:

- `Return changed and untracked template files within the scan scope.`
- `Add findings for split-hosts partition and params.limit mismatches.`
- `Render affected templates before and after changes and return diffs.`

### 4. Write Or Improve Top-Level File Comments Last

Use the block comments and docstrings as source material. A file-level comment should be short and useful to someone opening the file cold.

For executable or script-like files, prefer:

```text
One-line purpose.

Reads: main inputs.
Checks/Finds/Does/Indexes: main work.
Writes/Returns: main outputs or artifacts.
```

For libraries, prefer:

```text
One-line purpose.

Exports: primary types/functions.
Owns: key behavior or domain boundary.
Used by: important callers, only when helpful.
```

Keep it engineer-sized. If it reads like product copy, trim it.

### 5. Validate

Before finishing:

- Run syntax/compile checks for touched languages when available.
- Run existing tests/validators when reasonable for the scope.
- Run whitespace checks such as `git diff --check` in git repos.
- Re-scan docstrings/comments for vague mechanical phrases.
- Verify comments did not change behavior.

## Quality Bar

Good documentation is:

- Accurate to the code as written.
- Specific enough to help code review.
- Brief enough to stay readable.
- Stable across small implementation changes.
- Useful to a future AI scan that needs entrypoints, data flow, and intent quickly.

Bad documentation is:

- Longer than the code it explains.
- A paraphrase of obvious statements.
- Aspirational rather than source-of-truth.
- Full of generic filler like "process data" or "handle logic."

