#!/usr/bin/env python3
"""The audit: what a project already has, read before `/wiqrug:setup` asks a single question.

    audit.py [FOLDER] [--json]

Given a folder — the current one by default — it finds the git root as the project check does,
with the project check's own code, and lists, grouped:

    agent instructions   CLAUDE.md, AGENTS.md and their local or nested forms
    Claude Code          settings, rules, skills, commands, agents and hooks under .claude/
    other AI tools       their instruction files — read for rules worth keeping, never edited
    README               the project's own description
    ignore file          .gitignore
    build and test       the files a "done" command and a test framework are proposed from

then the "done" command and the test framework it proposes from the build and test files, and
every project skill or command whose name is one of wiqrug's skills — an overlap the user
decides on. A group with nothing in it says `none found`: an empty group is a finding too.

It only reads, and it exits 0 whatever it finds — outside a git repository too, where it gives the
project check's reason in one line: it runs as a skill's `!` snippet, and Claude Code aborts a skill whose snippet exits
non-zero. The proposal is a starting point the user confirms or replaces, never
a setting by itself.
"""
from __future__ import annotations

import argparse
import configparser
import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

# Importing the project check would write a bytecode cache into the installed plugin; it only reads.
sys.dont_write_bytecode = True
from project_check import PLUGIN, Answer, git_root, installed_version  # noqa: E402

NONE_FOUND = "none found"

INSTRUCTIONS = ("CLAUDE.md", "CLAUDE.local.md", ".claude/CLAUDE.md", "AGENTS.md", "AGENT.md")
# Other tools' instruction files: (path, tool). A folder entry lists every file under it.
OTHER_TOOLS = (
    (".cursorrules", "Cursor"), (".cursor/rules", "Cursor"),
    (".github/copilot-instructions.md", "GitHub Copilot"), (".github/instructions", "GitHub Copilot"),
    (".windsurfrules", "Windsurf"), (".windsurf/rules", "Windsurf"),
    (".clinerules", "Cline"), (".roo/rules", "Roo Code"), (".roorules", "Roo Code"),
    ("GEMINI.md", "Gemini CLI"), (".gemini/styleguide.md", "Gemini"),
    (".aider.conf.yml", "Aider"), ("CONVENTIONS.md", "Aider"),
    (".continue/rules", "Continue"), (".junie/guidelines.md", "Junie"),
    (".amazonq/rules", "Amazon Q"), (".kiro/steering", "Kiro"),
)
READMES = ("README.md", "README.rst", "README.txt", "README")
IGNORES = (".gitignore",)
# Build and test files read by name; each has a reader below that proposes from it.
BUILD_FILES = ("Makefile", "justfile", "package.json", "pyproject.toml", "setup.cfg", "tox.ini",
               "pytest.ini", "noxfile.py", "Cargo.toml", "go.mod", "pom.xml", "build.gradle",
               "build.gradle.kts", "composer.json", "Gemfile", "deno.json", "CMakeLists.txt")
CI = (".github/workflows", ".gitlab-ci.yml", ".gitea/workflows", "Jenkinsfile",
      ".circleci/config.yml", "azure-pipelines.yml")
AGGREGATE_TARGETS = ("check", "verify", "ci")
NODE_SCRIPTS = ("lint", "typecheck", "test")
NODE_FRAMEWORKS = ("vitest", "jest", "mocha", "ava", "@playwright/test", "cypress", "jasmine")
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "vendor", "dist", "build", "target"}


@dataclass
class Found:
    path: str
    note: str = ""
    overlaps: str = ""


@dataclass
class Proposal:
    """What one build or test file proposes: commands for "done", frameworks for tests."""
    commands: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    aggregate: str = ""


@dataclass
class Audit:
    root: str
    installed: str
    groups: dict[str, list[Found]]
    done: str
    frameworks: list[str]
    overlaps: list[str]


def wiqrug_skills() -> set[str]:
    return {path.parent.name for path in (PLUGIN / "skills").glob("*/SKILL.md")}


