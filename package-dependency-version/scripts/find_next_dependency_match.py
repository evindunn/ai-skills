#!/usr/bin/env python3
"""Find the next package release whose dependency metadata accepts a target version."""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

from packaging import markers
from packaging import requirements
from packaging import specifiers
from packaging import version


DEFAULT_INDEX_URL = "https://pypi.org/pypi"


@dataclasses.dataclass(frozen=True)
class Candidate:
    """Published release candidate and its parsed version."""

    raw: str
    parsed: version.Version


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description="Find the next package release whose Requires-Dist accepts a target dependency version."
    )
    parser.add_argument("package_requirement", help="Package requirement to search, e.g. 'fastapi~=0.141.1'.")
    parser.add_argument("dependency_requirement", help="Dependency requirement to match, e.g. 'anyio~=4.14.2'.")
    parser.add_argument(
        "--include-current",
        action="store_true",
        help="Include the lower-bound/current package version in the search.",
    )
    parser.add_argument(
        "--respect-package-spec",
        action="store_true",
        help="Only inspect releases that satisfy the full package requirement specifier.",
    )
    parser.add_argument(
        "--index-url",
        default=DEFAULT_INDEX_URL,
        help="Base PyPI-compatible JSON URL, default: https://pypi.org/pypi.",
    )
    return parser.parse_args()


def fetch_json(url: str) -> dict:
    """Fetch JSON from a URL."""

    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        raise SystemExit(f"Failed to fetch {url}: HTTP {error.code}") from error
    except urllib.error.URLError as error:
        raise SystemExit(f"Failed to fetch {url}: {error.reason}") from error


def project_url(index_url: str, project_name: str, release: str | None = None) -> str:
    """Build a PyPI JSON API URL."""

    base = index_url.rstrip("/")
    quoted_project = urllib.parse.quote(project_name)
    if release is None:
        return f"{base}/{quoted_project}/json"
    return f"{base}/{quoted_project}/{urllib.parse.quote(release)}/json"


def lower_bound(specifier_set: specifiers.SpecifierSet) -> version.Version | None:
    """Return the strongest inclusive lower-bound-like version from a specifier set."""

    bounds: list[version.Version] = []
    for item in specifier_set:
        if item.operator in {">=", "==", "~=", "==="}:
            try:
                bounds.append(version.Version(item.version.rstrip(".*")))
            except version.InvalidVersion:
                continue
    if not bounds:
        return None
    return max(bounds)


def dependency_probe_version(dependency: requirements.Requirement) -> version.Version:
    """Choose the dependency version to test against release metadata."""

    probe = lower_bound(dependency.specifier)
    if probe is None:
        raise SystemExit(
            f"Dependency requirement {dependency!s} needs an explicit lower-bound or exact version to test."
        )
    return probe


def candidate_releases(
    package: requirements.Requirement,
    releases: dict,
    include_current: bool,
    respect_package_spec: bool,
) -> list[Candidate]:
    """Return sorted stable release candidates after the package lower bound."""

    package_floor = lower_bound(package.specifier)
    candidates: list[Candidate] = []
    for raw_version, files in releases.items():
        if not files:
            continue
        try:
            parsed = version.Version(raw_version)
        except version.InvalidVersion:
            continue
        if parsed.is_prerelease:
            continue
        if respect_package_spec and parsed not in package.specifier:
            continue
        if package_floor is not None:
            if include_current:
                if parsed < package_floor:
                    continue
            elif parsed <= package_floor:
                continue
        candidates.append(Candidate(raw=raw_version, parsed=parsed))
    return sorted(candidates, key=lambda candidate: candidate.parsed)


def dependency_requirements(requires_dist: list[str] | None, dependency_name: str) -> list[requirements.Requirement]:
    """Return dependency requirements matching the requested dependency name."""

    matches: list[requirements.Requirement] = []
    for requirement_text in requires_dist or []:
        try:
            parsed = requirements.Requirement(requirement_text)
        except requirements.InvalidRequirement:
            continue
        if parsed.name.lower().replace("_", "-") == dependency_name.lower().replace("_", "-"):
            matches.append(parsed)
    return matches


def marker_applies(requirement: requirements.Requirement) -> bool:
    """Return whether a requirement marker applies to the current generic Python environment."""

    if requirement.marker is None:
        return True
    try:
        return requirement.marker.evaluate()
    except markers.InvalidMarker:
        return False


def main() -> int:
    """Run the resolver and print the first compatible release."""

    args = parse_args()
    package = requirements.Requirement(args.package_requirement)
    dependency = requirements.Requirement(args.dependency_requirement)
    target_dependency_version = dependency_probe_version(dependency)

    project_metadata = fetch_json(project_url(args.index_url, package.name))
    candidates = candidate_releases(
        package=package,
        releases=project_metadata.get("releases", {}),
        include_current=args.include_current,
        respect_package_spec=args.respect_package_spec,
    )
    if not candidates:
        print(f"No candidate releases found for {package!s}.", file=sys.stderr)
        return 1

    inspected = 0
    metadata_gaps: list[str] = []
    for candidate in candidates:
        inspected += 1
        release_metadata = fetch_json(project_url(args.index_url, package.name, candidate.raw))
        requires_dist = release_metadata.get("info", {}).get("requires_dist")
        if requires_dist is None:
            metadata_gaps.append(candidate.raw)
            continue

        matches = dependency_requirements(requires_dist, dependency.name)
        applicable_matches = [match for match in matches if marker_applies(match)]
        for match in applicable_matches:
            if target_dependency_version in match.specifier:
                print(f"match: {package.name}=={candidate.raw}")
                print(f"dependency: {match!s}")
                print(f"target_dependency_version: {dependency.name}=={target_dependency_version}")
                print(f"inspected_candidates: {inspected}")
                if metadata_gaps:
                    print(f"metadata_gaps: {', '.join(metadata_gaps)}")
                return 0

    print(f"No matching release found for {package!s} accepting {dependency!s}.")
    print(f"highest_candidate_inspected: {candidates[-1].raw}")
    print(f"inspected_candidates: {inspected}")
    if metadata_gaps:
        print(f"metadata_gaps: {', '.join(metadata_gaps)}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
