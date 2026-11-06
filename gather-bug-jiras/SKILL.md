---
name: gather-bug-jiras
description: Gather the current user's Open or In Progress Bugs from a configured Jira project and create an assigned tracking task with contains links. Uses available Jira skills and tools for access and a deterministic script for planning and verification.
---

# Gather bug Jiras

Choose the Jira skills and tools available in the current environment. Read the chosen skill's instructions and use its supported identity, search, metadata, create, update, and readback operations. No particular CLI, connector, employer, or credential mechanism is required. If no authenticated Jira access is available, explain what connection is missing; do not assume a work-specific tool exists or install one without authorization.

Use `scripts/gather_bug_jiras.py` for query generation, scope validation, duplicate checks, missing-link planning, and final verification. It is an offline Python 3.10+ script with no external dependencies, network calls, credentials, subprocesses, or remote mutations. Execute its operation plans through your chosen Jira tools; do not rewrite its logic ad hoc.

Scope: the current user's Bug issues with status exactly Open or In Progress. Target type is Task; default title is `Fix container CVEs` (override with `--summary` on every invocation). This includes every matching bug, even secret-rotation bugs; the title does not impose a CVE-only filter. Never include Closed, Outdated, or Verification Done. Changing statuses or content filters requires an explicit request and a script change.

## Local configuration

Copy `.env.example` to `.env` beside this file and configure `SOURCE_BUG_PROJECT_ID`, `TARGET_PROJECT_ID`, and `JIRA_BASE_URL`. Project identifiers are Jira project keys, not numeric IDs. The HTTPS Jira origin must match the selected tools' site; it controls displayed links, not authentication or routing. The script always reads its own skill folder's `.env`, independent of the working directory.

Supported syntax: literal `NAME=value` lines, optional matching quotes, blank lines, and full-line `#` comments. No variable expansion, shell execution, inline comments, or process-environment fallback. Missing or invalid configuration stops execution.

Keep internal identifiers, hostnames, identities, ticket exports, and plans out of published files. `.gitignore` excludes `.env` variants except `.env.example`, `work/`, JSONL journals, and Python caches. Use private files under `<skill-dir>/work/` or outside the publishing repository, preferably mode 0600. Git ignore does not untrack existing files; inspect staged changes before publishing. Do not publish automatically.

## Workflow

1. Run the script without inputs to obtain exact JQL and required fields:

   ```bash
   python3 <skill-dir>/scripts/gather_bug_jiras.py
   ```

2. Using your selected Jira skills/tools, resolve the authenticated current user's active account, execute both queries across **all pages**, confirm the target project supports Task, and discover the live link type with a direction labeled exactly `contains`. Never guess identities or link metadata. Stop if the site lacks the requested relationship.

3. Export results into the JSON shapes below, unwrapping tool-specific envelopes and preserving actual field values. Merge all search pages into one list; set `isLast: true` and omit `nextPageToken` only after consuming every page. The script rejects partial/duplicate exports. Never include credentials.

   - `identity.json`: `{"accountId":"<resolved-account-id>","active":true}`.
   - `bugs.json`: `{"isLast":true,"issues":[{"key":"BUGS-1","fields":{"issuetype":{"name":"Bug"},"status":{"name":"Open"},"assignee":{"accountId":"<resolved-account-id>"}}}]}`.
   - `existing.json`: the same search envelope for the duplicate query, retaining each issue's `summary`, `status.statusCategory.key`, and `assignee.accountId`. Keep all candidates, including nonexact titles and done issues. Empty searches use `{"isLast":true,"issues":[]}`.
   - `link-type.json`: the live link-type object with `name`, `inward`, and `outward`. Exactly one direction must be `contains`.
   - `target.json`, for linking/resuming/verifying: the fetched issue object with `key` and `fields` containing `summary`, `issuetype`, `assignee`, `status.statusCategory`, `issuelinks`, and `description`. Preserve actual link sides, type metadata, and the full ADF description.

4. Generate a plan from complete exports:

   ```bash
   python3 <skill-dir>/scripts/gather_bug_jiras.py \
     --identity <private-dir>/identity.json --bugs <private-dir>/bugs.json \
     --existing <private-dir>/existing.json --link-type <private-dir>/link-type.json
   ```

   No bugs means no creation. An active exact-title match stops creation: inspect and fetch the intended task, then use `--target <private-dir>/target.json` to resume. Resolve multiple active matches first. Unexpected links, an incorrect assignee, or an incorrect title/type stop planning without deletions or reassignment.

5. When creation is authorized, record the creation intent in a private run journal, then execute the emitted create operation through your selected Jira tools. Print and record the returned key immediately. Fetch the new target, refresh duplicate results, and regenerate the plan with `--target` to obtain only missing links and the description update. Map the emitted Jira fields/update payloads to the tools' supported arguments, preserving the assignee, ADF description, link name, and direction. Execute each mutation once and record completed operations.

6. Fetch the target again and rerun the same command with `--target <private-dir>/target.json --verify`. Only `mode: verified` confirms the fetched target matches the expected exact links, description, assignee, and active Task identity. This verifies the collected snapshot; re-query bugs and duplicates when resuming later.

On interruption or ambiguous failure, inspect the journal and live Jira state before continuing. Never blindly retry creation or replay a link write. Recover any created key through your selected Jira tools, refresh exports, and regenerate the missing-operation plan. The script stores no recovery state and performs no remote actions.

Report the verified URL, count, and status breakdown. On partial failure report the known key and completed phase without claiming completion. Distinguish fixture tests from live Jira verification.
