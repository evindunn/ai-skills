#!/usr/bin/env python3
"""Offline Jira query generation, operation planning, and snapshot verification.

The agent selects authenticated Jira tools and supplies complete JSON exports.
This script never connects to Jira, executes subprocesses, or performs writes.
CLI options, config, and exports are untrusted. Keep plans containing account
and issue identifiers in private ignored storage, outside published artifacts.
"""

import argparse
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

STATUSES = ("Open", "In Progress")
MAX_BYTES = 20_000_000
KEY = re.compile(r"[A-Z][A-Z0-9_]*-[1-9][0-9]*\Z")
PROJECT = re.compile(r"[A-Z][A-Z0-9_]{0,31}\Z")
ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class GatherError(Exception):
    """Represent a safe validation failure."""


def require(condition: bool, message: str) -> None:
    """Reject invalid data without printing raw config or identity fields."""
    if not condition:
        raise GatherError(message)


def text_value(value: object) -> bool:
    """Check a bounded nonempty printable metadata string."""
    return isinstance(value, str) and 0 < len(value) <= 256 and all(ord(c) >= 32 for c in value)


def load_config(path: Path) -> dict[str, str]:
    """Read bounded literal .env settings without execution or expansion."""
    allowed = {"SOURCE_BUG_PROJECT_ID", "TARGET_PROJECT_ID", "JIRA_BASE_URL"}
    require(not path.is_symlink(), "The .env file must not be a symlink.")
    try:
        with path.open("r", encoding="utf-8") as stream:
            text = stream.read(4097)
    except (OSError, UnicodeError) as exc:
        raise GatherError("Create the skill's .env from .env.example and configure it first.") from exc
    require(len(text) <= 4096, ".env exceeds the size limit.")
    settings = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, separator, value = line.partition("=")
        name, value = name.strip(), value.strip()
        require(separator == "=" and name in allowed and name not in settings, "Invalid, unknown, or duplicate .env setting.")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        require(bool(value) and all(ord(c) >= 32 for c in value), "Empty or invalid .env value.")
        settings[name] = value
    require(set(settings) == allowed, ".env must define SOURCE_BUG_PROJECT_ID, TARGET_PROJECT_ID, and JIRA_BASE_URL.")
    require(all(PROJECT.fullmatch(settings[name]) for name in ("SOURCE_BUG_PROJECT_ID", "TARGET_PROJECT_ID")), "Project identifiers in .env must be Jira project keys.")
    url = urlsplit(settings["JIRA_BASE_URL"])
    require(url.scheme == "https" and bool(url.hostname) and re.fullmatch(r"[a-zA-Z0-9.-]+", url.netloc) is not None and url.path in ("", "/") and not url.query and not url.fragment, "JIRA_BASE_URL must be an HTTPS origin without credentials, port, query, or path.")
    settings["JIRA_BASE_URL"] = settings["JIRA_BASE_URL"].rstrip("/")
    return settings


def read_json(path: Path) -> dict:
    """Load one bounded JSON object from a regular local file."""
    require(not path.is_symlink() and path.is_file(), "Input must be a regular file, not a symlink.")
    with path.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    require(len(raw) <= MAX_BYTES, "JSON input exceeds the size limit.")
    value = json.loads(raw)
    require(isinstance(value, dict), "Input must be a JSON object.")
    return value


def issue_list(data: dict, project: str) -> list[dict]:
    """Validate a fully paginated issue export and sort unique keys numerically."""
    require(data.get("isLast") is True and not data.get("nextPageToken"), "Export must contain all pages with isLast=true and no nextPageToken.")
    issues = data.get("issues")
    require(isinstance(issues, list) and len(issues) <= 10000, "Invalid or oversized issue list.")
    seen = set()
    for issue in issues:
        require(isinstance(issue, dict), "Invalid issue record.")
        key = issue.get("key", "")
        require(isinstance(key, str) and KEY.fullmatch(key) is not None and key.startswith(project + "-") and key not in seen, "Invalid, unexpected, or duplicate issue key.")
        require(isinstance(issue.get("fields"), dict), "Missing issue fields.")
        seen.add(key)
    return sorted(issues, key=lambda item: int(item["key"].rsplit("-", 1)[1]))


def link_direction(link_type: dict) -> str:
    """Resolve which Jira link side gives the tracker the contains label."""
    require(text_value(link_type.get("name")), "Link type requires a valid name.")
    inward, outward = link_type.get("inward"), link_type.get("outward")
    require(text_value(inward) and text_value(outward) and ((inward == "contains") != (outward == "contains")), "Select a live link type with exactly one contains direction.")
    return "inwardIssue" if inward == "contains" else "outwardIssue"


def target_links(target: dict, config: dict, summary: str, account: str, link_type: dict) -> set[str]:
    """Validate an active assigned task and return its exact contains set."""
    key, fields = target.get("key", ""), target.get("fields", {})
    require(isinstance(key, str) and KEY.fullmatch(key) is not None and key.startswith(config["TARGET_PROJECT_ID"] + "-"), "Target project/key mismatch.")
    require(fields.get("summary") == summary and fields.get("issuetype", {}).get("name") == "Task", "Target title/type mismatch.")
    require(fields.get("assignee", {}).get("accountId") == account, "Target assignee mismatch.")
    require(fields.get("status", {}).get("statusCategory", {}).get("key") in ("new", "indeterminate"), "Target is not active.")
    links = fields.get("issuelinks")
    require(isinstance(links, list) and len(links) <= 10000, "Invalid target links.")
    direction, keys = link_direction(link_type), set()
    for link in links:
        require(isinstance(link, dict) and all(link.get("type", {}).get(field) == link_type[field] for field in ("name", "inward", "outward")), "Target has unrelated links; inspect before resuming.")
        linked_key = link.get(direction, {}).get("key", "")
        require(isinstance(linked_key, str) and KEY.fullmatch(linked_key) is not None and linked_key not in keys, "Invalid link direction or duplicate link.")
        keys.add(linked_key)
    return keys


