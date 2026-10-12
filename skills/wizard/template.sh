#!/usr/bin/env bash
#
# Adapted from mattpocock/skills (MIT, © 2026 Matt Pocock).
#
# <WIZARD NAME>: <one line — what it does, and which existing scripts it wraps>.
#
#     sudo bash <absolute path>/<name>.sh [--environment <env>]          # asks at each stage
#     sudo bash <absolute path>/<name>.sh [--environment <env>] --yes    # asks only before the irreversible
#          bash <absolute path>/<name>.sh --verify                       # "did it work?" — needs no root
#
# Safe to re-run: every stage asks first whether its work is already done, and skips it if so.
# Everything printed is also kept in <git root>/logs/<name>-<UTC stamp>.log (WIZARD_LOG_DIR
# overrides the folder); a --verify run ends that log with the line
# `verify: <n> set up, <m> not set up`.
#
# Going back: <the command that undoes each stage, or "nothing to undo" and why>.
#
# Everything above the "STAGES" marker is the wizard library, copied from the template.sh of
# wiqrug's wizard skill: do not hand-edit it. Author the stages below the marker.
set -euo pipefail

# ──────────────────────────────────────────────────────────────────────────
# Wizard library: one UX, identical across every wizard.
# ──────────────────────────────────────────────────────────────────────────

# Asked once, before anything is redirected: is a person watching this?
_TTY_OUT=false; [[ -t 1 ]] && _TTY_OUT=true
_TTY_IN=false;  [[ -t 0 ]] && _TTY_IN=true
if $_TTY_OUT && command -v tput >/dev/null 2>&1 && [[ "$(tput colors 2>/dev/null || echo 0)" -ge 8 ]]; then
  BOLD=$(tput bold); DIM=$(tput dim); RESET=$(tput sgr0)
  BLUE=$(tput setaf 4); GREEN=$(tput setaf 2); YELLOW=$(tput setaf 3); RED=$(tput setaf 1)
else
  BOLD=""; DIM=""; RESET=""; BLUE=""; GREEN=""; YELLOW=""; RED=""
fi

# Author sets this at the top of the stages section.
TOTAL_STAGES=0

WIZARD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WIZARD_PATH="$WIZARD_DIR/$(basename "${BASH_SOURCE[0]}")"
# The repository the wizard sits in, found from the wizard's own folder — never from the folder
# it was started in. A wizard kept outside any repository uses its own folder. safe.directory
# lets a root run ask a repository the operator owns.
REPO_ROOT="$(git -c safe.directory='*' -C "$WIZARD_DIR" rev-parse --show-toplevel 2>/dev/null || true)"
REPO_ROOT="${REPO_ROOT:-$WIZARD_DIR}"
# The login account that owns the tree: who a root run acts for, and who owns its log.
OPERATOR="${SUDO_USER:-$(stat -c %U "$REPO_ROOT")}"
LOG_DIR="${WIZARD_LOG_DIR:-$REPO_ROOT/logs}"

_STAGE_INDEX=0
ENV_FILE="${ENV_FILE:-$REPO_ROOT/.env}"
MODE=apply        # apply | verify
ASSUME_YES=false  # --yes
ENVIRONMENT=""    # --environment; never inferred, and checked by the stages that need one
EXTRA_ARGS=()     # anything the library does not know, for the stages to parse
LOG=""
WRITTEN_ENV=()    # KEYs written to ENV_FILE this run
WRITTEN_SECRET=() # credential FILES written this run — paths, never values
CHANGED=()        # what this run changed
SKIPPED=()        # what is still to do by hand
N_SET_UP=0; N_NOT_SET_UP=0; N_NOT_ASKED=0

# wizard_args "$@" reads the flags every wizard shares. --help prints the header.
wizard_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --verify)        MODE=verify; shift ;;
      --yes|-y)        ASSUME_YES=true; shift ;;
      --environment)   ENVIRONMENT="${2:-}"; shift 2 ;;
      --environment=*) ENVIRONMENT="${1#*=}"; shift ;;
      --help|-h)       sed -n '2,/^set -euo/p' "$WIZARD_PATH" | sed '$d' | sed 's/^# \{0,1\}//'; exit 0 ;;
      *)               EXTRA_ARGS+=("$1"); shift ;;
    esac
  done
  [[ "$ENVIRONMENT" =~ ^[A-Za-z0-9_-]*$ ]] || die "not an environment's name: $ENVIRONMENT"
}

