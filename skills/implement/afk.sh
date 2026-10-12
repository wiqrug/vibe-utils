#!/usr/bin/env bash
#
# afk.sh — drain a work queue unattended, one fresh session per item.
#
#     bash <plugin>/skills/implement/afk.sh <slug> [--environment <name>] --dry-run
#     bash <plugin>/skills/implement/afk.sh <slug> [--environment <name>]
#
# Run it from anywhere inside a project set up with /wiqrug:setup. Every fact about the project —
# where the queue is, the "done" command and the exit by which it says "owed", how a fresh copy is
# prepared, the environments, whether a browser check exists — comes from the project check
# (`lib/project_check.py`), never from a folder this script guesses.
#
# It checks what it can while you watch — the project, the queue, the tree, the environment —
# then goes to the BACKGROUND, detached from the terminal, so closing the laptop or dropping the
# SSH connection does not end it. It prints the command to WATCH it — `afk_watch.py <slug>`, the
# loop's lines and each session's words and tool calls as they happen — and the report's path.
# ⚠️ Detaching needs `setsid`, which Git Bash on Windows does not have: there the run stays
# ATTACHED to the window it was started in, says once to leave that window open, and runs to its
# end there. Every other behaviour is the same.
#
# It runs under Git Bash as well as Linux: the lock is a folder (`mkdir`), not `flock`; Python is
# whichever name `bin/wiqrug-check` found (`python3`, `python` or `py`), never `python3` assumed.
#
# WHY one session per item rather than one long one: an item is sized to a fresh context
# window, so a session per item never compacts, its cost is bounded, and the loop's state
# lives in the item files and in git rather than in a conversation. A crash resumes.
#
# Options
#   --environment <name>           one of `environments.list`. Required when the project names
#                                  more than one — the owner names it, never the model; the one
#                                  there is when it names one; refused when it names none.
#   --max <n>|all                  items this run may attempt [5]; all: every item the queue offers
#   --effort <level>               low|medium|high|xhigh|max [medium]
#   --model <name>                 overrides the session default
#   --fallback-model <name>        used when the primary is overloaded
#   --max-budget-usd <amount>      ⚠️ PER ITEM, not per run — the flag belongs to one
#                                  `claude` invocation and there are --max of them
#   --max-spend-usd <amount>       the whole run's ceiling, checked between items
#   --on-limit <wait|stop>         a usage limit waits and retries, or stops [wait]
#   --limit-wait <minutes>         how long to wait before retrying [15]
#   --limit-max-wait <hours>       total time this run may spend waiting [6]
#   --no-review                    skip every review: each item's, its fix, and the branch's at the end
#   --dry-run                      print the plan and the first command; change nothing
#   --foreground                   stay attached to this terminal instead of detaching — what
#                                  happens anyway where `setsid` does not exist
#
#   An item with an `Attended: <why>` header is never offered to this loop, and the items that
#   depend on it wait; the console and the report say "attended: <why>". Typed by the owner,
#   `/wiqrug:implement` still builds it. The header is the item's own — there is no list to pass.
#
# EACH ITEM, BEFORE THE NEXT:
#   1. one session builds it: `/wiqrug:implement <item>`.
#   2. THE CODE GATE — the project's done command at the item's last commit, whatever the session
#      marked. Exit 0, or `done.owed-exit`, passes. Only this can stop an item.
#   3. a review session reads the item's diff on two axes (`/wiqrug:review-change <start> <item>`).
#   4. the item's OWN session, resumed, checks each finding: fixes what it confirms, refutes
#      only with evidence, and writes a gap in the spec as a `Spec question:` line, not code.
#   5. the code gate again. Then the next item.
#
# WHAT DOES NOT STOP IT, because each is the owner's to settle and none is a reason for the
# rest of the queue to wait:
#   * what a person checks — each item's `## Check in the browser`, and what the code gate could
#     not verify (it exited `done.owed-exit`: every check it could run passed, and only what a
#     running environment checks is left, because no environment runs this fresh copy). Both go
#     to the report's FOR YOU TO CHECK, beside the screenshots and check scripts the loop copies
#     out of the session's /tmp scratch into `logs/afk/<slug>/<stamp>/<item>/evidence/`.
#   * a box that passed before any work — /wiqrug:implement ticks it on the evidence of the
#     earlier work that delivered it, or writes `Box <n> worded wrong:`; that box is OWED and goes
#     to the report's spec questions. The item is built either way, never parked. So is a box
#     naming a record of the project's data that is not there: it cannot run as written.
#   * an older queue: its `Touches:` is ignored, its boxes for a person and its done box are
#     OWED — what depends on the item goes ahead. The done command's run on the branch tip at the
#     end closes that box: 0 ticks it, `done.owed-exit` marks it `[~]`.
#   * the code gate failing — ONCE. One more session (the item's own, resumed) is handed the log
#     to fix what it names, and the gate runs again; only a second failure sets the item aside.
#   * an item a session could not finish — it failed, left boxes a command should have
#     ticked, spent its --max-budget-usd, or left uncommitted changes (saved on a side branch
#     `afk/<slug>-leftover-NN-<stamp>`, then reset). It is SET ASIDE for the run; the items
#     that depend on it wait, and every other item is still built.
#
# WHAT DOES STOP IT: a billing error, the --max-spend-usd ceiling, a usage limit that
# outlasts --limit-max-wait (or --on-limit stop), and a second run of the same slug.
#
# WHAT IT REFUSES, and why each refusal exists:
#   * a project the project check does not call set up — every path below is a setting.
#   * a worktree path already checked out on another branch — this loop builds only in a
#     throwaway worktree of its own, never in a tree somebody works in.
#   * a missing or unknown environment, where the project names several — the sessions and the
#     done command work against one, and nobody but the owner may choose it.
#   * a dirty tree, and a preparation (`unattended.prepare`) that leaves files git sees —
#     uncommitted work at the start is work this loop would attribute to an item it did not
#     come from.
#   * an unsound or uncommitted queue — a malformed item is exit 2 before anything is
#     created, and the worktree is cut from HEAD, so the queue has to be committed.
#   * pushing — nothing here reaches the server. The run ends in a branch a person reads.
#
# THE CLOSING SESSION: an unattended session writes what it learned as a line under the item's
# `## To file`. After the last item, when any such line is unticked, ONE more session,
# `/wiqrug:update-knowledge <slug> --unattended`, files each line and ticks it — writing in any
# file it needs. It waits out a usage limit exactly as an item does, and its cost counts toward
# --max-spend-usd. Then the done command runs once on the branch tip.
# ⚠️ It never files a `D:` line: a decision is written in the owner's words, and nobody is there to
# give them. A `D:` line is not counted as one to file; what the session changes in the decisions
# folder (`documents.decisions`) anyway is undone by the loop, and a `D:` line it ticked is opened
# again. The report asks it.
#
# ⚠️ It ends in a BRANCH, never a merge, and in a REPORT: every run renders
# `logs/afk/<slug>/<stamp>/report.md` under the project's root (kept out of git through
# `.git/info/exclude`), in three parts — what was built, reviewed and proved; FOR YOU TO CHECK;
# the spec questions — after one line saying whether the branch's TIP passes the done command.
# The first part ends with the WHOLE BRANCH's review: one more session runs
# `/wiqrug:review-change` on the run's diff, whose two `reviewer` subagents wrote none of the
# code — a session reviewing its own work finds what its reasoning already agreed with — and a
# last session CHECKS each finding: confirmed, refuted only with evidence, else unchecked.
# Every review's cost counts toward --max-spend-usd.
#
# ⚠️ Effort belongs upstream, not here. /wiqrug:grill-with-docs, /wiqrug:to-spec and
# /wiqrug:to-tickets earn a high setting because a wrong call there costs hours and is paid once;
# an item arrives pre-decomposed with acceptance boxes that already name their commands, and is
# paid for N times. Hence the medium default.
#
# ⚠️ `set -e` is deliberately NOT used. Every ending this loop has is a session that did
# not exit 0, and each one means something different to whoever reads it — under `-e` the
# script would die on the first of them and say none of it.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN="$(cd "$HERE/../.." && pwd)"
LIB="$PLUGIN/lib"
ENVIRONMENT=""
SLUG=""
MAX=""
EFFORT=medium
MODEL=""
BUDGET=""
MAX_SPEND=""
FALLBACK=""
ON_LIMIT=wait
LIMIT_WAIT=15
LIMIT_MAX_WAIT=6
DRY=0
FOREGROUND=0
REVIEW=1
ARGS=("$@")
WORKTREE_ROOT="${AFK_ROOT:-$HOME/afk}"

die() { printf '\033[31mafk: %s\033[0m\n' "$*" >&2; exit 2; }
say() { printf '\033[1mafk\033[0m %s\n' "$*"; }

while (($#)); do
  case "$1" in
    --environment)    shift; ENVIRONMENT="${1:-}" ;;
    --max)            shift; MAX="${1:-}" ;;
    --effort)         shift; EFFORT="${1:-}" ;;
    --model)          shift; MODEL="${1:-}" ;;
    --max-budget-usd) shift; BUDGET="${1:-}" ;;
    --max-spend-usd)  shift; MAX_SPEND="${1:-}" ;;
    --fallback-model) shift; FALLBACK="${1:-}" ;;
    --on-limit)       shift; ON_LIMIT="${1:-}" ;;
    --limit-wait)     shift; LIMIT_WAIT="${1:-}" ;;
    --limit-max-wait) shift; LIMIT_MAX_WAIT="${1:-}" ;;
    --dry-run)        DRY=1 ;;
    --no-review)      REVIEW=0 ;;
    --foreground)     FOREGROUND=1 ;;
    -h|--help)        sed -n '/^set -uo pipefail/q;2,$p' "${BASH_SOURCE[0]}"; exit 0 ;;
    -*)               die "unknown option $1" ;;
    *)                SLUG="$1" ;;
  esac
  shift
done

number() { [[ ${2:-} =~ ^[0-9]+([.][0-9]+)?$ ]] || die "$1 needs a number"; }

[[ -z $MAX || $MAX == all ]] || { [[ $MAX =~ ^[0-9]+$ ]] && ((MAX > 0)); } || die "--max needs a positive number, or all"
case "$EFFORT" in low|medium|high|xhigh|max) ;; *) die "--effort: low|medium|high|xhigh|max" ;; esac
case "$ON_LIMIT" in wait|stop) ;; *) die "--on-limit: wait|stop" ;; esac
[[ -z $BUDGET ]] || number --max-budget-usd "$BUDGET"
[[ -z $MAX_SPEND ]] || number --max-spend-usd "$MAX_SPEND"
number --limit-wait "$LIMIT_WAIT"
number --limit-max-wait "$LIMIT_MAX_WAIT"

# ------------------------------------------------------------------ Python, first of all
# Every Python script below runs under the one name `bin/wiqrug-check` found — python3, python or
# py, each probed — and never under a second search of this script's own: two searches could find
# two Pythons, and Windows carries a `python3` that only opens the store. Read through `sh`, so a
# zip that lost the executable bit still runs it. With none, its own "missing" line, exit 2.
PY="$(sh "$PLUGIN/bin/wiqrug-check" --python 2>&1)" || die "$PY"

# ------------------------------------------------------------------ the project, first
# The one reader of the settings file answers for the folder this was started in. Anything but
# "set up" is its own one line, and the run stops there: every path below is a setting, and a
# loop that guessed one would build in the wrong place with nobody watching.
#
# Its answer becomes shell variables here, once: SOURCE_TREE (the git root), QUEUE (the queue
# folder, absolute), DECISIONS (the decisions folder, relative to the root, or empty for `none`),
# DONE (the "done" command, or empty for `none`), OWED_EXIT (or empty),
# PREPARE (an array of commands), ENVIRONMENTS (an array of names) and BROWSER (or empty).
# Each value is quoted by Python's shlex before the shell reads it.
project="$("$PY" "$LIB/project_check.py" --json 2>&1)"
settings="$("$PY" - "$project" <<'PY'
import json, re, shlex, sys
try:
    found = json.loads(sys.argv[1])
