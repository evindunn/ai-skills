#!/usr/bin/env python3
"""Rank source modules that are likely to benefit from tests."""

from __future__ import annotations

import argparse
import ast
import dataclasses
import hashlib
import json
import pathlib
import re
import sys
import tempfile
import time


CACHE_DIR = pathlib.Path(tempfile.gettempdir()) / "codex-refactor-testing-cache"
CACHE_TTL_SECONDS = 3_600
IGNORED_DIRS = (
    ".cache",
    ".git",
    ".mypy_cache",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "htmlcov",
    "node_modules",
    "vendor",
)
SOURCE_SUFFIXES = (".py", ".js", ".jsx", ".ts", ".tsx")
TEST_MARKERS = (".test.", ".spec.", "_test.", "test_", "_spec.")


@dataclasses.dataclass(frozen=True)
class Candidate:
    """
    Represent a ranked source-file test candidate.

    :param score: Deterministic value score for the source file.
    :param path: Repository-relative source path.
    :param reason: Comma-separated score reasons.
    """

    score: int
    path: pathlib.Path
    reason: str


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", type=pathlib.Path, help="Repository root to scan")
    parser.add_argument(
        "--cache-ttl",
        type=int,
        default=CACHE_TTL_SECONDS,
        help="Seconds to reuse cached candidates before rescanning",
    )
    parser.add_argument(
        "--complete",
        action="append",
        default=[],
        help="Repository-relative path to mark completed in the cache",
    )
    parser.add_argument("--limit", type=int, default=15, help="Maximum rows to print")
    parser.add_argument(
        "--refresh-cache",
        action="store_true",
        help="Ignore any fresh cache and rescan the repository",
    )
    parser.add_argument(
        "--show-completed",
        action="store_true",
        help="Include completed candidates in the printed table",
    )
    return parser.parse_args()


def is_ignored(path: pathlib.Path) -> bool:
    """Return whether a path should be skipped."""
    return any(part in IGNORED_DIRS for part in path.parts)


def is_test_path(path: pathlib.Path) -> bool:
    """Return whether a path looks like a test file."""
    normalized = path.as_posix().lower()
    return (
        "/test/" in normalized
        or "/tests/" in normalized
        or any(marker in path.name.lower() for marker in TEST_MARKERS)
    )


def iter_source_files(repo: pathlib.Path) -> list[pathlib.Path]:
    """Return source files in deterministic order."""
    return sorted(
        path
        for path in repo.rglob("*")
        if path.is_file()
        and path.suffix in SOURCE_SUFFIXES
        and not is_ignored(path.relative_to(repo))
        and not is_test_path(path.relative_to(repo))
    )


def existing_test_stems(repo: pathlib.Path) -> set[str]:
    """Return normalized test-related stems present in the repo."""
    stems: set[str] = set()
    for path in sorted(repo.rglob("*")):
        if not path.is_file() or path.suffix not in SOURCE_SUFFIXES:
            continue
        rel_path = path.relative_to(repo)
        if is_ignored(rel_path) or not is_test_path(rel_path):
            continue
        name = path.name.lower()
        for token in ("test_", "_test", ".test", ".spec", "_spec"):
            name = name.replace(token, "")
        stems.add(pathlib.Path(name).stem)
    return stems


