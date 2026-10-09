#!/usr/bin/env python3
"""Bring a project set up by an older wiqrug to the installed one: settings and structure only.

    upgrade.py [FOLDER] --plan  [--set SECTION.KEY=VALUE …] [--installed VERSION] [--notes FILE]
    upgrade.py [FOLDER] --apply [--set SECTION.KEY=VALUE …] [--installed VERSION] [--notes FILE]

`/wiqrug:setup --upgrade` runs it twice: `--plan` first, shown to the user, and `--apply` only
after their yes, with the same `--set` values. Both compute one plan from the same three inputs —
the project's settings file, the release notes (`UPGRADING.md` beside the plugin's manifest folder)
and the installed version — so `--apply` writes exactly what `--plan` showed.

The plan quotes every release section after the project's version up to the installed one, then
lists its changes, one line each:

    version   wiqrug.version — the old version, then the installed one
    rename    a setting a release renamed, keeping its value
    add       a setting a release added, with the value it gives every project
    remove    a setting a release removed
    folder    a folder a `documents` setting names that does not exist yet — created empty
    needs     a setting with no value anyone chose: `--set` gives it, or `--apply` refuses

A setting is never given a default the release did not write down: a blank is not a `none`. A
file a `documents` setting names is never created, and nothing under any document folder is read
or written — an upgrade changes the settings file and makes folders, nothing else.

    exit  meaning
    0     the plan was printed, or applied and the project check now answers set up / in progress
    1     no plan can be made or applied — the message says why, and nothing was written
    2     the command line itself is wrong

`--plan` writes nothing at all. `--apply` edits the settings file line by line, so every comment
and every paragraph around its `ini wiqrug` blocks stays as it was.
"""
from __future__ import annotations

import argparse
import configparser
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# Importing the neighbour would leave a __pycache__ in the plugin, holding this machine's paths.
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import project_check as check  # noqa: E402  — the one reader of the settings file, beside this one

NOTES = check.PLUGIN / "UPGRADING.md"
RELEASE = re.compile(r"^## (\d+(?:\.\d+)*)\s*$", re.MULTILINE)
CHANGES = re.compile(r"^```ini wiqrug-upgrade\s*\n(.*?)^```\s*$\n?", re.MULTILINE | re.DOTALL)
OPEN = re.compile(r"^```ini wiqrug\s*$")
SECTION = re.compile(r"^\[([^\]]+)\]\s*$")
KEY = re.compile(r"^([A-Za-z0-9_.-]+)\s*=")
#: The `documents` settings that name a folder; the rest name a file, which is a document.
FOLDERS = ("queue", "specs", "decisions", "research", "archive", "ledger", "units")


class Unplannable(Exception):
    """No plan can be made or applied; the message names why."""


@dataclass(frozen=True)
class Release:
    version: str
    note: str
    renamed: tuple[tuple[str, str], ...]
    added: tuple[tuple[str, str | None], ...]
    removed: tuple[str, ...]


@dataclass(frozen=True)
class Change:
    kind: str
    key: str
    detail: str = ""

    def line(self) -> str:
        detail = {"version": f"{self.key}: {self.detail}",
                  "rename": f"{self.key} → {self.detail}",
                  "add": f"{self.key} = {self.detail}",
                  "remove": self.key,
                  "folder": f"{self.detail} — created empty ({self.key})",
                  "needs": f"{self.key} — no value a release chose: give one with "
                           f"--set {self.key}=<value>"}[self.kind]
        return f"  {self.kind:<9} {detail}"


def split_key(dotted: str) -> tuple[str, str]:
    section, dot, key = dotted.partition(".")
    if not (section and dot and key):
        raise Unplannable(f"{dotted!r} is not written section.key")
    return section, key


def part(parser: configparser.RawConfigParser, name: str) -> list[tuple[str, str | None]]:
    """One section of a release's block, as (key, value) pairs; none when it is absent."""
    return parser.items(name) if parser.has_section(name) else []


def releases(text: str, after: str, upto: str) -> list[Release]:
    """Every release section of the notes newer than `after`, up to and including `upto`."""
    heads = list(RELEASE.finditer(text))
    found = []
    for i, head in enumerate(heads):
        version = head.group(1)
        if not check.version_key(after) < check.version_key(version) <= check.version_key(upto):
            continue
        body = text[head.end():heads[i + 1].start() if i + 1 < len(heads) else len(text)]
        parser = configparser.RawConfigParser(allow_no_value=True, default_section="\0")
        parser.optionxform = str  # type: ignore[assignment,method-assign]
        try:
            parser.read_string("\n".join(CHANGES.findall(body)))
        except configparser.Error as error:
            raise Unplannable(f"the notes for {version} cannot be read: {error}") from error
        renamed, added, removed = (part(parser, name) for name in ("renamed", "added", "removed"))
        for dotted, _ in [*renamed, *added, *removed]:
            split_key(dotted)
        found.append(Release(version, CHANGES.sub("", body).strip(),
                             tuple((old, str(new)) for old, new in renamed),
                             tuple(added),
                             tuple(key for key, _ in removed)))
    return sorted(found, key=lambda release: check.version_key(release.version))


