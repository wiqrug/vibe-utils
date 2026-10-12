# Unattended — the same loop, nobody watching

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/implement/afk.sh <slug> --dry-run
bash ${CLAUDE_PLUGIN_ROOT}/skills/implement/afk.sh <slug> --environment <name>
```

Run from anywhere inside the project. **Every fact about the project comes from its settings
file, through the project check** — the queue's folder (`documents.queue`), the "done" command
(`done.command`) and the exit by which it says "owed, not failed" (`done.owed-exit`), how a fresh
copy is made ready (`unattended.prepare`), the environments (`environments.list`) and whether a
browser check exists (`browser.check`). A project the check does not call set up is refused with
the check's own line.

One fresh session per item, in a throwaway worktree under `~/afk/` (`AFK_ROOT` moves it), ending
in a branch `afk/<slug>` that **a person reads before anything else happens.** The queue and the
settings file must be committed: the worktree is cut from `HEAD`. A run attempts **five items**
by default, and each is reviewed and fixed before the next starts:

1. **Build** — `/wiqrug:implement <item>`, one session.
2. **The code gate** — the loop runs the "done" command at the item's last commit, whatever the
   session marked. Exit 0 passes, and so does `done.owed-exit`. Only this can stop an item.
3. **Review** — a separate session runs `/wiqrug:review-change <the item's start> <the item
   file>`: a Standards and a Spec reviewer read the item's diff, and change nothing.
4. **Fix** — the item's own session, resumed, checks each finding: *confirmed* and fixed;
   *refuted* only with evidence; a gap in the spec written as a `Spec question:` line and no
   code; else *unchecked*.
5. **The code gate again** — then the next item.

Each item's session starts with the typed command `/wiqrug:implement <item>`: the skill is
`disable-model-invocation`, so a prompt in plain words would never load it.

**It goes to the background by itself.** Everything that can refuse — the project, the queue,
the tree, the environment, a second run of the same slug — refuses in front of whoever started
it; then it detaches (`setsid`, no terminal), so a closed laptop or a dropped SSH connection does
not end it. `--foreground` keeps it attached, and so does a machine without `setsid` — Git Bash on
Windows — where the run says once to leave the window open and finishes there. When it detaches it
prints the command to watch it:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/lib/afk_watch.py <slug> --project <the project's root>
```

It follows the newest run: the loop's own lines, and for each session what it says, every tool
it runs, what failed, and how the item ended with its time and cost. `--all` replays the current
session from its start; Ctrl-C stops only the watching. The same lines print the raw
`console.log`, the report's path and how to stop the run.

| flag | default | why you would change it |
|---|---|---|
| `--environment` | the one there is | Required when `environments.list` names several — the owner names it, never the model. Refused when it names none. The sessions are told it, and see it as `WIQRUG_ENVIRONMENT`. |
| `--effort` | `medium` | The thinking was spent in `/wiqrug:grill-with-docs`, `/wiqrug:to-spec` and `/wiqrug:to-tickets`, which are paid once; an item arrives pre-decomposed with boxes that name their commands, and is paid for N times. Raise it for an item you know is hard. |
| `--max` | `5` | How many items this run may attempt: a run sized so its branch can still be read. Lower it to read one item's branch before the next is built on it; `all` attempts every item the queue offers, each once, until nothing is ready — a branch that much longer to read. |
| `--max-budget-usd` | none | ⚠️ **Per item, not per run** — the flag belongs to one `claude` invocation and there are `--max` of them. `--max-budget-usd 5 --max 5` is a ceiling of twenty-five dollars. |
| `--max-spend-usd` | none | The whole run's ceiling, added up between items. This is the one that means what it looks like. |
| `--on-limit` | `wait` | `wait` retries the same item until the usage window reopens; `stop` ends the run and leaves the queue for the next one. |
| `--limit-wait`, `--limit-max-wait` | `15`m, `6`h | How often it retries while limited, and how long it may keep doing that. |
| `--model`, `--fallback-model` | session default | A cheaper model per item, or a fallback when the primary is overloaded. |
| `--no-review` | review | Skips every review: each item's and its fix, and the branch's at the end with its check. Only for a run whose diff you will read line by line anyway. |

**A fresh copy is made ready by the project's own commands.** `unattended.prepare` runs in order
from the new worktree's root, once per worktree, with `AFK_SOURCE_TREE` naming the tree the loop
was started in. A command that fails stops the run, and so does one that leaves files git sees:
what it makes must be in the project's ignore file, or every item would read as dirty.