# _log LINE appends LINE to the log with its colours stripped. Never a secret: nothing
# that reads one calls this.
_log() {
  [[ -n "$LOG" ]] || return 0
  printf '%s\n' "$1" | sed -e 's/\x1b\[[0-9;]*[A-Za-z]//g' -e 's/\x1b[()][A-Z0-9]//g' >> "$LOG"
}
# _emit FORMAT ARGS... prints to the screen and to the log.
_emit() {
  local line
  # shellcheck disable=SC2059
  printf -v line "$@"
  printf '%s' "$line"
  _log "${line%$'\n'}"
}

# wizard_start NAME "Title" opens the log at $LOG_DIR/NAME-<UTC stamp>.log and shows the
# opening frame. A root run hands the log to the operator, so the tree holds nothing of root's.
wizard_start() {
  local name="$1" title="$2" made=false
  [[ -d "$LOG_DIR" ]] || made=true
  mkdir -p "$LOG_DIR"
  LOG="$LOG_DIR/$name-$(date -u +%Y%m%dT%H%M%SZ).log"
  : > "$LOG"
  if [[ $EUID -eq 0 ]]; then
    if $made; then chown "$OPERATOR:" "$LOG_DIR" 2>/dev/null || true; fi
    chown "$OPERATOR:" "$LOG" 2>/dev/null || true
  fi
  _log "# $name — mode $MODE${ENVIRONMENT:+, environment $ENVIRONMENT}$($ASSUME_YES && printf ', --yes') — as $(id -un), $(date -u +%FT%TZ)"
  banner "$title"
}

