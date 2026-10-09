#!/usr/bin/env python3
"""work_next.py — which work item may be picked up, decided from the files.

WHY. The decision "is this item ready" must not be a judgement call made by whoever is
reading the folder, because the two cheapest ways to waste a day are to start an item
whose dependency is unfinished and to start one that rests on a decision nobody has made.
Both are computable from the item's own headers, so they are computed here.

    python3 ${CLAUDE_PLUGIN_ROOT}/lib/work_next.py <slug>               # the next ready item
    python3 ${CLAUDE_PLUGIN_ROOT}/lib/work_next.py <slug> --unattended  # never an attended one
    python3 ${CLAUDE_PLUGIN_ROOT}/lib/work_next.py <slug> --all         # every item and state
    python3 ${CLAUDE_PLUGIN_ROOT}/lib/work_next.py <slug> --json        # the same, machine-read
    python3 ${CLAUDE_PLUGIN_ROOT}/lib/work_next.py --selftest           # prove it still decides

**The queue is found through the project check**, never a fixed folder: `<slug>` is a folder
under the settings file's `documents.queue`, for the project that `--project` — the current
folder by default — is in. A path it prints is relative to that project's git root. A project
that is not set up, or keeps no queue, is exit 2 with the project check's own line: nothing
may be picked up there. While setup is in progress the queue is read all the same, because
setup builds itself from one. The item format is `/wiqrug:to-tickets`' item-format page.

Exit codes: 0 an item was printed · 1 nothing is ready, with the reason on stderr ·
2 the project, the folder or an item is malformed, and nothing may be picked up until it is
fixed.

An item is `owed` when every box still open is one no session can close:
  * a box **for a person** to tick by looking — in an OLDER queue, written before items stopped
    carrying a person's box, the done command's box and a `Touches:` line;
  * a `- [~]` box — the "done" command ran and passed everything it could check, and only what
    this copy of the project cannot reach was left unchecked;
  * a box whose item says `Box <n> worded wrong: <why>` under `## Comments` — it passed before
    any work and is worded wrong, which is a question for the owner, not work for a session;
  * the "`<done.command>` exits 0" box of an older queue, once any other box on the item is
    ticked — an item nobody built is not finished work. The loop runs the done
    command once on the branch tip at the end, and ticks, marks or reopens it from there. Not
    the box the loop adds when the code gate fails, which opens with "the code gate passes":
    that one is a command's to close, and holds the item open.
An owed item unblocks the items after it, so an unattended run does not stop on work that is
waiting for the owner; the boxes stay open, and the report lists them. A box wrapped over
several lines is one box: its indented continuation lines are part of its text.

A `## To file` line is a finding an unattended session leaves for the run's closing session,
which files every line — typed `G:`, `F:`, `Q:`, `answer:`, `term:`, `D:` or `defect:`, and
ticked once `/wiqrug:update-knowledge <slug>` has filed it. It is NOT an acceptance box: an item
whose only open boxes are To file lines is done, and `--json` lists them apart so the loop can
tell what the filing has to do.

Three `## Comments` lines are read, each by its exact prefix:
  * `Fails first: box <n> passed at <sha> before any work — delivered by <what>: <evidence>.` —
    the box passed before any work because earlier work delivered it, and the session ticked it
    on that evidence. `--json` lists them as `fails_first`, for the item's reviewer to check.
    A box that passed first never parks an item.
  * `Box <n> worded wrong: <why>` — `worded_wrong`; the box is owed (above).
  * `Spec question: <question>` — `spec_questions`: a review finding that is a gap in the spec,
    for the owner. The run's report lists both of the last two as its spec questions.

`Touches:` is no longer part of an item: an older queue carries it, and it is read past and
ignored — never required, never compared between items.

An item with an `Attended: <why>` header is built by the owner, typing `/wiqrug:implement` —
never by the unattended loop. With `--unattended` it is not offered, and the items that depend
on it wait; without, it is offered like any ready item. Its state says `attended` either way.
An `Attended:` line with no reason is malformed, never read as "not attended".

`WORK_NEXT_SET_ASIDE="01 04"` is the loop's own: the items an unattended session could not
finish in this run. They are not offered again, and the items that depend on them wait. It is
set by the loop, never by a person — an item a person keeps out says so in its `Attended:` line.

⚠️ A malformed item is exit 2, never "not ready". An item missing its `Touches:` line
cannot be checked for overlap, and an item with no acceptance box cannot be finished — in
both cases a loop that skipped it politely would drain the queue and report success.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Importing the neighbour would leave a __pycache__ in the plugin, holding this machine's paths.
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE))
import project_check  # noqa: E402  — the one reader of the settings file, beside this one

ITEM_NAME = re.compile(r"^(\d{2})-[a-z0-9-]+\.md$")
HEADER = re.compile(r"^(Advances|Blocked by|Waits on|Touches|Cites|Attended):\s*(.*)$")
BOX = re.compile(r"^\s*-\s*\[( |x|X|~)\]\s+(.+?)\s*$")
#: A box a person closes by looking. The phrase is the one `/to-tickets` writes on such a box.
FOR_A_PERSON = re.compile(r"for a person", re.IGNORECASE)
#: The line `/wiqrug:implement` writes under `## Comments` when a box passed before any work and
#: it ticked the box on the evidence of the earlier work that delivered it. A session's success
#: note ("Fails first: boxes 1 and 2 ran and exited 1") starts the same way and is not one.
FAILS_FIRST = re.compile(
    r"^\s*(?:-\s+)?Fails first:\s*(box \d+ passed at \S+ before any work\b.*?)\s*$")
#: A box that passed before any work and is worded wrong: it stays open, and is owed.
WORDED_WRONG = re.compile(r"^\s*(?:-\s+)?Box (\d+) worded wrong:\s*(.+?)\s*$")
#: A review finding that is a gap in the spec: a question for the owner, never code.
SPEC_QUESTION = re.compile(r"^\s*(?:-\s+)?Spec question:\s*(.+?)\s*$")
#: How the box the loop adds when the code gate fails begins. It names the done command too, so
#: without this it would read as an old queue's done box — owed — and an item whose gate failed
#: would settle, letting what depends on it be built on code that does not pass.
GATE_BOX = "the code gate passes"
EMPTY = {"", "-", "—", "none", "None"}


def is_done_box(text: str, done: str) -> bool:
    """The one test of "this box is an older queue's done box" — "`<done.command>` exits 0" — for
    this reader and for the loop, which marks it on the branch tip. Never the box the loop adds
    when the code gate fails. A substring, never a regex: the command is the project's, and may
    hold any character a regex reads."""
    return bool(done) and done in text and not text.startswith(GATE_BOX)


class Malformed(Exception):
    """An item that cannot be judged. Never treated as merely not-ready."""


@dataclass
class Item:
    number: str
    path: Path
    title: str
    advances: str = ""
    blocked_by: list[str] = field(default_factory=list)
    waits_on: list[str] = field(default_factory=list)
    cites: list[str] = field(default_factory=list)
    #: Why the owner builds it and the unattended loop never does; empty for any other item.
    attended: str = ""
    boxes: list[tuple[bool, str]] = field(default_factory=list)
    #: Box texts marked `- [~]`: every check ran green, only the running stack is unchecked.
    stack_owed: set[str] = field(default_factory=set)
    #: `## To file` lines, (filed, text). Never acceptance boxes: they do not hold the item open.
    to_file: list[tuple[bool, str]] = field(default_factory=list)
    #: `Fails first:` lines under `## Comments` — a box ticked on earlier work's evidence.
    fails_first: list[str] = field(default_factory=list)
    #: `Box <n> worded wrong:` lines, box number (1-based, under ## Acceptance) to why.
    worded_wrong: dict[int, str] = field(default_factory=dict)
    #: `Spec question:` lines — the owner's to answer.
    spec_questions: list[str] = field(default_factory=list)
    #: The project's `done.command`, which an old queue's done box names; empty when unknown.
    done_command: str = ""

    @property
    def done(self) -> bool:
        return bool(self.boxes) and all(ticked for ticked, _ in self.boxes)

    def is_done_box(self, text: str) -> bool:
        return is_done_box(text, self.done_command)

    @property
    def owed_boxes(self) -> list[str]:
        """Open boxes no session can close — a person's, the `[~]` ones, a box worded wrong, or
        an old queue's done box, which the loop settles on the branch tip."""
        # ⚠️ The done box only once something on the item is proved: an item nobody has built,
        # whose other boxes are a person's, would otherwise read as finished work.
        built = any(ticked for ticked, _ in self.boxes)
        return [text for number, (ticked, text) in enumerate(self.boxes, start=1)
                if not ticked and (text in self.stack_owed or FOR_A_PERSON.search(text)
                                   or number in self.worded_wrong
                                   or (built and self.is_done_box(text)))]

    @property
    def owed(self) -> bool:
        """Not done, and nothing left on it that another session could do."""
        open_boxes = sum(1 for ticked, _ in self.boxes if not ticked)
        return not self.done and bool(self.boxes) and open_boxes == len(self.owed_boxes)

    @property
    def settled(self) -> bool:
        """Done or owed: what a dependant waits for, and what a loop counts as drained."""
        return self.done or self.owed

    @property
    def ticked(self) -> int:
        return sum(1 for ticked, _ in self.boxes if ticked)


