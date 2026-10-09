#!/usr/bin/env python3
"""afk_watch.py — follow an unattended run as it happens, in words a person can read.

    python3 ${CLAUDE_PLUGIN_ROOT}/lib/afk_watch.py <slug> [--project FOLDER]   # the newest run
    python3 ${CLAUDE_PLUGIN_ROOT}/lib/afk_watch.py <slug> --all        # replay it from the start
    python3 ${CLAUDE_PLUGIN_ROOT}/lib/afk_watch.py --selftest

The run's logs are under `logs/afk/<slug>/` at the git root of the project `--project` names —
the current folder by default; `afk.sh` prints the command with it, so it pastes anywhere.

WHY. `afk.sh` runs in the background, and what it leaves while it runs is two kinds of file:
`console.log`, the loop's own one line per step, and one `<item>.jsonl` per session — every
event of a `claude -p` run, one JSON object a line, which nobody can read as it scrolls. This
prints both as they grow: the loop's lines, and for the session what it says, each tool it
runs, what failed, and how the item ended.

Watching changes nothing. Ctrl-C stops the watching, never the run; `kill $(cat <logs>/pid)`
is how a run is stopped. When the run ends this says where its report is and exits.

Exit codes: 0 the run ended, or the watch was stopped · 2 there is no such run.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Importing the neighbour would leave a __pycache__ in the plugin, holding this machine's paths.
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE))
import project_check  # noqa: E402  — finds the project's git root, as every wiqrug script does

#: Replayed from the current item when the watch starts mid-run, so it opens on context.
TAIL_EVENTS = 12
WIDTH = 160


@dataclass
class Followed:
    """One growing file, read from where the last poll stopped."""

    path: Path
    offset: int = 0
    partial: str = ""

    def new_lines(self) -> list[str]:
        try:
            with self.path.open(encoding="utf-8", errors="replace") as handle:
                handle.seek(self.offset)
                chunk = handle.read()
                self.offset = handle.tell()
        except OSError:
            return []
        # ⚠️ A line is only complete once its newline is written. A poll that lands mid-write
        # keeps the fragment and finishes it next time, rather than failing to parse half a line.
        text = self.partial + chunk
        lines = text.split("\n")
        self.partial = lines.pop()
        return lines


@dataclass
class Watch:
    logs: Path
    replay: bool
    console: Followed | None = None
    sessions: dict[str, Followed] = field(default_factory=dict)


def clip(text: str, width: int = WIDTH) -> str:
    text = " ".join(text.split())
    return text if len(text) <= width else text[: width - 1] + "…"


def tool_line(name: str, given: dict) -> str:
    """One line per tool call: what a person would say the session is doing."""
    what = (given.get("description") or given.get("command") or given.get("file_path")
            or given.get("skill") or given.get("pattern") or given.get("prompt") or "")
    return f"  →  {name:<6} {clip(str(what), WIDTH - 12)}"


def render(event: dict) -> list[str]:
    """Lines for one stream-json event. Most events say nothing a person needs."""
    kind = event.get("type")
    nested = "  " if event.get("parent_tool_use_id") else ""
    out: list[str] = []
    if kind == "assistant":
        for part in event.get("message", {}).get("content", []) or []:
            if not isinstance(part, dict):
                continue
            if part.get("type") == "text" and str(part.get("text", "")).strip():
                lines = [line for line in str(part["text"]).splitlines() if line.strip()]
                out.append(f"  💬 {clip(lines[0], WIDTH - 6)}")
                out += [f"     {clip(line, WIDTH - 6)}" for line in lines[1:4]]
                if len(lines) > 4:
                    out.append(f"     … {len(lines) - 4} more line(s)")
            elif part.get("type") == "tool_use":
                out.append(tool_line(str(part.get("name", "?")), part.get("input") or {}))
    elif kind == "user":
        content = event.get("message", {}).get("content", [])
        for part in content if isinstance(content, list) else []:
            if isinstance(part, dict) and part.get("type") == "tool_result" and part.get("is_error"):
                body = part.get("content")
                if isinstance(body, list):
                    body = " ".join(str(b.get("text", "")) for b in body if isinstance(b, dict))
                out.append(f"  ✗  {clip(str(body or 'a tool failed'), WIDTH - 6)}")
    elif kind == "system" and event.get("subtype") == "api_retry":
        out.append(f"  …  the API asked to retry ({event.get('error', 'unknown')})")
    elif kind == "result":
        minutes = (event.get("duration_ms") or 0) / 60000
        out.append(f"  ■  session ended: {event.get('subtype', '?')} · {event.get('num_turns', '?')} turns"
                   f" · {minutes:.1f} min · ${event.get('total_cost_usd') or 0:.2f}")
    return [nested + line for line in out]


def parse(line: str) -> dict | None:
    line = line.strip()
    if not line:
        return None
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        return None
    return event if isinstance(event, dict) else None


def newest_run(tree: Path, slug: str) -> Path | None:
    root = tree / "logs/afk" / slug
    runs = sorted(path for path in root.glob("*T*Z") if path.is_dir()) if root.is_dir() else []
    return runs[-1] if runs else None


def running(logs: Path) -> bool:
    """Whether the loop's own process is still alive. No pid file yet means it is starting."""
    try:
        pid = int((logs / "pid").read_text().strip())
    except (OSError, ValueError):
        return not (logs / "report.md").exists()
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def poll(watch: Watch, first: bool) -> None:
    stamp = time.strftime("%H:%M:%S")
    if watch.console is None and (watch.logs / "console.log").exists():
        watch.console = Followed(watch.logs / "console.log")
    if watch.console:
        for line in watch.console.new_lines():
            if line.strip():
                print(f"{stamp} afk │ {line.rstrip()}")

    # One session at a time, each under its own header: a new file is announced just before
    # its first lines, so a replay never prints two headers and then both sessions' lines.
    for path in sorted(watch.logs.glob("*.jsonl")):
        if path.name == "run.jsonl":
            continue
        name = path.name
        if name not in watch.sessions:
            watch.sessions[name] = Followed(path)
            print(f"{stamp} ─── session for {path.stem} ───")
        followed = watch.sessions[name]
        rendered = [text for line in followed.new_lines()
                    if (event := parse(line)) for text in render(event)]
        # Opening mid-run: the current session's last few lines, not its whole history.
        if first and not watch.replay and len(rendered) > TAIL_EVENTS:
            print(f"{stamp}   … {len(rendered) - TAIL_EVENTS} earlier line(s) of {Path(name).stem}"
                  " — --all replays them")
            rendered = rendered[-TAIL_EVENTS:]
        for text in rendered:
            print(f"{stamp} {text}")
    sys.stdout.flush()