def queries(config: dict, summary: str) -> dict:
    """Generate fixed-scope JQL for the agent's selected Jira integration."""
    return {
        "bugs_jql": f'project = {config["SOURCE_BUG_PROJECT_ID"]} AND assignee = currentUser() AND issuetype = Bug AND status in ("Open", "In Progress") ORDER BY key ASC',
        "existing_jql": f'project = {config["TARGET_PROJECT_ID"]} AND assignee = currentUser() AND summary ~ {json.dumps(summary)} ORDER BY key ASC',
        "bug_fields": ["status", "assignee", "issuetype"],
        "existing_fields": ["summary", "status", "assignee", "issuetype"],
        "target_fields": ["summary", "status", "assignee", "issuetype", "issuelinks", "description"],
    }


def plan(config: dict, summary: str, identity: dict, bugs: dict, existing: dict, link_type: dict, target: dict | None = None, verify: bool = False) -> dict:
    """Validate complete exports and produce portable Jira operation payloads."""
    account = identity.get("accountId")
    require(text_value(account) and identity.get("active") is True, "Resolve one active current-user identity first.")
    issues = issue_list(bugs, config["SOURCE_BUG_PROJECT_ID"])
    for issue in issues:
        fields = issue["fields"]
        require(fields.get("issuetype", {}).get("name") == "Bug" and fields.get("status", {}).get("name") in STATUSES, "Bug export includes excluded types/statuses.")
        require(fields.get("assignee", {}).get("accountId") == account, "Bug export includes another assignee.")
    active = []
    for candidate in issue_list(existing, config["TARGET_PROJECT_ID"]):
        fields = candidate["fields"]
        require(fields.get("assignee", {}).get("accountId") == account and isinstance(fields.get("summary"), str) and fields.get("status", {}).get("statusCategory", {}).get("key") in ("new", "indeterminate", "done"), "Invalid duplicate-check export.")
        if fields["summary"] == summary and fields["status"]["statusCategory"]["key"] != "done":
            active.append(candidate["key"])
    direction = link_direction(link_type)
    expected = {issue["key"] for issue in issues}
    result = {"mode": "plan", "count": len(issues), "statuses": {status: sum(i["fields"]["status"]["name"] == status for i in issues) for status in STATUSES}, "keys": sorted(expected), "operations": []}
    if not issues and target is None:
        require(not verify, "Verification requires a fetched target.")
        return result
    require(not active or (target is not None and active == [target.get("key")]), "Active matching task exists; fetch the intended target before planning a resume.")
    text = f'Track the {len(issues)} Bug tickets assigned to the tracking task assignee with status Open or In Progress. Each source ticket is linked with contains.'
    description = {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": text}]}]}
    if target is None:
        require(not verify, "Verification requires a fetched target.")
        result["operations"] = [{"operation": "create", "fields": {"project": {"key": config["TARGET_PROJECT_ID"]}, "issuetype": {"name": "Task"}, "summary": summary, "assignee": {"accountId": account}, "description": description}}]
        result["next"] = "Record the returned key, fetch the new target, and rerun with --target before linking."
        return result
    current = target_links(target, config, summary, account, link_type)
    require(current <= expected, "Target has links outside scope; authorize removals separately.")
    result.update(key=target["key"], url=config["JIRA_BASE_URL"] + "/browse/" + target["key"])
    if verify:
        require(current == expected and target["fields"].get("description") == description, "Final links or description do not match the plan.")
        result["mode"] = "verified"
        return result
    for key in sorted(expected - current):
        result["operations"].append({"operation": "update", "key": target["key"], "update": {"issuelinks": [{"add": {"type": {"name": link_type["name"]}, direction: {"key": key}}}]}})
    if target["fields"].get("description") != description:
        result["operations"].append({"operation": "update", "key": target["key"], "fields": {"description": description}})
    return result


def main() -> int:
    """Print discovery queries, an operation plan, or a verification result."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", default="Fix container CVEs")
    for name in ("identity", "bugs", "existing", "link-type", "target"):
        parser.add_argument("--" + name, type=Path)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    try:
        require(text_value(args.summary) and len(args.summary) <= 200, "Title must contain 1-200 printable characters.")
        config = load_config(ENV_FILE)
        inputs = (args.identity, args.bugs, args.existing, args.link_type)
        if not any(inputs) and args.target is None and not args.verify:
            result = queries(config, args.summary)
        else:
            require(all(inputs), "Planning requires --identity, --bugs, --existing, and --link-type JSON files.")
            result = plan(config, args.summary, *(read_json(path) for path in inputs), target=read_json(args.target) if args.target else None, verify=args.verify)
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0
    except (GatherError, OSError, ValueError, KeyError, TypeError, AttributeError, RecursionError) as exc:
        message = str(exc) if isinstance(exc, GatherError) else "Invalid configuration or JSON input."
        print(f"Stopped: {message}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