def split_values(raw: str) -> list[str]:
    """`02, 05` and `02 05` both mean the same thing, and a dash means nothing."""
    if raw.strip() in EMPTY:
        return []
    return [part for part in re.split(r"[,\s]+", raw.strip()) if part]


def parse(path: Path) -> Item:
    match = ITEM_NAME.match(path.name)
    if not match:
        raise Malformed(f"{path.name}: not NN-slug.md")
    text = path.read_text(errors="replace")
    lines = text.splitlines()
    title = next((line[2:].strip() for line in lines if line.startswith("# ")), "")
    item = Item(number=match.group(1), path=path, title=title)

    last: str | None = None
    section = ""
    #: The list the box being read went into, while its indented continuation may follow.
    wrapping: list[tuple[bool, str]] | None = None
    marks: list[str] = []
    for line in lines:
        header = HEADER.match(line)
        if header:
            last = header.group(1)
            _assign(item, last, header.group(2))
            continue
        if line.startswith("## "):
            heading = line[3:].strip().lower()
            section = ("acceptance" if heading.startswith("acceptance")
                       else "to file" if heading == "to file"
                       else "comments" if heading == "comments" else "")
            last, wrapping = None, None
            continue
        # An old queue's `Touches:` runs on over indented lines; they are read past, never kept.
        if last == "Touches" and line.startswith((" ", "\t")) and line.strip():
            continue
        if section == "comments":
            _comment(item, line)
            continue
        box = BOX.match(line) if section else None
        if box:
            wrapping = item.to_file if section == "to file" else item.boxes
            wrapping.append((box.group(1).lower() == "x", box.group(2)))
            if wrapping is item.boxes:
                marks.append(box.group(1))
        elif wrapping is not None and line.startswith((" ", "\t")) and line.strip():
            # A wrapped box is one box: "for a person" on its second line still makes it a
            # person's, and the report shows the whole of it.
            ticked, text = wrapping[-1]
            wrapping[-1] = (ticked, f"{text} {line.strip()}")
        else:
            wrapping = None

    item.stack_owed = {text for mark, (_, text) in zip(marks, item.boxes) if mark == "~"}
    _validate(item)
    return item


