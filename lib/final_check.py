#!/usr/bin/env python3
"""The final check: whether a project `/wiqrug:setup` has just set up actually works.

    final_check.py [FOLDER] [--no-session]

Setup's last step. Given a folder inside the project — the current one by default — it prints
one line per check, ✅, ⚠️ or ❌, and nothing else on stdout:

    project check   every skill but grill-me and interview calls the launcher as its first line,
                    and the launcher answers "set up" here
    done command    `done.command` runs from the root and exits 0 (✅) or `done.owed-exit` (⚠️ —
                    every check it could run passed, the rest is owed: not a tick). A failure
                    is the PROJECT's own and is named as such: setup never edits the code that
                    the command checks, and nothing here tries to fix it
    loop dry run    a one-item demonstration queue is written under `documents.queue`, the
                    unattended loop's dry run plans that item, and the queue is removed again —
                    the line is ❌ if anything the demonstration wrote is still there after it
    a session       a fresh `claude -p`, asked what `CLAUDE.md` requires, answers with a
                    `done:` line holding exactly the "done" command and a `queue:` line holding
                    exactly the queue folder the settings file holds. `--no-session` skips
                    it — no session is started, and stderr says so — for a check that must not
                    spend a model call

Exit 0 when no line is ❌, 1 when any is, 2 when the command line is wrong. A check that
cannot run (no bash for the loop, no `claude` for the session) is ❌ naming what is missing:
a check that cannot run has not passed.
"""
from __future__ import annotations

import argparse
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

# Importing the project check would write a bytecode cache into the installed plugin.
sys.dont_write_bytecode = True
import project_check  # noqa: E402  — the one reader of the settings file, beside this one

PLUGIN = project_check.PLUGIN
LAUNCHER = PLUGIN / "bin" / "wiqrug-check"
LOOP = PLUGIN / "skills" / "implement" / "afk.sh"
DONE_TIMEOUT_S = 30 * 60
SESSION_TIMEOUT_S = 5 * 60
#: In the item format a queue is written in: no file named as work, and no box for the done
#: command, which the loop runs itself as the code gate.
DEMO_ITEM = """# 01: Demonstration

Advances:   wiqrug-setup

## What to build

Written by wiqrug's final check to prove the unattended loop can plan an item here, then removed.

## Acceptance

- [ ] `git rev-parse --verify --quiet HEAD` exits 0
"""
QUESTION = ("Read CLAUDE.md in this repository, and whatever it points to for the project's "
            "settings. Without changing anything, answer in exactly two lines and nothing else: "
            "`done: ` followed by the exact command that says work here is done, then `queue: ` "
            "followed by the folder where the work queue lives, relative to the repository root.")
NO_FIRST_STEP = {"grill-me", "interview"}
MARKS = {"passed": "✅", "owed": "⚠️", "failed": "❌"}


@dataclass
class Line:
    passed: bool
    text: str
    owed: bool = False

    def __str__(self) -> str:
        return f"{MARKS['owed' if self.owed else 'passed' if self.passed else 'failed']} {self.text}"


def check_project(root: Path) -> Line:
    """The launcher, run as a skill's first line runs it: `wiqrug-check --skill` from the root."""
    every = sorted(path.parent.name for path in (PLUGIN / "skills").glob("*/SKILL.md"))
    skills = [name for name in every
              if "!`wiqrug-check --skill`" in (PLUGIN / "skills" / name / "SKILL.md")
              .read_text(encoding="utf-8")]
    skipped = [name for name in every if name not in skills and name not in NO_FIRST_STEP]
    if skipped:
        return Line(False, f"project check: {', '.join(skipped)} do not call it first — the "
                           "installed wiqrug is damaged; reinstall it")
    done = subprocess.run(["sh", str(LAUNCHER), "--skill"], cwd=root, capture_output=True,
                          text=True, encoding="utf-8", check=False)
    first = (done.stdout.splitlines() or ["(nothing printed)"])[0]
    if first.startswith(project_check.SET_UP_PREFIX):
        return Line(True, f"project check: {len(skills)} skills call it, and it answers "
                          f"\"{first}\"")
    return Line(False, f"project check: \"{first}\" — every skill but grill-me and interview "
                       "stops on that")


def check_done(root: Path, settings: project_check.Settings) -> Line:
    command = settings["done"]["command"]
    owed = settings["done"]["owed-exit"]
    if command == project_check.NONE:
        return Line(False, "done command: `none` — nothing an agent builds here is proved by a "
                           "command; agree one in done.command")
    shell = shutil.which("bash")
    try:
        done = subprocess.run([shell, "-c", str(command)] if shell else str(command), cwd=root,
                              shell=shell is None, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=DONE_TIMEOUT_S,
                              check=False)
    except subprocess.TimeoutExpired:
        return Line(False, f"done command: `{command}` did not finish within "
                           f"{DONE_TIMEOUT_S // 60} minutes — the project's own check; setup "
                           "leaves the application's code alone")
    if done.returncode == 0:
        return Line(True, f"done command: `{command}` exited 0")
    if done.returncode == owed:
        return Line(True, f"done command: `{command}` exited {owed}, its owed exit — every "
                          "check it could run here passed; the rest is owed", owed=True)
    tail = (done.stdout + done.stderr).strip().splitlines()[-5:]
    if tail:
        print(f"final check: the last lines of `{command}`:", *tail, sep="\n    ", file=sys.stderr)
    return Line(False, f"done command: `{command}` exited {done.returncode} — the project's own "
                       "check fails; that is the project's to fix, and setup leaves the "
                       "application's code alone")