except json.JSONDecodeError:
    print("CHECK_FAILED=" + shlex.quote(sys.argv[1].strip() or "the project check printed nothing"))
    raise SystemExit
if found.get("answer") != "set-up":
    print("CHECK_FAILED=" + shlex.quote(found.get("message") or found.get("answer") or "?"))
    raise SystemExit
s = found["settings"]
def text(value):
    return "" if value in (None, "none") else str(value)
# An environment entry is its name, then what it is: the name is the first word.
names = [re.split(r"[\s:,]", entry.strip(), maxsplit=1)[0] for entry in s["environments"]["list"]]
print("CHECK_FAILED=''")
print("SOURCE_TREE=" + shlex.quote(found["root"]))
print("QUEUE=" + shlex.quote(text(s["documents"]["queue"])))
print("DECISIONS=" + shlex.quote(text(s["documents"]["decisions"])))
print("DONE=" + shlex.quote(text(s["done"]["command"])))
print("OWED_EXIT=" + shlex.quote(text(s["done"]["owed-exit"])))
print("BROWSER=" + shlex.quote(text(s["browser"]["check"])))
print("PREPARE=(" + " ".join(shlex.quote(c) for c in s["unattended"]["prepare"]) + ")")
print("ENVIRONMENTS=(" + " ".join(shlex.quote(n) for n in names if n) + ")")
PY
)"
eval "$settings"
[[ -z ${CHECK_FAILED:-} ]] || die "$CHECK_FAILED"
[[ -n $QUEUE ]] || die "documents.queue is \`none\` — this project keeps no work queue"
QUEUE_REL="${QUEUE#"$SOURCE_TREE"/}"
# Relative, as a worktree holds it: the loop compares it in the copy, never the source tree.
DECISIONS="${DECISIONS#"$SOURCE_TREE"/}"
DECISIONS="${DECISIONS%/}"
[[ -n $SLUG ]] || die "a work slug is required — a folder under $QUEUE_REL/"
[[ -d $QUEUE/$SLUG ]] || die "no $QUEUE_REL/$SLUG"