def _comment(item: Item, line: str) -> None:
    """The three `## Comments` lines the loop reads; any other comment is prose."""
    delivered = FAILS_FIRST.match(line)
    if delivered:
        item.fails_first.append(delivered.group(1))
    wrong = WORDED_WRONG.match(line)
    if wrong:
        item.worded_wrong[int(wrong.group(1))] = wrong.group(2)
    question = SPEC_QUESTION.match(line)
    if question:
        item.spec_questions.append(question.group(1))


def _assign(item: Item, header: str, raw: str) -> None:
    if header == "Advances":
        item.advances = raw.strip()
    elif header == "Blocked by":
        item.blocked_by = split_values(raw)
    elif header == "Waits on":
        item.waits_on = split_values(raw)
    elif header == "Cites":
        item.cites = split_values(raw)
    elif header == "Attended":
        # The header keeps an item from the loop; with its reason forgotten it would do the
        # opposite, silently. So a blank reason is malformed, never "not attended".
        if raw.strip() in EMPTY:
            raise Malformed(f"{item.path.name}: `Attended:` with no reason — "
                            "say why the owner builds it, or drop the line")
        item.attended = raw.strip()


def _validate(item: Item) -> None:
    if not item.title:
        raise Malformed(f"{item.path.name}: no `# NN: title` line")
    if not item.advances:
        raise Malformed(f"{item.path.name}: no `Advances:` — name the unit it moves")
    if not item.boxes:
        raise Malformed(f"{item.path.name}: no acceptance box under `## Acceptance`")


