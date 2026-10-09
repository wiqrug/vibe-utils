# Gotchas

<!-- wiqrug template: gotcha. Format of every entry —

## G-<nnn> · <area>: <the symptom, as somebody would meet it>

**Symptom.** What was seen.
**Cause.** Why it happens — read in the source, the configuration or the data, not inferred.
**Instead.** What to do.
**Enforced by** the test, guard or refusing script that stops it coming back — or `none:` and why.

<nnn> is the next free number: the highest G- in this file, plus one, three digits. A G- is
permanent. <area> is one the file already uses where one fits; a new area is a deliberate act.
A trap that already has an entry gets an **Occurrence.** line on that entry — what was being done
when it bit, and why its enforcement did not catch it — never a second entry. -->

Traps: things that behave unlike their documentation, unlike common sense, or unlike the way they
behaved last week. Read this before debugging anything that "should work".
