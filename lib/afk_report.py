#!/usr/bin/env python3
"""afk_report.py — what a run of the loop did, in one file a person can read.

WHY. A finished run leaves four things behind: a branch, a set of ticked boxes, a folder
of JSONL transcripts and a spent budget. Three of those are unreadable, and the fourth is
only meaningful next to the other three. Coming back to that a day later — or opening a
fresh session that was not there — means re-deriving the run from its own exhaust.

So the run renders its own answer, in three parts: what was BUILT, REVIEWED AND PROVED; what is
FOR YOU TO CHECK — each screen's browser steps, what the code gate could not verify, and what
waits on a running copy of the project after the merge; and the SPEC QUESTIONS — boxes worded
wrong, and review findings that were gaps in the spec. The second decides what you go and test;
the third, what you have to decide.

    python3 ${CLAUDE_PLUGIN_ROOT}/lib/afk_report.py <slug> --logs <root>/logs/afk/<slug>/<stamp>
    python3 ${CLAUDE_PLUGIN_ROOT}/lib/afk_report.py <slug> --worktree ~/afk/<slug>
    python3 ${CLAUDE_PLUGIN_ROOT}/lib/afk_report.py --selftest

The queue is found through the project check, for the project the `--worktree` (the current
folder by default) is a copy of. It reads an unattended run's `run.jsonl` when there is one, and
degrades honestly when there is not: after an interactive `/wiqrug:implement` there is no
per-item SHA record, so the commits are listed unattributed and the report says that is what
happened. "The done command" is the project's `done.command`, which the run's first row names.

Exit codes: 0 the report was written · 2 the queue could not be read.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Importing the neighbour would leave a __pycache__ in the plugin, holding this machine's paths.
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE))

import work_next  # noqa: E402 — the path insert above is what makes it importable

AXES = (("standards", "Standards"), ("spec", "Spec"))
VERDICTS = ("confirmed", "refuted", "unchecked")
#: An item's fix session has a fourth verdict: the finding is a gap in the spec, not code.
SPEC_QUESTION = "spec question"
FIX_VERDICTS = VERDICTS + (SPEC_QUESTION,)


@dataclass
class Session:
    """One item's `claude -p` run, read back from what it left behind."""

    item: str = ""
    status: str = ""
    before: str = ""
    after: str = ""
    cost: float = 0.0
    log: str = ""
    turns: int = 0
    limited: int = 0
    final: str = ""
    commits: list[str] = field(default_factory=list)
    session_id: str = ""
    peak: int | None = None         # None is unknown, never 0: see read_peak
    peak_why: str = ""
    review: dict = field(default_factory=dict)  # its `item-review` row, with the words


def run_git(tree: Path, *args: str) -> str:
    """git, or an empty string. A report that cannot read git still has to render."""
    try:
        done = subprocess.run(["git", "-C", str(tree), *args],
                              capture_output=True, text=True, check=False, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return ""
    return done.stdout.strip() if done.returncode == 0 else ""


def read_transcript(path: Path) -> tuple[str, int, int, str]:
    """(final text, turns, rate-limit retries, session id) from one stream-json log.

    ⚠️ Every line is tried and a bad one is skipped: a session killed mid-write leaves a
    truncated last line, and a report that dies on it reports nothing about a run that
    may have done most of its work.
    """
    final, turns, limited, session_id = "", 0, 0, ""
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(event, dict):
                    continue
                if not session_id and isinstance(event.get("session_id"), str):
                    session_id = event["session_id"]
                if event.get("subtype") == "api_retry" and event.get("error") == "rate_limit":
                    limited += 1
                if event.get("type") == "result":
                    turns = event.get("num_turns") or turns
                    text = event.get("result")
                    if isinstance(text, str) and text.strip():
                        final = text.strip()
    except OSError:
        pass
    return final, turns, limited, session_id


#: Where an item should finish, in tokens of context — `/wiqrug:to-tickets` sizes items to it.
PEAK_LIMIT = 150_000


def session_log(tree: Path, session_id: str) -> Path:
    """Claude Code's own log of one session: under `~/.claude/projects/` (or
    `$CLAUDE_CONFIG_DIR/projects/`), in a folder named after the directory the session ran
    in, every character that is not a letter or a digit turned into a dash."""
    home = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
    return home / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(tree)) / f"{session_id}.jsonl"


def read_peak(path: Path) -> tuple[int | None, str]:
    """(peak context, why it is unknown) from one session's own log.

    Context is what one API call held: input + cache-creation + cache-read tokens. A
    subagent's calls (`isSidechain`) are its own window, and a `<synthetic>` record is not a
    call, so neither counts. ⚠️ A log that cannot be read, or holds no call, is None with the
    reason — never 0, which would read as an item that fitted with room to spare.
    """
    peak = 0
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(record, dict) or record.get("type") != "assistant" \
                        or record.get("isSidechain"):
                    continue
                message = record.get("message")
                if not isinstance(message, dict) or message.get("model") == "<synthetic>":
                    continue
                usage = message.get("usage")
                if not isinstance(usage, dict):
                    continue
                peak = max(peak, sum(int(usage.get(key) or 0) for key in (
                    "input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")))
    except FileNotFoundError:
        return None, f"no session log at `{path}`"
    except (OSError, ValueError, TypeError) as exc:
        return None, f"`{path}` could not be read: {exc}"
    if not peak:
        return None, f"`{path}` records no API call"
    return peak, ""


def peak_text(session: Session) -> str:
    """The item's peak, for its line under `## Per item`."""
    if session.peak is None:
        return f"peak context **unknown** — {session.peak_why or 'no transcript recorded'}"
    over = f" ⚠️ over {PEAK_LIMIT // 1000}k" if session.peak > PEAK_LIMIT else ""
    return f"peak context {session.peak:,} tokens{over}"


def read_meta(logs: Path) -> dict:
    """The run's settings, written as `run.jsonl`'s first line by `afk.sh`.

    Which model and which effort produced a branch is not recoverable from the branch,
    and it is the first thing a reader asks when the work is worse than expected.
    """
    try:
        for line in (logs / "run.jsonl").read_text(errors="replace").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if isinstance(row, dict) and row.get("kind") == "meta":
                return row
            break
    except (OSError, json.JSONDecodeError):
        pass
    return {}


def read_tip(logs: Path) -> dict:
    """The last `tip` row: the done command at the branch's tip, written as the run ends.

    Absent after an interactive run, or a run that built nothing — and then the report
    says the tip was not checked, never that it passed.
    """
    tip: dict = {}
    try:
        lines = (logs / "run.jsonl").read_text(errors="replace").splitlines()
    except OSError:
        return tip
    for line in lines:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict) and row.get("kind") == "tip":
            tip = row
    return tip


