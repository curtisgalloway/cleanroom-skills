---
name: cleanroom-verifier
description: >-
  Verify a spec behind the clean-room wall and write its verification record: wraps driver-lab's
  spec-verifier (the record format and the per-claim procedure) and adds the wall — the verifier
  loads cleanroom-investigator, the record quotes no source and must pass leak_scan.py, and a
  clean-room driver spec from cleanroom-spec gets cleanroom-spec's own verifier first, then an
  accuracy pass on every tagged fact. Use when asked to verify, re-verify or audit a clean-room
  driver spec, after editing one, after its sources moved, or to verify any spec whose sources
  are encumbered. Orchestrator only; needs driver-lab installed alongside.
---

<!--
SPDX-FileCopyrightText: 2026 contributors
SPDX-License-Identifier: Apache-2.0
-->

# Clean-room verifier (spec-verifier, behind the wall)

**Terms.** A *verification record* is the file of per-claim verdicts (`PASS`, `FAIL`,
`UNVERIFIABLE`, `GAP`, `ADJUDICATE`) kept outside the spec; driver-lab's `spec-verifier` defines
it, with the procedure that produces it. A *clean-room driver spec* is the per-peripheral spec
`cleanroom-spec` produces, with its provenance ledger and usage notice. *Encumbered source*, the
*wall* and the *clean side* are in the [glossary](../../GLOSSARY.md).

driver-lab's `spec-verifier` is neutral: it verifies board specs and peripheral specs and
reviews, and says that a skill defining its own spec kind may wrap it. This skill is that wrapper
for the clean room. **Load `spec-verifier` and follow it**, with the rules below added to it and
winning where the two differ. The text below moved here from `spec-verifier` in driver-lab's
license-split milestone LS7, unchanged apart from names, except where noted in driver-lab's
`evidence/LS7.md`.

Why a skill of its own rather than a section of `cleanroom-spec`: `cleanroom-spec` runs one
verifier, its transfer review, before a spec lands; this skill is the on-demand re-run of both that
review and the accuracy pass, and its record rules apply to any spec verified from encumbered
source, not only to `cleanroom-spec`'s. It wraps `spec-verifier` the way `cleanroom-investigator`
wraps `board-expert`.

## Rules added to `spec-verifier`

- **Which skills create which kind** (`spec-verifier`'s opening): `cleanroom-spec` runs this phase
  as its last step for clean-room driver specs, and points back here for the re-run.
- **Claims** (`spec-verifier`'s Terms): for a clean-room driver spec, one tagged fact
  (`[databook]`, `[standard]`, `[DT]`, `[inference]`) in the register tables and sequences.
- **No source in the record.** It is a clean-side artifact like the spec: describe what was
  compared and how it differs; never quote driver or firmware code. `cleanroom-investigator`'s rule
  applies in full, and the record must pass `cleanroom-investigator/scripts/leak_scan.py`.
- **Identify the kind** (procedure step 1): the `cleanroom-spec` required structure (provenance
  ledger, usage notice) means a clean-room driver spec.
- **Spawn the verifier** (procedure step 3): give it `cleanroom-investigator` for the clean-room
  rule and the cache discipline, in addition to what `spec-verifier` lists; for a driver spec, its
  cited documents.
- **Board specs** (`spec-verifier` § Board specs): `[source-observed]` (defined in
  `cleanroom-investigator/BOARD-SPECS.md`) names a page or a tree and is compared against it like
  any other claim, TODO or not.
- **Vendor layers** (from driver-lab's `board-expert/VENDOR-GUIDE.md`): every fact from a vendor
  or local root reaches the report tagged with its layer, so a downstream clean-room verifier can
  see that a citation is not publicly checkable.

## Clean-room driver specs

The kind produced by `cleanroom-spec`. Two passes, and the first is not this skill's to redefine:

1. **`cleanroom-spec`'s own verifier**, exactly as that skill defines it: a fresh subagent with its
   verifier template, the five checks (mechanical scan, leak judgment, hardware-derived structure,
   attractants, usage notice), and `cleanroom-investigator/scripts/leak_scan.py`. Run it; record its
   verdict in the record's body as the first line (`Clean-room verifier: PASS` or `FAIL — <what>`).
   That verifier checks the wall, not accuracy, by design.
2. **Accuracy**, which that verifier deliberately leaves out: every `[databook]`, `[standard]`, and
   `[DT]` fact in the register tables, bit fields, sequences, and constants is compared against the
   cited document section or device tree the way a board spec's facts are. `[source-observed]`
   facts are checked for their required markers ("order not known to be required", "re-derive on
   hardware") and against the source commit named in the provenance ledger; the verifier reads
   that source under `cleanroom-investigator`'s rule and quotes none of it. An `[inference]` fact is
   verified on its **argument**, not on a citation: do the stated premises hold at the pinned
   source, and does the conclusion actually follow from them? A premise that does not hold is a
   `FAIL`; premises that hold under a conclusion they do not support is also a `FAIL`, with the
   gap in the reasoning named. The commonest form is a workaround a driver applies to a whole
   family being written as a hardware requirement, when the erratum scopes it to one part. An
   `[emulated]` fact is checked against an extract of what its cited runs recorded, never against
   the model's source: it is a `FAIL` when it claims more than the runs show, names the model's
   mechanism instead of an observation, or is the only authority behind a step.

- **Claims** are keyed by section and ordinal (tables: `<Section>/<table>/<row name>`; sequences:
  `<Section>/<step number>`).
- **Two verifiers** for the register map and the init sequence.
- **Record location**: `resources/<spec-basename>.verify.md` beside the spec, or the project's
  `docs/provenance/` directory when the spec's ledger already lives there; `spec_file` relative to
  the record's parent's parent. The record itself must pass `leak_scan.py`.
