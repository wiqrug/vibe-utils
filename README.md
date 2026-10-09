# wiqrug

A development loop for Claude Code, packaged as a plugin. It takes a request from a rough idea to
finished, proved work:

1. **grill** the idea until it is understood (`/wiqrug:grill-me`, `/wiqrug:grill-with-docs`);
2. **specify** it (`/wiqrug:to-spec`) and cut it into **tickets** a fresh session can build
   (`/wiqrug:to-tickets`);
3. **build** them one at a time (`/wiqrug:implement`), with you watching or unattended;
4. **keep what was learned** — decisions, traps, terms, open questions
   (`/wiqrug:update-knowledge`).

Every skill is called with the `wiqrug:` prefix, so none collides with a project's own skills.

This repository is the plugin and its own marketplace: `.claude-plugin/marketplace.json` lists one
plugin whose source is this folder.

## Install

⚠️ **`bin/wiqrug-check` must stay executable.** Every skill runs it first, a skill whose first
command cannot run ends with no answer and no error, and an install copies the mode it finds.
Some unpackers drop it, so after unpacking the zip, run this inside the unpacked folder:

```text
chmod +x bin/wiqrug-check
```

Committing the folder from Windows, where git records no mode by itself, mark it once after
`git add` and before the commit:

```text
git update-index --chmod=+x bin/wiqrug-check
```

Add the marketplace once. `<source>` is the GitHub repository you uploaded this folder to, written as
your account, a slash and the repository's name — or the path of an unpacked copy:

```text
claude plugin marketplace add <source>
```

Then install the plugin, choosing where it applies — the second from inside the repository:

```text
claude plugin install wiqrug@wiqrug --scope user       # every project on this machine
claude plugin install wiqrug@wiqrug --scope project    # this repository only, shared through git
```

`/plugin` inside Claude Code offers the same choice interactively.

## First: `/wiqrug:setup`

**Run `/wiqrug:setup` in a project before any other skill.** It checks that git and Python are
there — it never runs `git init` for you — then audits what the project already has: `CLAUDE.md`
and AGENTS.md, Claude Code's settings, rules, skills, agents and hooks, other AI tools' instruction
files (read, never edited), the README, the ignore file, and the build and test files it proposes
your "done" command from. It interviews you from there about how the project should be
organised, plays the result back and writes nothing until you confirm. Changes to an existing
`CLAUDE.md` are numbered proposals you answer one by one, and each of your skills that overlaps
one of wiqrug's is yours to keep, retire to an archive folder, or fold into the settings. Every skill reads the
settings file it writes; in a project without one, `/wiqrug:grill-me` still works and every other
skill stops and asks you to run setup.

`/wiqrug:setup --upgrade` brings a project set up by an older wiqrug to the installed version,
showing what it would change before it changes anything.

## The settings file and the project check

Setup writes wiqrug.md in the .claude folder at the repository's root, and you commit it:
Markdown, with the settings themselves in `ini wiqrug` blocks and the reason for each beside it.
`lib/settings.example.md` lists every setting and explains it.

`wiqrug-check`, from the plugin's `bin/`, is the only thing that reads it, and every skill but
`grill-me` and `interview` runs it first, as `wiqrug-check --skill`: the same answer with exit 0
whatever it is, because Claude Code abandons a skill silently when a command it runs while loading
exits non-zero, and the answer the skill must show you would be lost. Run it yourself from anywhere inside the project to see
what the skills see: whether git and Python are there, whether the project is set up and by which
version, and every setting with its paths made absolute. `wiqrug-check --json` prints the same for
scripts; its exit codes are listed at the top of `lib/project_check.py`.

## Versions

The plugin's version is set in `.claude-plugin/plugin.json` and changes only on a release, so an
update reaches users when a version is published, not on every push.

## Platforms

Proved on Linux: installed from a local copy for the user and for one repository, and `grill-me`,
`implement` and `setup` answering in throwaway folders. Installing from GitHub has not been run.
**Untested on Windows**: the scripts are written to run under Git Bash, and every
command a skill runs is a call to a Python script, but nobody has run them there yet. Under Git
Bash the unattended loop does not go to the background — Git Bash has no `setsid` — so it runs
attached to the window you start it in: leave that window open until it ends.

## Licence

MIT — see `LICENSE`. Some skills are adapted from Matt Pocock's skills; `NOTICE` carries his
copyright and licence.
