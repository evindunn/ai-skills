#!/usr/bin/env python3
"""Render a skill template with key=value arguments."""

import pathlib
import string
import sys


def parse_template_vars(arguments: list[str]) -> dict[str, str]:
    """Parse CLI key=value pairs into template variables."""
    template_vars: dict[str, str] = {}
    for argument in arguments:
        if "=" not in argument:
            raise ValueError(f"Expected key=value argument, got: {argument}")
        key, value = argument.split("=", 1)
        if not key:
            raise ValueError(f"Template variable name cannot be empty: {argument}")
        template_vars[key] = value
    return template_vars


def render_template(template_path: pathlib.Path, template_vars: dict[str, str]) -> str:
    """
    Render a template file with named placeholders.

    :param template_path: Path to the template file.
    :param template_vars: Placeholder values keyed by variable name.
    :returns: Rendered template text.
    :raises ValueError: If the template references a missing variable.
    """
    template_text = template_path.read_text(encoding="utf-8")
    formatter = string.Formatter()
    try:
        return formatter.vformat(template_text, (), template_vars)
    except KeyError as error:
        missing_key = error.args[0]
        raise ValueError(f"Missing template variable: {missing_key}") from error


def main(argv: list[str]) -> int:
    """
    Render a template to standard output.

    :param argv: Command-line arguments including the program name.
    :returns: Process exit status code.
    """
    if len(argv) < 2:
        print(
            "Usage: render_template.py TEMPLATE_FILE [key=value ...]",
            file=sys.stderr,
        )
        return 2

    template_path = pathlib.Path(argv[1])

    try:
        template_vars = parse_template_vars(argv[2:])
        rendered = render_template(template_path, template_vars)
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1

    sys.stdout.write(rendered)
    if not rendered.endswith("\n"):
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