def status(root: Path) -> str:
    return subprocess.run(["git", "-C", str(root), "status", "--porcelain",
                           "--untracked-files=all"], capture_output=True, text=True,
                          check=True).stdout


def first_missing(path: Path) -> Path:
    """The outermost folder of `path` that does not exist yet — what a demonstration creates."""
    while not path.parent.exists():
        path = path.parent
    return path


def check_loop(root: Path, settings: project_check.Settings) -> Line:
    queue = settings["documents"]["queue"]
    if queue is None:
        return Line(False, "loop dry run: documents.queue is `none` — the loop has no queue")
    shell = shutil.which("bash")
    if shell is None:
        return Line(False, "loop dry run: bash is not installed — the unattended loop needs it "
                           "(Git Bash on Windows)")
    slug = f"wiqrug-demonstration-{secrets.token_hex(3)}"
    folder = Path(str(queue)) / slug
    created = first_missing(folder)
    before = status(root)
    environments = settings["environments"]["list"]
    args = [shell, str(LOOP), slug, "--dry-run", "--no-review"]
    if environments:
        args += ["--environment", str(environments[0]).split()[0]]
    with tempfile.TemporaryDirectory(prefix="wiqrug-final-check-") as scratch:
        try:
            folder.mkdir(parents=True)
            (folder / "01-demonstration.md").write_text(DEMO_ITEM, encoding="utf-8")
            run = subprocess.run(args, cwd=root, capture_output=True, text=True,
                                 encoding="utf-8", errors="replace", check=False,
                                 env={**os.environ, "AFK_ROOT": scratch})
        finally:
            shutil.rmtree(created, ignore_errors=True)
    left = status(root) != before or created.exists()
    planned = run.returncode == 0 and "01-demonstration.md" in run.stdout
    if planned and not left:
        return Line(True, "loop dry run: it plans the one-item demonstration queue, which is "
                          "removed again")
    if not planned:
        why = (run.stderr.strip().splitlines() or run.stdout.strip().splitlines()
               or ["(nothing printed)"])[-1]
        return Line(False, f"loop dry run: exited {run.returncode} on the demonstration queue — "
                           f"{why}")
    return Line(False, f"loop dry run: planned, but the demonstration queue left {created} or "
                       "changed what git sees")


def check_session(root: Path, settings: project_check.Settings) -> Line:
    if settings["documents"]["queue"] is None:
        return Line(False, "a session: documents.queue is `none` — there is no queue to name")
    claude = shutil.which("claude")
    if claude is None:
        return Line(False, "a session: `claude` is not on PATH — run again with --no-session to "
                           "skip this check")
    command = str(settings["done"]["command"])
    queue = Path(str(settings["documents"]["queue"])).relative_to(root).as_posix()
    try:
        done = subprocess.run([claude, "-p", QUESTION], cwd=root, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=SESSION_TIMEOUT_S,
                              check=False)
    except subprocess.TimeoutExpired:
        return Line(False, f"a session: no answer within {SESSION_TIMEOUT_S // 60} minutes")
    said = answered(done.stdout)
    missing = [f"`{want}`" for label, want in (("done", command), ("queue", queue))
               if said.get(label) != want]
    if done.returncode == 0 and not missing:
        return Line(True, f"a session reading CLAUDE.md names the done command `{command}` and "
                          f"the queue {queue}")
    return Line(False, f"a session reading CLAUDE.md did not name {' and '.join(missing) or '…'}"
                       f" (exit {done.returncode}) — CLAUDE.md should point at the settings file")


def answered(reply: str) -> dict[str, str]:
    """The `done:` and `queue:` lines of a reply, each value without its backticks or a trailing
    slash. A word met elsewhere in the reply is not an answer: `true` is in most sentences."""
    found: dict[str, str] = {}
    for line in reply.splitlines():
        label, colon, value = line.strip().strip("*-` ").partition(":")
        label = label.strip().lower()
        if colon and label in ("done", "queue"):
            value = value.strip().strip("*` ")
            found.setdefault(label, value.rstrip("/") if label == "queue" else value)
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("folder", nargs="?", type=Path, default=Path.cwd(),
                        help="a folder inside the project; the current one by default")
    parser.add_argument("--no-session", action="store_true",
                        help="skip the check that starts a fresh claude session")
    args = parser.parse_args(argv)
    if not args.folder.is_dir():
        parser.error(f"{args.folder} is not a folder")
    found = project_check.check(args.folder.resolve())
    lines = [check_project(found.root or args.folder.resolve())]
    if found.answer == "set-up" and found.root is not None:
        lines += [check_done(found.root, found.settings),
                  check_loop(found.root, found.settings)]
        if args.no_session:
            print("final check: --no-session — no session was asked what CLAUDE.md requires",
                  file=sys.stderr)
        else:
            lines.append(check_session(found.root, found.settings))
    else:
        print("final check: the rest needs a project the project check calls set up",
              file=sys.stderr)
    for line in lines:
        print(line)
    return 0 if all(line.passed for line in lines) else 1


if __name__ == "__main__":
    sys.exit(main())
