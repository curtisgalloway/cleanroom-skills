<!--
SPDX-FileCopyrightText: 2026 contributors
SPDX-License-Identifier: Apache-2.0
-->

# cleanroom-skills

Agent skills for writing a device driver for one operating system when the only reference driver
is under a license you may not copy from (for example a GPL Linux driver, when the new driver is
for a differently licensed OS). The method keeps a wall between the agents that read the original
source and the agents that write the new code, and records how each spec crossed that wall.

**Terms.** A *skill* is a packaged set of agent instructions with optional scripts; a *plugin* is
a bundle of skills installed from a *marketplace* listing. A *spec* is a per-device description
of the hardware (registers, init order, quirks) precise enough to write a driver from.
*Clean-room* means that no one who writes the spec's consumer, the driver, has read the original
source; the *wall* is that separation, the *dirty side* reads the source and the *clean side*
writes code. *Encumbered source* is source whose license you may not copy from. A *provenance
attestation* (`PROVENANCE.md`) is the private record of how one spec was made. More in the
[glossary](GLOSSARY.md).

- **What it is:** the published method. `cleanroom-investigator` reads the source and reports
  hardware facts in its own words, tagged by where each came from, and ships a leak scanner;
  `cleanroom-spec` turns those facts into a peripheral spec that an independent verifier must pass
  (a leak scan and a transfer review) before anyone on the clean side reads it;
  `cleanroom-verifier` re-checks a spec's accuracy without breaching the wall and writes a
  verification record; `cleanroom-implementer` keeps the agent writing the driver away from the
  source, with hooks, a Linux sandbox and session audits.
- **Its output is never published.** No clean-room spec is published by this project, and the
  skills tell you not to publish yours. Anyone who wants a clean-room spec runs the method
  themselves and keeps the spec and a filled-in `PROVENANCE.md` (template in
  [skills/cleanroom-spec/templates/PROVENANCE.md](skills/cleanroom-spec/templates/PROVENANCE.md)) as their own
  private record.
- **What it is not for:** laundering GPL code. If you can use the GPL, or the reference source is
  yours or permissively licensed, you do not need a wall: use driver-lab's
  `anchored-peripheral-spec`, which cites every fact back to the source lines, and publish the
  spec where its license fits. Also not for NDA or vendor-licensed material you are not allowed
  to read at all, and not legal advice: none of this has had legal review.
- **It depends on [driver-lab](https://github.com/curtisgalloway/driver-lab), installed
  alongside.** driver-lab's skills are neutral and know nothing of the wall; two skills here wrap
  them and add it. `cleanroom-investigator` wraps `board-expert`, which supplies the board facts
  and specs, and `cleanroom-verifier` wraps `spec-verifier`, which supplies the record format and
  procedure. driver-lab never depends on this repository.
- **Evidence that the method works** is driver-lab's frozen evaluation archive, at the commit this
  repository was split from:
  [evals/](https://github.com/curtisgalloway/driver-lab/tree/5d7eac2dabbb07265a61b56a3ad710eb9d03c454/evals)
  (the ENC28J60 and e1000 campaigns, which rebuild Linux drivers from specs and test them
  against the originals) and its
  [evidence/](https://github.com/curtisgalloway/driver-lab/tree/5d7eac2dabbb07265a61b56a3ad710eb9d03c454/evidence)
  records.

## Which skill do I want?

| Situation | Skill |
| --- | --- |
| You need a spec for a peripheral whose reference driver you may not copy from | `cleanroom-spec` (it runs `cleanroom-investigator` and a board expert as subagents) |
| A question about how an OS or firmware drives some hardware, answered as facts, never source code | `cleanroom-investigator`, as a subagent; never in the context that writes code |
| Re-verify a clean-room spec after an edit or after its sources moved, or check its accuracy | `cleanroom-verifier` |
| Write or cache into a board spec behind the wall | `cleanroom-investigator`, with its `BOARD-SPECS.md` |
| You are the agent writing code from a landed clean-room spec, or installing the enforcement for one | `cleanroom-implementer` |

## Installing

Install driver-lab's `driver-porting` plugin first (see its README), then this one.

### Claude Code

```
/plugin marketplace add curtisgalloway/cleanroom-skills
/plugin install cleanroom-skills@cleanroom-skills
```

### Codex

```
codex plugin marketplace add curtisgalloway/cleanroom-skills
codex plugin add cleanroom-skills@cleanroom-skills
```

## Tests

Python 3 standard library only, from the repository root:

```bash
python3 utilities/check-no-private-paths.py
python3 -m unittest discover -s skills/cleanroom-investigator/tests -v
python3 -m unittest discover -s skills/cleanroom-implementer/tests -v
```

CI (`.github/workflows/checks.yml`) runs these and the portability scan from
[public-skills](https://github.com/curtisgalloway/public-skills) on
`skills/cleanroom-implementer/scripts`, pinned to a commit.

## History

The skills were split out of driver-lab with their history on 2026-10-06; see
[TRANSITION.md](TRANSITION.md). Licensed under Apache-2.0 ([LICENSE](LICENSE)).