def python_complexity(text: str) -> tuple[int, int]:
    """Return function/class and branch counts for Python source."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return 0, 0
    definitions = sum(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) for node in ast.walk(tree))
    branch_types = (
        ast.BoolOp,
        ast.ExceptHandler,
        ast.For,
        ast.If,
        ast.IfExp,
        ast.Try,
        ast.While,
        ast.With,
    )
    match_type = getattr(ast, "Match", None)
    if match_type is not None:
        branch_types = branch_types + (match_type,)
    branches = sum(isinstance(node, branch_types) for node in ast.walk(tree))
    return definitions, branches


def text_complexity(text: str) -> tuple[int, int]:
    """Return approximate function/class and branch counts for JS-like source."""
    definitions = len(re.findall(r"\b(function|class)\b|=>", text))
    branches = len(re.findall(r"\b(if|for|while|switch|catch|case)\b|\?[^.:]", text))
    return definitions, branches


def score_file(repo: pathlib.Path, path: pathlib.Path, test_stems: set[str]) -> Candidate | None:
    """Score a source file as a potential test target."""
    rel_path = path.relative_to(repo)
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None

    definitions, branches = python_complexity(text) if path.suffix == ".py" else text_complexity(text)
    lines = len(text.splitlines())
    if lines < 20 and definitions + branches < 2:
        return None

    stem = path.stem.lower()
    has_direct_test = stem in test_stems
    score = 0
    reasons: list[str] = []

    if not has_direct_test:
        score += 35
        reasons.append("no direct test")
    if branches:
        score += min(branches * 4, 28)
        reasons.append(f"{branches} branches")
    if definitions:
        score += min(definitions * 3, 21)
        reasons.append(f"{definitions} definitions")
    if re.search(r"\b(parse|serialize|validate|transform|load|save|request|response|command|config)\b", text, re.I):
        score += 12
        reasons.append("boundary logic")
    if 80 <= lines <= 500:
        score += 10
        reasons.append(f"{lines} lines")
    elif lines > 500:
        score += 5
        reasons.append(f"{lines} lines")

    return Candidate(score=score, path=rel_path, reason=", ".join(reasons))


def build_candidates(repo: pathlib.Path) -> list[Candidate]:
    """Return deterministically ranked test-target candidates."""
    test_stems = existing_test_stems(repo)
    candidates = [
        candidate
        for source_file in iter_source_files(repo)
        if (candidate := score_file(repo, source_file, test_stems)) is not None
    ]
    candidates.sort(key=lambda candidate: (-candidate.score, candidate.path.as_posix()))
    return candidates


def cache_path(repo: pathlib.Path) -> pathlib.Path:
    """Return the cache file path for a repository."""
    repo_key = hashlib.sha256(repo.as_posix().encode("utf-8")).hexdigest()[:16]
    return CACHE_DIR / f"{repo_key}.json"


def candidate_to_mapping(candidate: Candidate) -> dict[str, object]:
    """Return a JSON-serializable candidate mapping."""
    return {
        "score": candidate.score,
        "path": candidate.path.as_posix(),
        "reason": candidate.reason,
    }


def candidate_from_mapping(mapping: dict[str, object]) -> Candidate:
    """Return a candidate loaded from a cache mapping."""
    return Candidate(
        score=int(mapping["score"]),
        path=pathlib.Path(str(mapping["path"])),
        reason=str(mapping["reason"]),
    )


def load_cache(repo: pathlib.Path, cache_ttl: int) -> dict[str, object] | None:
    """Return a fresh cache mapping when one exists."""
    path = cache_path(repo)
    try:
        cache = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None

    created_at = float(cache.get("created_at", 0))
    if cache.get("repo") != repo.as_posix() or time.time() - created_at > cache_ttl:
        return None
    return cache


def save_cache(
    repo: pathlib.Path,
    candidates: list[Candidate],
    completed: list[str],
    created_at: float | None = None,
) -> dict[str, object]:
    """Write and return the cache mapping for a repository."""
    cache = {
        "completed": sorted(set(completed)),
        "created_at": time.time() if created_at is None else created_at,
        "candidates": [candidate_to_mapping(candidate) for candidate in candidates],
        "repo": repo.as_posix(),
    }
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path(repo).write_text(json.dumps(cache, indent=2, sort_keys=True), encoding="utf-8")
    return cache


def update_cache(
    repo: pathlib.Path,
    cache_ttl: int,
    completed_paths: list[str],
    refresh_cache: bool,
) -> tuple[dict[str, object], bool]:
    """Return a cache mapping and whether it came from an existing cache."""
    cache = None if refresh_cache else load_cache(repo, cache_ttl)
    used_existing_cache = cache is not None
    if cache is None:
        cache = save_cache(repo, build_candidates(repo), [])

    completed = set(str(pathlib.Path(path).as_posix()) for path in cache.get("completed", []))
    completed.update(str(pathlib.Path(path).as_posix()) for path in completed_paths)
    if completed != set(cache.get("completed", [])):
        candidates = [candidate_from_mapping(mapping) for mapping in cache["candidates"]]
        cache = save_cache(repo, candidates, sorted(completed), float(cache["created_at"]))
    return cache, used_existing_cache


def print_candidates(cache: dict[str, object], limit: int, show_completed: bool, used_existing_cache: bool) -> None:
    """Print cached candidates with next/completed status."""
    completed = set(str(path) for path in cache.get("completed", []))
    candidates = [candidate_from_mapping(mapping) for mapping in cache["candidates"]]
    visible_candidates = [
        candidate for candidate in candidates if show_completed or candidate.path.as_posix() not in completed
    ]
    pending_candidates = [candidate for candidate in candidates if candidate.path.as_posix() not in completed]
    next_path = pending_candidates[0].path.as_posix() if pending_candidates else ""

    cache_status = "reused" if used_existing_cache else "refreshed"
    print(f"cache\t{cache_status}\tcreated_at={int(float(cache['created_at']))}")
    print("status\tscore\tpath\treason")
    for candidate in visible_candidates[:limit]:
        candidate_path = candidate.path.as_posix()
        if candidate_path in completed:
            status = "completed"
        elif candidate_path == next_path:
            status = "next"
        else:
            status = "pending"
        print(f"{status}\t{candidate.score}\t{candidate_path}\t{candidate.reason}")


def main() -> int:
    """Run the scanner and print ranked candidates."""
    args = parse_args()
    repo = args.repo.resolve()
    if not repo.is_dir():
        print(f"error: {repo} is not a directory", file=sys.stderr)
        return 2

    cache, used_existing_cache = update_cache(repo, args.cache_ttl, args.complete, args.refresh_cache)
    print_candidates(cache, args.limit, args.show_completed, used_existing_cache)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