def read_review(logs: Path) -> dict:
    """The last `review` row, with the reviewer's own words under `text` when it wrote any.

    Absent after an interactive run and after a run older than the review — and then the
    report says nobody reviewed the branch, never that it is clean.
    """
    review: dict = {}
    try:
        lines = (logs / "run.jsonl").read_text(errors="replace").splitlines()
    except OSError:
        return review
    for line in lines:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict) and row.get("kind") == "review":
            review = row
    if review.get("status") == "reviewed":
        try:
            review["text"] = (logs / "review.md").read_text(errors="replace").strip()
        except OSError:
            review["text"] = ""
    if review.get("check") == "checked":
        try:
            review["check_text"] = (logs / "check.md").read_text(errors="replace")
        except OSError:
            review["check_text"] = ""
    return review


@dataclass
class Finding:
    """One reviewer finding, with the verdict the check gave it — after the rule below."""

    text: str
    verdict: str
    evidence: str = ""
    demoted: bool = False           # the check said "refuted" and gave no evidence


@dataclass
class Axis:
    """One axis of the review, as the check returned it. `ran` False: the review skipped it."""

    title: str
    ran: bool = True
    note: str = ""
    findings: list[Finding] = field(default_factory=list)
    missing: bool = False           # the check's answer had nothing at all for this axis


def parse_check(text: str) -> dict | None:
    """The last ```json block of the check session's answer, or None when there is none.

    None is not "no findings": it is an answer nobody could read, and the report says so.
    """
    blocks = re.findall(r"```json\s*\n(.*?)```", text, flags=re.DOTALL)
    for block in reversed(blocks):
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data
    return None


def checked_axes(data: dict, allowed: tuple[str, ...] = VERDICTS) -> list[Axis]:
    """Standards then Spec, each finding with one of VERDICTS — the decision the report shows.

    ⚠️ "refuted" stands only with evidence — a command and its output, or quoted lines. A
    refuted finding with none is shown as unchecked: a claim dismissed on nobody's evidence is
    exactly as unverified as one nobody looked at, and a reader would otherwise skip it. Any
    verdict that is not one of the three is unchecked for the same reason.
    """
    axes = []
    for key, title in AXES:
        raw = data.get(key)
        if not isinstance(raw, dict):
            axes.append(Axis(title, missing=True))
            continue
        axis = Axis(title, ran=raw.get("ran") is not False, note=str(raw.get("note") or ""))
        for row in raw.get("findings") or []:
            if not isinstance(row, dict):
                continue
            verdict = str(row.get("verdict") or "").strip().lower()
            evidence = str(row.get("evidence") or "").strip()
            demoted = verdict == "refuted" and not evidence
            if demoted or verdict not in allowed:
                verdict = "unchecked"
            axis.findings.append(Finding(str(row.get("finding") or "").strip(), verdict,
                                         evidence, demoted))
        axes.append(axis)
    return axes


#: The reviewers' own totals, the last lines of `/wiqrug:review-change`'s report.
REVIEW_TOTAL = re.compile(r"^\W*(Standards|Spec)\W*:\s*(\d+)\s+findings?\b", re.MULTILINE)


def review_totals(text: str) -> dict[str, int]:
    """{axis title: the count its reviewer wrote}. An axis with no total line is absent."""
    return {axis: int(count) for axis, count in REVIEW_TOTAL.findall(text)}


def total_mismatch(axis: Axis, totals: dict[str, int]) -> list[str]:
    """A line when the check returned a different number of findings than the reviewer wrote.

    ⚠️ The report's list is the check's transcription; a finding it dropped or merged would
    otherwise vanish from the count with nothing to say so.
    """
    wrote = totals.get(axis.title)
    if axis.missing or not axis.ran or wrote is None or wrote == len(axis.findings):
        return []
    return [f"⚠️ **Count mismatch:** the {axis.title} reviewer wrote {wrote} finding(s) in "
            f"`review.md`; the check returned {len(axis.findings)}. Read `review.md` for the "
            "difference.", ""]


def axis_lines(axis: Axis, level: str = "###") -> list[str]:
    """One axis: a heading with its verdict counts, then every finding with its verdict. A
    `spec question` count shows only where a fix session gave one."""
    if axis.missing:
        return [f"{level} {axis.title} — the check returned nothing for this axis; read "
                "`review.md`", ""]
    if not axis.ran:
        return [f"{level} {axis.title} — not run: {axis.note or 'no reason given'}", ""]
    shown = VERDICTS + ((SPEC_QUESTION,) if any(f.verdict == SPEC_QUESTION
                                                  for f in axis.findings) else ())
    counts = " · ".join(f"{sum(f.verdict == v for f in axis.findings)} {v}" for v in shown)
    out = [f"{level} {axis.title} — {len(axis.findings)} finding(s): {counts}", ""]
    for number, finding in enumerate(axis.findings, 1):
        lines = finding.text.splitlines() or ["(the check copied no text)"]
        out.append(f"{number}. **{finding.verdict}**"
                   + (" (marked refuted with no evidence)" if finding.demoted else "")
                   + f" — {lines[0]}")
        out += [f"   {line}" for line in lines[1:]]
        if finding.evidence:
            out += ["   Evidence:"] + [f"   > {line}" for line in finding.evidence.splitlines()]
    return out + [""]


def read_item_reviews(logs: Path) -> dict[str, dict]:
    """{item path: its `item-review` row}, with the review's words under `text` and the fix
    session's answer under `fix_text`. The last row per item wins: one item, one review."""
    rows: dict[str, dict] = {}
    try:
        lines = (logs / "run.jsonl").read_text(errors="replace").splitlines()
    except OSError:
        return rows
    for line in lines:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict) and row.get("kind") == "item-review" and row.get("item"):
            rows[str(row["item"])] = row
    for item, row in rows.items():
        stem = logs / Path(item).stem
        for key, suffix in (("text", ".review.md"), ("fix_text", ".fix.md")):
            try:
                row[key] = Path(f"{stem}{suffix}").read_text(errors="replace").strip()
            except OSError:
                row[key] = ""
    return rows


def fix_axes(review: dict) -> list[Axis] | None:
    """The fix session's verdicts, or None when it gave none anybody could read."""
    if review.get("fix") != "fixed":
        return None
    data = parse_check(review.get("fix_text", ""))
    return None if data is None else checked_axes(data, FIX_VERDICTS)