**A usage limit is waited out, not reported as a failure.** The retry *is* the probe: a
session started while the window is still full exits in seconds having spent nothing, so
polling costs nothing and no reset time has to be parsed out of a message whose shape
nothing here has measured. A limit is recognised in either shape it takes — an `api_retry`
with `rate_limit`, or the measured one: a `rejected` `rate_limit_event`, an assistant
`rate_limit` error, a `429` result. A half-edit the limit interrupted is kept on a
`-limitN` leftover branch, so the retry starts from committed work; the reviews wait
too. ⚠️ **A billing error is not a usage limit** — nothing resets, so it stops immediately
rather than spinning until the wait ceiling.

It refuses a project not set up, a worktree path checked out on another branch, a missing or
unknown environment, a dirty tree, an unsound queue, an uncommitted one, and a branch that the
branch the project stands on has already merged and moved past — it prints the commands that
remove it, so the next run cuts fresh. A branch carrying a commit the base lacks is a stopped run,
and is resumed. It denies the session `git push`: nothing an unattended run does reaches a server.

**What needs the owner never stops the queue; it goes in the report.** Only code can stop an
item: the code gate, the "done" command, at the item's last commit, after the build and again
after the fixes. A failed gate gets one repair: a session — the item's own, resumed — is handed
the log, and the gate runs again. A second failure sets the item aside, and the loop **adds an
open box to the item** — *the code gate passes at this item's last commit* — naming the command,
its exit and its log, so the item reads as unfinished: what depends on it waits, and the next run
offers it again. At the end the loop runs the done command on the branch tip once more, and that
answer heads the report.

| after an item | the item | the run |
|---|---|---|
| every box ticked | `done` | goes on |
| only boxes no session can close left open — a box worded wrong, and in an older queue a person's box, a `[~]` box or its "done" box | `owed` — counts as settled, its boxes listed in the report | goes on, dependants included |
| a box passed before any work, or names a record that is not there (`/wiqrug:implement` step 2) | ticked on the evidence of the earlier work that delivered it, for the reviewer to check — or left open with `Box <n> worded wrong:`, owed, and a spec question in the report. **Never parked** | goes on |
| did not exit 0 · spent its `--max-budget-usd` · the code gate failed after its one repair · a box a command should close is open | **set aside** for this run | goes on with every item that does not depend on it |
| deleted one of its own acceptance boxes, or left one with an unclosed backtick | **set aside** — `damaged`; restore the boxes from the commit the report names | goes on with every item that does not depend on it |
| left uncommitted changes | set aside; the changes are kept on `afk/<slug>-leftover-NN-<stamp>` and the worktree reset | goes on |

A **review that fails** costs the review, not the item: the item was built and gated, the run
goes on, and the report says *not reviewed* beside it. A **fix** that did not finish — its
session failed, or left uncommitted changes, kept on a `-fix` leftover branch — costs the fix:
the report says its findings were not fixed. A fix that breaks the gate is judged like the build:
one repair, then set aside. A billing error or a usage limit the run cannot wait out, in an item's
review or fix, ends the run with the item kept as built.

**An older queue keeps working as written** — one written before items stopped naming files, a
person's box and the done command's box. The loop ignores its `Touches:`, lists its boxes for a
person under *For you to check*, and treats its "`<done.command>` exits 0" box as owed once
anything else on the item is ticked. At the end, the done command's run on the branch tip sets
that box on every item **this run** settled — `0` ticks it, `done.owed-exit` marks it `[~]`,
anything else reopens it — whatever its session marked. An item an earlier run settled is left as
that run's tip set it.

**An item marked `Attended: <why>` is never offered to the loop**, and the items that depend on
it wait. It is not set aside, because no session tried it: the start-up lines and the report's
`## Not attempted` say `attended: <why>`, in the item's own words. The owner builds it by typing
`/wiqrug:implement`. Nothing but the header keeps an item out.

Only these end the run: `STOPPED` — billing (the account, not the model; waiting will not fix
it) · `STOPPED` — the run's `--max-spend-usd` · `PAUSED` — a usage limit that outlasted
`--limit-max-wait`, or `--on-limit stop` (not a failure; run it again) · the cap, `--max` ·
nothing ready (the queue is settled, or what is left waits on a decision, an attended item or a
set-aside one).

Running the same command again resumes: a set-aside item is offered again, and an item short
only of an older queue's done box is owed, so it costs no session at all.

⚠️ **The failure to design against is not a crash.** It is hours of finished, confident work
resting on a wrong call made in the first ten minutes. `--dry-run` first, then read the
diff — and `--max 1` when the first item is the one a wrong call would ride on.

`done.owed-exit` is how the gate says what it could not verify: every check it could run passed,
and only what a running environment checks was left, because no environment runs a throwaway
worktree. The gate passes on it and the report sends the rest to *For you to check*, after the
merge. On an older queue's done box the loop writes it as `- [~]`, the one other open mark. A
project whose `done.owed-exit` is `none` never gets one: there, every exit but 0 is a failure.

## The closing session, after the last item

