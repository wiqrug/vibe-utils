---
name: wizard
description: Write, or hand over, a bash wizard that walks the user through steps only they can run — root, a group membership, a credential, a third-party dashboard. Use whenever the next step needs sudo or a secret the agent must not see; the agent checks it without root and hands over one command, never runs it.
---

# Wizard

!`wiqrug-check --skill`

If the first line above does not begin `wiqrug: set up —`, show that line to the user and stop.

Adapted from mattpocock/skills (MIT, © 2026 Matt Pocock).

A **wizard** is a bash script that walks the user, stage by stage, through a procedure only
they can perform: one needing root, a group membership, a credential, or a third-party
dashboard. It shows progress (`Stage 2/5`), checks each stage's state before doing anything
and skips what is done, captures what must be typed, and ends with a summary of what changed
and what is still to do by hand.

[template.sh](template.sh) is the library: Matt Pocock's wizard, kept whole — `stage`,
progress N/M, `confirm`, `ask_secret`, the closing summary. It is a bash script for the user's
terminal on a Linux or macOS host with GNU coreutils, not a command this skill runs. **Your job is
only to author the stages.** Everything above its `STAGES` marker is copied into every wizard word
for word, so that every wizard behaves the same: a change to the library is a change to every
wizard in the project, in one commit.

## The rules the library enforces

- **The agent never runs `sudo`.** A wizard started without root stops at `needs_root` and
  prints the ONE command to run — `sudo bash <absolute path> <its arguments>` — which you hand
  the user exactly as printed. Never several; never a paraphrase.
- **Every stage is `check_or_do "what" CHECK DO`.** CHECK returns 0 done, 1 not done, 2 cannot
  be asked from here. An apply skips what is done, runs DO for the rest and asks again; a DO
  that returns 3 left an irreversible step undone on purpose.
- **`--verify` answers "did it work?" without root.** It runs every CHECK, changes nothing,
  never prompts, and ends its log with the line
  `verify: <n> set up, <m> not set up[, <k> not asked]`. It exits 1 when anything is not set up,
  2 when nothing is not set up but something was not asked, and 0 only when every stage was asked
  and is set up. "Not asked" is its own count: a question nobody could put is not an answer either
  way, so a 2 is never reported as a pass.
- **`--yes` runs every stage without prompts, except irreversible ones.** Those use
  `confirm_irreversible`, which always asks, and answers *no* when nobody is at a terminal.
  `--yes` never answers a typed confirmation phrase either; the user types it.
- **Everything is logged** to `logs/<wizard>-<UTC stamp>.log` at the git root (or
  `WIZARD_LOG_DIR`), colours stripped, owned by the operator even when root wrote it, so the result
  can be read without pasting it back. Check that the project's ignore file covers that folder.
- **A secret is never echoed, logged or put on a command line.** `ask_secret` reads hidden, logs
  only a length, and never reads the current value to offer it back. A captured credential goes
  where the project keeps credentials — `write_secret_file`, 0400 root:root, created with that
  mode before it holds anything. `write_env` refuses a credential's name: the `.env` file holds
  configuration only.
- **A secret that lives on a website is typed there by the user.** `dashboard_secret NAME URL`
  opens the page, names the secret, and lists it as still to do by hand; the wizard never carries
  the value.

## Process

1. **Scope from what exists.** Read the scripts the procedure already has — each usually has an
   apply and a root-free check. A wizard **wraps them and re-does none of their work**: its CHECK
   is usually their check, its DO their apply. One wizard per procedure. A step that touches
   something the project check lists under `agents.never-touch` is exactly what a wizard hands to
   the user.
2. **Show the user the stages** in order — what each checks, what it runs, what (if anything)
   is typed and where it lands, which step is irreversible — before writing.
3. **Author it.** Copy `${CLAUDE_SKILL_DIR}/template.sh`; replace the header (what it does, how
   to run it, that it is safe to re-run, how to go back) and the example stage. A repeatable
   wizard lives with the project's other scripts — ask the user where, once, if there is no
   obvious folder. One that does something the project would never keep in a tracked script —
   deleting data above all — lives outside the repository, in the user's home folder, and the
   reason is said where it is handed over.
4. **Check it without running it**, by the wizard's absolute path:
   ```bash
   bash -n /absolute/path/to/<name>.sh
   shellcheck /absolute/path/to/<name>.sh
   bash /absolute/path/to/<name>.sh --verify </dev/null
   ```
   `shellcheck` only where it is installed; read the `--verify` run's last line. **Never run one
   end to end**: it needs root, and the user's terminal. Trace the apply path by reading it:
   every stage's CHECK, every DO, every value typed and where it lands.
5. **Hand over** the command `needs_root` printed, and the `--verify` line that proves it
   afterwards. The user's log is in the log folder; read it rather than asking what happened.

## Before and after any root step you hand over

Whether or not it is a wizard:

- **Probe first.** Before listing a root step taken from a status note or an old hand-over,
  probe its current state without root (`systemctl is-enabled`, a script's `--verify`, a file's
  date). Only hand over what is still needed.
- **Do the root-free prerequisites** (commits it depends on) before handing it over.
- **Write every command in full**, `sudo` included, one per line in a code block. The user types
  a command exactly as written: a shorthand in prose ("`systemctl enable a` and
  `enable --now b.timer`") is run literally and fails as a bash builtin.
- **Several wizards at once** go out as one command per line, in the order they must run, with
  the `--verify` that proves each one finished before the next is started.
- **Wait for the output before marking anything ✅.**