# The environment: the owner's to name where the project has several, the one there is where it
# has one, and nothing where it has none. A session is told which, and so is the done command.
if ((${#ENVIRONMENTS[@]} == 0)); then
  [[ -z $ENVIRONMENT ]] || die "--environment $ENVIRONMENT: this project names no environments (environments.list is none)"
elif ((${#ENVIRONMENTS[@]} == 1)); then
  [[ -z $ENVIRONMENT || $ENVIRONMENT == "${ENVIRONMENTS[0]}" ]] \
    || die "--environment $ENVIRONMENT: this project's one environment is ${ENVIRONMENTS[0]}"
  ENVIRONMENT="${ENVIRONMENTS[0]}"
else
  [[ -n $ENVIRONMENT ]] || die "--environment is required: one of ${ENVIRONMENTS[*]} — the owner names it, never the model"
  [[ " ${ENVIRONMENTS[*]} " == *" $ENVIRONMENT "* ]] \
    || die "--environment $ENVIRONMENT is not one of this project's: ${ENVIRONMENTS[*]}"
fi
export WIQRUG_ENVIRONMENT="$ENVIRONMENT"

WAIT_S=$("$PY" -c "print(int(float('$LIMIT_WAIT') * 60))")
WAIT_CAP_S=$("$PY" -c "print(int(float('$LIMIT_MAX_WAIT') * 3600))")

# work_next <tree> <args…> — the queue reader, for the project that <tree> is a copy of.
work_next() { local tree="$1"; shift; "$PY" "$LIB/work_next.py" "$@" --project "$tree"; }

# ------------------------------------------------------------------ the queue, first
# Nothing is created until the queue is known to be sound: a malformed item is exit 2
# here, so a run never starts against a folder it would have to give up on.
work_next "$SOURCE_TREE" "$SLUG" --all || die "the queue is not sound — fix it first"

READY="$(work_next "$SOURCE_TREE" "$SLUG" --unattended 2>/dev/null || true)"
[[ -n $READY ]] || die "nothing is ready in $SLUG (work_next.py $SLUG --all says why)"

# Five by default: a run is sized so its branch can still be read, and every item in it rests on
# the ones before. One attempt per item is the most a run makes, since an item that did not
# finish is set aside rather than retried.
[[ -n $MAX ]] || MAX=5

# ⚠️ One run per slug. Two loops draining one worktree would each commit the other's work.
# The lock is a FOLDER, `<slug>.lock/`, because `mkdir` succeeds for exactly one caller on every
# system — Git Bash has no `flock`. Its `pid` file names the run that holds it, and this run
# removes it when it ends, however it ends (the EXIT trap; a `die` included).
# The stale-lock rule: a folder whose `pid` names no running process belongs to a run that ended
# without removing it — killed with -9, or the machine went down — and is taken. A folder with no
# `pid` file, or one naming a live process, is a run going: refused, naming the folder to remove
# by hand if the owner knows better. A detaching run HANDS its lock to its child: the child, told
# the parent's pid, takes over the folder and writes its own.
LOCK="$WORKTREE_ROOT/$SLUG.lock"
release_lock() { [[ $(cat "$LOCK/pid" 2>/dev/null) == "$$" ]] && rm -rf "$LOCK"; return 0; }
mkdir -p "$WORKTREE_ROOT"
if ! mkdir "$LOCK" 2>/dev/null; then
  holder="$(cat "$LOCK/pid" 2>/dev/null || true)"
  if [[ -n ${AFK_LOCK_FROM:-} && $holder == "$AFK_LOCK_FROM" ]]; then
    :                                           # handed over by the run that detached this one
  elif [[ $holder =~ ^[0-9]+$ ]] && ! kill -0 "$holder" 2>/dev/null; then
    say "a stale lock from run $holder, which is no longer running — taking it"
    rm -rf "$LOCK"
    mkdir "$LOCK" 2>/dev/null || die "another run of $SLUG took the lock first — its output is under logs/afk/$SLUG/"
  else
    die "another run of $SLUG is going${holder:+ (pid $holder)} — its output is under logs/afk/$SLUG/.
    If none is, remove the lock folder: rm -r $LOCK"
  fi
fi
printf '%s\n' "$$" > "$LOCK/pid"
trap release_lock EXIT
unset AFK_LOCK_FROM                             # this run's alone, not its sessions'

# ------------------------------------------------------------------- the worktree
WORKTREE="$WORKTREE_ROOT/$SLUG"
BRANCH="afk/$SLUG"
# The branch the source tree stands on: what the worktree is cut from, and what a finished run's
# branch is merged into. Empty on a detached HEAD.
BASE_BRANCH="$(git -C "$SOURCE_TREE" symbolic-ref --short -q HEAD || true)"

# An existing folder at the worktree's place is this loop's only when it is a checkout of its own
# branch: anything else is a tree somebody works in, or the project itself.
if [[ -d $WORKTREE ]]; then
  here="$(git -C "$WORKTREE" symbolic-ref --short -q HEAD 2>/dev/null || true)"
  [[ $here == "$BRANCH" ]] \
    || die "refusing: $WORKTREE is ${here:+checked out on $here, }not a worktree of $BRANCH — this loop builds only in a worktree of its own"
fi

# ⚠️ An existing branch is reused as it is, which is right for RESUMING a stopped run — its
# ticked boxes live there — and wrong once the base branch holds everything the branch has and
# has moved on: every item would be built against the code the base has since replaced. Equal
# to the base is not stale, and a branch with a commit the base lacks is a run to resume.
if [[ -n $BASE_BRANCH && $BASE_BRANCH != "$BRANCH" ]] \
   && git -C "$SOURCE_TREE" rev-parse --verify --quiet "refs/heads/$BRANCH" >/dev/null \
   && [[ $(git -C "$SOURCE_TREE" rev-parse "$BRANCH") != $(git -C "$SOURCE_TREE" rev-parse "$BASE_BRANCH") ]] \
   && git -C "$SOURCE_TREE" merge-base --is-ancestor "$BRANCH" "$BASE_BRANCH"; then
  remove=""
  [[ -d $WORKTREE ]] && remove="git -C $SOURCE_TREE worktree remove $WORKTREE && "
  die "refusing: $BRANCH${remove:+ (worktree $WORKTREE)} is already merged into $BASE_BRANCH, and $BASE_BRANCH has moved on. A run would build against the code $BASE_BRANCH replaced. Remove it, and the next run cuts fresh from $BASE_BRANCH:
    ${remove}git -C $SOURCE_TREE branch -d $BRANCH"
fi

# ⚠️ Reuse the branch when it is already there. A second run after the worktree was
# removed used to die with "could not create the worktree", because `-b` refuses a branch
# that exists — a confusing message for the ordinary case of running this twice.
if [[ ! -d $WORKTREE ]]; then
  if git -C "$SOURCE_TREE" rev-parse --verify --quiet "refs/heads/$BRANCH" >/dev/null; then
    ((DRY)) && say "would reuse existing branch $BRANCH in a new worktree $WORKTREE" || {
      git -C "$SOURCE_TREE" worktree add "$WORKTREE" "$BRANCH" \
        || die "could not attach a worktree to the existing $BRANCH"
    }
  else
    ((DRY)) && say "would create worktree $WORKTREE on a new branch $BRANCH" || {
      git -C "$SOURCE_TREE" worktree add "$WORKTREE" -b "$BRANCH" HEAD \
        || die "could not create the worktree"
    }
  fi
else
  say "reusing worktree $WORKTREE"
fi

if ((DRY == 0)); then
  [[ -d $WORKTREE ]] || die "no worktree at $WORKTREE"
  [[ -z "$(git -C "$WORKTREE" status --porcelain)" ]] \
    || die "$WORKTREE is dirty — commit or discard before an unattended run"

  # A fresh copy lacks what git does not carry — installed dependencies, generated files. The
  # project's own commands (`unattended.prepare`) make it ready, in order, from its root, once per
  # worktree: the mark lives in the worktree's own git folder, so removing the worktree removes
  # it. AFK_SOURCE_TREE names the tree this was started in, for a command that links from it.
  # ⚠️ What they leave must be ignored by git, or the first item reads as dirty and every
  # leftover branch carries it: that is refused here, naming the files.
  prepared="$(git -C "$WORKTREE" rev-parse --path-format=absolute --git-dir)/wiqrug-prepared"
  if ((${#PREPARE[@]})) && [[ ! -e $prepared ]]; then
    for command in "${PREPARE[@]}"; do
      say "preparing the worktree: $command"
      (cd "$WORKTREE" && AFK_SOURCE_TREE="$SOURCE_TREE" bash -c "$command") \
        || die "unattended.prepare failed: $command"
    done
    left="$(git -C "$WORKTREE" status --porcelain)"
    [[ -z $left ]] || die "unattended.prepare left files git sees in $WORKTREE — ignore them in the project's .gitignore:
$left"
    : > "$prepared"
  fi
fi

STAMP="${AFK_STAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"
LOGS="$SOURCE_TREE/logs/afk/$SLUG/$STAMP"
if ((DRY == 0)); then
  mkdir -p "$LOGS"
  # The run's logs live in the project's tree, where a person looks, and are never committed:
  # excluded for this clone only, so the project's own .gitignore is not edited.
  exclude="$(git -C "$SOURCE_TREE" rev-parse --path-format=absolute --git-common-dir)/info/exclude"
  mkdir -p "$(dirname "$exclude")"
  grep -qxF "/logs/afk/" "$exclude" 2>/dev/null || printf '/logs/afk/\n' >> "$exclude"
fi

# Denied on purpose: the push needs a credential a person types, and nothing an unattended
# run does may reach the server.
DENY='Bash(git push*)'

CLAUDE_FLAGS=(--output-format stream-json --verbose --disallowedTools "$DENY"
              --effort "$EFFORT" --permission-prompts none)
[[ -n $MODEL ]]    && CLAUDE_FLAGS+=(--model "$MODEL")
[[ -n $BUDGET ]]   && CLAUDE_FLAGS+=(--max-budget-usd "$BUDGET")
[[ -n $FALLBACK ]] && CLAUDE_FLAGS+=(--fallback-model "$FALLBACK")
# A review session — an item's, the branch's, and the check — reads the run's logs; the reviewers
# are its subagents, and the check only reads.
REVIEW_FLAGS=(--add-dir "$LOGS" --disallowedTools "$DENY"
              --output-format stream-json --verbose --permission-prompts none)
[[ -n $MODEL ]]  && REVIEW_FLAGS+=(--model "$MODEL")
[[ -n $BUDGET ]] && REVIEW_FLAGS+=(--max-budget-usd "$BUDGET")

# ---------------------------------------------------------------- reading a run back
# `system/api_retry` events carry an `error` category, and they mean three different
# things that must not share one word:
#
#   rate_limit     — the usage window is full. It RESETS. Waiting fixes it, and with
#                    --on-limit wait this run waits and retries the same item.
#   billing_error  — there is no credit, or the account cannot be charged. Nothing
#                    resets, so waiting is an unattended run spinning until its cap.
#   anything else  — the work failed, and somebody has to read the log.
#
# ⚠️ A full usage window arrives in a SECOND shape too, and it is the one measured on a real
# run of the loop this was ported from: no `api_retry` at all, but a
# `rate_limit_event` whose status is `rejected`, an assistant message carrying
# `"error": "rate_limit"`, and a `result` with `api_error_status: 429`. Read as "failed",
# it set the item aside and ended the run at the limit instead of waiting it out. Any one
# of the three is a limit. `allowed` and `allowed_warning` are the ordinary stream of a
# healthy session and mean nothing here.
#
# ⚠️ A budget ceiling is told apart LAST and on evidence: a `result.subtype` naming the
# budget when one is given, else the cumulative spend having reached the ceiling. Neither
# is guessed — when neither holds, this says "failed" and points at the log.
verdict() {
  "$PY" - "$1" <<'PY'
import json, sys

limited = billing = budget = False
cost = 0.0
try:
    with open(sys.argv[1], encoding="utf-8", errors="replace") as handle:
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
            if event.get("subtype") == "api_retry":
                if event.get("error") == "rate_limit":
                    limited = True
                elif event.get("error") == "billing_error":
                    billing = True
            info = event.get("rate_limit_info")
            if event.get("type") == "rate_limit_event" and isinstance(info, dict) \
                    and info.get("status") == "rejected":
                limited = True
            if event.get("type") == "assistant" and event.get("error") == "rate_limit":
                limited = True
            if event.get("type") == "result":
                cost = event.get("total_cost_usd") or cost
                if event.get("api_error_status") == 429:
                    limited = True
                if "budget" in str(event.get("subtype", "")).lower():
                    budget = True
except OSError:
    pass
why = "limited" if limited else "billing" if billing else "budget" if budget else "failed"
print(f"{why} {cost:.4f}")
PY
}

record() {                     # record <item> <status> <before> <after> <cost> <log>
  ((DRY)) && return 0
  "$PY" - "$LOGS/run.jsonl" "$@" <<'PY'
import json, sys
out, item, status, before, after, cost, log = sys.argv[1:8]
with open(out, "a", encoding="utf-8") as handle:
    handle.write(json.dumps({"item": item, "status": status, "before": before,
                             "after": after, "cost": float(cost), "log": log}) + "\n")
PY
}

add() { "$PY" -c "print(f'{float('$1') + float('$2'):.4f}')"; }

# ⚠️ Whether an item is finished is `work_next.py`'s decision and nothing else's. This used
# to be a `grep` for an unticked box anywhere in the file, which is a SECOND answer to a
# question that already had one: the parser counts boxes under `## Acceptance` only, so an
# unticked box in a Comments block made the loop stop on an item the queue calls done.
item_state() {                  # item_state <item path> -> "<state>\t<why>"
  local json
  json="$(work_next "$QUEUE_ROOT" "$SLUG" --json 2>/dev/null || true)"
  [[ -n $json ]] || { printf 'unknown\tthe queue could not be read'; return 0; }
  printf '%s' "$json" | "$PY" -c 'import json, sys
rows = json.load(sys.stdin)
row = next((r for r in rows if r["path"] == sys.argv[1]), None)
print("unknown\tno such item in the queue" if row is None
      else row["state"] + "\t" + row["why"])' "$1"
}

# done_box <item> [<mark>] — exit 0 when the item's ## Acceptance holds an older queue's done box,
# and with <mark> set that box's mark to x, ~ or a space. Which box that is, is the queue reader's
# `is_done_box` — never a second test here — so the box the loop adds when the code gate fails is
# never mistaken for it. Only a box under ## Acceptance: a Comments line quoting the command is not.
done_box() {
  "$PY" - "$LIB" "$WORKTREE/$1" "$DONE" "${2:-}" <<'PY'
import re, sys
sys.dont_write_bytecode = True
sys.path.insert(0, sys.argv[1])
from pathlib import Path
from work_next import is_done_box
path, done, mark = Path(sys.argv[2]), sys.argv[3], sys.argv[4]
lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
inside = found = False
for at, line in enumerate(lines):
    if line.startswith("## "):
        inside = line.strip() == "## Acceptance"
        continue
    box = re.match(r"^(\s*-\s*)\[[ xX~]\]\s*(.*)$", line, re.DOTALL)
    if inside and box and is_done_box(box.group(2), done):
        found = True
        if mark:
            lines[at] = re.sub(r"\[[ xX~]\]", f"[{mark}]", line, count=1)
if mark and found:
    path.write_text("".join(lines), encoding="utf-8")
raise SystemExit(0 if found else 1)
PY
}

# run_verify <log> — the done command at the worktree's HEAD. Sets VERIFY_RC, and VERIFIED_AT to
# the commit it judged, so the end of the run knows whether the tip was ever checked.
run_verify() {
  (cd "$WORKTREE" && bash -c "$DONE") > "$1" 2>&1
  VERIFY_RC=$?
  VERIFIED_AT="$(git -C "$WORKTREE" rev-parse HEAD)"
  VERIFY_LOG="$1"
}

# gate_passes — the last run of the done command passed the gate: exit 0, or `done.owed-exit`.
gate_passes() { ((VERIFY_RC == 0)) || [[ -n $OWED_EXIT && $VERIFY_RC == "$OWED_EXIT" ]]; }

# code_gate <item> — THE CODE GATE: the project's done command at the item's LAST commit, whatever
# the session said. Exit 0 passes; `done.owed-exit` passes too — every check it could run passed,
# and what only a running environment checks goes to the report. Anything else fails. No box is
# marked: an item carries no done box now, and an older queue's is settled on the branch tip
# (check_tip). A `gate` row in run.jsonl records each judgement, which the report reads.
#
# ⚠️ It runs at the last commit, not the one the session judged. A session runs the checks, then
# commits its write-up — and that last commit is the one nothing checked.
GATED_AT=""
code_gate() {
  local item="$1" head
  [[ -n $DONE ]] || return 0
  # A commit the gate already passed is not judged twice: a review that fixed nothing moves
  # nothing, and its second judgement would only cost time.
  head="$(git -C "$WORKTREE" rev-parse HEAD)"
  [[ $head == "$GATED_AT" ]] && return 0
  run_verify "$LOGS/$(basename "$item" .md).gate.log"
  "$PY" - "$LOGS/run.jsonl" "$item" "$VERIFY_RC" "$VERIFY_LOG" "$head" <<'PY'
import json, sys
out, item, rc, log, head = sys.argv[1:6]
with open(out, "a", encoding="utf-8") as handle:
    handle.write(json.dumps({"kind": "gate", "item": item, "rc": int(rc), "log": log,
                             "head": head}) + "\n")
PY
  if ! gate_passes; then
    say "       the code gate FAILED (the done command exited $VERIFY_RC) at $item's last commit;"
    say "       read ${VERIFY_LOG#"$SOURCE_TREE"/}"
    return 1
  fi
  GATED_AT="$head"
  if ((VERIFY_RC == 0)); then say "       the code gate passed at its last commit"
  else say "       the code gate passed (exit $VERIFY_RC): what only a running environment checks goes to the report"
  fi
}

# session_id <transcript> — the item session's id, read where the report reads it: two readers
# of one transcript format would be two answers to one question.
session_id() {
  [[ -n ${1:-} && -f ${1:-} ]] || return 0
  "$PY" -c 'import sys
sys.dont_write_bytecode = True
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import afk_report
print(afk_report.read_transcript(Path(sys.argv[2]))[3])' "$LIB" "$1"
}

# repair_gate <item> <transcript> — ONE more session when the code gate failed at the item's
# last commit: it is handed the log and asked to fix what it names, and the gate judges again.
# Exit 0 only when the second judgement passes. It resumes the item's own session when the
# transcript names one, so it keeps what it knew; otherwise a fresh one reads the item.
# ⚠️ Without it, one fault in a write-up set an item aside and every item behind it waited: a
# twelve-item run once ended after three, for a fix of one path.
# One attempt, never a loop — a failure the session cannot see in the log is a person's.
REPAIR_COST=0
repair_gate() {
  local item="$1" transcript="$2" log id resume=() prompt rel
  REPAIR_COST=0
  log="$LOGS/$(basename "$item" .md).repair.jsonl"
  rel="${VERIFY_LOG#"$SOURCE_TREE"/}"
  id="$(session_id "$transcript")"
  [[ -n $id ]] && resume=(--resume "$id")
  prompt="The afk loop ran the code gate, the project's done command $DONE, at the last commit of
$item and it exited $VERIFY_RC. Its log is $VERIFY_LOG — read it first. Fix exactly what it
names, in whichever file it names; nothing else. If a ## Comments line in the item says a check
passed, correct it. Run the done command again; commit when it exits 0${OWED_EXIT:+ or $OWED_EXIT}.
If the log names something you cannot fix, commit nothing and say why in one line."
  say "       one repair: a session is handed ${rel} ($([[ -n $id ]] && echo "resuming $id" || echo "a fresh session"))"
  if ! (cd "$WORKTREE" && AFK_SOURCE_TREE="$SOURCE_TREE" claude -p "$prompt" "${resume[@]}" "${CLAUDE_FLAGS[@]}" \
          < /dev/null > "$log" 2>&1); then
    read -r _ REPAIR_COST <<<"$(verdict "$log")"
    say "       the repair session did not exit 0 — read ${log#"$SOURCE_TREE"/}"
    return 1
  fi
  read -r _ REPAIR_COST <<<"$(verdict "$log")"
  if [[ -n "$(git -C "$WORKTREE" status --porcelain)" ]]; then
    say "       the repair left uncommitted changes — kept on $(keep_leftovers "$item" repair)"
    return 1
  fi
  code_gate "$item"
}

# gate_box <item> — the code gate failed, and one repair did not fix it: the loop ADDS an open box
# naming the gate to the item's ## Acceptance, and commits it. Nothing else in the file would say
# so — an item carries no done box now — and an item whose boxes are all ticked reads as done:
# what depends on it would be built on code that does not pass, this run and the next. The box
# holds it open; the next run offers it again, and its session closes it like any box. It opens
# with the queue reader's GATE_BOX, which is what keeps it from reading as an older queue's done box.
gate_box() {
  local item="$1" head
  head="$(git -C "$WORKTREE" rev-parse --short HEAD)"
  "$PY" - "$LIB" "$WORKTREE/$item" "$VERIFY_RC" "$head" "${VERIFY_LOG#"$SOURCE_TREE"/}" \
          "$DONE" "$OWED_EXIT" <<'PY'
import re, sys
sys.dont_write_bytecode = True
sys.path.insert(0, sys.argv[1])
from work_next import GATE_BOX
path, rc, head, log, done, owed = sys.argv[2:8]
# A command holding a backtick is written bare: a box with an unclosed backtick reads as damaged.
command = done if "`" in done else f"`{done}`"
box = (f"- [ ] {GATE_BOX} at this item's last commit: {command} exits 0"
       f"{f' or {owed}' if owed else ''} — it exited {rc} at {head} and one repair did not "
       f"fix it; the loop added this box (its log: {log})")
lines = open(path, encoding="utf-8").read().split("\n")
start = next((i for i, line in enumerate(lines) if re.match(r"^## Acceptance\s*$", line)), None)
if start is None:
    raise SystemExit(0)
end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
last = max((i for i in range(start + 1, end) if re.match(r"^\s*- \[[ xX~]\] ", lines[i])),
           default=start)
lines.insert(last + 1, box)
open(path, "w", encoding="utf-8").write("\n".join(lines))
PY
  git -C "$WORKTREE" add -- "$item"
  if ! git -C "$WORKTREE" commit -qm "afk: $(basename "$item" .md) — the code gate exited $VERIFY_RC; a box holds it open" -- "$item"; then
    # Undone, not left: the next item's session would be blamed for the uncommitted edit.
    git -C "$WORKTREE" reset -q -- "$item"; git -C "$WORKTREE" checkout -q -- "$item"
    say "       ⚠️  the code gate's box could not be committed, so the item may read as done — read ${VERIFY_LOG#"$SOURCE_TREE"/}"
  fi
}

# set_aside <item> <why> — this item is not offered again in this run.
# boxes_damaged <item> <before> — why the session's edit broke the item's own acceptance, or
# nothing. A box that vanished cannot show as open, and a box whose backtick is unclosed has
# lost its tail, "— **for a person**" included, so it reads as one a command should close.
# ⚠️ Both happened to two items of one real run: a session found the browser section by
# searching for its heading, matched the box that quotes it, and rewrote from there.
boxes_damaged() {
  "$PY" - "$WORKTREE/$1" <(git -C "$WORKTREE" show "$2:$1" 2>/dev/null) <<'PY'
import re, sys

def boxes(path: str) -> list[str]:
    try:
        text = open(path, encoding="utf-8").read()
    except OSError:
        return []
    section = re.split(r"(?m)^## Acceptance\s*$", text, maxsplit=1)
    if len(section) < 2:
        return []
    body = re.split(r"(?m)^## ", section[1], maxsplit=1)[0]
    return [line for line in body.splitlines() if re.match(r"^- \[[ x~]\] ", line)]

now, then = boxes(sys.argv[1]), boxes(sys.argv[2])
why = []
if len(now) < len(then):
    why.append(f"its session deleted {len(then) - len(now)} acceptance box(es)")
broken = [b for b in now if b.count("`") % 2]
if broken:
    why.append(f"{len(broken)} box line(s) have an unclosed backtick")
print("; ".join(why))
PY
}

set_aside() {
  export WORK_NEXT_SET_ASIDE="${WORK_NEXT_SET_ASIDE:-} $(basename "$1" | cut -c1-2)"
  aside+=("$(basename "$1" .md) — $2")
  say "       set aside: $2. What depends on it waits; the rest of the queue goes on."
}

# check_tip — the branch a person is handed is judged at its tip, once, whatever the items
# said. A set-aside session's commits, a reset after leftovers and the closing session all move
# HEAD past the last done-command run, so the tip is re-run unless it is exactly the commit last
# checked. The answer is a `tip` row in run.jsonl, which the report prints above everything else.
#
# It also closes the done box of every item this run settled from an older queue: 0 ticks it,
# `done.owed-exit` marks it `[~]`, anything else leaves it open. That mark is committed on its
# own, after the commit the done command judged — it changes only the item files.
check_tip() {
  local head rel
  [[ -n $DONE ]] || return 0
  [[ -n $(git -C "$WORKTREE" rev-list "$RUN_BASE..HEAD" 2>/dev/null) || ${#aside[@]} -gt 0 ]] \
    || return 0
  head="$(git -C "$WORKTREE" rev-parse HEAD)"
  [[ $head == "${VERIFIED_AT:-}" ]] || run_verify "$LOGS/tip.verify.log"
  rel="${VERIFY_LOG#"$SOURCE_TREE"/}"
  if ((VERIFY_RC == 0)); then
    say "the branch tip ${head:0:12} passes the done command"
  elif [[ -n $OWED_EXIT && $VERIFY_RC == "$OWED_EXIT" ]]; then
    say "the branch tip ${head:0:12} passes every check the done command could run; the rest is owed after the merge"
  else
    say "⚠️  the branch tip ${head:0:12} FAILS the done command (exit $VERIFY_RC) — read $rel"
  fi
  close_done_boxes "$VERIFY_RC"
  "$PY" - "$LOGS/run.jsonl" "$head" "$VERIFY_RC" "$VERIFY_LOG" <<'PY'
import json, sys
out, head, rc, log = sys.argv[1:5]
with open(out, "a", encoding="utf-8") as handle:
    handle.write(json.dumps({"kind": "tip", "head": head, "rc": int(rc), "log": log}) + "\n")
PY
}

# close_done_boxes <rc> — an older queue's done box on every item THIS run settled, set from the
# tip's done command: 0 ticks it, `done.owed-exit` marks it `[~]`, anything else reopens it. The
# tip holds those items' work, and the box asks exactly this question — so the tip's answer is
# the box's, whatever this run's session marked (a session ticks the box, then its write-up
# breaks the check). An item of an earlier run is never touched: its box was settled by that
# run's tip, and a fresh copy's tip exits `done.owed-exit` whenever an environment is needed, so
# rewriting it would turn every finished item owed.
close_done_boxes() {
  local mark item changed=()
  if (($1 == 0)); then mark=x
  elif [[ -n $OWED_EXIT && $1 == "$OWED_EXIT" ]]; then mark="~"
  else mark=" "
  fi
  for item in "${settled_items[@]}"; do
    done_box "$item" "$mark" || continue
    git -C "$WORKTREE" diff --quiet -- "$item" || changed+=("$item")
  done
  ((${#changed[@]})) || return 0
  git -C "$WORKTREE" add -- "${changed[@]}"
  if git -C "$WORKTREE" commit -qm "afk: the tip's done command exited $1 — the done box of ${#changed[@]} item(s) set [$mark]" \
       -- "${changed[@]}"; then
    say "       the done box of ${#changed[@]} item(s) from an older queue is now [$mark]"
  else
    git -C "$WORKTREE" reset -q -- "${changed[@]}"; git -C "$WORKTREE" checkout -q -- "${changed[@]}"
    say "       ⚠️  the done boxes could not be committed — left as the sessions marked them"
  fi
}

# may_wait — exit 0 when a usage limit is to be waited out: --on-limit wait, and another
# --limit-wait still fits under --limit-max-wait. limit_wait <what> <retrying what> [<note>]
# then says so and sleeps. ⚠️ Every session this loop starts — an item, the filing, the
# review — waits through these two and only these: `waited` is the run's one budget of
# waiting, and a third copy of the arithmetic is the one that would forget to add to it.
may_wait() { [[ $ON_LIMIT == wait ]] && ((waited + WAIT_S <= WAIT_CAP_S)); }
limit_wait() {
  say "rate limited on $1 — waiting ${LIMIT_WAIT}m, then retrying $2"
  say "       (${3:+$3, }$((waited / 60))m waited so far of ${LIMIT_MAX_WAIT}h)"
  sleep "$WAIT_S"
  waited=$((waited + WAIT_S))
}

# review_branch <why-not> — the run's whole diff is reviewed once, at the end, along two axes
# (`/wiqrug:review-change`: Standards and Spec, two reviewer subagents), and then every finding is
# checked by one more session. It writes `review.md` (the reviewers' report) and `check.md`
# (the verdicts) beside the transcripts and a `review` row in run.jsonl, which the report
# prints first. An empty <why-not> means review; anything else is recorded as the reason there
# was no review — never silence, because a report with no review section reads as a branch
# somebody already looked at.
#
# ⚠️ Why a check at all: a reviewer's finding is a claim, and one real run handed over twenty
# of them that nobody verified. The check changes nothing; it
# only says which claims hold. Its verdict rule — a "refuted" with no evidence is unchecked —
# lives in afk_report.py, which renders it, so it is held there and nowhere else.
#
# ⚠️ A usage limit waits, on the same terms as an item — --on-limit, --limit-wait, and what
# is left of --limit-max-wait. A real run filled its window on its last item and so lost the
# review too; an unattended run that ends at the limit should end
# reviewed. Any other failure is one attempt: it costs the review, not the branch, and the
# report says it did not happen and why.
# keep_leftovers <item> [suffix] — commit what a session left uncommitted onto a side branch,
# reset the worktree to its last commit, and print the branch's name.
keep_leftovers() {
  local tag; tag="$(basename "$1" .md)"
  [[ $tag =~ ^([0-9]{2})- ]] && tag="${BASH_REMATCH[1]}"
  local leftover="afk/$SLUG-leftover-$tag-$STAMP${2:+-$2}"
  git -C "$WORKTREE" add -A
  # ⚠️ Branch and reset only on a commit that happened: after a failed one, HEAD~1 is the
  # session's last REAL commit, and the reset would throw it away.
  if ! git -C "$WORKTREE" commit -qm "afk: what the session for $(basename "$1" .md) left uncommitted"; then
    printf 'nothing — its commit failed, so the changes are still in the worktree'
    return 0
  fi
  git -C "$WORKTREE" branch "$leftover"
  git -C "$WORKTREE" reset -q --hard HEAD~1
  printf '%s' "$leftover"
}

# end_session <what> <log> <prompt> <flag…> — one end-of-run session that changes no code:
# the review or the check. It waits out a usage limit through may_wait/limit_wait, adds its
# cost to the spend and to END_COST, and sets END_WHY to "" when it exited 0, else to why not,
# in words. Whatever it left uncommitted in a clean tree is kept on a side branch.
#
# ⚠️ Both sessions hold Bash, so "changes nothing" is an instruction, not a restriction. HEAD is
# recorded before and compared after: a session that committed fails its row, and the commits
# stay on the branch, named, for a person to read — never reset away unseen.
end_session() {
  local what="$1" log="$2" prompt="$3" why="" cost=0 before head; shift 3
  before="$(git -C "$WORKTREE" status --porcelain)"
  head="$(git -C "$WORKTREE" rev-parse HEAD)"
  while ! (cd "$WORKTREE" && claude -p "$prompt" "$@" < /dev/null > "$log" 2>&1); do
    read -r why cost <<<"$(verdict "$log")"
    [[ $why == limited ]] && may_wait || break
    spent="$(add "$spent" "$cost")"; END_COST="$(add "$END_COST" "$cost")"
    limit_wait "$what" "it"
    why=""
  done
  read -r _ cost <<<"$(verdict "$log")"
  spent="$(add "$spent" "$cost")"; END_COST="$(add "$END_COST" "$cost")"
  case $why in
    "")      END_WHY="" ;;
    limited) END_WHY="a usage limit — run it again later, or read the diff unreviewed" ;;
    billing) END_WHY="a billing error" ;;
    budget)  END_WHY="it spent its --max-budget-usd" ;;
    *)       END_WHY="the session did not exit 0" ;;
  esac
  local now; now="$(git -C "$WORKTREE" rev-parse HEAD)"
  if [[ $now != "$head" ]]; then
    END_WHY="it committed to the branch (${head:0:12}..${now:0:12}), and it must change nothing — read those commits before merging"
  fi
  # Only what the session itself left: a tree already dirty before it is the loop's to explain.
  if [[ -z $before && -n "$(git -C "$WORKTREE" status --porcelain)" ]]; then
    say "       $what left uncommitted changes — kept on $(keep_leftovers "${what// /-}")"
  fi
}

review_branch() {
  local skip="$1" log="$LOGS/review.jsonl" check_log="$LOGS/check.jsonl"
  local status=reviewed why="" check=none check_why="" spec="$QUEUE_REL/$SLUG/understanding.md"
  local flags=("${REVIEW_FLAGS[@]}")
  END_COST=0
  if [[ -n $skip ]]; then
    status=skipped; why="$skip"; log=""; check_log=""
    say "not reviewed: $why"
  else
    [[ -f $WORKTREE/$spec ]] || spec=""
    say "reviewing the branch — /wiqrug:review-change: a Standards and a Spec reviewer, read-only"
    end_session "the review" "$log" "$(review_prompt "$spec")" "${flags[@]}" \
      --tools Read,Grep,Glob,Bash,Agent,Skill
    why="$END_WHY"
    if [[ -z $why ]]; then
      final_text "$log" > "$LOGS/review.md"
      [[ -s $LOGS/review.md ]] || why="the session ended without a review"
    fi
    if [[ -n $why ]]; then
      status=failed; check_log=""
      say "⚠️  NOT reviewed: $why — read ${log#"$SOURCE_TREE"/}"
    else
      say "       the review is in ${LOGS#"$SOURCE_TREE"/}/review.md — checking each finding, one more session"
      end_session "the check" "$check_log" "$(check_prompt "$LOGS/review.md")" "${flags[@]}" \
        --tools Read,Grep,Glob,Bash
      check_why="$END_WHY"
      if [[ -z $check_why ]]; then
        final_text "$check_log" > "$LOGS/check.md"
        [[ -s $LOGS/check.md ]] && check=checked || check_why="the session ended without an answer"
      fi
      [[ -n $check_why ]] && { check=failed; say "⚠️  the findings were NOT checked: $check_why — read ${check_log#"$SOURCE_TREE"/}"; }
    fi
  fi
  "$PY" -c 'import json, sys
out, status, why, cost, log, check, check_why, check_log = sys.argv[1:9]
with open(out, "a", encoding="utf-8") as handle:
    handle.write(json.dumps({"kind": "review", "status": status, "why": why,
                             "cost": float(cost), "log": log, "check": check,
                             "check_why": check_why, "check_log": check_log}) + "\n")' \
    "$LOGS/run.jsonl" "$status" "$why" "$END_COST" "$log" "$check" "$check_why" "$check_log"
}

# review_item <item> <before> <transcript> — the item's own review, before the next item starts.
# A review session runs `/wiqrug:review-change <before> <item>` — Standards and Spec on this
# item's diff only, changing nothing — and then the item's OWN session, resumed, is handed the
# findings: it fixes what it confirms, refutes only with evidence, and writes a gap in the spec
# as a `Spec question:` line rather than code. The fix is judged like the build: the caller
# runs the code gate again. An `item-review` row in run.jsonl says what happened, which the
# report reads beside the item.
#
# ⚠️ Why the item's own session fixes: it knows why the code is the way it is, so it can tell a
# real defect from a misreading — and why a separate session reviews: a session reviewing its
# own work finds what its reasoning already agreed with. One real run reviewed once, at the end,
# after thirteen items: its worst finding sat in the first item, under all the others.
ITEM_COST=0
FIX_STOP=0
review_item() {
  local item="$1" before="$2" transcript="$3" stem status=reviewed why="" fix=none fix_why=""
  local review_log fix_log id resume=() cost head
  stem="$LOGS/$(basename "$item" .md)"
  review_log="$stem.review.jsonl"; fix_log="$stem.fix.jsonl"
  ITEM_COST=0; FIX_STOP=0
  if ((REVIEW == 0)); then
    status=skipped; why="--no-review"; review_log=""; fix_log=""
  elif git -C "$WORKTREE" diff --quiet "$before" HEAD; then
    status=skipped; why="the item committed no change, so there is no diff to read"; review_log=""; fix_log=""
  else
    say "       reviewing the item — /wiqrug:review-change since ${before:0:12}: Standards and Spec, read-only"
    END_COST=0
    end_session "the review of $(basename "$item" .md)" "$review_log" \
      "$(item_review_prompt "$item" "$before")" "${REVIEW_FLAGS[@]}" --tools Read,Grep,Glob,Bash,Agent,Skill
    ITEM_COST="$END_COST"; why="$END_WHY"
    if [[ -z $why ]]; then
      final_text "$review_log" > "$stem.review.md"
      [[ -s $stem.review.md ]] || why="the session ended without a review"
    fi
  fi
  [[ $why == "a usage limit"* || $why == "a billing error" ]] && FIX_STOP=1
  if [[ $status == reviewed && -n $why ]]; then
    status=failed; fix_log=""
    say "⚠️       NOT reviewed: $why — read ${review_log#"$SOURCE_TREE"/}"
  elif [[ $status == reviewed ]]; then
    id="$(session_id "$transcript")"
    resume=()
    [[ -n $id ]] && resume=(--resume "$id")
    say "       its own session checks and fixes each finding ($([[ -n $id ]] && echo "resuming $id" || echo "a fresh session"))"
    head="$(git -C "$WORKTREE" rev-parse HEAD)"
    fix=fixed
    while ! (cd "$WORKTREE" && AFK_SOURCE_TREE="$SOURCE_TREE" claude -p "$(fix_prompt "$item" "$before" "$stem.review.md")" \
          "${resume[@]}" "${CLAUDE_FLAGS[@]}" < /dev/null > "$fix_log" 2>&1); do
      read -r fix_why cost <<<"$(verdict "$fix_log")"
      spent="$(add "$spent" "$cost")"; ITEM_COST="$(add "$ITEM_COST" "$cost")"
      [[ $fix_why == limited ]] && may_wait || break
      if [[ -n "$(git -C "$WORKTREE" status --porcelain)" ]]; then
        say "       the fix left uncommitted changes — kept on $(keep_leftovers "$item" "fix-limit")"
      fi
      limit_wait "the fix of $(basename "$item" .md)" "it"
      fix_why=""
    done
    if [[ -z $fix_why ]]; then
      read -r _ cost <<<"$(verdict "$fix_log")"
      spent="$(add "$spent" "$cost")"; ITEM_COST="$(add "$ITEM_COST" "$cost")"
      final_text "$fix_log" > "$stem.fix.md"
    else
      fix=failed
      [[ $fix_why == limited || $fix_why == billing ]] && FIX_STOP=1
      case $fix_why in
        limited) fix_why="a usage limit" ;;
        billing) fix_why="a billing error" ;;
        budget)  fix_why="it spent its --max-budget-usd" ;;
        *)       fix_why="the session did not exit 0" ;;
      esac
      say "⚠️       the findings were NOT fixed: $fix_why — read ${fix_log#"$SOURCE_TREE"/}"
    fi
    # A half-finished fix is kept, not judged: the item was built and gated before it, and the
    # report says the fix did not finish.
    if [[ -n "$(git -C "$WORKTREE" status --porcelain)" ]]; then
      say "       the fix left uncommitted changes — kept on $(keep_leftovers "$item" fix)"
      [[ $fix == fixed ]] && { fix=failed; fix_why="it left uncommitted changes"; }
    fi
    say "       $(git -C "$WORKTREE" rev-list --count "$head..HEAD") fix commit(s)"
  else
    say "       not reviewed: $why"
  fi
  "$PY" -c 'import json, sys
out, item, status, why, review, fix, fix_why, fix_log, cost = sys.argv[1:10]
with open(out, "a", encoding="utf-8") as handle:
    handle.write(json.dumps({"kind": "item-review", "item": item, "status": status, "why": why,
                             "review": review, "fix": fix, "fix_why": fix_why,
                             "fix_log": fix_log, "cost": float(cost)}) + "\n")' \
    "$LOGS/run.jsonl" "$item" "$status" "$why" "$review_log" "$fix" "$fix_why" "$fix_log" "$ITEM_COST"
}

# open_to_file — how many `## To file` lines are unticked across the queue, as work_next.py
# reads them: one parser for the item format, never a grep beside it. `?` when work_next.py
# fails or prints no list: a count nobody could take is not a zero. A `D:` line is not counted:
# the closing session may not file it, so it is no reason to start one.
open_to_file() {
  local json
  json="$(work_next "$QUEUE_ROOT" "$SLUG" --json 2>/dev/null)" || { echo "?"; return 0; }
  "$PY" -c '
import json, sys
try:
    rows = json.loads(sys.argv[1])
    print(sum(not line["filed"] and not line["decision"]
              for row in rows for line in row.get("to_file", [])))
except (json.JSONDecodeError, TypeError, KeyError, AttributeError):
    print("?")' "$json"
}

# refuse_decisions <before> — an unattended run never files a `D:` line. A decision is written in
# the owner's words, and a closing session once wrote its own into one; the skill's instruction
# had not stopped it. So, whatever the session did since <before>, every file it changed in the
# decisions folder goes back to what it was (a citation fix aside: keep_citations), every `D:`
# line it ticked is opened again, and so is
# any other line it filed into a file put back — that is filed nowhere now
# (work_next.reopen_decisions: one parser for the item format) — and the loop commits that on its
# own. Sets DECIDED (the paths, comma-separated), REOPENED (how many lines), UNDONE (the commit,
# or empty) and REFUSAL (empty, or `unknown` when the reopen step failed and `uncommitted` when the
# commit did, comma-separated) for the filing row, which the report reads.
# keep_citations <before> <changed decision file>… — sets the caller's `paths` to the decision
# files the loop puts back: every one the closing session changed, except one whose only change
# is which path a backticked citation names (work_next.citations_only). The closing session fixes
# what the knowledge base names in whichever file it names, and a dead path cited in a decision
# is fixed only there; that fix decides nothing, so it is kept, and said. Added or deleted files
# always go back; when the check itself fails, every file goes back.
keep_citations() {
  local before="$1" out path
  shift
  out="$("$PY" - "$LIB" "$WORKTREE" "$before" "$@" <<'PY'
import subprocess, sys
sys.dont_write_bytecode = True
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import work_next
tree, before = Path(sys.argv[2]), sys.argv[3]
def show(ref, rel):
    run = subprocess.run(["git", "-C", str(tree), "show", f"{ref}:{rel}"],
                         capture_output=True, text=True, encoding="utf-8", check=False)
    return run.stdout if run.returncode == 0 else None
for rel in sys.argv[4:]:
    old, new = show(before, rel), show("HEAD", rel)
    if old is None or new is None or not work_next.citations_only(old, new):
        print(rel)
PY
)" || out="$(printf '%s\n' "$@")"
  while IFS= read -r path; do [[ -n $path ]] && paths+=("$path"); done <<<"$out"
  for path in "$@"; do
    [[ $'\n'$out$'\n' == *$'\n'$path$'\n'* ]] \
      || say "⚠️  kept the closing session's fix to a path cited in $path — it changes nothing but the path a check named"
  done
}

refuse_decisions() {
  local before="$1" paths=() items=() changed=()
  DECIDED=""; REOPENED=0; UNDONE=""; REFUSAL=""
  local path
  # A read loop, as this file reads every list of lines: no mapfile.
  if [[ -n $DECISIONS ]]; then
    while IFS= read -r path; do changed+=("$path"); done \
      < <(git -C "$WORKTREE" diff --name-only "$before" HEAD -- "$DECISIONS/")
  fi
  ((${#changed[@]})) && keep_citations "$before" "${changed[@]}"
  while IFS= read -r path; do items+=("$path"); done \
    < <(git -C "$WORKTREE" diff --name-only "$before" HEAD -- "$QUEUE_REL/$SLUG/")
  if ((${#items[@]})); then
    REOPENED="$("$PY" - "$LIB" "$WORKTREE" "$before" "$(printf '%s\n' "${paths[@]}")" "${items[@]}" <<'PY'
import re, subprocess, sys
sys.dont_write_bytecode = True
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import work_next
tree, before, total, rewrites = Path(sys.argv[2]), sys.argv[3], 0, []
# The decision files about to be put back, by path, file name and ID: a line filed into one
# is filed nowhere once it is.
undone = []
for rel in filter(None, sys.argv[4].split("\n")):
    name = Path(rel).name
    undone += [rel, name] + re.findall(r"^[A-Z]+-\d+", name)
for rel in sys.argv[5:]:
    path = tree / rel
    if not path.is_file():
        continue
    old = subprocess.run(["git", "-C", str(tree), "show", f"{before}:{rel}"],
                         capture_output=True, text=True, encoding="utf-8", check=False).stdout
    new, count = work_next.reopen_decisions(old, path.read_text(encoding="utf-8"), tuple(undone))
    if count:
        rewrites.append((path, new))
        total += count
# Every item is read before one is written: a step that fails half way has rewritten none.
for path, new in rewrites:
    path.write_text(new, encoding="utf-8")
print(total)
PY
)" || REOPENED="?"
  fi
  # A count nobody could take is not a zero: a failed step leaves a ticked D: line ticked, and
  # the run says so rather than "nothing ticked".
  if [[ ! $REOPENED =~ ^[0-9]+$ ]]; then
    REOPENED=0; REFUSAL=unknown
    say "⚠️  whether the closing session ticked a D: line could not be checked — the loop's reopen step failed; read the To file lines in $QUEUE_REL/$SLUG/ before anything is merged: a decision is the owner's"
  fi
  ((${#paths[@]})) || [[ $REOPENED != 0 ]] || return 0
  ((${#paths[@]})) && git -C "$WORKTREE" restore --source="$before" --staged --worktree -- "${paths[@]}"
  DECIDED="$(IFS=,; printf '%s' "${paths[*]}")"
  # A commit naming its paths takes them as the tree holds them: a restored deletion included.
  if git -C "$WORKTREE" commit -qm "afk: a decision is the owner's — the closing session's change to ${DECISIONS:-the decisions} undone, its D: lines open again" \
       -- "${paths[@]}" "${items[@]}"; then
    UNDONE="$(git -C "$WORKTREE" rev-parse --short HEAD)"
    if ((${#paths[@]})); then
      say "⚠️  the closing session changed ${#paths[@]} file(s) under $DECISIONS/ — undone in $UNDONE; $REOPENED To file line(s) open again: a decision is the owner's"
    else
      say "⚠️  the closing session ticked, moved or removed $REOPENED D: line(s) — open again in $UNDONE: a decision is the owner's"
    fi
  else
    git -C "$WORKTREE" reset -q -- "${paths[@]}" "${items[@]}"
    git -C "$WORKTREE" checkout -q -- "${paths[@]}" "${items[@]}" 2>/dev/null
    # The checkout put the session's ticks back: nothing was reopened, and the report says why.
    REOPENED=0; REFUSAL="${REFUSAL:+$REFUSAL,}uncommitted"
    say "⚠️  the closing session's change to ${#paths[@]} file(s) under $DECISIONS/ and to its D: lines could not be undone in a commit — read them before anything is merged"
  fi
}

# file_findings <why-not> — THE CLOSING SESSION, `/wiqrug:update-knowledge <slug> --unattended`,
# ONE session after the last item: it files every unticked `## To file` line and ticks it,
# writing in any file it needs. None is started when no line is open, nor when the queue cannot
# be read — that is `failed`, not `none`, because nobody could count the lines. It waits out a
# usage limit on the item's terms (may_wait/limit_wait), its cost is added to the run's spend,
# and a `filing` row in run.jsonl says what happened, which the report's `## Filed` reads beside
# the lines themselves.
# ⚠️ Why one session at the end: a finding left in an item file and never filed is lost when the
# queue is archived, and it looks filed to anybody who does not open the item — and knowledge
# written by each item, into files the next item also writes, is how one item's notes once
# stopped another item's run.
file_findings() {
  local skip="$1" open log="$LOGS/filing.jsonl" status=filed why="" cost=0 before after
  DECIDED=""; REOPENED=0; UNDONE=""; REFUSAL=""
  open="$(open_to_file)"
  before="$(git -C "$WORKTREE" rev-parse HEAD)"
  if [[ -z $open || $open == "?" ]]; then
    status=failed; log=""
    why="the queue could not be read (work_next.py $SLUG --json failed), so whether a To file line is open is unknown"
    say "⚠️  no closing session: $why"
  elif [[ $open == 0 ]]; then
    status=none; why="no To file line is open"; log=""
    say "nothing to file — no To file line is open, so no closing session"
  elif [[ -n $skip ]]; then
    status=skipped; why="$skip"; log=""
    say "⚠️  $open To file line(s) NOT filed: $why"
  else
    say "the closing session — $open To file line(s), one session of /wiqrug:update-knowledge $SLUG"
    # --unattended: step 1 (file the To file lines) and step 5 (regenerate, test, fix, commit)
    # only. Memory and the Now note are the owner's to review, and nobody is watching this one.
    while ! (cd "$WORKTREE" && AFK_SOURCE_TREE="$SOURCE_TREE" claude -p "/wiqrug:update-knowledge $SLUG --unattended" \
          "${CLAUDE_FLAGS[@]}" < /dev/null > "$log" 2>&1); do
      read -r why cost <<<"$(verdict "$log")"
      [[ $why == limited ]] && may_wait || break
      spent="$(add "$spent" "$cost")"
      if [[ -n "$(git -C "$WORKTREE" status --porcelain)" ]]; then
        say "       its session left uncommitted changes — kept on $(keep_leftovers filing limit)"
      fi
      limit_wait "the closing session" "it"
      why=""
    done
    read -r _ cost <<<"$(verdict "$log")"
    spent="$(add "$spent" "$cost")"
    if [[ -n $why ]]; then
      status=failed
      case $why in
        limited) why="a usage limit — run /wiqrug:update-knowledge $SLUG in the worktree later" ;;
        billing) why="a billing error" ;;
        budget)  why="it spent its --max-budget-usd" ;;
        *)       why="the session did not exit 0" ;;
      esac
      say "⚠️  the closing session failed: $why — read ${log#"$SOURCE_TREE"/}"
    fi
    if [[ -n "$(git -C "$WORKTREE" status --porcelain)" ]]; then
      say "       the closing session left uncommitted changes — kept on $(keep_leftovers filing)"
    fi
    refuse_decisions "$before"
    open="$(open_to_file)"
    [[ $status == filed ]] && say "       filed; ${open:-0} To file line(s) still open"
  fi
  after="$(git -C "$WORKTREE" rev-parse HEAD)"
  "$PY" -c 'import json, sys
out, status, why, cost, log, before, after, decided, reopened, undone, refusal = sys.argv[1:12]
with open(out, "a", encoding="utf-8") as handle:
    handle.write(json.dumps({"kind": "filing", "status": status, "why": why,
                             "cost": float(cost), "log": log,
                             "before": before, "after": after,
                             "decisions": [p for p in decided.split(",") if p],
                             "reopened": int(reopened or 0), "undone": undone,
                             "refusal": refusal}) + "\n")' \
    "$LOGS/run.jsonl" "$status" "$why" "$cost" "$log" "$before" "$after" \
    "$DECIDED" "$REOPENED" "$UNDONE" "$REFUSAL"
}

# final_text <stream-json log> — the session's last `result` text, or nothing. It asks
# afk_report.py, which already reads it for the report: two readers of one transcript format
# would be two answers to one question.
final_text() {
  "$PY" -c 'import sys
sys.dont_write_bytecode = True
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import afk_report
text = afk_report.read_transcript(Path(sys.argv[2]))[0]
if text:
    print(text)' "$LIB" "$1"
}

review_prompt() {               # review_prompt <spec path, or nothing>
  cat <<EOF
/wiqrug:review-change $RUN_BASE${1:+ $1}

The branch was built by an unattended run from the queue $QUEUE_REL/$SLUG/; you wrote none of
it, and you change none of it. Nothing asks you anything: take the base above as named. Each
item was reviewed and fixed as it was built; this reads the whole run together. In the Spec
reviewer's brief, also ask for any ticked box whose command could not have tested what the box
claims. Your final message is the step-5 report — ## Standards, ## Spec and the two total
lines — and nothing else.
EOF
}

item_review_prompt() {          # item_review_prompt <item> <before>
  cat <<EOF
/wiqrug:review-change $2 $1

The diff since $2 is ONE item of an unattended run, $1, from the queue $QUEUE_REL/$SLUG/; you
wrote none of it, and you change none of it. Nothing asks you anything: take the base and the
spec above as named. In the Spec reviewer's brief, also ask: whether every box ticked on a
"Fails first:" line's evidence really was delivered by the earlier work that line names; whether
every box left open by a "Box <n> worded wrong:" line really passed at $2, before any work, or
names a record of the project's data that really is not there, and is really worded wrong —
rather than a box the session could not make pass; any ticked box
whose command could not have tested what the box claims; and, for each finding, whether it is
a defect of the code or a gap in the spec. Your final message is the step-5
report — ## Standards, ## Spec and the two total lines — and nothing else.
EOF
}

fix_prompt() {                  # fix_prompt <item> <before> <review.md>
  local gate="run the project's done command, $DONE, until it exits 0${OWED_EXIT:+ or $OWED_EXIT}"
  [[ -n $DONE ]] || gate="run each box's command you touched again"
  cat <<EOF
A Standards and a Spec reviewer read your diff for $1 since $2. Their report is $3 — read it
first. Check each finding before acting on it, and give it exactly one verdict:
  confirmed      — the code, read or run, shows it holds. Fix it, one commit per fix, and
                   $gate.
  refuted        — ONLY with evidence: a command you ran and its output, or the quoted lines
                   (with their file) that contradict it.
  spec question  — the finding is a gap in the spec: the item or understanding.md never decided
                   it. Write no code for it. Append one line under the item's ## Comments,
                   "Spec question: <the question, for the owner>", and commit it.
  unchecked      — anything else, including a finding you could not settle either way.
If a confirmed finding shows a ticked box does not hold and you cannot make it hold, untick
that box. If it shows a "Box <n> worded wrong:" line is wrong — the box neither passed before
any work nor names a record that is not there — make the box pass and delete the line, or untick nothing and delete the line. Leave
nothing uncommitted. Your final message is one \`\`\`json block and nothing else, in this shape:
{"standards": {"ran": true, "note": "", "findings": [
   {"finding": "<the finding, verbatim, with its file and line>",
    "verdict": "confirmed", "evidence": "<the fixing commit, or the command and its output>"}]},
 "spec": {"ran": true, "note": "", "findings": []}}
An axis the review did not run has "ran": false and its reason in "note". Keep the review's
order within each axis; never move a finding to the other axis.
EOF
}

check_prompt() {                # check_prompt <review.md>
  cat <<EOF
Check each finding of the review at $1. It reviewed the branch an unattended run built from
the queue $QUEUE_REL/$SLUG/, since $RUN_BASE. You change nothing: no edit, no commit.

For every finding under ## Standards and under ## Spec, give exactly one verdict:
  confirmed  — the code, read or run, shows the finding holds;
  refuted    — ONLY with evidence: a command you ran and its output, or the quoted lines
               (with their file) that contradict it;
  unchecked  — anything else, including a finding you could not settle either way.
A "refuted" without evidence is reported as unchecked, so do not write one.

Your final message is one \`\`\`json block and nothing else, in this shape:
{"standards": {"ran": true, "note": "", "findings": [
   {"finding": "<the finding, verbatim, with its file and line>",
    "verdict": "confirmed", "evidence": "<the command and its output, or the quoted lines>"}]},
 "spec": {"ran": true, "note": "", "findings": []}}
An axis the review did not run — "no spec available" — has "ran": false and its reason in "note".
Keep the review's order within each axis; never move a finding to the other axis.
EOF
}

# ⚠️ A session's evidence has to outlive /tmp. A throwaway copy of the running project belongs
# outside every worktree, and `logs/` is inside the project — so each session is given a scratch
# directory under /tmp, and what a reviewer needs from it is COPIED into the run's logs when the
# session ends. The loop's first real run left 52 screenshots and its check scripts in /tmp, the
# only record of the boxes it handed to a person.
SCRATCH_ROOT="${AFK_SCRATCH_ROOT:-/tmp}/afk-$SLUG-$STAMP"

scratch_prompt() {              # scratch_prompt <scratch> <evidence>
  cat <<EOF
This is an unattended afk run. Put every throwaway copy of the running project, and every check
script, under $1 (it exists; for example $1/run), never anywhere else in /tmp.
EOF
  if [[ -n $BROWSER ]]; then
    cat <<EOF
Prove a screen with the project's browser check, \`$BROWSER\`, not a hand-built drive: no
screenshots unless a check fails. The owner does not review pictures; they follow the item's
## Check in the browser, which you rewrite as concrete steps once the screen exists.
EOF
  else
    cat <<EOF
This project has no browser check: a screen is a box for a person, and the item's
## Check in the browser holds the steps they follow, which you rewrite as concrete steps once
the screen exists.
EOF
  fi
  [[ -z $ENVIRONMENT ]] || printf 'The owner named the environment for this run: %s. Work against no other.\n' "$ENVIRONMENT"
  cat <<EOF
When this session ends the loop copies scripts and any failure screenshots into $2 — cite that
path, not the /tmp one, in the item's ## Comments and in your report.
EOF
}

# harvest <item> <scratch> <transcript> <since> — copy screenshots and drive scripts into
# the run's logs. The item's scratch first; then any other /tmp directory the transcript
# names, because a session that ignored the scratch still left evidence somebody needs.
# ⚠️ An allowlist of extensions, never "everything": a scratch holds a PostgreSQL cluster,
# minted passwords (`*.pw`) and a browser's saved cookies (`*.json`).
harvest() {
  local dest="$LOGS/$(basename "$1" .md)/evidence"
  "$PY" - "$2" "$3" "$4" "$dest" "$SCRATCH_ROOT" "$LOGS" "$WORKTREE" "$SOURCE_TREE" <<'PY'
import os, re, shutil, sys
from pathlib import Path

scratch, transcript, since, dest, *mine = sys.argv[1:]
mine = [Path(path).resolve() for path in mine]
since = float(since)
IMAGES = {".png", ".jpg", ".jpeg", ".webp"}
SCRIPTS = {".mjs", ".js", ".ts", ".sh", ".py"}
SKIP_DIRS = {"data", "node_modules", ".venv", "state"}
MAX_FILE, MAX_TOTAL = 20 << 20, 200 << 20

sources = [("scratch", Path(scratch))]
try:
    text = Path(transcript).read_text(encoding="utf-8", errors="replace")
except OSError:
    text = ""
for name in sorted(set(re.findall(r"/tmp/([A-Za-z0-9][A-Za-z0-9._-]*)", text))):
    path = Path("/tmp") / name
    # Claude's own temp folders and every afk scratch are not a session's evidence.
    if name.startswith(("claude-", "afk-")) or not path.is_dir() or path.is_symlink():
        continue
    # ⚠️ Never a folder that holds this run's own scratch, logs or trees, either way round:
    # walking one copies the destination into itself.
    real = path.resolve()
    if any(real == other or real in other.parents or other in real.parents for other in mine):
        continue
    sources.append((f"tmp-{name}", path))

images = scripts = total = 0
outside = []
for label, top in sources:
    copied = 0
    for folder, dirs, files in os.walk(top):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            source = Path(folder) / name
            kind = source.suffix.lower()
            if kind not in IMAGES | SCRIPTS:
                continue
            try:
                info = source.stat()
            except OSError:
                continue
            if info.st_mtime < since or info.st_size > MAX_FILE or total + info.st_size > MAX_TOTAL:
                continue
            target = Path(dest) / label / source.relative_to(top)
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
            except OSError:
                continue
            total += info.st_size
            copied += 1
            images += kind in IMAGES
            scripts += kind in SCRIPTS
    if copied and label != "scratch":
        outside.append(str(top))
if images or scripts:
    line = f"evidence: {images} screenshot(s), {scripts} script(s) copied to {dest}"
    if outside:
        line += f" — some from outside its scratch: {', '.join(outside)}"
    print(line)
else:
    print("evidence: none — no screenshot or drive script under its scratch or a /tmp path it named")
PY
}

say "slug=$SLUG environment=${ENVIRONMENT:-<none>} worktree=$WORKTREE branch=$BRANCH"
say "done command: ${DONE:-<none>}${OWED_EXIT:+ (exit $OWED_EXIT: owed, not failed)} · browser check: ${BROWSER:-<none>}"
say "max=$MAX effort=$EFFORT model=${MODEL:-<session default>} budget/item=${BUDGET:-<none>} run ceiling=${MAX_SPEND:-<none>}"
# The items this loop will never offer, each with the reason its own `Attended:` line gives.
while IFS= read -r line; do say "$line"; done < <(
  work_next "$SOURCE_TREE" "$SLUG" --json 2>/dev/null | "$PY" -c 'import json, sys
rows = [r for r in json.load(sys.stdin) if r["attended"] and r["state"] not in ("done", "owed")]
for r in rows:
    print("{} attended: {} — built by the owner, never by this loop".format(r["number"], r["attended"]))
if not rows:
    print("attended items: none")')
say "on a usage limit: $ON_LIMIT$( [[ $ON_LIMIT == wait ]] && printf ' — retry every %sm, up to %sh of waiting' "$LIMIT_WAIT" "$LIMIT_MAX_WAIT")"
((DRY)) && say "logs would land in ${LOGS#"$SOURCE_TREE"/}" || say "logs: ${LOGS#"$SOURCE_TREE"/}"

((DRY)) || "$PY" - "$LOGS/run.jsonl" "$SLUG" "$ENVIRONMENT" "$EFFORT" "${MODEL:-session default}" "$MAX" "${BUDGET:-}" \
                    "$DONE" "$OWED_EXIT" "$BASE_BRANCH" <<'PY'
import json, sys
out, slug, env, effort, model, mx, budget, done, owed, base = sys.argv[1:11]
with open(out, "w", encoding="utf-8") as handle:
    handle.write(json.dumps({"kind": "meta", "slug": slug, "environment": env or None,
                             "effort": effort, "model": model, "max": mx if mx == "all" else int(mx),
                             "budget_per_item": budget or None, "done": done or None,
                             "owed_exit": int(owed) if owed else None,
                             "base_branch": base or None}) + "\n")
PY

# A dry run creates no worktree, so the queue must be read from the tree that has one.
QUEUE_ROOT="$WORKTREE"
[[ -d $WORKTREE ]] || QUEUE_ROOT="$SOURCE_TREE"

# ⚠️ The worktree is cut from HEAD, so an UNCOMMITTED queue passes the preflight above —
# which reads this tree — and then the loop, which reads the worktree, finds nothing and
# reports "nothing ready". That reads as a drained queue. Check the tree the loop will use.
# It runs in a dry run too, whenever a worktree exists: a preview that reads the worktree
# has to report the worktree's problems, or --dry-run says "nothing ready" about a queue
# that is merely uncommitted.
if ((DRY == 0)) || [[ -d $WORKTREE ]]; then
  work_next "$QUEUE_ROOT" "$SLUG" --all >/dev/null 2>&1 \
    || die "$QUEUE_REL/$SLUG, or the settings file, is not in $BRANCH — a worktree is cut from
      HEAD, so commit them first. They are sound in this tree, which is why the preflight passed."
fi

# ------------------------------------------------------------------ to the background
# Everything that can refuse has refused by now, in front of whoever started this. The rest
# runs in its own session (`setsid`), with no terminal, so a closed laptop or a dropped SSH
# connection sends it no hangup. It re-runs this script with the same arguments and stamp.
# Where `setsid` does not exist — Git Bash — nothing detaches: the run goes on here, attached,
# and says so once, because closing this window ends it.
if ((DRY == 0 && FOREGROUND == 0)) && [[ -z ${AFK_DETACHED:-} ]] && ! command -v setsid >/dev/null 2>&1; then
  say "no setsid here, so this run stays attached to this window — leave this window open until it ends"
  FOREGROUND=1
fi
if ((DRY == 0 && FOREGROUND == 0)) && [[ -z ${AFK_DETACHED:-} ]]; then
  trap - EXIT                                 # the child takes the lock over; this one keeps it
  AFK_DETACHED=1 AFK_STAMP="$STAMP" AFK_LOCK_FROM="$$" setsid nohup bash "${BASH_SOURCE[0]}" "${ARGS[@]}" \
    > "$LOGS/console.log" 2>&1 < /dev/null &
  for _ in 1 2 3 4 5 6 7 8 9 10; do [[ -s $LOGS/pid ]] && break; sleep 0.5; done
  # Absolute paths on purpose: these are pasted into another terminal, in any directory.
  printf '\nRunning in the background (pid %s). You can close this terminal.\n\n' \
         "$(cat "$LOGS/pid" 2>/dev/null || echo '?')"
  printf '    watch it      %s %s/afk_watch.py %s --project %s\n' "$PY" "$LIB" "$SLUG" "$SOURCE_TREE"
  printf '                  what each session says and runs, as it happens; Ctrl-C stops only the watching\n'
  printf '    raw log       tail -f %s/console.log\n' "$LOGS"
  printf '    when it ends  %s/report.md — what needs you is its first section\n' "$LOGS"
  printf '    stop it       kill $(cat %s/pid)\n\n' "$LOGS"
  exit 0
fi
((DRY)) || printf '%s\n' "$$" > "$LOGS/pid"

drained=0
owed=0
VERIFY_RC=""
VERIFIED_AT=""
VERIFY_LOG=""
RUN_BASE=""
((DRY)) || RUN_BASE="$(git -C "$WORKTREE" rev-parse HEAD)"
# What this run sets aside starts empty: a value inherited from another run is not this one's.
export WORK_NEXT_SET_ASIDE=""
aside=()
settled_items=()
last_item=""
spent=0
waited=0
stop=0
failed_item=0

# settle <item> <before> <log> — judge what the item's sessions left: uncommitted work, the
# code gate (with its one repair), damaged boxes, and the boxes themselves. Sets STATE to done
# or owed and returns 0; otherwise records the item, sets it aside, and returns 1. Run after the
# build and again after the review's fixes, because a fix is judged exactly like the build.
settle() {
  local item="$1" before="$2" log="$3" leftover damage why repaired
  # ⚠️ Whatever a session left uncommitted is kept on a side branch and the worktree reset,
  # so the next step starts from committed work only — never from a half-finished slice that
  # no commit, and so no report, would attribute to it.
  if [[ -n "$(git -C "$WORKTREE" status --porcelain)" ]]; then
    leftover="$(keep_leftovers "$item")"
    say "$item left uncommitted changes — kept on $leftover"
    record "$item" dirty "$before" "$(git -C "$WORKTREE" rev-parse HEAD)" "$item_cost" "$log"
    set_aside "$item" "its session left uncommitted changes (kept on $leftover)"
    return 1
  fi
  if ! code_gate "$item"; then
    repaired=0
    repair_gate "$item" "$log" && repaired=1
    spent="$(add "$spent" "$REPAIR_COST")"
    item_cost="$(add "$item_cost" "$REPAIR_COST")"
    if ((!repaired)); then
      gate_box "$item"
      record "$item" gate-failed "$before" "$(git -C "$WORKTREE" rev-parse HEAD)" "$item_cost" "$log"
      set_aside "$item" "the code gate did not pass, and one repair did not fix it"
      return 1
    fi
  fi
  # ⚠️ An item is drained when its BOXES are settled, not when its session exited 0: every
  # box ticked, or the only ones left open are ones no session can close. A session that
  # commits without ticking leaves an item indistinguishable from an unstarted one.
  damage="$(boxes_damaged "$item" "$before")"
  if [[ -n $damage ]]; then
    say "$item: $damage — restore the item's boxes from $before before"
    say "       trusting it. Read $log"
    record "$item" damaged "$before" "$(git -C "$WORKTREE" rev-parse HEAD)" "$item_cost" "$log"
    set_aside "$item" "$damage"
    return 1
  fi
  IFS=$'\t' read -r STATE why <<<"$(item_state "$item")"
  if [[ $STATE != done && $STATE != owed ]]; then
    say "$item still has unticked acceptance boxes a command should have closed — the"
    say "       queue says: $why. Read $log"
    record "$item" unticked "$before" "$(git -C "$WORKTREE" rev-parse HEAD)" "$item_cost" "$log"
    set_aside "$item" "boxes a command should close are still open"
    return 1
  fi
  STATE_WHY="$why"
}

# --max all: every item the queue offers. Each is attempted at most once in a run, so the queue's
# length bounds it; the run still ends as soon as nothing is ready.
ROUNDS="$MAX"
if [[ $MAX == all ]]; then
  ROUNDS="$(work_next "$QUEUE_ROOT" "$SLUG" --json 2>/dev/null \
    | "$PY" -c 'import json, sys; print(len(json.load(sys.stdin)))' || true)"
  [[ $ROUNDS =~ ^[0-9]+$ ]] || die "--max all: the queue could not be counted (work_next.py $SLUG --json)"
fi
for ((round = 1; round <= ROUNDS; round++)); do
  item="$(work_next "$QUEUE_ROOT" "$SLUG" --unattended 2>/dev/null || true)"
  if [[ -z $item ]]; then
    say "nothing ready — stopping after $drained item(s)"
    break
  fi
  # Belt and braces behind the unticked-box check below: the same item twice means the
  # queue has not moved, whatever the reason.
  if [[ $item == "$last_item" ]]; then
    say "STOPPED: $item came back unchanged — the queue has not moved"
    break
  fi
  last_item="$item"

  say "[$round/$MAX] $item"
  if ((DRY)); then
    printf '  would run: claude -p "/wiqrug:implement %s" %s\n' "$item" "${CLAUDE_FLAGS[*]}"
    printf '             with its scratch under %s, copied into its logs when it ends\n' "$SCRATCH_ROOT"
    printf '  then: the code gate (the done command, %s) at its last commit, one repair if it fails\n' "${DONE:-none here}"
    if ((REVIEW)); then
      printf '  then: /wiqrug:review-change on its diff, and its own session resumed to fix the findings,\n'
      printf '        and the code gate again — before the next item starts\n'
    else
      printf '  then: no review (--no-review)\n'
    fi
    printf '  after the last item: /wiqrug:update-knowledge %s, one session, if a To file line is open (%s now)\n' \
           "$SLUG" "$(open_to_file)"
    printf '        then the done command on the branch tip\n'
    if ((REVIEW)); then
      printf '  and at the end: /wiqrug:review-change reads the whole diff on two axes, then each finding is checked (--no-review skips both)\n'
    else
      printf '  and at the end: no review (--no-review)\n'
    fi
    break
  fi

  # ------------------------------------------------- one item, retried while limited
  # The retry IS the probe. A session that starts while the window is still full exits
  # in seconds having spent nothing, so polling costs nothing and needs no reset time
  # parsed out of a message whose shape nothing here has ever measured.
  attempt=1
  item_cost=0
  base="$LOGS/$(basename "$item" .md)"
  scratch="$SCRATCH_ROOT/$(basename "$item" | cut -c1-2)"
  mkdir -p "$scratch"
  since="$(date +%s)"
  while :; do
    before="$(git -C "$WORKTREE" rev-parse HEAD)"
    log="$base.jsonl"
    ((attempt > 1)) && log="$base.retry$attempt.jsonl"

    # ⚠️ Nothing is recorded here. One item is ONE row in run.jsonl, written once the
    # post-checks below have decided what actually happened to it — a row per attempt
    # counts one session twice and doubles the spend the report adds up.
    if (cd "$WORKTREE" && AFK_SCRATCH="$scratch" AFK_SOURCE_TREE="$SOURCE_TREE" claude -p "/wiqrug:implement $item" "${CLAUDE_FLAGS[@]}" \
          --append-system-prompt "$(scratch_prompt "$scratch" "${base#"$SOURCE_TREE"/}/evidence")" \
          > "$log" 2>&1); then
      read -r _ cost <<<"$(verdict "$log")"
      spent="$(add "$spent" "$cost")"
      item_cost="$cost"
      break
    fi

    read -r why cost <<<"$(verdict "$log")"
    spent="$(add "$spent" "$cost")"
    if [[ $why == failed && -n $BUDGET ]] \
       && [[ $("$PY" -c "print(int(float('$cost') >= float('$BUDGET') * 0.95))") == 1 ]]; then
      why=budget
    fi

    if [[ $why == limited ]] && may_wait; then
      # ⚠️ The limit lands mid-session, so the tree can hold half an edit. The retry is a
      # fresh session that knows nothing of it: it starts from committed work, and the
      # half-edit is kept on a side branch, exactly as an item's leftovers are below.
      if [[ -n "$(git -C "$WORKTREE" status --porcelain)" ]]; then
        say "       its session left uncommitted changes — kept on $(keep_leftovers "$item" "limit$attempt")"
      fi
      limit_wait "$item" "the SAME item" "attempt $attempt"
      attempt=$((attempt + 1))
      continue
    fi
    if [[ $why == limited && $ON_LIMIT == wait ]]; then
      say "PAUSED on $item — still rate limited after $((waited / 60))m of waiting,"
      say "       which is this run's --limit-max-wait. The queue is unchanged: run"
      say "       this again and it resumes here."
      record "$item" limited "$before" "$before" "$cost" "$log"
      stop=1; break
    fi

    case "$why" in
      limited) say "PAUSED on $item — a usage limit, NOT a failure, and --on-limit is"
               say "       stop. Run this again after the reset and it resumes here." ;;
      billing) say "STOPPED on $item — a BILLING error. Nothing resets; waiting will not"
               say "       fix it. Check the account, then run this again." ;;
      budget)  say "$item spent its per-item budget of \$$BUDGET — read $log" ;;
      *)       say "the session working $item did not exit 0 — read $log" ;;
    esac
    record "$item" "$why" "$before" "$(git -C "$WORKTREE" rev-parse HEAD)" "$cost" "$log"
    case "$why" in
      limited|billing) stop=1 ;;
      *) failed_item=1 ;;
    esac
    break
  done
  # Every ending, a failed one included: its screenshots are how somebody sees why.
  say "       $(harvest "$item" "$scratch" "$log" "$since")"
  ((stop)) && break

  if ((failed_item)); then
    failed_item=0
    # Its leftovers are kept, and it is recorded already: one item is one row.
    if [[ -n "$(git -C "$WORKTREE" status --porcelain)" ]]; then
      say "$item left uncommitted changes — kept on $(keep_leftovers "$item")"
    fi
    set_aside "$item" "its session did not finish"
    continue
  fi

  # A box that passed before any work no longer parks an item: /wiqrug:implement ticked it on the
  # evidence of the earlier work that delivered it — the review checks that claim — or wrote
  # `Box <n> worded wrong:`, which leaves the box owed and asks the owner.
  settle "$item" "$before" "$log" || continue

  # The item's own review, and its fixes, before the next item starts — judged again after.
  review_item "$item" "$before" "$log"
  item_cost="$(add "$item_cost" "$ITEM_COST")"
  settle "$item" "$before" "$log" || continue

  record "$item" "$STATE" "$before" "$(git -C "$WORKTREE" rev-parse HEAD)" "$item_cost" "$log"
  settled_items+=("$item")
  drained=$((drained + 1))
  [[ $STATE == owed ]] && { owed=$((owed + 1)); say "       owed: $STATE_WHY — listed in the report"; }
  # The item was built and gated; its review or fix met the account's limit or billing, which
  # ends the run exactly as it would on an item.
  if ((FIX_STOP)); then
    say "STOPPED after $item: its review or fix met a billing error or a usage limit it could not"
    say "       wait out. The item is built; run this again later to go on."
    stop=1; break
  fi

  if [[ -n $MAX_SPEND ]] \
     && [[ $("$PY" -c "print(int(float('$spent') >= float('$MAX_SPEND')))") == 1 ]]; then
    say "STOPPED: \$$spent spent, which is this run's --max-spend-usd of \$$MAX_SPEND."
    say "         The queue is unchanged — raise the ceiling and run it again."
    break
  fi
done

((DRY)) && exit 0

# Filing comes before the tip check and the review, so both judge the branch as handed over.
if ((stop)); then
  file_findings "the run stopped on a usage limit or a billing error"
elif [[ -n $MAX_SPEND ]] \
     && [[ $("$PY" -c "print(int(float('$spent') >= float('$MAX_SPEND')))") == 1 ]]; then
  file_findings "the run reached its --max-spend-usd"
else
  file_findings ""
fi
check_tip
# The review runs whenever the run left commits to read — unless it was told not to, or the
# run ended because spending more is exactly what it must not do.
if [[ -z $(git -C "$WORKTREE" rev-list "$RUN_BASE..HEAD" 2>/dev/null) ]]; then
  review_branch "the run committed nothing, so there is no diff to read"
elif ((REVIEW == 0)); then
  review_branch "--no-review"
elif ((stop)); then
  review_branch "the run stopped on a usage limit or a billing error"
elif [[ -n $MAX_SPEND ]] \
     && [[ $("$PY" -c "print(int(float('$spent') >= float('$MAX_SPEND')))") == 1 ]]; then
  review_branch "the run reached its --max-spend-usd"
else
  review_branch ""
fi
say "drained $drained item(s) onto $BRANCH, $owed of them owed to a person · estimated spend \$$spent"
for line in "${aside[@]}"; do say "set aside  $line"; done
work_next "$QUEUE_ROOT" "$SLUG" --all

# ⚠️ The report is rendered on EVERY ending, not only a clean one. A run that stopped on
# its first item is the run whose report is worth the most, because it is the one where
# what happened is least obvious from the branch.
"$PY" "$LIB/afk_report.py" "$SLUG" --logs "$LOGS" --worktree "$WORKTREE" \
        --branch "$BRANCH" || say "the report could not be rendered — the logs are still in $LOGS"

if ((drained == 0)); then
  cat <<EOF

Nothing was drained, so there is no diff to read. The run's own output is the evidence:
    cat ${LOGS#"$SOURCE_TREE"/}/report.md
EOF
else
  cat <<EOF

Nothing has been pushed and nothing is merged. Read it, then decide:
    cat ${LOGS#"$SOURCE_TREE"/}/report.md
    git -C "$WORKTREE" log --oneline ${RUN_BASE:0:12}..HEAD
    git -C "$WORKTREE" diff ${RUN_BASE:0:12}..HEAD
EOF
fi