A session writes what it learned as an unticked line under its item's `## To file`, rather than
into the knowledge files: knowledge written by each item, into files the next item also writes,
is how one item's notes once stopped another item's run. After the last item, and before the tip
check and the branch review, the loop counts the open lines through the queue reader and, when
there are any, runs **one** more session: `/wiqrug:update-knowledge <slug> --unattended`, which
files each line and ticks it with where it now lives, **in any file**. No open line, no session.

It waits out a usage limit on the same terms as an item and the review — `--on-limit`,
`--limit-wait`, and what is left of `--limit-max-wait`; the run has one budget of waiting. Its
cost counts toward `--max-spend-usd`. It is skipped when the run stopped on a limit, billing or
the spend ceiling, and the lines stay open for the next run. The report's `## Filed` lists every
line — filed, or not and why.

⚠️ **It never files a `D:` line**: a decision is written in the owner's words, and a closing
session once wrote its own into one. A `D:` line is not counted as one to file, so it alone
starts no session; the session leaves it unticked with the reason; and whatever the session does
anyway, the loop (`refuse_decisions`) puts every file it changed in `documents.decisions` back,
opens again every `D:` line it ticked, commits that on its own, and records it in the `filing`
row. The report asks each open `D:` line under its spec questions, and says so when the loop had
to undo a change.

## A session's evidence lands in the run's logs

Each session is given a scratch directory under `/tmp/afk-<slug>-<stamp>/<NN>` — in its
environment as `AFK_SCRATCH`, and in an appended system prompt — for any throwaway copy of the
running project and its check scripts. When it ends, its scripts and any failure screenshots are
copied into `logs/afk/<slug>/<stamp>/<item>/evidence/` under the project's root, together with
any other `/tmp` folder its transcript names; the report puts that folder under the item's
boxes. Only images and scripts are copied, never a whole folder: a scratch can hold a database,
passwords and a browser's cookies. The run's `logs/afk/` is kept out of git through the clone's
own `.git/info/exclude`, so the project's ignore file is not edited.

## Every run writes its own report

`logs/afk/<slug>/<stamp>/report.md`, rendered on **every** ending including a stopped one —
the run that stopped on its first item is the one whose report is worth the most, because it
is the one where what happened is least obvious from the branch.

It has three parts, in this order, after one line on whether the branch's tip passes the done
command:

1. **Built, reviewed and proved.** Each item the run settled, how the code gate judged it, and
   its own review in one line — how many findings were confirmed and fixed, refuted, spec
   questions, unchecked — and any box ticked on earlier work's evidence, for a reader to check
   too. Then **what the branch reviewer found**: after the last item, one more session runs
   `/wiqrug:review-change` on the run's whole diff — two `reviewer` subagents, **Standards** (the
   project's own rules) and **Spec** (`understanding.md` and the items) — and a last session
   **checks each finding** and changes nothing: *confirmed*; *refuted* only with evidence,
   meaning a command and its output, or the quoted lines that contradict it; otherwise
   *unchecked*. The two axes are separate sections, never merged or re-ranked; a "refuted" with
   no evidence is shown as *unchecked*. Every review session holds Bash, so "changes nothing" is
   checked, not assumed: `HEAD` is recorded before each and compared after, and a session that
   committed fails its row, with its commits left on the branch for a person to read. Every
   review counts toward `--max-spend-usd`. ⚠️ **A run or an item with no review says so in the
   same place**: it committed nothing, it ran with `--no-review`, it stopped on a limit or the
   ceiling, or the review itself failed — a report missing it reads as a branch somebody already
   looked at.
2. **For you to check.** What no command could close, on the items a session actually worked on:
   what the code gate could not verify (it exited `done.owed-exit`), an older queue's boxes for a
   person, what the sessions said they could not prove, each item's own `## Check in the browser`
   verbatim — and what a running copy of the project checks, after the merge. ⚠️ **An item nothing
   reached is listed separately, under `## Not attempted`.** Its boxes are not a review list —
   sending somebody to test work that was never built is a confident wrong answer.
3. **Spec questions.** Every box worded wrong, and every `Spec question:` line an item's fix
   wrote — read from the item files, which outlive the report. Then every open `D:` To file line
   in the queue, as a decision for the owner: no unattended run files one.

Then **`## Filed`**, and under **`## Per item`** each item's boxes, its commits, its review's
verdicts finding by finding, and its **peak context**: the most one API call held, read from that
session's own log under `~/.claude/projects/`. Anything over the 150k an item is sized to is
flagged; a log that is missing or unreadable shows the peak as **unknown**, never as 0.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/lib/afk_report.py <slug> --logs <root>/logs/afk/<slug>/<stamp> --worktree ~/afk/<slug>
```

re-renders it at any time. It also renders after an interactive run, from the item files and
git alone — there are no per-item commit boundaries recorded then, and it says so rather than
guessing them.
