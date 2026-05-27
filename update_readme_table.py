#!/usr/bin/env python3
"""Regenerate README.md skill table from local SKILL.md files."""

from __future__ import annotations

import re
from pathlib import Path


FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
FIELD_RE = re.compile(r"^(name|description):\s*(.+?)\s*$", re.MULTILINE)


def parse_skill(skill_path: Path) -> dict[str, str] | None:
    content = skill_path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(content)
    if not match:
        return None

    fields: dict[str, str] = {}
    for key, value in FIELD_RE.findall(match.group(1)):
        fields[key] = value.strip()

    if "name" not in fields or "description" not in fields:
        return None

    fields["path"] = str(skill_path.parent.relative_to(skill_path.parent.parent))
    return fields


def example_for(name: str) -> str:
    return f"/{name}"


def discover_skills(repo_root: Path) -> list[dict[str, str]]:
    skills: list[dict[str, str]] = []
    for skill_path in sorted(repo_root.glob("*/SKILL.md")):
        if skill_path.parent.name.startswith("."):
            continue
        skill = parse_skill(skill_path)
        if skill:
            skills.append(skill)
    return sorted(skills, key=lambda item: item["name"])


def render_readme(skills: list[dict[str, str]]) -> str:
    lines = [
        "# Skills",
        "",
        "| Skill | Description | Example |",
        "| --- | --- | --- |",
    ]
    for skill in skills:
        name = skill["name"]
        description = skill["description"].replace("|", "\\|")
        example = example_for(name).replace("|", "\\|")
        lines.append(f"| `{name}` | {description} | `{example}` |")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    repo_root = Path(__file__).resolve().parent
    skills = discover_skills(repo_root)
    readme_path = repo_root / "README.md"
    readme_path.write_text(render_readme(skills), encoding="utf-8")
    print(f"Updated {readme_path} with {len(skills)} skills.")


if __name__ == "__main__":
    main()