# needs_root ARGS... stops a run that needs root and hands over the ONE command, in full.
# The agent never runs sudo; the user types this line exactly as written.
needs_root() {
  local args=""
  [[ $EUID -ne 0 ]] || return 0
  [[ $# -eq 0 ]] || args="$(printf ' %q' "$@")"
  _emit '\n  %sThis needs root. Run, exactly:%s\n\n    sudo bash %s%s\n\n' "$BOLD" "$RESET" "$WIZARD_PATH" "$args"
  _emit '  %sTo ask whether it is already done, without root:  bash %s --verify%s\n\n' "$DIM" "$WIZARD_PATH" "$RESET"
  exit 2
}

# _clear wipes the terminal so only the current step is on screen. No-op when
# output isn't a terminal, and in --verify, whose answer is read top to bottom.
_clear() {
  $_TTY_OUT && [[ "$MODE" != verify ]] || return 0
  if command -v tput >/dev/null 2>&1; then tput clear; else printf '\033[2J\033[3J\033[H'; fi
}

# banner "Title" shows the opening frame: what this wizard does.
banner() {
  _clear
  _emit '\n%s%s  %s%s\n' "$BOLD" "$BLUE" "$1" "$RESET"
  _emit '%s  %s stages · %s%s\n\n' "$DIM" "$TOTAL_STAGES" "$MODE" "$RESET"
  [[ "$MODE" == verify ]] && return 0
  _emit '%s  Each stage checks first and skips what is already done. Stop any time with\n' "$DIM"
  _emit '  Ctrl-C and re-run later. Everything shown is kept in %s%s\n' "$LOG" "$RESET"
  pause "Ready to start?"
}

# stage "Name" clears the screen, then announces a stage and shows progress.
stage() {
  _clear
  _STAGE_INDEX=$((_STAGE_INDEX + 1))
  _emit '\n%s%s▸ Stage %s/%s · %s%s\n' \
    "$BOLD" "$BLUE" "$_STAGE_INDEX" "$TOTAL_STAGES" "$1" "$RESET"
}

# say "..." prints a plain instruction line.
say()  { _emit '  %s\n' "$1"; }
# step "..." is an action the human takes.
step() { _emit '  %s•%s %s\n' "$BLUE" "$RESET" "$1"; }
note() { _emit '  %s%s%s\n' "$DIM" "$1" "$RESET"; }
warn() { _emit '  %s⚠ %s%s\n' "$YELLOW" "$1" "$RESET"; }
die()  { _emit '\n  %s✗ %s%s\n\n' "$RED" "$1" "$RESET" >&2; exit 1; }

# open_url URL opens it in the human's browser when there is one; always prints it.
open_url() {
  local url="$1"
  _emit '  %s↗ open%s %s\n' "$GREEN" "$RESET" "$url"
  [[ $EUID -ne 0 && "$MODE" != verify ]] || return 0
  { if   command -v wslview     >/dev/null 2>&1; then wslview "$url"
    elif command -v explorer.exe >/dev/null 2>&1; then explorer.exe "$url"
    elif command -v xdg-open    >/dev/null 2>&1; then xdg-open "$url"
    elif command -v open        >/dev/null 2>&1; then open "$url"
    fi
  } >/dev/null 2>&1 || true
}

# pause "msg" waits for the human to confirm they've done the manual part. Nobody is
# asked under --yes or --verify, or when nobody is at a terminal.
pause() {
  if $ASSUME_YES || [[ "$MODE" == verify ]] || ! $_TTY_IN; then return 0; fi
  printf '  %s%s%s ' "$DIM" "${1:-Press Enter to continue}" "$RESET"
  read -r _ || true
}

# confirm "question" is a y/N gate; returns success on yes. Under --yes it answers yes.
confirm() {
  [[ "$MODE" != verify ]] || return 1
  if $ASSUME_YES; then _log "  ? $1 [--yes: yes]"; return 0; fi
  confirm_irreversible "$1"
}

# confirm_irreversible "question" ALWAYS asks, --yes or not, and a run with nobody at the
# terminal is a no. Use it before anything that cannot be undone.
confirm_irreversible() {
  local reply=""
  [[ "$MODE" != verify ]] || return 1
  if ! $_TTY_IN; then _log "  ? $1 [no terminal: no]"; warn "not done — nobody at a terminal to answer: $1"; return 1; fi
  printf '  %s? %s [y/N]%s ' "$YELLOW" "$1" "$RESET"
  read -r reply || true
  _log "  ? $1 [${reply:-N}]"
  [[ "$reply" =~ ^[Yy] ]]
}

# ask KEY "Prompt" reads a value into $KEY. Offers the existing ENV_FILE value as
# a default on re-runs (Enter keeps it). Visible input — never a secret.
ask() {
  local key="$1" prompt="$2" current input
  current=$(_existing "$key" || true)
  if [[ -n "$current" ]]; then
    printf '  %s%s%s %s[Enter keeps %s]%s ' "$BOLD" "$prompt" "$RESET" "$DIM" "$current" "$RESET"
  else
    printf '  %s%s%s ' "$BOLD" "$prompt" "$RESET"
  fi
  read -r input || true
  [[ -z "$input" && -n "$current" ]] && input="$current"
  _log "  $prompt $input"
  printf -v "$key" '%s' "$input"
}

# ask_secret KEY "Prompt" [FILE] is like ask, but input is hidden, never logged, and the
# current value is NEVER read to offer it back: when FILE already exists, Enter keeps it
# and $KEY is left empty.
ask_secret() {
  local key="$1" prompt="$2" file="${3:-}" input=""
  $_TTY_IN || die "$prompt — needs a person at a terminal; re-run the command in one"
  if [[ -n "$file" && -e "$file" ]]; then
    printf '  %s%s%s %s[Enter keeps the one in %s]%s ' "$BOLD" "$prompt" "$RESET" "$DIM" "$file" "$RESET"
  else
    printf '  %s%s%s ' "$BOLD" "$prompt" "$RESET"
  fi
  read -rs input || true
  printf '\n'
  _log "  $prompt [hidden, ${#input} characters]"
  printf -v "$key" '%s' "$input"
}

# _existing KEY: current value of KEY in ENV_FILE, if any. Settings only — see write_env.
_existing() {
  [[ -f "$ENV_FILE" ]] || return 1
  local line; line=$(grep -E "^${1}=" "$ENV_FILE" | tail -n1) || return 1
  printf '%s' "${line#*=}"
}

# write_env KEY VALUE upserts KEY=VALUE into ENV_FILE. Configuration only: a name that
# says it is a credential is refused, because a credential belongs where the project keeps
# credentials (write_secret_file), never in a settings file.
write_env() {
  local key="$1" value="$2" tmp
  [[ ! "$key" =~ (PASS|SECRET|TOKEN|_KEY$) ]] || die "$key is a credential; it goes to the store (write_secret_file), not $ENV_FILE"
  touch "$ENV_FILE"
  tmp=$(mktemp "$ENV_FILE.XXXXXX")
  grep -vE "^${key}=" "$ENV_FILE" > "$tmp" || true
  printf '%s=%s\n' "$key" "$value" >> "$tmp"
  chmod --reference="$ENV_FILE" "$tmp"; chown --reference="$ENV_FILE" "$tmp" 2>/dev/null || true
  mv "$tmp" "$ENV_FILE"
  WRITTEN_ENV+=("$key")
  _emit '  %s✓ wrote%s %s → %s\n' "$GREEN" "$RESET" "$key" "$ENV_FILE"
}

# write_secret_file PATH VALUE writes a credential where the project keeps credentials:
# 0400 root:root, created with that mode BEFORE it holds anything, moved into place whole. The value travels by a builtin, never argv, and only its length is ever shown.
write_secret_file() {
  local path="$1" value="$2" tmp
  [[ $EUID -eq 0 ]] || die "writing $path needs root"
  [[ -n "$value" ]] || die "refusing to write an empty credential to $path"
  install -d -m 0755 -o root -g root "$(dirname "$path")"
  tmp="$(mktemp "$(dirname "$path")/.$(basename "$path").XXXXXX")"
  chmod 0400 "$tmp"; chown root:root "$tmp"
  printf '%s' "$value" > "$tmp"
  mv -f "$tmp" "$path"
  WRITTEN_SECRET+=("$path")
  _emit '  %s✓ wrote%s %s (%s characters, 0400 root:root)\n' "$GREEN" "$RESET" "$path" "${#value}"
}

# dashboard_secret NAME URL: a secret that lives on a website — a forge's repository
# secrets, a provider's console. The wizard never carries the value there: it opens the
# page, names the secret, and lists it as still to do by hand.
dashboard_secret() {
  local name="$1" url="$2"
  open_url "$url"
  step "Add the secret $name on that page, pasting its value there."
  SKIPPED+=("the secret $name — $url")
}

# run CMD... runs a wrapped script, showing and logging what it prints; returns its exit.
# Its output is kept in $RUN_OUTPUT for the caller to read.
RUN_OUTPUT=""
run() {
  local rc line out
  out="$(mktemp)"
  _log "  \$ $*"
  set +e
  "$@" 2>&1 | while IFS= read -r line; do printf '    %s\n' "$line"; _log "    $line"; printf '%s\n' "$line" >> "$out"; done
  rc=${PIPESTATUS[0]}
  set -e
  RUN_OUTPUT="$(cat "$out")"; rm -f "$out"
  return "$rc"
}
# as_operator CMD... runs CMD as the login account — how a root run asks a root-free question.
as_operator() {
  if [[ $EUID -eq 0 ]]; then runuser -u "$OPERATOR" -- "$@"; else "$@"; fi
}

# set_up / not_set_up / not_asked "what" record one verdict. "Not asked" is its own count:
# a question nobody could put is not an answer either way.
set_up()     { N_SET_UP=$((N_SET_UP + 1));         _emit '  %s✓%s %s\n' "$GREEN" "$RESET" "$1"; }
not_set_up() { N_NOT_SET_UP=$((N_NOT_SET_UP + 1)); _emit '  %s✗%s %s\n' "$RED" "$RESET" "$1"; }
not_asked()  { N_NOT_ASKED=$((N_NOT_ASKED + 1));   _emit '  %s—%s %s\n' "$YELLOW" "$RESET" "$1"; }

# check_or_do "what" CHECK DO — the shape of every stage. CHECK returns 0 when the work is
# done, 1 when it is not, 2 when it cannot be asked from here. --verify records CHECK's
# answer and changes nothing; an apply skips what is done, else runs DO and asks again.
# DO returns 3 to leave the work undone on purpose — an irreversible step the person refused.
check_or_do() {
  local what="$1" check="$2" act="$3" rc=0
  "$check" || rc=$?
  if [[ "$MODE" == verify ]]; then
    case $rc in 0) set_up "$what" ;; 2) not_asked "$what" ;; *) not_set_up "$what" ;; esac
    return 0
  fi
  if [[ $rc -eq 0 ]]; then _emit '  %s✓ already done, skipped:%s %s\n' "$GREEN" "$RESET" "$what"; return 0; fi
  if ! confirm "$what — do it now?"; then
    warn "not done: $what"; SKIPPED+=("$what — re-run, or add --yes"); return 0
  fi
  "$act" || { rc=$?; [[ $rc -eq 3 ]] || exit "$rc"
    warn "left undone: $what"; SKIPPED+=("$what"); return 0; }
  rc=0; "$check" || rc=$?
  [[ $rc -eq 0 ]] || die "$what — still not done after this stage; the log is $LOG"
  CHANGED+=("$what")
}