def review_summary(review: dict) -> str:
    """One line on an item's own review. ⚠️ No row is "not reviewed", never "clean"."""
    if not review:
        return "**not reviewed** — this run recorded no review of it"
    if review.get("status") != "reviewed":
        return f"**not reviewed** — {review.get('why') or 'no reason recorded'}"
    axes = fix_axes(review)
    if axes is None:
        why = review.get("fix_why") or "its answer held no readable ```json block"
        return f"reviewed; the findings were **not checked or fixed** — {why}"
    findings = [f for axis in axes for f in axis.findings]
    if not findings and not sum(review_totals(review.get("text", "")).values()):
        return "reviewed: no finding"
    counts = {v: sum(f.verdict == v for f in findings) for v in FIX_VERDICTS}
    totals = review_totals(review.get("text", ""))
    wrote = sum(totals.values())
    mismatch = (f" · ⚠️ its reviewers wrote {wrote}, the fix answered for {len(findings)}"
                if totals and wrote != len(findings) else "")
    return (f"reviewed: {len(findings)} finding(s) — {counts['confirmed']} confirmed, the "
            f"fix's commit in its evidence · {counts['refuted']} refuted · "
            f"{counts[SPEC_QUESTION]} spec question(s) · {counts['unchecked']} unchecked"
            + mismatch)


def read_gates(logs: Path | None) -> dict[str, dict]:
    """{item path: its last `gate` row} — the code gate, the project's done command at the
    item's last commit. The last row wins: the gate runs again after the review's fixes."""
    gates: dict[str, dict] = {}
    if logs is None:
        return gates
    try:
        lines = (logs / "run.jsonl").read_text(errors="replace").splitlines()
    except OSError:
        return gates
    for line in lines:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict) and row.get("kind") == "gate" and row.get("item"):
            gates[str(row["item"])] = row
    return gates


def gate_summary(logs: Path | None, item: str) -> str:
    """How the code gate judged the item. ⚠️ No gate row is said, never read as a pass."""
    row = read_gates(logs).get(item)
    if row is None:
        why = ("the project's done command is `none`" if logs is not None
               and read_meta(logs) and not read_meta(logs).get("done")
               else "this run recorded none")
        return f"**no code gate ran** — {why}"
    if row.get("rc") == 0:
        return "code gate passed"
    return "code gate passed — with what it could not verify, below" if gate_lines(logs, item) \
        else f"**code gate failed** (exit {row.get('rc')})"


def gate_lines(logs: Path | None, item: str) -> list[str]:
    """What the code gate could not verify at the item's last commit: the done command exited
    `done.owed-exit` — every check it could run passed, and the rest needs a running copy."""
    row = read_gates(logs).get(item)
    owed = read_meta(logs).get("owed_exit") if logs is not None else None
    if row is None or owed is None or row.get("rc") != owed:
        return []
    return [f"the done command exited {owed}: every check it could run passed; {OWED} — "
            f"its log: `{row.get('log', '')}`"]


def read_filing(logs: Path) -> dict:
    """The last `filing` row: the closing-check session `afk.sh` runs after the last item.

    Absent after an interactive run and after a run older than the step — and then the report
    says no filing session ran, never that the findings were filed.
    """
    filing: dict = {}
    try:
        lines = (logs / "run.jsonl").read_text(errors="replace").splitlines()
    except OSError:
        return filing
    for line in lines:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict) and row.get("kind") == "filing":
            filing = row
    return filing


def filed_section(slug: str, items: list[work_next.Item], filing: dict) -> list[str]:
    """`## Filed`: every `## To file` line in the queue — filed, or not and why.

    ⚠️ A ticked line is filed because the item file says so; nothing here checks the knowledge
    base. An unticked one is the report's to explain, because a finding that silently stays
    in an item file is archived with it and never read again.
    """
    lines = [(item, filed, text) for item in items for filed, text in item.to_file]
    if not lines and not filing:
        return []
    out = ["## Filed", ""]
    status, why = filing.get("status", ""), filing.get("why", "")
    if status == "filed":
        out += [f"One session of `/wiqrug:update-knowledge {slug}` filed the run's findings after "
                "the last item" + (f" · ${float(filing.get('cost') or 0):.2f}" if filing.get("cost") else "")
                + (f" · `{filing['log']}`" if filing.get("log") else "") + ".", ""]
    elif status in ("skipped", "failed"):
        out += [f"**No findings filed by this run** — {why}.", ""]
    elif status == "none":
        out += ["No `## To file` line was open, so no filing session ran.", ""]
    else:
        out += ["No filing session is recorded for this run.", ""]
    filed = [(item, text) for item, done, text in lines if done]
    left = [(item, text) for item, done, text in lines if not done]
    for item, text in filed:
        out.append(f"- [x] **{item.number}** {text}")
    if filed:
        out.append("")
    if left:
        reason = {"filed": "the filing session left it unticked — read its log",
                  "skipped": why, "failed": why}.get(status) \
            or f"no filing session ran — run `/wiqrug:update-knowledge {slug}`"
        out += ["Not filed:", ""]
        out += [f"- [ ] **{item.number}** {text} — {reason}" for item, text in left]
        out.append("")
    return out


def review_section(review: dict, logs: Path | None) -> list[str]:
    """The review, as the first section: each axis apart, every finding with its verdict.

    ⚠️ A branch nobody reviewed says so in the same place a review would stand. A report
    that simply lacks the section reads as one whose review found nothing. And a review whose
    findings were not checked is printed verbatim under a line that says so — never as
    verdicts nobody gave.
    """
    if logs is None:
        return []
    out = ["### What the branch reviewer found", ""]
    text = review.get("text", "") if review.get("status") == "reviewed" else ""
    if not text:
        why = review.get("why") or "this run recorded no review"
        out += [f"**Not reviewed** — {why}. Nobody but the sessions that built it has read "
                "this diff.", ""]
        if review.get("log"):
            out += [f"Log: `{review['log']}`", ""]
        return out
    data = parse_check(review.get("check_text", "")) if review.get("check") == "checked" else None
    if data is not None:
        out += ["`/wiqrug:review-change` read the whole diff after the last item: a Standards and a "
                "Spec reviewer, neither of which wrote any of it. One more session then checked "
                "each finding — *refuted* only with evidence, otherwise *unchecked*. The two "
                "axes are shown apart, never merged or re-ranked. The reviewers' own words are "
                "in `review.md`, beside this report.", ""]
        totals = review_totals(text)
        for axis in checked_axes(data):
            out += axis_lines(axis, "####") + total_mismatch(axis, totals)
        return out
    why = review.get("check_why") or (
        "its answer held no readable ```json block" if review.get("check") == "checked"
        else "this run recorded no check")
    out += [f"The findings were **not checked** — {why}. Every one of them is unchecked: a "
            "claim nobody verified. The reviewers' words, verbatim:", ""]
    # Its headings are demoted two levels, so they sit under this one.
    out += [("##" + line) if line.startswith("#") else line for line in text.splitlines()]
    if review.get("check_log"):
        out += ["", f"Check log: `{review['check_log']}`"]
    return out + [""]