def files_under(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.is_dir():
        return []
    return sorted(p for p in path.rglob("*")
                  if p.is_file() and not SKIP_DIRS.intersection(p.parts))


def lines_note(path: Path) -> str:
    try:
        count = len(path.read_text(encoding="utf-8", errors="replace").splitlines())
    except OSError as error:
        return f"unreadable: {error.strerror}"
    return f"{count} line{'s' * (count != 1)}"


def rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix() + ("/" if path.is_dir() else "")


def audit_instructions(root: Path) -> list[Found]:
    found = [Found(name, lines_note(root / name)) for name in INSTRUCTIONS
             if (root / name).is_file()]
    return found + [Found(rel(root, p), f"nested, {lines_note(p)}") for p in nested(root)]


def nested(root: Path) -> list[Path]:
    """Every CLAUDE.md below the root, not descending into dependency or build folders."""
    found = []
    for folder, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        here = Path(folder)
        if "CLAUDE.md" in files and here not in (root, root / ".claude"):
            found.append(here / "CLAUDE.md")
    return found


def audit_claude_code(root: Path, ours: set[str]) -> list[Found]:
    claude = root / ".claude"
    found = [Found(rel(root, claude / name), "settings" + hooks_note(claude / name))
             for name in ("settings.json", "settings.local.json") if (claude / name).is_file()]
    found += [Found(rel(root, p), "rule") for p in files_under(claude / "rules")]
    for skill in sorted(p.parent for p in claude.glob("skills/*/SKILL.md")):
        found.append(Found(rel(root, skill), "skill", overlap(skill.name, ours)))
    for command in sorted(claude.glob("commands/**/*.md")):
        found.append(Found(rel(root, command), "command", overlap(command.stem, ours)))
    found += [Found(rel(root, p), "agent") for p in sorted(claude.glob("agents/**/*.md"))]
    found += [Found(rel(root, p), "hook script") for p in files_under(claude / "hooks")]
    if (root / ".mcp.json").is_file():
        found.append(Found(".mcp.json", "MCP servers"))
    return found


def hooks_note(path: Path) -> str:
    try:
        settings = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ", unreadable as JSON"
    hooks = settings.get("hooks") if isinstance(settings, dict) else None
    return f", hooks on {', '.join(sorted(hooks))}" if isinstance(hooks, dict) and hooks else ""


def overlap(name: str, ours: set[str]) -> str:
    return f"/wiqrug:{name}" if name in ours else ""


def audit_other_tools(root: Path) -> list[Found]:
    return [Found(rel(root, p), f"{tool} — read, never edited")
            for name, tool in OTHER_TOOLS for p in files_under(root / name)]


def audit_named(root: Path, names: tuple[str, ...]) -> list[Found]:
    return [Found(name, lines_note(root / name)) for name in names if (root / name).is_file()]


def read_text(path: Path) -> str:
    """An absent file reads as nothing; one that is there but unreadable raises OSError — it is
    not a file that proposes nothing, and audit_build says so."""
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def from_makefile(root: Path, name: str) -> Proposal:
    targets = re.findall(r"^([A-Za-z0-9_.-]+)\s*:(?!=)", read_text(root / name), re.MULTILINE)
    tool = "make" if name == "Makefile" else "just"
    found = Proposal()
    for target in (*AGGREGATE_TARGETS, "test"):
        if target in targets:
            found.commands = [f"{tool} {target}"]
            found.aggregate = found.commands[0] if target in AGGREGATE_TARGETS else ""
            break
    return found


def node_runner(root: Path) -> str:
    for lock, runner in (("pnpm-lock.yaml", "pnpm"), ("yarn.lock", "yarn"), ("bun.lockb", "bun"),
                         ("bun.lock", "bun")):
        if (root / lock).is_file():
            return runner
    return "npm"


def from_package_json(root: Path) -> Proposal:
    try:
        package = json.loads(read_text(root / "package.json") or "{}")
    except ValueError:
        return Proposal()
    scripts = package.get("scripts") or {}
    runner = node_runner(root)
    found = Proposal()
    for name in AGGREGATE_TARGETS:
        if name in scripts:
            found.aggregate = f"{runner} run {name}"
            found.commands = [found.aggregate]
            break
    else:
        found.commands = [f"{runner} test" if name == "test" else f"{runner} run {name}"
                          for name in NODE_SCRIPTS if name in scripts]
    declared = {**(package.get("dependencies") or {}), **(package.get("devDependencies") or {})}
    test_script = str(scripts.get("test", ""))
    found.frameworks = [name for name in NODE_FRAMEWORKS
                        if name in declared or re.search(rf"\b{re.escape(name)}\b", test_script)]
    return found


def python_runner(root: Path) -> str:
    if (root / "uv.lock").is_file():
        return "uv run "
    if (root / "poetry.lock").is_file():
        return "poetry run "
    return ""


def from_python(root: Path) -> Proposal:
    pyproject = read_text(root / "pyproject.toml")
    setup_cfg = configparser.RawConfigParser()
    try:
        setup_cfg.read_string(read_text(root / "setup.cfg"))
    except configparser.Error:
        pass
    pytest = ("[tool.pytest" in pyproject or re.search(r"\bpytest\b", pyproject) is not None
              or (root / "pytest.ini").is_file() or (root / "conftest.py").is_file()
              or setup_cfg.has_section("tool:pytest") or "[pytest]" in read_text(root / "tox.ini"))
    if pytest:
        return Proposal([f"{python_runner(root)}pytest"], ["pytest"])
    if (root / "tox.ini").is_file():
        return Proposal(["tox"], [])
    if any((root / name).is_dir() for name in ("tests", "test")) and (pyproject or setup_cfg.sections()):
        return Proposal(["python -m unittest discover"], ["unittest"])
    return Proposal()


def from_other(root: Path, name: str) -> Proposal:
    simple = {"Cargo.toml": ("cargo test", "cargo test"), "go.mod": ("go test ./...", "go test"),
              "pom.xml": ("mvn verify", "maven surefire"),
              "build.gradle": ("./gradlew check", "gradle test"),
              "build.gradle.kts": ("./gradlew check", "gradle test"),
              "deno.json": ("deno test", "deno test")}
    if name in simple:
        command, framework = simple[name]
        return Proposal([command], [framework])
    if name == "composer.json" and "phpunit" in read_text(root / name):
        return Proposal(["vendor/bin/phpunit"], ["phpunit"])
    if name == "Gemfile" and "rspec" in read_text(root / name):
        return Proposal(["bundle exec rspec"], ["rspec"])
    return Proposal()


def propose(root: Path, name: str) -> Proposal:
    if name in ("Makefile", "justfile"):
        return from_makefile(root, name)
    if name == "package.json":
        return from_package_json(root)
    if name in ("pyproject.toml", "setup.cfg", "tox.ini", "pytest.ini", "noxfile.py"):
        return from_python(root)
    return from_other(root, name)


def describe(proposal: Proposal) -> str:
    parts = []
    if proposal.commands:
        parts.append("proposes " + " && ".join(proposal.commands))
    if proposal.frameworks:
        parts.append("tests with " + ", ".join(proposal.frameworks))
    return "; ".join(parts) or "proposes nothing on its own"


def audit_build(root: Path) -> tuple[list[Found], str, list[str]]:
    found: list[Found] = []
    commands: list[str] = []
    frameworks: list[str] = []
    aggregate = ""
    for name in BUILD_FILES:
        if not (root / name).is_file():
            continue
        try:
            proposal = propose(root, name)
        except OSError as error:
            found.append(Found(name, f"unreadable: {error.strerror} — nothing proposed from it"))
            continue
        found.append(Found(name, describe(proposal)))
        aggregate = aggregate or proposal.aggregate
        commands += [c for c in proposal.commands if c not in commands]
        frameworks += [f for f in proposal.frameworks if f not in frameworks]
    found += [Found(rel(root, p), "CI — the commands it runs are what the project calls done")
              for name in CI for p in files_under(root / name)]
    return found, aggregate or " && ".join(commands), frameworks


def run(root: Path) -> Audit:
    ours = wiqrug_skills()
    build, done, frameworks = audit_build(root)
    groups = {
        "Agent instructions — CLAUDE.md, AGENTS.md": audit_instructions(root),
        "Claude Code — settings, rules, skills, commands, agents, hooks":
            audit_claude_code(root, ours),
        "Other AI tools — read for rules worth keeping, never edited": audit_other_tools(root),
        "README": audit_named(root, READMES),
        "Ignore file": audit_named(root, IGNORES),
        "Build and test files": build,
    }
    overlaps = [f"{f.overlaps.removeprefix('/wiqrug:')} ({f.path})"
                for found in groups.values() for f in found if f.overlaps]
    return Audit(str(root), installed_version(), groups, done, frameworks, overlaps)


def human(found: Audit) -> str:
    lines = [f"wiqrug audit: {found.root} — wiqrug {found.installed} installed", ""]
    for title, entries in found.groups.items():
        lines.append(title)
        lines += [f"    {e.path}  {e.note}" + (f" — overlaps {e.overlaps}" if e.overlaps else "")
                  for e in entries] or [f"    {NONE_FOUND}"]
        lines.append("")
    lines.append(f"Proposed \"done\" command: {found.done or NONE_FOUND + ' — ask for it'}")
    lines.append(f"Test framework: {', '.join(found.frameworks) or NONE_FOUND + ' — ask for it'}")
    lines.append("Overlapping skills — keep, retire to the archive, or fold into the settings: "
                 + (", ".join(found.overlaps) or NONE_FOUND))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("folder", nargs="?", type=Path, default=Path.cwd(),
                        help="a folder inside the project; the current one by default")
    parser.add_argument("--json", action="store_true", help="one JSON object instead of text")
    args = parser.parse_args(argv)
    if not args.folder.is_dir():
        parser.error(f"{args.folder} is not a folder")
    root = git_root(args.folder.resolve())
    if isinstance(root, Answer):
        print(f"wiqrug audit: skipped — {root.message.removeprefix('wiqrug: ')}")
        return 0
    found = run(root)
    print(json.dumps(asdict(found), ensure_ascii=False) if args.json else human(found))
    return 0


if __name__ == "__main__":
    sys.exit(main())