def queue_of(project: Path) -> tuple[Path, Path, str]:
    """(the git root, the queue folder, the done command or "") of the project `project` is in,
    from the project check. Anything but a project with a queue is Malformed, carrying the
    check's own line."""
    found = project_check.check(project.resolve())
    if found.answer not in ("set-up", "in-progress") or found.root is None:
        raise Malformed(found.message)
    queue = found.settings["documents"]["queue"]
    if queue is None:
        raise Malformed(f"documents.queue is `none` in {found.file} — this project keeps no "
                        "work queue; set one with /wiqrug:setup --upgrade")
    done = found.settings.get("done", {}).get("command")
    return found.root, Path(str(queue)), "" if done in (None, "none") else str(done)


def load(slug: str, queue: Path, done: str = "") -> list[Item]:
    """The items of `queue/slug`. `done` is the project's done command, by which an old queue's
    done box is known; without it, that box is read as one a command closes."""
    folder = queue / slug
    if not folder.is_dir():
        raise Malformed(f"no such work folder: {folder}")
    items = [parse(path) for path in sorted(folder.glob("*.md"))
             if ITEM_NAME.match(path.name)]
    if not items:
        raise Malformed(f"{folder} holds no NN-slug.md item")
    numbers = [item.number for item in items]
    if len(set(numbers)) != len(numbers):
        raise Malformed(f"{folder}: two items share a number")
    for item in items:
        item.done_command = done
    return items


def set_aside_by_the_loop() -> set[str]:
    """Items the loop set aside in this run (`WORK_NEXT_SET_ASIDE`) — never offered again."""
    return set(split_values(os.environ.get("WORK_NEXT_SET_ASIDE", "")))


def state(item: Item, by_number: dict[str, Item]) -> tuple[str, str]:
    """(state, why). One place decides this, so a loop and a report cannot disagree."""
    if item.done:
        return "done", f"{item.ticked}/{len(item.boxes)} boxes"
    if item.owed:
        return "owed", f"{len(item.owed_boxes)} box(es) wait for the owner or the closing check"
    unknown = [n for n in item.blocked_by if n not in by_number]
    if unknown:
        return "malformed", f"Blocked by: names no item {', '.join(unknown)}"
    unfinished = [n for n in item.blocked_by if not by_number[n].settled]
    if unfinished:
        return "blocked", f"waiting for {', '.join(unfinished)}"
    if item.number in set_aside_by_the_loop():
        return "set aside", "its session could not finish it in this run"
    if item.waits_on:
        return "waiting", f"waits on {', '.join(item.waits_on)} — a decision, not a task"
    if item.attended:
        return "attended", item.attended
    return "ready", f"{item.ticked}/{len(item.boxes)} boxes ticked"