def done_name(meta: dict) -> str:
    """How the report names the done command: by its own words when the run recorded them."""
    return f"the done command (`{meta['done']}`)" if meta.get("done") else "the done command"


def tip_line(tip: dict, logs: Path | None, meta: dict | None = None) -> str:
    """One line on the branch a person is about to be handed. Blank when there is no run."""
    if logs is None:
        return ""
    meta = meta or {}
    done = done_name(meta)
    if not tip:
        return f"Branch tip: **not checked** — {done} was not run at the end of this run."
    head, rc = str(tip.get("head", ""))[:12], tip.get("rc")
    if rc == 0:
        return f"Branch tip `{head}`: {done} exit 0."
    if rc is not None and rc == meta.get("owed_exit"):
        return (f"Branch tip `{head}`: {done} exit {rc} — every check it could run passed; "
                f"{OWED}.")
    return (f"⚠️ **Branch tip `{head}` FAILS {done}** (exit {rc}) — read "
            f"`{tip.get('log', '')}` before anything else.")


def evidence(logs: Path | None, item: str) -> tuple[Path | None, int, int]:
    """(folder, screenshots, scripts) the loop copied out of the item's /tmp scratch."""
    if logs is None:
        return None, 0, 0
    folder = logs / Path(item).stem / "evidence"
    if not folder.is_dir():
        return None, 0, 0
    files = [path for path in folder.rglob("*") if path.is_file()]
    shots = sum(path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"} for path in files)
    return folder, shots, len(files) - shots


def evidence_line(logs: Path | None, item: str) -> str:
    folder, shots, scripts = evidence(logs, item)
    if folder is None:
        return ""
    return f"evidence: `{folder}` — {shots} screenshot(s), {scripts} script(s)"


def read_run(logs: Path) -> list[Session]:
    """The per-item record `afk.sh` writes. Absent after an interactive run."""
    sessions: list[Session] = []
    record = logs / "run.jsonl"
    if not record.is_file():
        return sessions
    try:
        lines = record.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return sessions
    for line in lines:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        # Only an item's own row: a `kind` row (meta, tip, review, an item's review) is not one,
        # though an `item-review` row names its item too.
        if not isinstance(row, dict) or "item" not in row or "kind" in row:
            continue
        sessions.append(Session(item=str(row.get("item", "")),
                                status=str(row.get("status", "")),
                                before=str(row.get("before", "")),
                                after=str(row.get("after", "")),
                                cost=float(row.get("cost") or 0.0),
                                log=str(row.get("log", ""))))
    return sessions


def enrich(sessions: list[Session], logs: Path, tree: Path) -> None:
    """Attach each session's own final report and the commits it actually made."""
    for session in sessions:
        if session.log:
            path = Path(session.log)
            if not path.is_absolute():
                path = logs / path
            session.final, session.turns, session.limited, session.session_id = \
                read_transcript(path)
        if session.session_id:
            session.peak, session.peak_why = read_peak(session_log(tree, session.session_id))
        elif session.log:
            session.peak_why = "its transcript names no session id"
        if session.before and session.after and session.before != session.after:
            span = run_git(tree, "log", "--oneline", "--no-decorate",
                           f"{session.before}..{session.after}")
            session.commits = [line for line in span.splitlines() if line.strip()]


def not_proved_lines(final: str) -> list[str]:
    """The session's own `NOT proved` lines, verbatim.

    Never matched against a box: the box text and the report text are written by two
    different hands, and a fuzzy match that pairs the wrong ones is worse than showing
    both and letting a reader pair them.
    """
    return [line.strip() for line in final.splitlines()
            if line.strip().lower().startswith("not proved")]


def attempted(items: list[work_next.Item], sessions: list[Session]) -> set[str]:
    """Which items a session actually worked on.

    ⚠️ An item nobody attempted is NOT part of the review list. Listing its boxes as
    "what needs you" sends a reader to test work that was never built — which is the
    same confident-wrong-number failure as rendering an uncomputed price as zero.

    With a `run.jsonl` this is recorded fact. Without one — an interactive run — the
    only honest signal in the files is that something was proved on the item at all.
    """
    if sessions:
        return {Path(session.item).name[:2] for session in sessions}
    return {item.number for item in items if item.ticked}


#: What a `[~]` box still needs: the loop's fresh copy is run by no environment.
OWED = "what only a running environment can check is owed, after the merge"
STACK_OWED = f"the done command passed every check it could run; {OWED}"


def human_boxes(items: list[work_next.Item],
                sessions: list[Session]) -> list[tuple[str, str, str]]:
    """(number, title, box) for every unticked box on an ATTEMPTED item, but a box worded
    wrong — that one is a spec question, not a check.

    The one place the list is counted: the report's list and the console's count both come
    from here, so the two can never disagree."""
    seen = attempted(items, sessions)
    pending = []
    for item in items:
        if item.number not in seen:
            continue
        for number, (ticked, text) in enumerate(item.boxes, start=1):
            if not ticked and number not in item.worded_wrong:
                shown = f"{text} — {STACK_OWED}" if text in item.stack_owed else text
                pending.append((item.number, item.title, shown))
    return pending


def spec_questions(items: list[work_next.Item],
                   sessions: list[Session]) -> list[tuple[str, str, str]]:
    """(number, title, question) for every box worded wrong and every `Spec question:` line on
    an attempted item — read from the item files, which outlive this report."""
    seen = attempted(items, sessions)
    out = []
    for item in items:
        if item.number not in seen:
            continue
        for number, why in sorted(item.worded_wrong.items()):
            box = item.boxes[number - 1][1] if 0 < number <= len(item.boxes) else "(no such box)"
            out.append((item.number, item.title, f"box {number}, {box} — worded wrong: {why}"))
        out += [(item.number, item.title, question) for question in item.spec_questions]
    return out


#: Session endings after which the item still counts toward the queue's progress.
SETTLED = {"done", "owed"}

BROWSER = "## check in the browser"


def browser_steps(path: Path) -> list[str]:
    """The item's own `## Check in the browser`, verbatim, without trailing blank lines.

    Written by `/to-tickets` as what the owner should see, and rewritten as concrete steps by the
    session that built the screen. Never generated here: a step nobody wrote is a step
    nobody checked could be followed.
    """
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    out: list[str] = []
    inside = False
    for line in lines:
        if line.startswith("## "):
            inside = line.strip().lower() == BROWSER
            continue
        if inside:
            out.append(line)
    while out and not out[-1].strip():
        out.pop()
    while out and not out[0].strip():
        out.pop(0)
    return out


def render(slug: str, items: list[work_next.Item], sessions: list[Session],
           tree: Path, branch: str, logs: Path | None, meta: dict | None = None,
           tip: dict | None = None, review: dict | None = None,
           filing: dict | None = None) -> str:
    by_number = {item.number: item for item in items}
    done = [item for item in items if item.done]
    seen = attempted(items, sessions)
    untouched = [item for item in items if item.number not in seen and not item.done]
    review = review or {}
    filing = filing or {}
    spent = (sum(session.cost for session in sessions) + float(review.get("cost") or 0.0)
             + float(filing.get("cost") or 0.0))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")

    head = [f"Rendered {now} · tree `{tree}` · branch `{branch}`",
            settings_line(meta or {}),
            tip_line(tip or {}, logs if sessions else None, meta),
            f"{len(done)}/{len(items)} items done"
            + (f" · {len(sessions)} session(s)"
               + (" and a filing session" if filing.get("status") == "filed" else "")
               + (" and a review" if review.get("status") == "reviewed" else "")
               + f" · estimated ${spent:.2f}" if sessions else "")
            + " · **nothing pushed, nothing merged**"]
    # A run nothing recorded settings for drops the line rather than printing a blank one.
    out = [f"# {slug} — what the loop did", ""] + [line for line in head if line] + [""]

    out += built_section(items, sessions, by_number, review, logs)
    out += check_section(items, sessions, logs)
    out += questions_section(items, sessions)
    out += filed_section(slug, items, filing)

    aside = [session for session in sessions if session.status not in SETTLED]
    if aside:
        out += ["## Set aside in this run", "",
                "Each of these did not finish. The loop went on with every item that does "
                "not depend on it; the ones that do are still queue. Read the log, fix or "
                "reword the item, and run the same command again — it resumes here.", ""]
        for session in aside:
            number = Path(session.item).name[:2]
            title = by_number[number].title if number in by_number else session.item
            leftover = " — its uncommitted work is on an `afk/*-leftover-*` branch" \
                if session.status == "dirty" else ""
            out.append(f"- **{number}** {title} — `{session.status}`{leftover}"
                       + (f" · `{session.log}`" if session.log else ""))
        out.append("")

    if untouched:
        out += ["## Not attempted", "",
                "This run never reached these, so nothing about them has been proved "
                "OR disproved — they are still queue, not review.", ""]
        for item in untouched:
            name, why = work_next.state(item, by_number)
            out.append(f"- **{item.number}** {item.title} — {name}: {why}")
        out.append("")

    out += ["## The queue now", "", "```"]
    for item in items:
        name, why = work_next.state(item, by_number)
        out.append(f"{item.number}  {name:<9} {item.title[:52]:<52} {why}")
    out += ["```", ""]

    out += ["## Per item", ""]
    if sessions:
        out += ["Each item's peak context is the most one API call held, read from its "
                "session's own log under `~/.claude/projects/`; `/wiqrug:to-tickets` sizes an item to "
                f"finish under about {PEAK_LIMIT // 1000}k.", ""]
        for session in sessions:
            out += render_session(session, by_number, logs)
    else:
        out += ["No `run.jsonl` — this was not an unattended run, so commits are not "
                "attributed per item. The branch's log:", "", "```"]
        out += [line for line in
                run_git(tree, "log", "--oneline", "--no-decorate", "-20").splitlines()]
        out += ["```", ""]

    base = sessions[0].before if sessions and sessions[0].before else ""
    onto = (meta or {}).get("base_branch")
    span = (f"{base}..HEAD" if base else f"$(git -C \"{tree}\" merge-base {branch} {onto})..{branch}"
            if onto else f"-20 {branch}")
    out += ["## How to read it", "", "```bash",
            f'git -C "{tree}" log --oneline --no-decorate {span}',
            f'git -C "{tree}" diff {span}',
            "```", ""]
    if base:
        out += [f"`{base[:12]}` is where this run started — recorded, not inferred.", ""]
    if logs is not None:
        out += [f"Transcripts: `{logs}`", ""]
    return "\n".join(out)


def built_section(items: list[work_next.Item], sessions: list[Session],
                  by_number: dict[str, work_next.Item], review: dict,
                  logs: Path | None) -> list[str]:
    """Part 1: what was built, reviewed and proved — each settled item with its own review,
    then the whole branch's review. An item that did not settle is under *Set aside*."""
    out = ["## Built, reviewed and proved", ""]
    settled = [session for session in sessions if session.status in SETTLED]
    if not sessions:
        built = [item for item in items if item.number in attempted(items, sessions)]
        out += ["No `run.jsonl` — an interactive run, so no review is recorded per item. Items "
                "with a box proved:", ""]
        out += [f"- **{item.number}** {item.title} — {item.ticked}/{len(item.boxes)} boxes"
                for item in built] or ["- none"]
        return out + [""]
    if not settled:
        out += ["Nothing was built to the end in this run. What stopped it is under *Set "
                "aside* and in the transcripts.", ""]
    else:
        out += ["Each line says how the item was gated — the code gate, the project's done "
                "command at its last commit — and how it was reviewed: a Standards and a Spec reviewer "
                "on its own diff before the next item started, then its own session checking "
                "each finding. A verdict is that session's; its evidence is under *Per item*.", ""]
    for session in settled:
        number = Path(session.item).name[:2]
        item = by_number.get(number)
        title = item.title if item else session.item
        ticked = f"{item.ticked}/{len(item.boxes)} boxes" if item else ""
        out.append(f"- **{number}** {title} — `{session.status}` · {ticked} · "
                   f"{gate_summary(logs, session.item)} · {review_summary(session.review)}")
        for line in (item.fails_first if item else []):
            out.append(f"  - ticked on earlier work's evidence, for the reviewer to check: {line}")
    if settled:
        out.append("")
    return out + review_section(review, logs if sessions else None)


def check_section(items: list[work_next.Item], sessions: list[Session],
                  logs: Path | None) -> list[str]:
    """Part 2: FOR YOU TO CHECK — what no command could close: each item's browser steps, what
    the code gate could not verify, the open boxes of an older queue, and what a running copy of
    the project checks after the merge. ⚠️ Only items a session actually worked on: sending
    somebody to test work never built is the confident-wrong-number failure."""
    out = ["## For you to check", ""]
    seen = attempted(items, sessions)
    paths = {Path(session.item).name[:2]: session.item for session in sessions}
    settled = [session for session in sessions if session.status in SETTLED]
    gated = [(Path(s.item).name[:2], line) for s in settled for line in gate_lines(logs, s.item)]
    pending = human_boxes(items, sessions)
    steps = [(item, browser_steps(item.path)) for item in items if item.number in seen]
    steps = [(item, lines) for item, lines in steps if lines]
    said = [line for session in sessions for line in not_proved_lines(session.final)]
    titles = {item.number: item.title for item in items}
    if not (gated or pending or steps or said or settled):
        return out + ["Nothing — no item was built to the end in this run.", ""]
    if settled:
        out += ["On a running copy of the project, once the branch is merged. **What only a "
                "running environment checks is checked there, after the merge**: no "
                "environment runs an unattended worktree.", ""]
    if gated:
        out += ["What the code gate could not verify:", ""]
        out += [f"- **{number}** {titles.get(number, '')} — {line}" for number, line in gated]
        out.append("")
    if pending:
        out += ["Boxes no command could tick:", ""]
        for at, (number, title, box) in enumerate(pending):
            out.append(f"- **{number}** {title} — {box}")
            # The evidence goes under an item's LAST box, where its list ends.
            if at + 1 == len(pending) or pending[at + 1][0] != number:
                line = evidence_line(logs, paths.get(number, ""))
                if line:
                    out.append(f"  - {line}")
        out.append("")
    if said:
        out += ["What the sessions said they could not prove:", ""]
        out += [f"- {line}" for line in said] + [""]
    if not (gated or pending or steps or said):
        out += ["Nothing else: nothing the code gate could not verify, no box left for a "
                "person, and no browser steps.", ""]
    if steps:
        out += ["### Check in the browser", "",
                "Where the project has a browser check, the session proved each screen with it; "
                "these are what only a person can see. Each item's steps are its own words, "
                "verbatim.", ""]
        for item, lines in steps:
            out += [f"#### {item.number} — {item.title}", ""] + lines + [""]
    return out


def questions_section(items: list[work_next.Item], sessions: list[Session]) -> list[str]:
    """Part 3: the spec questions — the owner's to answer, never a session's to guess."""
    out = ["## Spec questions", ""]
    found = spec_questions(items, sessions)
    if not found:
        return out + ["None: no box was found worded wrong, and no review finding was a gap "
                      "in the spec.", ""]
    out += ["Each is a gap in the spec, not a defect of the code: nothing was built for it.", ""]
    out += [f"- **{number}** {title} — {question}" for number, title, question in found]
    return out + [""]


def settings_line(meta: dict) -> str:
    """What produced this run. Blank when nothing recorded it — never inferred."""
    if not meta:
        return ""
    parts = [f"effort `{meta.get('effort', '?')}`", f"model `{meta.get('model', '?')}`"]
    if meta.get("environment"):
        parts.append(f"environment `{meta['environment']}`")
    if meta.get("budget_per_item"):
        parts.append(f"budget/item ${meta['budget_per_item']}")
    return "Run settings: " + " · ".join(parts)


def render_session(session: Session, by_number: dict[str, work_next.Item],
                   logs: Path | None = None) -> list[str]:
    number = Path(session.item).name[:2]
    item = by_number.get(number)
    title = item.title if item else session.item
    head = f"### {number} — {title}"
    out = [head, "",
           f"`{session.status}`"
           + (f" · ${session.cost:.2f}" if session.cost else "")
           + (f" · {session.turns} turns" if session.turns else "")
           + (f" · {session.limited} rate-limit retries" if session.limited else "")
           + f" · {peak_text(session)}", ""]
    if item:
        for ticked, text in item.boxes:
            mark = "x" if ticked else "~" if text in item.stack_owed else " "
            out.append(f"- [{mark}] {text}")
        out.append("")
    line = evidence_line(logs, session.item)
    if line:
        out += [line[0].upper() + line[1:], ""]
    if session.status in SETTLED:
        out += [f"Its review: {review_summary(session.review)}.", ""]
        axes = fix_axes(session.review)
        if axes:
            for axis in axes:
                out += axis_lines(axis, "####")
        elif session.review.get("text"):
            out += ["<details><summary>what its reviewers wrote</summary>", "", "```",
                    session.review["text"], "```", "", "</details>", ""]
    if session.commits:
        out += ["```"] + session.commits + ["```", ""]
    elif session.status == "done":
        out += ["No commit on this item — it ticked its boxes without changing "
                "anything, which is worth a second look.", ""]
    if session.final:
        out += ["<details><summary>what the session reported</summary>", "",
                "```", session.final.strip(), "```", "", "</details>", ""]
    return out


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("slug", nargs="?")
    parser.add_argument("--logs", help="the run's log folder (holds run.jsonl)")
    parser.add_argument("--worktree", help="the tree the items were built in")
    parser.add_argument("--branch", default="", help="the branch the work landed on")
    parser.add_argument("--out", help="where to write [<logs>/report.md]")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()
    if not args.slug:
        parser.error("a slug is required (or --selftest)")

    tree = Path(args.worktree).expanduser().resolve() if args.worktree else Path.cwd()

    try:
        tree, queue, done = work_next.queue_of(tree)
        items = work_next.load(args.slug, queue, done)
    except (work_next.Malformed, OSError) as exc:
        print(f"afk_report: {exc}", file=sys.stderr)
        return 2

    logs = Path(args.logs).expanduser().resolve() if args.logs else None
    sessions = read_run(logs) if logs else []
    enrich(sessions, logs or tree, tree)
    reviews = read_item_reviews(logs) if logs else {}
    for session in sessions:
        session.review = reviews.get(session.item, {})
    branch = args.branch or run_git(tree, "rev-parse", "--abbrev-ref", "HEAD") or "HEAD"
    text = render(args.slug, items, sessions, tree, branch, logs,
                  read_meta(logs) if logs else {}, read_tip(logs) if logs else {},
                  read_review(logs) if logs else {}, read_filing(logs) if logs else {})

    out = Path(args.out) if args.out else (logs / "report.md" if logs else None)
    if out is None:
        print(text)
        return 0
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    except OSError as exc:
        print(f"afk_report: could not write {out}: {exc}", file=sys.stderr)
        print(text)
        return 2
    print(f"report: {out}")
    pending = human_boxes(items, sessions)
    questions = spec_questions(items, sessions)
    print(f"        {len(pending)} box(es) for you to check, {len(questions)} spec question(s)")
    return 0


# --------------------------------------------------------------------------- selftest
ITEM = """# 01: A thing

Advances:   unit-x
Cites:      F-1

## What to build

A thing.

## Acceptance

- [x] `tests pass`
- [ ] `the screen reads correctly`
"""


def selftest() -> int:
    """Prove the claims that matter: an unticked box reaches For you to check, and a run with
    no `run.jsonl` still renders rather than dying — then each part of the report."""
    import tempfile

    failures = []
    with tempfile.TemporaryDirectory() as raw:
        tree = Path(raw)
        queue = tree / "plans"
        folder = queue / "demo"
        folder.mkdir(parents=True)
        (folder / "01-a-thing.md").write_text(ITEM)
        items = work_next.load("demo", queue)

        text = render("demo", items, [], tree, "afk/demo", None)
        if "the screen reads correctly" not in text.split("## For you to check")[1]:
            failures.append("an unticked box did not reach For you to check")
        if "Not attempted" in text:
            failures.append("a part-proved item was called not attempted")
        if "not attributed per item" not in text:
            failures.append("a report with no run.jsonl did not say so")

        session = Session(item="plans/demo/01-a-thing.md", status="done", cost=0.5,
                          final="proved  tests — exit 0\nNOT proved  the screen — needs a browser")
        meta = {"effort": "medium", "model": "claude-opus-5", "environment": "staging",
                "done": "make check", "owed_exit": 3}
        text = render("demo", items, [session], tree, "afk/demo", tree, meta)
        if "NOT proved  the screen — needs a browser" not in text:
            failures.append("the session's own NOT proved line was dropped")
        if "$0.50" not in text:
            failures.append("the spend did not render")
        if "effort `medium`" not in text or "model `claude-opus-5`" not in text:
            failures.append("the run settings did not render")

        (folder / "02-another.md").write_text(ITEM.replace("01:", "02:"))
        two = work_next.load("demo", queue)
        text = render("demo", two, [session], tree, "afk/demo", tree, meta)
        if "## Not attempted" not in text:
            failures.append("an item nothing touched was not separated out")
        if "**02**" in text.split("## Not attempted")[0]:
            failures.append("an unattempted item reached the parts before Not attempted")
        if len(human_boxes(two, [session])) != 1:
            failures.append("the console's count of boxes for a person counted an unattempted item")

        (tree / "run.jsonl").write_text(
            '{"kind": "meta", "effort": "high", "model": "m"}\n'
            '{"item": "plans/demo/01-a-thing.md", "status": "done", "before": "a",'
            ' "after": "b", "cost": 0.25, "log": "x.jsonl"}\n')
        if read_meta(tree).get("effort") != "high":
            failures.append("the meta line was not read back")
        if len(read_run(tree)) != 1:
            failures.append("the meta line was counted as a session")

        text = render("demo", items, [session], tree, "afk/demo", tree, meta, {})
        if "Branch tip: **not checked**" not in text:
            failures.append("a run with no tip row did not say the tip was unchecked")
        text = render("demo", items, [session], tree, "afk/demo", tree, meta,
                      {"kind": "tip", "head": "abcdef1234567890", "rc": 1, "log": "t.log"})
        if "FAILS the done command (`make check`)" not in text:
            failures.append("a failing tip did not reach the head of the report")
        text = render("demo", items, [session], tree, "afk/demo", tree, meta,
                      {"kind": "tip", "head": "abcdef1234567890", "rc": 3, "log": "t.log"})
        if "exit 3 — every check it could run passed" not in text:
            failures.append("a tip at done.owed-exit was not called owed")
        text = render("demo", items, [session], tree, "afk/demo", tree, {**meta, "owed_exit": None},
                      {"kind": "tip", "head": "abcdef1234567890", "rc": 3, "log": "t.log"})
        if "FAILS the done command" not in text:
            failures.append("exit 3 was called owed in a project with no done.owed-exit")
        shots = tree / "01-a-thing/evidence/scratch"
        shots.mkdir(parents=True)
        (shots / "a.png").write_bytes(b"x")
        (shots / "drive.mjs").write_text("x")
        text = render("demo", items, [session], tree, "afk/demo", tree, meta, {})
        if "1 screenshot(s), 1 script(s)" not in text.split("## For you to check")[1].split("## Spec")[0]:
            failures.append("the evidence folder did not reach For you to check")

        (folder / "01-a-thing.md").write_text(
            ITEM + "\n## Check in the browser\n\n1. Open the settings page as an editor\n\n## Comments\n- x\n")
        items = work_next.load("demo", queue)
        text = render("demo", items, [session], tree, "afk/demo", tree, meta, {})
        check = text.split("## For you to check")[1].split("## Spec questions")[0]
        if "### Check in the browser" not in check or "1. Open the settings page as an editor" not in check:
            failures.append("an item's browser steps did not reach For you to check")
        if "- x" in check.split("### Check in the browser")[1]:
            failures.append("the steps ran on into the item's Comments")

        text = render("demo", items, [session], tree, "afk/demo", tree, meta, {}, {})
        if "**Not reviewed** — this run recorded no review" not in text:
            failures.append("a run with no review row did not say nobody reviewed it")
        (tree / "review.md").write_text("## Findings (1)\n\n### 1. a count that lies\n")
        (tree / "run.jsonl").write_text(
            '{"kind": "review", "status": "reviewed", "why": "", "cost": 0.5, "log": "r"}\n')
        text = render("demo", items, [session], tree, "afk/demo", tree, meta, {},
                      read_review(tree))
        parts = [text.index(h) for h in ("## Built, reviewed and proved",
                                          "### What the branch reviewer found",
                                          "## For you to check", "## Spec questions")]
        if parts != sorted(parts) or "##### 1. a count that lies" not in text:
            failures.append("the three parts are out of order, or the branch review is not "
                            "in the first, verbatim, demoted two levels")
        if "and a review · estimated $1.00" not in text:
            failures.append("the review's cost was not added to the spend")
        if "**not checked** — this run recorded no check" not in text:
            failures.append("a review with no check did not say its findings were unchecked")
        (tree / "check.md").write_text('```json\n' + json.dumps({
            "standards": {"ran": True, "findings": [
                {"finding": "S1 holds", "verdict": "confirmed", "evidence": "line 3"},
                {"finding": "S2 dismissed", "verdict": "refuted", "evidence": ""}]},
            "spec": {"ran": False, "note": "no spec available"}}) + '\n```\n')
        (tree / "run.jsonl").write_text(
            '{"kind": "review", "status": "reviewed", "why": "", "cost": 0.5, "log": "r",'
            ' "check": "checked"}\n')
        text = render("demo", items, [session], tree, "afk/demo", tree, meta, {},
                      read_review(tree))
        if "#### Standards — 2 finding(s): 1 confirmed · 0 refuted · 1 unchecked" not in text:
            failures.append("the Standards axis did not carry its verdict counts")
        if "2. **unchecked** (marked refuted with no evidence) — S2 dismissed" not in text:
            failures.append("a refuted finding with no evidence was not shown as unchecked")
        if "#### Spec — not run: no spec available" not in text:
            failures.append("an axis the review skipped did not say so")
        if "Count mismatch" in text:
            failures.append("a review with no total lines printed a count mismatch")
        (tree / "review.md").write_text(
            "## Standards\n\n1. S1\n2. S2\n3. S3\n\n"
            "Standards: 3 findings; worst: S1\nSpec: not run, no spec available\n")
        text = render("demo", items, [session], tree, "afk/demo", tree, meta, {},
                      read_review(tree))
        if "the Standards reviewer wrote 3 finding(s) in `review.md`; the check returned 2" \
                not in text.split("#### Spec")[0]:
            failures.append("a check that dropped a finding did not print a count mismatch")
        if text.count("Count mismatch") != 1:
            failures.append("a skipped axis, or a matching one, printed a count mismatch")
        (tree / "review.md").write_text("**Standards:** 2 findings; worst: S1\n")
        text = render("demo", items, [session], tree, "afk/demo", tree, meta, {},
                      read_review(tree))
        if "Count mismatch" in text:
            failures.append("equal totals printed a count mismatch")

        (folder / "01-a-thing.md").write_text(
            ITEM + "\n## To file\n\n- [x] G: a trap — G-400\n- [ ] term: Filing\n")
        items = work_next.load("demo", queue)
        text = render("demo", items, [session], tree, "afk/demo", tree, meta, {}, {},
                      {"kind": "filing", "status": "failed", "why": "a billing error"})
        filed = text.split("## Filed")[1].split("\n## ")[0] if "## Filed" in text else ""
        if "- [x] **01** G: a trap — G-400" not in filed:
            failures.append("a filed To file line did not reach ## Filed")
        if "- [ ] **01** term: Filing — a billing error" not in filed:
            failures.append("an unfiled line did not say why it was not filed")
        text = render("demo", items, [session], tree, "afk/demo", tree, meta, {}, {}, {})
        if "no filing session ran — run `/wiqrug:update-knowledge demo`" not in text:
            failures.append("with no filing row, ## Filed did not say none ran")

        failures += _selftest_review_and_questions(tree, folder, session, meta)

        # A subagent's window and a synthetic record are not the item's: alone, they are unknown.
        log = tree / "peak.jsonl"
        log.write_text(
            '{"type": "assistant", "isSidechain": true, "message": {"usage": {"input_tokens": 9}}}\n'
            '{"type": "assistant", "message": {"model": "<synthetic>", "usage": {"input_tokens": 7}}}\n')
        if read_peak(log)[0] is not None:
            failures.append("a log holding no call of the item's own gave a peak")
        with log.open("a") as handle:
            handle.write('{"type": "assistant", "message": {"usage": {"input_tokens": 2,'
                         ' "cache_creation_input_tokens": 30, "cache_read_input_tokens": 400}}}\n')
        if read_peak(log)[0] != 432:
            failures.append("the peak was not input + cache creation + cache read")

    for line in failures:
        print(f"selftest FAIL  {line}", file=sys.stderr)
    print(f"selftest {'FAILED' if failures else 'ok'} — 43 checks")
    return 1 if failures else 0


def _selftest_review_and_questions(tree: Path, folder: Path, session: Session,
                                   meta: dict) -> list[str]:
    """An item's own review, what the code gate could not verify, and the spec questions —
    each read from what the run and the item file left."""
    failures = []
    (folder / "02-another.md").unlink(missing_ok=True)
    (folder / "01-a-thing.md").write_text(ITEM.replace("- [x] `tests pass`", (
        "- [x] `tests pass`\n- [ ] `c.py` passes")) + (
        "\n## Comments\n\nBox 2 worded wrong: c.py passed before any work.\n"
        "Spec question: does a blank price mean removed?\n"))
    items = work_next.load("demo", folder.parent, "make check")
    (tree / "01-a-thing.fix.md").write_text("```json\n" + json.dumps({
        "standards": {"ran": True, "findings": [
            {"finding": "a count with no rows", "verdict": "confirmed", "evidence": "abc123"}]},
        "spec": {"ran": True, "findings": [
            {"finding": "blank price", "verdict": "spec question", "evidence": ""}]}}) + "\n```\n")
    rows = [{"kind": "meta", "effort": "medium", "model": "m", "done": "make check",
             "owed_exit": 3},
            {"kind": "gate", "item": session.item, "rc": 1, "log": "g1.log"},
            {"kind": "gate", "item": session.item, "rc": 3, "log": "g2.log"},
            {"kind": "item-review", "item": session.item, "status": "reviewed", "why": "",
             "review": "r", "fix": "fixed", "fix_why": "", "cost": 0.1}]
    (tree / "run.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
    session.review = read_item_reviews(tree)[session.item]
    text = render("demo", items, [session], tree, "afk/demo", tree, meta, {}, {})
    built = text.split("## Built, reviewed and proved")[1].split("## For you to check")[0]
    if "1 confirmed, the fix's commit in its evidence · 0 refuted · 1 spec question(s)" not in built:
        failures.append("an item's own review did not reach part 1 with its counts")
    check = text.split("## For you to check")[1].split("## Spec questions")[0]
    if "the done command exited 3: every check it could run passed" not in check \
            or "`g2.log`" not in check:
        failures.append("the gate's owed exit, its last row, did not reach For you to check")
    (tree / "run.jsonl").write_text("".join(json.dumps(row) + "\n" for row in (
        rows[:1] + [{"kind": "gate", "item": session.item, "rc": 0, "log": "g.log"}] + rows[3:])))
    passed = render("demo", items, [session], tree, "afk/demo", tree, meta, {}, {})
    if "the done command exited" in passed.split("## For you to check")[1] \
            or "code gate passed ·" not in passed:
        failures.append("a gate that exited 0 was listed as something it could not verify")
    (tree / "run.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
    if "`c.py` passes" in check:
        failures.append("a box worded wrong was listed as a check, not a spec question")
    questions = text.split("## Spec questions")[1].split("\n## ")[0]
    if "box 2, `c.py` passes — worded wrong" not in questions \
            or "does a blank price mean removed?" not in questions:
        failures.append("a worded-wrong box or a Spec question line is not a spec question")
    if "#### Spec — 1 finding(s): 0 confirmed · 0 refuted · 0 unchecked · 1 spec question" \
            not in text.split("## Per item")[1]:
        failures.append("the item's fix verdicts did not reach Per item")
    if "code gate passed — with what it could not verify" not in built:
        failures.append("the gate's verdict did not reach the item's line")
    (tree / "01-a-thing.review.md").write_text("Standards: 3 findings\nSpec: 1 findings\n")
    session.review = read_item_reviews(tree)[session.item]
    text = render("demo", items, [session], tree, "afk/demo", tree, meta, {}, {})
    if "its reviewers wrote 4, the fix answered for 2" not in text:
        failures.append("a fix that dropped findings did not say so")
    session.review = {"status": "skipped", "why": "--no-review"}
    text = render("demo", items, [session], tree, "afk/demo", tree, meta, {}, {})
    if "**not reviewed** — --no-review" not in text.split("## For you to check")[0]:
        failures.append("an item nobody reviewed was not said to be unreviewed")
    session.review = {}
    (folder / "01-a-thing.md").write_text(ITEM)
    return failures


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
