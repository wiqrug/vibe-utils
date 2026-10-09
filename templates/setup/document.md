# <NN>: <the kind of document> at <its path>

Advances:   wiqrug-setup
Blocked by: 01
Touches:    <the path documents.<kind> names>

<!-- wiqrug template: one ticket per kind of document the playback agreed as NEW. A kind kept in
an existing folder or file, or agreed `none`, gets no ticket: setup moves nothing. -->

## What to build

Lay down `documents.<kind>` at `<its path>` from the knowledge template the plugin's knowledge
README names for this kind at the `<standard | full>` level, as it stands, `<placeholders>` and
all. A folder that holds one file per record is created with a README of one or two sentences
saying what goes in it and which template each file follows, so git keeps the empty folder.
Nothing else in the project is touched.

## Acceptance

- [ ] `test -e "<its path>"` exits 0
- [ ] `git status --porcelain` lists nothing outside `<its path>` and this ticket

## Comments
