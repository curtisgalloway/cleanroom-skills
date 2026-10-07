<!--
SPDX-FileCopyrightText: 2026 contributors
SPDX-License-Identifier: Apache-2.0
-->

# cleanroom-skills

Instructions for coding agents working in this repository. The user guide is the
[README](README.md); terms are in the [glossary](GLOSSARY.md); how the repository was split out
of driver-lab is in [TRANSITION.md](TRANSITION.md).

## What this is

Three skills: `cleanroom-investigator`, `cleanroom-spec` and `cleanroom-implementer`. They depend
on driver-lab's skills (`board-expert`, `anchored-peripheral-spec`, `spec-verifier`), installed
alongside; driver-lab never depends on this repository. **Skill names are an interface**: other
repositories hand off to these skills by name, so renaming one breaks them.

## Checks

CI (`.github/workflows/checks.yml`) runs these on every pull request; run them locally before a
commit:

```bash
python3 utilities/check-no-private-paths.py
python3 -m unittest discover -s skills/cleanroom-investigator/tests
python3 -m unittest discover -s skills/cleanroom-implementer/tests
python3 <public-skills>/plugins/agent-workflow/skills/agent-agnostic-skills/scripts/portability_scan.py \
  skills/cleanroom-implementer/scripts
```

The last one needs a public-skills checkout; CI pins the scanner to one of its commits.

## Rules

- **No clean-room output here.** This repository is public and holds the method only. Never
  commit a clean-room spec, a filled-in `PROVENANCE.md`, a provenance ledger, scan reports, or
  source under another license, even as a test fixture; fixtures are invented devices.
- **Privacy**: files name machines by role only ("the test host"): no addresses, host names, user
  names or home paths. `check-no-private-paths.py` catches home paths; the rest is on review.
- **Git**: a topic branch and a pull request per change, cut from a freshly fetched
  `origin/main`. Push or open a pull request only on the user's explicit "push", and "push" never
  means pushing `main`. Merge only when told; deleting the merged branch, local and remote, is
  part of merging. Stage files by name.
- **Changing what a skill does** (its rules, the hook's policy, the scanner) needs a test that
  fails without the change, and a reviewer who reads the diff.