def follow(tree: Path, slug: str, replay: bool, interval: float) -> int:
    logs = newest_run(tree, slug)
    waited = 0.0
    while logs is None and waited < 30:          # watching the moment afk.sh was started
        time.sleep(1)
        waited += 1
        logs = newest_run(tree, slug)
    if logs is None:
        print(f"afk_watch: no run of {slug} under {tree / 'logs/afk' / slug}", file=sys.stderr)
        return 2

    print(f"watching {logs.relative_to(tree)} — Ctrl-C stops the watching, not the run")
    watch = Watch(logs=logs, replay=replay)
    poll(watch, first=True)
    try:
        while running(logs):
            time.sleep(interval)
            poll(watch, first=False)
        time.sleep(interval)
        poll(watch, first=False)
    except KeyboardInterrupt:
        print("\nstopped watching; the run goes on")
        return 0
    report = logs / "report.md"
    print(f"\nthe run has ended. Report: {report if report.exists() else '(none written — read console.log)'}")
    return 0


# --------------------------------------------------------------------------- selftest
def selftest() -> int:
    """The shapes the first real runs produced, rendered; and a line split mid-write."""
    import tempfile

    failures = []
    said = render({"type": "assistant", "message": {"content": [
        {"type": "text", "text": "Item 01 is built.\nline two"},
        {"type": "tool_use", "name": "Bash", "input": {"command": "x", "description": "Run the suite"}}]}})
    if not (said and "Item 01 is built." in said[0] and "Run the suite" in said[-1]):
        failures.append(f"assistant text and a tool call: {said}")
    failed = render({"type": "user", "message": {"content": [
        {"type": "tool_result", "is_error": True, "content": "Exit code 1\nboom"}]}})
    if not (failed and "Exit code 1" in failed[0]):
        failures.append(f"a failed tool: {failed}")
    if render({"type": "user", "message": {"content": [{"type": "tool_result", "content": "ok"}]}}):
        failures.append("a successful tool result was printed")
    ended = render({"type": "result", "subtype": "success", "num_turns": 56,
                    "duration_ms": 1316145, "total_cost_usd": 4.827})
    if not (ended and "56 turns" in ended[0] and "21.9 min" in ended[0] and "$4.83" in ended[0]):
        failures.append(f"the session's end: {ended}")
    if render({"type": "system", "subtype": "hook_started"}):
        failures.append("a hook event was printed")

    with tempfile.TemporaryDirectory() as raw:
        path = Path(raw) / "01-x.jsonl"
        path.write_text('{"type": "result", "subt')
        followed = Followed(path)
        if followed.new_lines():
            failures.append("half a line was handed on")
        with path.open("a") as handle:
            handle.write('ype": "success"}\n')
        lines = followed.new_lines()
        if len(lines) != 1 or parse(lines[0]) != {"type": "result", "subtype": "success"}:
            failures.append(f"a line finished on the next poll did not parse: {lines}")

    for line in failures:
        print(f"selftest FAIL  {line}", file=sys.stderr)
    print(f"selftest {'FAILED' if failures else 'ok'} — 7 checks")
    return 1 if failures else 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("slug", nargs="?")
    parser.add_argument("--all", action="store_true", help="replay the current session from its start")
    parser.add_argument("--interval", type=float, default=1.0, help="seconds between polls [1]")
    parser.add_argument("--project", type=Path, default=Path.cwd(),
                        help="a folder inside the project; the current one by default")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)
    if args.selftest:
        return selftest()
    if not args.slug:
        parser.error("a slug is required (or --selftest)")
    tree = project_check.git_root(args.project.resolve())
    if isinstance(tree, project_check.Answer):
        print(tree.message, file=sys.stderr)
        return 2
    return follow(tree, args.slug, args.all, args.interval)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