class SettingsText:
    """The settings file as lines, edited one setting at a time inside its `ini wiqrug` blocks."""

    def __init__(self, text: str) -> None:
        self.lines = text.splitlines()
        self.ending = "\n" if text.endswith("\n") else ""

    def text(self) -> str:
        return "\n".join(self.lines) + self.ending

    def layout(self) -> tuple[dict[str, tuple[int, int]], dict[str, int]]:
        """Each `section.key`'s (first line, line after its last), and each section's end."""
        entries: dict[str, tuple[int, int]] = {}
        ends: dict[str, int] = {}
        inside, section, current = False, "", ""
        for i, line in enumerate(self.lines):
            if not inside:
                inside = bool(OPEN.match(line))
                continue
            if line.startswith("```"):
                inside, current = False, ""
            elif SECTION.match(line):
                section, current = SECTION.match(line).group(1), ""  # type: ignore[union-attr]
                ends[section] = i + 1
            elif KEY.match(line) and section:
                current = f"{section}.{KEY.match(line).group(1)}"  # type: ignore[union-attr]
                entries[current] = (i, i + 1)
                ends[section] = i + 1
            elif current and line[:1].isspace() and line.strip():
                entries[current] = (entries[current][0], i + 1)
                ends[section] = i + 1
            else:
                current = ""
        return entries, ends

    def take(self, dotted: str) -> list[str]:
        start, end = self.layout()[0][dotted]
        taken = self.lines[start:end]
        del self.lines[start:end]
        return taken

    def put(self, dotted: str, lines: list[str]) -> None:
        section, _ = split_key(dotted)
        ends = self.layout()[1]
        if section in ends:
            self.lines[ends[section]:ends[section]] = lines
            return
        self.lines += ["", f"## {section}", "",
                       "Added by `/wiqrug:setup --upgrade`; the release notes say why.", "",
                       "```ini wiqrug", f"[{section}]", *lines, "```"]
        self.ending = "\n"

    def apply(self, change: Change) -> None:
        if change.kind == "version":
            start, _ = self.layout()[0][change.key]
            self.lines[start] = f"version = {change.detail.split(' → ')[1]}"
        elif change.kind == "rename":
            (old_section, _), (new_section, new_key) = split_key(change.key), split_key(change.detail)
            if old_section == new_section:
                start, _ = self.layout()[0][change.key]
                self.lines[start] = KEY.sub(f"{new_key} =", self.lines[start], count=1)
                return
            first, *rest = self.take(change.key)
            self.put(change.detail, [KEY.sub(f"{new_key} =", first, count=1), *rest])
        elif change.kind == "add":
            self.put(change.key, [f"{split_key(change.key)[1]} = {change.detail}"])
        elif change.kind == "remove":
            self.take(change.key)


@dataclass
class Plan:
    root: Path
    file: Path
    version: str
    installed: str
    notes: list[Release]
    changes: list[Change]
    text: str

    def render(self) -> str:
        if not self.changes:
            return (f"wiqrug: {self.root} is at wiqrug {self.version}; {self.installed} is "
                    "installed — nothing to upgrade.")
        lines = [f"wiqrug: upgrade plan for {self.root} — wiqrug {self.version} → "
                 f"{self.installed}.", "", "What changed for projects, from UPGRADING.md:"]
        for release in self.notes:
            lines += ["", f"  ## {release.version}", ""]
            lines += [f"  > {line}".rstrip() for line in release.note.splitlines()]
        lines += ["", f"What would change in {self.file.relative_to(self.root)} and the folders:"]
        lines += [change.line() for change in self.changes]
        lines += ["", "No document's content is read or written."]
        return "\n".join(lines)


