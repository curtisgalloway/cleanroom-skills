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
- Until driver-lab's next milestone (LS7), driver-lab also keeps its copies of the three skills
  and the clean-room rules inside `board-expert` and `spec-verifier`; LS7 removes them there and
  moves those rules here.
