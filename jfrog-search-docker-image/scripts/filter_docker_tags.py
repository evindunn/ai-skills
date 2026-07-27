#!/usr/bin/env python3
"""List and filter Docker image tags from a JFrog Artifactory Docker repository."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Iterable


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="List Docker tags from Artifactory via `jf rt curl` and filter them."
    )
    parser.add_argument("--repo", required=True, help="Artifactory Docker repo, e.g. public-docker-prod.")
    parser.add_argument("--image", required=True, help="Docker image path, e.g. library/python.")
    parser.add_argument("--prefix", default="", help="Only include tags with this prefix.")
    parser.add_argument("--contains", action="append", default=[], help="Only include tags containing this text. Repeatable.")
    parser.add_argument("--suffix", default="", help="Only include tags with this suffix.")
    parser.add_argument("--limit", type=int, default=0, help="Maximum number of tags to print; 0 means no limit.")
    parser.add_argument("--registry", default="<registry-host>", help="Registry host for image strings.")
    parser.add_argument("--image-string", action="store_true", help="Print full image strings instead of tags only.")
    return parser.parse_args()


def run_jfrog_tag_list(repo: str, image: str) -> dict:
    """Return parsed tag-list JSON from Artifactory's Docker API."""
    api_path = f"/api/docker/{repo}/v2/{image}/tags/list"
    result = subprocess.run(
        ["jf", "rt", "curl", api_path],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        raise SystemExit(result.returncode)

    json_start = result.stdout.find("{")
    if json_start == -1:
        raise SystemExit("No JSON object found in jf output.")
    return json.loads(result.stdout[json_start:])


def filter_tags(tags: Iterable[str], prefix: str, contains: list[str], suffix: str) -> list[str]:
    """Filter Docker tags using prefix, contains, and suffix criteria."""
    matches = []
    for tag in tags:
        if prefix and not tag.startswith(prefix):
            continue
        if suffix and not tag.endswith(suffix):
            continue
        if any(value not in tag for value in contains):
            continue
        matches.append(tag)
    return sorted(matches, key=tag_sort_key)


def tag_sort_key(tag: str) -> tuple:
    """Sort dotted version tags naturally while keeping non-version parts stable."""
    parts: list[object] = []
    for chunk in tag.replace("-", ".").split("."):
        if chunk.isdigit():
            parts.append((0, int(chunk)))
        else:
            parts.append((1, chunk))
    return tuple(parts)


def main() -> int:
    """Run the Docker tag search."""
    args = parse_args()
    payload = run_jfrog_tag_list(args.repo, args.image)
    tags = filter_tags(payload.get("tags", []), args.prefix, args.contains, args.suffix)
    if args.limit:
        tags = tags[: args.limit]

    for tag in tags:
        if args.image_string:
            print(f"{args.registry}/{args.repo}/{args.image}:{tag}")
        else:
            print(tag)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
