#!/usr/bin/env python3
"""The project check: the one reader of a project's wiqrug settings file.

    wiqrug-check [FOLDER] [--json] [--installed VERSION]

Every skill but `grill-me` and `interview` makes this its first line, as the snippet
!`wiqrug-check --skill` — the launcher's form that always exits 0, since Claude Code aborts a skill
whose snippet does not — and the unattended loop calls it at start. Given a folder — the current one by
default — it finds the git root and gives exactly one answer:

    exit  answer        meaning
    0     set-up        every setting, its paths resolved to absolute ones from the git root
    3     missing       a dependency is missing — git, a git repository, or Python — named
    4     not-set-up    no settings file at the git root: run /wiqrug:setup
    5     older         written by an older wiqrug than the installed one: /wiqrug:setup --upgrade
    6     in-progress   setup has not finished: only setup and to-tickets go on
    7     invalid       the settings file is unreadable, a required key is absent or blank
    2                   the command line itself is wrong

The human answer is one line starting `wiqrug:`, then, for set-up and in-progress, one
`section.key = value` line per setting: that block is what a skill reads. `--json` prints one
object — `answer`, `message`, `root`, `file`, `version`, `installed`, `settings` — for the loop.
In it a path set to `none` is null and a list setting is a list.

**The file's place is `.claude/wiqrug.md` at the git root.** It is configuration for Claude Code
sessions, so it sits beside Claude Code's own; it keeps the project's root free of one more file;
and it is found from the git root, never from the folder a session happens to stand in.

**Its format is Markdown whose `ini wiqrug` fenced blocks hold the settings**, read with the
standard library's `configparser`. A person reads it rendered, with the reason for each setting
written beside it; a machine reads only the blocks. The alternatives each failed one requirement:
JSON carries no comments, so no reason can sit beside a setting; TOML needs `tomllib`, which only
Python 3.11 has; YAML needs a third-party library. INI gives sections, `#` comments, and lists as
one indented line per entry. Nothing is interpolated and `#` or `;` inside a value is kept, so a
command is read exactly as written. A blank value is refused: `none` says "the project has none".

**The launcher is `bin/wiqrug-check`**, on the Bash tool's PATH because a plugin's `bin/` is. It
finds Python as `python3`, `python` or `py` — each probed, since Windows can carry a `python3`
that only opens the store — and names Python as missing when none runs. `bin/wiqrug-check.cmd` is
the same for PowerShell, untested. A settings file written by a newer wiqrug than the installed one
is read as it stands; only an older one is refused.
"""
from __future__ import annotations

import argparse
import configparser
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
SETTINGS = Path(".claude") / "wiqrug.md"
FENCE = re.compile(r"^```ini wiqrug\s*\n(.*?)^```\s*$", re.MULTILINE | re.DOTALL)
NONE = "none"
IN_PROGRESS = "setup-in-progress"

# Every setting: (section, key, kind). A "path" resolves from the git root and may be `none`;
# a "list" is one entry per line and may be `none`; a "text" is read as written; an "exit" is a
# process's exit code from 1 to 255, or `none`.
SCHEMA = (
    ("wiqrug", "version", "text"),
    ("wiqrug", "state", "text"),
    *(("documents", key, "path") for key in (
        "queue", "specs", "decisions", "gotchas", "glossary", "questions", "now", "research",
        "archive", "ledger", "units")),
    ("knowledge", "level", "text"),
    ("done", "command", "text"),
    ("done", "owed-exit", "exit"),
    ("tests", "framework", "text"),
    ("tests", "limits", "list"),
    ("unattended", "prepare", "list"),
    ("environments", "list", "list"),
    ("browser", "check", "text"),
    ("language", "deliverables", "text"),
    ("agents", "never-touch", "list"),
)
IN_PROGRESS_KEYS = (("wiqrug", "version"), ("documents", "queue"))
#: How the two answers a skill acts on begin. Skills quote these verbatim, and the bundle check
#: holds every quotation to them, so rewording one here cannot leave every skill refusing.
SET_UP_PREFIX = "wiqrug: set up —"
IN_PROGRESS_PREFIX = "wiqrug: setup in progress"
FULL_ONLY = (("documents", "ledger"), ("documents", "units"))
LEVELS = ("standard", "full")
STATES = ("complete", IN_PROGRESS)
EXIT = {"set-up": 0, "missing": 3, "not-set-up": 4, "older": 5, "in-progress": 6, "invalid": 7}

Settings = dict[str, dict[str, object]]


@dataclass
class Answer:
    answer: str
    message: str
    root: Path | None = None
    file: Path | None = None
    version: str | None = None
    installed: str | None = None
    settings: Settings = field(default_factory=dict)

    def as_json(self) -> dict[str, object]:
        return {"answer": self.answer, "message": self.message,
                "root": str(self.root) if self.root else None,
                "file": str(self.file) if self.file else None,
                "version": self.version, "installed": self.installed, "settings": self.settings}


class Refused(Exception):
    """The settings file cannot be used; the message names why."""


def installed_version() -> str:
    manifest = PLUGIN / ".claude-plugin" / "plugin.json"
    return str(json.loads(manifest.read_text(encoding="utf-8"))["version"])


def version_key(version: str) -> tuple[int, ...]:
    """`0.10.0` as (0, 10, 0), so versions compare by number and not as text."""
    if not re.fullmatch(r"\d+(\.\d+)*", version):
        raise Refused(f"wiqrug.version {version!r} is not a version like 0.1.0")
    return tuple(int(part) for part in version.split("."))


