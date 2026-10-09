# Knowledge templates

What `/wiqrug:setup` lays down for a project's knowledge base, and the format
`/wiqrug:file-knowledge` and `/wiqrug:update-knowledge` write each kind in. Nothing is generated:
each template states its own format, in a comment at its head that stays in the project's copy.

A level's templates are `common/` plus the level's own folder:

| Kind | Setting | Standard | Full |
|---|---|---|---|
| term | `documents.glossary` | `common/glossary.md` | `common/glossary.md` |
| decision (`D-`) | `documents.decisions` | `common/decision.md`, one file each | the same |
| gotcha (`G-`) | `documents.gotchas` | `common/gotchas.md` | the same |
| open question | `documents.questions` | `standard/questions.md` — the question itself | `full/questions.md` — the worklist of open `Q-` items |
| Now and Next | `documents.now` | `standard/now.md` | `full/now.md` — points at the units |
| fact (`F-`) | `documents.ledger` | — | `full/fact.md`, one file each |
| question (`Q-`) | `documents.ledger` | — | `full/question.md`, one file each |
| unit | `documents.units` | — | `full/unit.md`, one file each |

A file the table names once is laid down as it stands, `<placeholders>` and all; a template marked
"one file each" is the shape of every new file in that folder.
