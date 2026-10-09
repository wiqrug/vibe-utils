# Building the agreed structure

What `/wiqrug:setup` does after the user's yes, once the in-progress settings file is written and
`wiqrug-check` answers `wiqrug: setup in progress`. The playback is the whole input: nothing is
decided here that it did not decide, and **the project's application code is never touched** —
not to make a test pass, not to fix a path.

`${CLAUDE_PLUGIN_ROOT}` below is the plugin's folder, which setup's own page names: write that
path in its place in every command.

## 1 — the queue

Write the agreed setup as a queue in the project's own queue folder — `documents.queue`, from the
in-progress settings file — under `<documents.queue>/wiqrug-setup/`, in the item format of
`${CLAUDE_PLUGIN_ROOT}/skills/to-tickets/items.md`. Each ticket starts from its template, with
every `<placeholder>` filled from the playback and the template's comment removed:

| # | ticket | template |
|---|---|---|
| 01 | the settings file in full | `${CLAUDE_PLUGIN_ROOT}/templates/setup/settings.md` |
| next | one per kind of document agreed as new — a kind kept where it is gets none | `${CLAUDE_PLUGIN_ROOT}/templates/setup/document.md` |
| next | one per project skill to retire or fold — a kept one gets none | `${CLAUDE_PLUGIN_ROOT}/templates/setup/skill.md` |
| last | one per accepted `CLAUDE.md` proposal, in number order, or one for a new `CLAUDE.md` | `${CLAUDE_PLUGIN_ROOT}/templates/setup/claude-md.md` |

⚠️ **Setup's tickets are the one kind of item that keeps a `Touches:` line.** A work item names no
files, because the session that builds it finds them from the code; a setup ticket writes named
files into somebody else's project, and step 3 checks every subagent's writes against its
`Touches:` — that check is how setup never touches the project's application code. The queue
reader reads the line past, as it does an older queue's.

Number them from `01` in that order. Then read the queue back:

```bash
wiqrug-check --run "${CLAUDE_PLUGIN_ROOT}/lib/work_next.py" wiqrug-setup --all
```

It must list every ticket and exit 0; exit 2 names the malformed one — fix it before anything else.

## 2 — the branch

```bash
git switch -c wiqrug-setup
```

The settings file and the queue are not committed yet, so they come along. Everything setup
commits is on this branch, so a setup the user dislikes is one branch to delete. If the branch
already exists, show `git log --oneline wiqrug-setup` and ask whether to resume on it or delete
it; never reuse it unasked.

## 3 — one subagent per ticket, one at a time

The tickets mostly touch the same few files, so **never two at once**. For each ticket, in order,
start one `general-purpose` subagent in the foreground, with this prompt and the ticket's path
and the project's root filled in:

```text
Build one setup ticket: <the ticket's path>, in the project at <the root>. Read it whole first.
Write only the paths under its Touches: — never the project's application code, and never
another ticket's file. For a new CLAUDE.md, load the writing-for-agents skill first. For a
document, read ${CLAUDE_PLUGIN_ROOT}/templates/knowledge/README.md first. Then run each acceptance
box's command and note its exit code. Do not tick boxes and do not commit. Report in at most 150
words: what you wrote, each box's command with its exit code, and anything you could not do.
```

When it returns, **check its result yourself** — the subagent's word is not a tick:

1. `git status --porcelain` lists only the ticket's `Touches:` paths, the ticket and, for 01, the
   queue. Anything else is reverted, with `git restore` or by deleting what it created.
2. Run each box's command. A box is ticked only because the command ran here and exited 0.
3. Every box green: tick them in the ticket, then commit the ticket's paths and the ticket file —
   the first commit carries the whole queue as written —
   as `wiqrug setup <NN>: <the ticket's title>`. One commit per ticket.

A box still red: one more subagent, handed the command and its output. Red again: stop building,
leave the ticket uncommitted, and go to the report with what failed.

## 4 — the final check

```bash
wiqrug-check --run "${CLAUDE_PLUGIN_ROOT}/lib/final_check.py"
```

Run from inside the project: it finds the root itself. Show its ✅/⚠️/❌ lines **exactly as
printed**. A ⚠️ is the done command's owed exit — everything it could check passed, the rest is
owed — and is never reported as ✅. A ❌ on the done command is the project's own failing check:
report it as the project's, and leave the code it names alone. Any other ❌ is setup's: say which
ticket it points to.

## 5 — the report

```text
Branch       wiqrug-setup, on <the branch it was cut from | no commit: a new repository>
Commits      <one line per ticket: hash  wiqrug setup NN: title>
Final check  <its lines, verbatim>
Not built    <a ticket stopped red, with its command and output — or: none>
```

Then how to keep it or throw it away, filled in with the branch it was cut from:

```bash
git switch <base> && git merge --no-ff wiqrug-setup && git branch -d wiqrug-setup   # keep it
git switch <base> && git branch -D wiqrug-setup                                     # throw it away
```

In a repository that had no commit before setup, `wiqrug-setup` holds its first commits: keep it
with `git branch -m wiqrug-setup main`; throw it away with `git switch --orphan main` and then
`git branch -D wiqrug-setup`.