def settings_changes(parser: configparser.RawConfigParser, notes: list[Release],
                     given: dict[str, str]) -> list[Change]:
    present = {f"{s}.{k}" for s in parser.sections() for k in parser.options(s)}
    changes = []
    asked: list[str] = []
    for release in notes:
        for old, new in release.renamed:
            if old in present and new not in present:
                changes.append(Change("rename", old, new))
                present = (present - {old}) | {new}
        for dotted, setting in release.added:
            if dotted in present:
                continue
            if setting is None:
                asked.append(dotted)
                continue
            changes.append(Change("add", dotted, setting))
            present.add(dotted)
        for dotted in release.removed:
            if dotted in present:
                changes.append(Change("remove", dotted))
                present.discard(dotted)
    complete = parser.get("wiqrug", "state", fallback="").strip() != check.IN_PROGRESS
    wanted = [f"{s}.{k}" for s, k, _ in check.SCHEMA] if complete else []
    wanted += [dotted for dotted in asked if dotted not in wanted]
    for dotted in dict.fromkeys([*wanted, *given]):
        if dotted in present and dotted in given:
            raise Unplannable(f"--set {dotted}: it already has a value, in the settings file or "
                              "from a release — an upgrade never replaces one; edit it by hand")
        if dotted in present:
            continue
        if dotted not in given:
            changes.append(Change("needs", dotted))
            continue
        if dotted not in wanted:
            raise Unplannable(f"--set {dotted}: no setting of that name is missing")
        changes.append(Change("add", dotted, given[dotted]))
        present.add(dotted)
    return changes


def folder_changes(root: Path, text: str) -> list[Change]:
    """Every folder a `documents` setting names, once the settings are changed, that is absent."""
    parser = check.parse(text)
    changes = []
    for key in FOLDERS:
        raw = parser.get("documents", key, fallback=check.NONE).strip()
        if raw in (check.NONE, ""):
            continue
        path = (root / raw).resolve()
        if not path.is_relative_to(root):
            raise Unplannable(f"documents.{key} = {raw} is outside the repository")
        if not path.exists():
            changes.append(Change("folder", f"documents.{key}", raw))
    return changes


def make_plan(folder: Path, installed: str, notes_file: Path, given: dict[str, str]) -> Plan:
    root = check.git_root(folder)
    if isinstance(root, check.Answer):
        raise Unplannable(root.message.removeprefix("wiqrug: "))
    path = root / check.SETTINGS
    if not path.is_file():
        raise Unplannable(f"{root} is not set up — run /wiqrug:setup first")
    try:
        text = path.read_text(encoding="utf-8")
        parser = check.parse(text)
        version = check.value(parser, "wiqrug", "version")
        if check.version_key(version) >= check.version_key(installed):
            return Plan(root, path, version, installed, [], [], text)
        notes = releases(notes_file.read_text(encoding="utf-8"), version, installed)
        changes = [Change("version", "wiqrug.version", f"{version} → {installed}"),
                   *settings_changes(parser, notes, given)]
        edited = SettingsText(text)
        for change in changes:
            edited.apply(change)
        changes += folder_changes(root, edited.text())
    except check.Refused as why:
        raise Unplannable(f"{path} is refused — {why}; fix it by hand first") from why
    return Plan(root, path, version, installed, notes, changes, edited.text())


def apply(plan: Plan) -> check.Answer:
    needs = [change.key for change in plan.changes if change.kind == "needs"]
    if needs:
        raise Unplannable(f"nothing written: {', '.join(needs)} need a value — give each with --set")
    for change in plan.changes:
        if change.kind == "folder":
            (plan.root / change.detail).mkdir(parents=True, exist_ok=True)
    plan.file.write_text(plan.text, encoding="utf-8")
    return check.check(plan.root, plan.installed)


def given_values(pairs: list[str]) -> dict[str, str]:
    given = {}
    for pair in pairs:
        dotted, equals, setting = pair.partition("=")
        split_key(dotted.strip())
        if not equals or not setting.strip():
            raise Unplannable(f"--set {pair}: a value is never blank — write `{check.NONE}` "
                              "where the project has none")
        given[dotted.strip()] = setting.strip()
    return given


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("folder", nargs="?", type=Path, default=Path.cwd(),
                        help="a folder inside the project; the current one by default")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--plan", action="store_true", help="print the plan; write nothing")
    mode.add_argument("--apply", action="store_true", help="write exactly the plan")
    parser.add_argument("--set", action="append", default=[], metavar="SECTION.KEY=VALUE",
                        help="the value of a setting the plan says needs one")
    parser.add_argument("--installed", help="the installed wiqrug version; plugin.json's by default")
    parser.add_argument("--notes", type=Path, default=NOTES, help="the release notes to read")
    args = parser.parse_args(argv)
    if not args.folder.is_dir():
        parser.error(f"{args.folder} is not a folder")
    try:
        plan = make_plan(args.folder.resolve(), args.installed or check.installed_version(),
                         args.notes, given_values(args.set))
        print(plan.render())
        if args.plan or not plan.changes:
            return 0
        found = apply(plan)
    except Unplannable as why:
        print(f"wiqrug: cannot upgrade — {why}.")
        return 1
    print("", "Applied. The project check now answers:", check.human(found).splitlines()[0],
          sep="\n")
    return 0 if found.answer in ("set-up", "in-progress") else 1


if __name__ == "__main__":
    sys.exit(main())
