# Upgrading a project

What changed for a project set up by an earlier wiqrug, one section per release, newest last.
`/wiqrug:setup --upgrade` quotes every section after the project's version up to the installed one,
then shows the changes it would make and asks before making them.

An upgrade changes the settings file and the folders the settings name — never a document's
content. A section's `ini wiqrug-upgrade` block is what `lib/upgrade.py` reads; the prose around it
is what the plan quotes. The block may hold three sections, each key written `section.key`:

- `[renamed]` — `old.key = new.key`: the setting keeps its value under its new name;
- `[added]` — `section.key = value`, the value every project gets; a key with no `=` has no value
  a release can choose, and the upgrade asks the project for it;
- `[removed]` — `section.key`, deleted from the settings file.

A release that changes nothing for projects says so and has no block.

## 0.1.0

The first release. A settings file that names an earlier version has its version raised, and a
folder its `documents` settings name that does not exist yet is created empty; nothing else about
the project changes.

## 0.2.0

Nothing changes for projects: the settings file has its version raised, and no setting or folder
is added, renamed or removed. The skills changed: `/wiqrug:improve-codebase-architecture` is new,
and `/wiqrug:research` reports in the conversation, saving a file only when one is asked for.
