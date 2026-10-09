#!/usr/bin/env python3
"""Print a skill's body — its SKILL.md without the frontmatter — so another skill can paste it.

    python3 paste.py <path to SKILL.md>

`grill-me` pastes `interview` with this, by the absolute path Claude Code substitutes for
${CLAUDE_PLUGIN_ROOT}, so it works whatever folder the session stands in and on any system with
Python: a snippet that is shell syntax would not run in PowerShell. Exits 1 naming a file it
cannot read.
"""
from __future__ import annotations

import sys
from pathlib import Path


def body(text: str) -> str:
    """The text after a leading `---` block; the whole text when there is none."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return text
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return "\n".join(lines[i + 1:]).lstrip("\n")
    return text


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: paste.py <path to SKILL.md>", file=sys.stderr)
        return 2
    path = Path(argv[0])
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        print(f"paste.py: cannot read {path}: {error}")
        return 1
    print(body(text))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