# finish clears, then shows a closing summary. A --verify run's log ends with its verdict:
#   verify: <n> set up, <m> not set up[, <k> not asked]
# and the run exits 1 when anything is not set up, 2 when nothing is not set up but something
# could not be asked, and 0 only when every stage was asked and is set up. A 2 is not a pass.
finish() {
  _clear
  if [[ "$MODE" == verify ]]; then
    local verdict="verify: $N_SET_UP set up, $N_NOT_SET_UP not set up"
    (( N_NOT_ASKED )) && verdict+=", $N_NOT_ASKED not asked"
    (( N_NOT_SET_UP )) && _emit '\n  %sTo set it up, as root:%s  sudo bash %s%s\n' "$BOLD" "$RESET" "$WIZARD_PATH" "${ENVIRONMENT:+ --environment $ENVIRONMENT}"
    printf '\n%s\n' "$verdict"
    [[ -z "$LOG" ]] || printf '%s\n' "$verdict" >> "$LOG"
    (( N_NOT_SET_UP == 0 )) || exit 1
    (( N_NOT_ASKED == 0 )) || exit 2
    exit 0
  fi
  _emit '\n%s%s  ✓ Done%s\n' "$BOLD" "$GREEN" "$RESET"
  if (( ${#CHANGED[@]} )); then note "changed ${#CHANGED[@]}: ${CHANGED[*]}"; else note "nothing changed — it was all already done"; fi
  (( ${#WRITTEN_ENV[@]} ))    && note "wrote ${#WRITTEN_ENV[@]} setting(s) to $ENV_FILE: ${WRITTEN_ENV[*]}"
  (( ${#WRITTEN_SECRET[@]} )) && note "wrote ${#WRITTEN_SECRET[@]} credential file(s): ${WRITTEN_SECRET[*]}"
  if (( ${#SKIPPED[@]} )); then
    _emit '\n'; warn "still to do by hand:"
    for s in "${SKIPPED[@]}"; do note "  - $s"; done
  fi
  _emit '\n  Prove it without root:  bash %s --verify%s\n' "$WIZARD_PATH" "${ENVIRONMENT:+ --environment $ENVIRONMENT}"
  _emit '  The log:  %s\n\n' "$LOG"
}

# ──────────────────────────────────────────────────────────────────────────
# STAGES: author this section. One stage() per step, each a check_or_do.
# Replace the example below. Set TOTAL_STAGES to match the stages you write.
# ──────────────────────────────────────────────────────────────────────────

TOTAL_STAGES=1
wizard_args "$@"
[[ "$MODE" == verify ]] || needs_root "$@"
wizard_start example "Example setup"

# ── Example stage: replace with your real steps ───────────────────────────
example_done() { [[ -e /etc/example/ready ]]; }
example_do()   { bash "$REPO_ROOT/scripts/example.sh" --environment "$ENVIRONMENT"; }
stage "Example: the thing the existing script sets up"
say "What this stage does, in one line, and which script does the work."
check_or_do "the example is ready" example_done example_do
# ──────────────────────────────────────────────────────────────────────────

finish