def git_root(folder: Path) -> Path | Answer:
    git = shutil.which("git")
    if git is None:
        return Answer("missing", "wiqrug: git is not installed (not found on PATH) — install git, "
                                 "then run this again.")
    done = subprocess.run([git, "-C", str(folder), "rev-parse", "--show-toplevel"],
                          capture_output=True, text=True, check=False)
    if done.returncode != 0:
        return Answer("missing", f"wiqrug: {folder} is not a git repository — open the session in "
                                 "your project, or run `git init` there yourself first.")
    return Path(done.stdout.strip()).resolve()


def parse(text: str) -> configparser.RawConfigParser:
    blocks = FENCE.findall(text)
    if not blocks:
        raise Refused("it holds no ```ini wiqrug block")
    parser = configparser.RawConfigParser(empty_lines_in_values=False, default_section="\0")
    parser.optionxform = str  # type: ignore[assignment,method-assign]
    try:
        parser.read_string("\n".join(blocks))
    except configparser.Error as error:
        raise Refused(f"it cannot be read: {error}".replace("\n", " ")) from error
    return parser


def value(parser: configparser.RawConfigParser, section: str, key: str) -> str:
    raw = parser.get(section, key, fallback=None)
    if raw is None:
        raise Refused(f"{section}.{key} is missing")
    if not raw.strip():
        raise Refused(f"{section}.{key} is blank — write `{NONE}` where the project has none")
    return raw.strip()


def resolve(root: Path, kind: str, raw: str) -> object:
    if kind == "text":
        return raw
    if raw == NONE:
        return [] if kind == "list" else None
    if kind == "exit":
        return int(raw) if re.fullmatch(r"\d{1,3}", raw) and 1 <= int(raw) <= 255 else raw
    if kind == "list":
        return [line.strip() for line in raw.splitlines() if line.strip()]
    return str((root / raw).resolve())


def read(parser: configparser.RawConfigParser, root: Path,
         keys: tuple[tuple[str, str], ...]) -> Settings:
    kinds = {(section, key): kind for section, key, kind in SCHEMA}
    settings: Settings = {}
    for section, key in keys:
        settings.setdefault(section, {})[key] = resolve(root, kinds[section, key],
                                                         value(parser, section, key))
    return settings


def validate(settings: Settings) -> None:
    for section, key, kind in SCHEMA:
        setting = settings[section][key]
        if kind == "exit" and isinstance(setting, str):
            raise Refused(f"{section}.{key} is {setting!r}, not an exit code from 1 to 255 or "
                          f"`{NONE}`")
    level = settings["knowledge"]["level"]
    if level not in LEVELS:
        raise Refused(f"knowledge.level is {level!r}, not one of {', '.join(LEVELS)}")
    if level == "full":
        for section, key in FULL_ONLY:
            if settings[section][key] is None:
                raise Refused(f"{section}.{key} is `{NONE}`, but full knowledge keeps one")


def check(folder: Path, installed: str | None = None) -> Answer:
    """The one answer for the project that `folder` is in."""
    root = git_root(folder)
    if isinstance(root, Answer):
        return root
    installed = installed or installed_version()
    path = root / SETTINGS
    found = Answer("invalid", "", root, path, None, installed)
    if not path.is_file():
        found.answer = "not-set-up"
        found.message = f"wiqrug: {root} is not set up — run /wiqrug:setup first."
        return found
    try:
        parser = parse(path.read_text(encoding="utf-8"))
        found.version = value(parser, "wiqrug", "version")
        if version_key(found.version) < version_key(installed):
            found.answer = "older"
            found.message = (f"wiqrug: {root} was set up by wiqrug {found.version}; "
                             f"{installed} is installed — run /wiqrug:setup --upgrade.")
            return found
        state = value(parser, "wiqrug", "state") if parser.has_option("wiqrug", "state") else ""
        if state == IN_PROGRESS:
            found.settings = read(parser, root, IN_PROGRESS_KEYS)
            found.answer = "in-progress"
            found.message = (f"{IN_PROGRESS_PREFIX} in {root} — finish setup with "
                             "/wiqrug:setup; only setup and to-tickets go on.")
            return found
        found.settings = read(parser, root, tuple((s, k) for s, k, _ in SCHEMA))
        if state not in STATES:
            raise Refused(f"wiqrug.state is {state!r}, not one of {', '.join(STATES)}")
        validate(found.settings)
    except Refused as why:
        found.settings = {}
        found.message = f"wiqrug: {path} is refused — {why}. Fix it, or run /wiqrug:setup."
        return found
    found.answer = "set-up"
    found.message = (f"{SET_UP_PREFIX} {root}, wiqrug {found.version}, "
                     f"{found.settings['knowledge']['level']} knowledge.")
    return found


def human(found: Answer) -> str:
    lines = [found.message]
    for section, keys in found.settings.items():
        for key, setting in keys.items():
            if isinstance(setting, list) and setting:
                lines.append(f"{section}.{key} =")
                lines += [f"    {entry}" for entry in setting]
                continue
            lines.append(f"{section}.{key} = {NONE if setting in (None, []) else setting}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("folder", nargs="?", type=Path, default=Path.cwd(),
                        help="a folder inside the project; the current one by default")
    parser.add_argument("--json", action="store_true", help="one JSON object, for the loop")
    parser.add_argument("--installed", help="the installed wiqrug version; plugin.json's by default")
    args = parser.parse_args(argv)
    if not args.folder.is_dir():
        parser.error(f"{args.folder} is not a folder")
    found = check(args.folder.resolve(), args.installed)
    print(json.dumps(found.as_json(), ensure_ascii=False) if args.json else human(found))
    return EXIT[found.answer]


if __name__ == "__main__":
    sys.exit(main())
