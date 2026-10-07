<!--
SPDX-FileCopyrightText: 2026 contributors
SPDX-License-Identifier: Apache-2.0
-->

# Split out of driver-lab

On 2026-10-06 the clean-room skills moved out of
[driver-lab](https://github.com/curtisgalloway/driver-lab) into this repository, so that
driver-lab holds only the open method (specs that cite their sources and are published where
their license fits) and this one holds the clean-room method, whose output is never published.
The reasons and the full plan are in driver-lab's
[license-split design](https://github.com/curtisgalloway/driver-lab/blob/5d7eac2dabbb07265a61b56a3ad710eb9d03c454/docs/LICENSE-SPLIT.md)
(requirement LS-R14) and its milestone LS6.

## What moved

| driver-lab path | Here |
| --- | --- |
| `skills/cleanroom-spec/` | `skills/cleanroom-spec/` |
| `skills/cleanroom-implementer/` | `skills/cleanroom-implementer/` |
| `skills/os-investigator/` | `skills/cleanroom-investigator/` (skill renamed `cleanroom-investigator`) |

Nothing else came across in the history. The skills' content is unchanged apart from the rename
and from naming driver-lab where they refer to its skills (`board-expert`,
`anchored-peripheral-spec`, `spec-verifier`) and its license-split design. Added on top: the
license, plugin manifests, README, AGENTS.md, glossary, CI and the privacy check (copied from
driver-lab's `utilities/`).

## History and hashes

The history was cut from driver-lab commit `5d7eac2` with `git filter-repo`, keeping the three
skill directories and renaming `skills/os-investigator` to `skills/cleanroom-investigator`. Every
kept commit got a new hash; driver-lab commits that touched none of the three skills have no copy
here. [history/driver-lab-commit-map.txt](history/driver-lab-commit-map.txt) maps each driver-lab
commit to its copy. driver-lab's own history was cut out of
[public-skills](https://github.com/curtisgalloway/public-skills) the same way (driver-lab's
`TRANSITION.md` and `history/public-skills-commit-map.txt`), so this history starts where
driver-lab's does, with public-skills commits from 2026-09-01. A public-skills hash translates
through driver-lab's map first, then this one.

`git log --follow skills/cleanroom-investigator/SKILL.md` shows the history from before the
rename.

## What stayed in driver-lab

- The evaluations (`evals/`), their evidence and notebooks, `RECONSTRUCTION.md` and
  `QEMU-DIFFERENTIAL.md`: a frozen archive. This repository links to them at the pinned commit
  above.
- `board-expert`, `anchored-peripheral-spec`, `spec-verifier` and the other open skills, which the
  clean-room skills use; install driver-lab alongside.
- Until driver-lab's milestone LS7, driver-lab also kept its copies of the three skills and the
  clean-room rules inside `board-expert` and `spec-verifier`.

## What moved in LS7

driver-lab's milestone LS7 deleted its copies of the three skills and moved the clean-room text
out of its open skills, so that those carry none. The text landed here unchanged apart from names
(`os-investigator` is `cleanroom-investigator`) and the merges and reframings noted there;
driver-lab's `evidence/LS7.md` lists every passage with its source lines and destination.

| driver-lab source | Here |
| --- | --- |
| `board-expert/SKILL.md`: delegation reasons, "Method and constraints", the cache and document rules, the cache rule; `board-expert/QUESTIONS.md`: this skill's and `cleanroom-spec`'s rows | `skills/cleanroom-investigator/SKILL.md`, "Wrapping `board-expert`" |
| `board-expert/SPEC-FORMAT.md`: "Clean-room rules for spec content", the clean-room reading of "What a spec is", the `[source-observed]` class, the `[rtl]` and `[emulated]` notes on encumbered sources; `board-spec-scaffold` and its templates: the clean-room convention, research-fill step, stub and vendor-skill text | `skills/cleanroom-investigator/BOARD-SPECS.md` |
| `spec-verifier/SKILL.md`: "Clean-room driver specs" and the clean-room text in its shared parts; `board-expert/VENDOR-GUIDE.md`: the clean-room verifier note | `skills/cleanroom-verifier/SKILL.md` (new) |

## What moved in LS8

driver-lab's milestone LS8 moved the clean-room text out of its root documents, so that outside
its frozen archive driver-lab names this method only in one README line pointing here (a check,
`utilities/check-open-side.py`, enforces that in its CI). driver-lab's `evidence/LS8.md` lists
every passage with its source lines.

| driver-lab source | Here |
| --- | --- |
| `DESIGN.md`: the licensing wall, the clean-room terms, the investigator, `cleanroom-spec` and implementation pieces, lifecycle steps 2, 3 and 5 and the clean-room sentences of steps 1 and 4, the leak scanner, the boundary limit | [DESIGN.md](DESIGN.md) (new), passage by passage with line ranges |
| `README.md`: "Clean-room driver porting" | README, "How the pipeline fits together" |
| `AGENTS.md`: the Isolation rule and the sandbox approval note | AGENTS.md, "Isolation" |
| `GLOSSARY.md`: clean-room boundary, transfer review, attractant, provenance ledger, provenance attestation | GLOSSARY.md (rows that were already here; strace, canary, operator, blind requirement list and frozen archive added) |

driver-lab's evaluations stay there as a frozen archive with a header pointing here;
`RECONSTRUCTION.md` and `QEMU-DIFFERENTIAL.md` stay with them.