def report(items: list[Item], by_number: dict[str, Item]) -> None:
    for item in items:
        name, why = state(item, by_number)
        print(f"  {item.number}  {name:<9} {item.title[:58]:<58} {why}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(add_help=True, description=__doc__.splitlines()[0])
    parser.add_argument("slug", nargs="?")
    parser.add_argument("--all", action="store_true", help="every item and its state")
    parser.add_argument("--json", action="store_true", help="machine-readable")
    parser.add_argument("--unattended", action="store_true",
                        help="the loop's pick: never an item marked Attended:")
    parser.add_argument("--project", type=Path, default=Path.cwd(),
                        help="a folder inside the project; the current one by default")
    parser.add_argument("--selftest", action="store_true", help="prove it still decides")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()
    if not args.slug:
        parser.error("a slug is required (or --selftest)")

    try:
        root, queue, done = queue_of(args.project)
        items = load(args.slug, queue, done)
    except Malformed as bad:
        print(f"work_next: {bad}", file=sys.stderr)
        return 2
    by_number = {item.number: item for item in items}
    states = {item.number: state(item, by_number) for item in items}

    broken = [f"{n}: {why}" for n, (name, why) in states.items() if name == "malformed"]
    if broken:
        print("work_next: " + "; ".join(broken), file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps([{"number": i.number, "path": i.path.relative_to(root).as_posix(),
                           "title": i.title, "state": states[i.number][0],
                           "why": states[i.number][1],
                           "waits_on": i.waits_on, "advances": i.advances,
                           "attended": i.attended,
                           "to_file": [{"filed": filed, "text": text}
                                       for filed, text in i.to_file],
                           "fails_first": i.fails_first,
                           "worded_wrong": [{"box": n, "why": why}
                                            for n, why in sorted(i.worded_wrong.items())],
                           "spec_questions": i.spec_questions}
                          for i in items], indent=2))
        return 0
    if args.all:
        report(items, by_number)
        return 0

    offered = ("ready",) if args.unattended else ("ready", "attended")
    ready = [i for i in items if states[i.number][0] in offered]
    if ready:
        print(ready[0].path.relative_to(root).as_posix())
        return 0

    remaining = [f"{i.number} {states[i.number][0]} ({states[i.number][1]})"
                 for i in items if states[i.number][0] not in ("done", "owed")]
    if not remaining:
        print(f"work_next: every item in {args.slug} is done or owed to a person", file=sys.stderr)
        return 1
    print("work_next: nothing ready — " + "; ".join(remaining), file=sys.stderr)
    return 1


# --------------------------------------------------------------------------- selftest

SAMPLE = """# {n}: {title}

Advances:   some-unit
Blocked by: {blocked}
Waits on:   {waits}

## Acceptance

- [{box}] `a.py` passes
{extra}"""

#: The demo queue's place: deliberately not the example's `docs/work`, so a reader that guessed
#: the usual folder instead of asking the project check finds the decoy there, not this.
DEMO_QUEUE = "plans/queue"


def _write(folder: Path, number: str, title: str, *, blocked: str = "-",
           waits: str = "-", box: str = " ", extra: str = "") -> None:
    (folder / f"{number}-{title}.md").write_text(
        SAMPLE.format(n=number, title=title, blocked=blocked, waits=waits, box=box, extra=extra))


def _quietly(argv: list[str]) -> tuple[int, str]:
    """Run main(), returning its exit code and everything it printed — inside the selftest its
    diagnostics would read as failures."""
    sink = io.StringIO()
    with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
        code = main(argv)
    return code, sink.getvalue()


def _repository(folder: Path, queue: str | None) -> Path:
    """A throwaway git repository; with `queue`, set up by the example settings file pointing
    `documents.queue` there, at the installed version."""
    folder.mkdir()
    subprocess.run(["git", "init", "-q", str(folder)], check=True, capture_output=True)
    if queue is not None:
        text = (HERE / "settings.example.md").read_text(encoding="utf-8")
        text = re.sub(r"(?m)^version = .*$",
                      f"version = {project_check.installed_version()}", text)
        text = re.sub(r"(?m)^queue = .*$", f"queue = {queue}", text)
        (folder / project_check.SETTINGS).parent.mkdir()
        (folder / project_check.SETTINGS).write_text(text, encoding="utf-8")
    return folder


def _states(project: Path, slug: str = "demo") -> dict[str, str]:
    _, queue, done = queue_of(project)
    items = load(slug, queue, done)
    by_number = {i.number: i for i in items}
    return {i.number: state(i, by_number)[0] for i in items}


def selftest() -> int:
    """Each case is one wrong answer this script would otherwise give. The demo queue lives in
    a throwaway git repository in the system's temporary folder, set up by its own settings
    file — never inside the repository this script is read from."""
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as raw:
        scratch = Path(raw).resolve()
        home = project_check.git_root(HERE)
        if isinstance(home, Path) and (scratch == home or home in scratch.parents):
            print(f"selftest FAILED — the temporary folder {scratch} is inside {home}",
                  file=sys.stderr)
            return 1
        root = _repository(scratch / "project", DEMO_QUEUE)
        project = ["--project", str(root)]
        folder = root / DEMO_QUEUE / "demo"
        folder.mkdir(parents=True)
        decoy = root / "docs/work/demo"
        decoy.mkdir(parents=True)
        _write(decoy, "01", "decoy")

        _write(folder, "01", "first", box="x")
        _write(folder, "02", "second", blocked="01")
        _write(folder, "03", "third", blocked="02")
        _write(folder, "04", "fourth", waits="P2")
        got = _states(root)
        want = {"01": "done", "02": "ready", "03": "blocked", "04": "waiting"}
        if got != want:
            failures.append(f"states: {got} != {want}")

        # Found through the project check, from a folder below the root, and printed from it.
        (root / "src").mkdir()
        code, out = _quietly(["demo", "--project", str(root / "src")])
        if (code, out.strip()) != (0, f"{DEMO_QUEUE}/demo/02-second.md"):
            failures.append(f"from a subfolder: exit {code}, {out.strip()!r} — "
                            "the queue is the project check's documents.queue, from the git root")

        # Not set up, or set up with no queue: refused (2) with the reason, never "not ready".
        bare = _repository(scratch / "bare", None)
        code, out = _quietly(["demo", "--project", str(bare)])
        if code != 2 or "/wiqrug:setup" not in out:
            failures.append(f"not set up: exit {code}, {out.strip()!r} — must refuse, naming setup")
        noqueue = _repository(scratch / "noqueue", "none")
        code, out = _quietly(["demo", "--project", str(noqueue)])
        if code != 2 or "documents.queue" not in out:
            failures.append(f"queue none: exit {code}, {out.strip()!r} — must refuse, naming it")

        (folder / "05-broken.md").write_text("# 05: broken\n\nAdvances: x\n")
        if _quietly(["demo", *project])[0] != 2:
            failures.append("a malformed item must exit 2, never be skipped")
        (folder / "05-broken.md").unlink()

        for name in ("02", "03", "04"):
            path = next(folder.glob(f"{name}-*.md"))
            path.write_text(path.read_text().replace("- [ ]", "- [x]"))
        if _quietly(["demo", *project])[0] != 1:
            failures.append("an all-done queue must exit 1")

        # Owed: a person's box and a stack box left open still unblock what follows.
        for path in folder.glob("*.md"):
            path.unlink()
        _write(folder, "01", "first", box="x",
               extra="- [ ] screenshots — **for a person to look at**\n- [~] `make check` exits 0\n")
        _write(folder, "02", "second", blocked="01")
        _write(folder, "03", "third", extra="- [ ] `b.py` passes\n")
        got = _states(root)
        if got != {"01": "owed", "02": "ready", "03": "ready"}:
            failures.append(f"owed: {got} — a person's box must unblock, a command's must not")

        # Set aside by the loop: not offered again, and what depends on it waits.
        _write(folder, "01", "first", extra="- [ ] `b.py` passes\n")
        os.environ["WORK_NEXT_SET_ASIDE"] = "01"
        try:
            items = load("demo", folder.parent)
            by_number = {i.number: i for i in items}
            got = {i.number: state(i, by_number)[0] for i in items}
            if got != {"01": "set aside", "02": "blocked", "03": "ready"} \
                    or "could not finish" not in state(by_number["01"], by_number)[1]:
                failures.append(f"set aside: {got}")
        finally:
            os.environ.pop("WORK_NEXT_SET_ASIDE", None)

        # Attended: the loop never picks it and its dependant waits; the owner is offered it.
        path = next(folder.glob("01-*.md"))
        path.write_text(path.read_text().replace(
            "Waits on:", "Attended:   the owner judges the wording\nWaits on:"))
        (folder / "03-third.md").unlink()
        items = load("demo", folder.parent)
        by_number = {i.number: i for i in items}
        got_why = {i.number: state(i, by_number) for i in items}
        if got_why != {"01": ("attended", "the owner judges the wording"),
                       "02": ("blocked", "waiting for 01")} \
                or _quietly(["demo", "--unattended", *project])[0] != 1 \
                or _quietly(["demo", *project])[0] != 0:
            failures.append(f"attended: {got_why} — offered to the loop, or kept from the owner")

        # Attended with no reason: malformed, never offered to the loop as an ordinary item.
        for blank in ("", "-", "—", "none"):
            path.write_text(re.sub(r"(?m)^Attended:.*$", f"Attended: {blank}", path.read_text()))
            if _quietly(["demo", "--unattended", *project])[0] != 2:
                failures.append(f"attended {blank!r}: not malformed — the loop would build it")
                break

        # To file: a finding waiting to be filed is not work left on the item.
        for path in folder.glob("*.md"):
            path.unlink()
        _write(folder, "01", "first", box="x",
               extra="\n## To file\n\n- [ ] G: the loop: a trap\n- [x] term: Filing — filed\n")
        _write(folder, "02", "second", blocked="01")
        items = load("demo", folder.parent)
        by_number = {i.number: i for i in items}
        got = {i.number: state(i, by_number)[0] for i in items}
        if got != {"01": "done", "02": "ready"} or len(items[0].boxes) != 1 \
                or items[0].to_file != [(False, "G: the loop: a trap"),
                                        (True, "term: Filing — filed")]:
            failures.append(f"to file: {got}, {items[0].to_file} — a To file line is not a box")

        # Fails first: the stop line is read under ## Comments only, and is not a box.
        _write(folder, "01", "first", extra=(
            "- [ ] Fails first: quoted in a box, not a stop\n\n## Comments\n\n"
            "Fails first: box 1 passed at abc1234 before any work — `a.py`. Stopped.\n"))
        items = load("demo", folder.parent)
        if items[0].fails_first != ["box 1 passed at abc1234 before any work — `a.py`. Stopped."] \
                or len(items[0].boxes) != 2:
            failures.append(f"fails first: {items[0].fails_first}, {len(items[0].boxes)} boxes")

        # Fails first, succeeded: a session's note that its boxes ran and failed is not one.
        _write(folder, "01", "first", extra=(
            "\n## Comments\n\n"
            "Fails first: boxes 1 and 2 ran and exited 1 at abc1234 before any work.\n"
            "- Fails first: box 1 exited 1 at abc1234.\n"))
        items = load("demo", folder.parent)
        if items[0].fails_first:
            failures.append(f"fails first, succeeded: {items[0].fails_first} read as a stop")

        failures += _selftest_items_name_no_files(root, folder)

    cases = 21  # one per failures.append: a count must equal the checks behind it
    for line in failures:
        print(f"selftest FAIL  {line}", file=sys.stderr)
    print(f"selftest {'FAILED' if failures else 'ok'} — "
          f"{cases - len(failures)}/{cases} cases", file=sys.stderr if failures else sys.stdout)
    return 1 if failures else 0


def _selftest_items_name_no_files(root: Path, folder: Path) -> list[str]:
    """The item format with no `Touches:`, no done box and no person's box, and the three
    Comments lines that settle a box. The example settings' done command is `make check`."""
    failures: list[str] = []
    for path in folder.glob("*.md"):
        path.unlink()
    project = ["--project", str(root)]

    # Touches: is ignored, not required: an item without it is sound, and an older one — its
    # paths running on over indented lines — is read past, never as boxes or compared.
    _write(folder, "01", "first")
    (folder / "02-second.md").write_text(
        "# 02: second\n\nAdvances:   some-unit\nTouches:    a.py\n            b.py\n\n"
        "## Acceptance\n\n- [ ] `b.py` passes\n")
    (folder / "03-third.md").write_text(
        "# 03: third\n\nAdvances:   some-unit\nTouches:    a.py\n\n"
        "## Acceptance\n\n- [ ] `c.py` passes\n")
    code, out = _quietly(["demo", "--all", *project])
    if code != 0 or "shared paths" in out \
            or len(load("demo", folder.parent)[1].boxes) != 1:
        failures.append(f"touches: exit {code} — an item without Touches: must be sound, and "
                        "an older one's read past, never compared")
    (folder / "03-third.md").unlink()

    # A box worded wrong is owed: the item settles, and its dependant is offered.
    _write(folder, "01", "first", box="x", extra=(
        "- [ ] `c.py` passes\n\n## Comments\n\n"
        "Box 2 worded wrong: c.py passed before any work; it should name the new case.\n"))
    _write(folder, "02", "second", blocked="01")
    if _states(root) != {"01": "owed", "02": "ready"} \
            or 2 not in load("demo", folder.parent)[0].worded_wrong:
        failures.append(f"worded wrong: {_states(root)} — a box worded wrong must be owed")

    # An older queue's done box is owed once something is built, never before; the box the loop
    # adds when the code gate fails names the command too, and is a command's to close.
    _write(folder, "01", "first", box="x", extra="- [ ] `make check` exits 0\n")
    if _states(root)["01"] != "owed":
        failures.append("done box: an older queue's open done box must be owed")
    (folder / "01-first.md").write_text(
        "# 01: first\n\nAdvances:   some-unit\n\n## Acceptance\n\n"
        "- [ ] screenshots — **for a person to look at**\n- [ ] `make check` exits 0\n")
    if _states(root)["01"] == "owed":
        failures.append("done box: an unbuilt item with a done box was read as owed")
    _write(folder, "01", "first", box="x", extra=(
        f"- [ ] {GATE_BOX} at this item's last commit: `make check` exits 0 — it exited 1\n"))
    if _states(root)["01"] != "ready":
        failures.append("gate box: the loop's code-gate box was read as owed")

    # A spec question and a box ticked on earlier work's evidence are read, and neither holds
    # the item open nor stops it.
    _write(folder, "01", "first", box="x", extra=(
        "\n## Comments\n\n"
        "Fails first: box 1 passed at abc1234 before any work — delivered by 03: its test. Ticked.\n"
        "Spec question: should a blank price read as removed?\n"))
    first = load("demo", folder.parent)[0]
    if first.spec_questions != ["should a blank price read as removed?"] \
            or not first.fails_first or _states(root)["01"] != "done":
        failures.append(f"comments: {first.spec_questions}, {first.fails_first}")

    # A wrapped box is one box: "for a person" on its continuation line makes it a person's.
    _write(folder, "01", "first", box="x", extra=(
        "- [ ] the screen reads right, following the steps below —\n"
        "  **for a person**\n- [~] `make check` exits 0, what the copy cannot reach\n"
        "  unchecked\n"))
    first = load("demo", folder.parent)[0]
    if _states(root)["01"] != "owed" or len(first.boxes) != 3 \
            or not first.boxes[1][1].endswith("**for a person**") \
            or first.stack_owed != {first.boxes[2][1]}:
        failures.append(f"wrapped box: {[t for _, t in first.boxes]} — read as its first line")

    # A box worded wrong does not excuse a box a command should close.
    _write(folder, "01", "first", extra=(
        "- [ ] `c.py` passes\n\n## Comments\n\nBox 2 worded wrong: it passed first.\n"))
    if _states(root)["01"] != "ready":
        failures.append("worded wrong: box 1, a command's, was excused too")
    return failures


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
