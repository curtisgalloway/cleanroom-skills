<!--
SPDX-FileCopyrightText: 2026 contributors
SPDX-License-Identifier: Apache-2.0
-->

# Clean-room design

The design text for the clean-room method, moved here from driver-lab's `DESIGN.md` in the
license split (driver-lab milestone LS8, 2026-10-06; requirement LS-R14). driver-lab's
[DESIGN.md](https://github.com/curtisgalloway/driver-lab/blob/main/DESIGN.md) keeps the open
method: the hardware map, the evidence model, verification, continuous review (C1–C8) and the
evaluation method. This document is the part of that design that concerns the wall, and is read
together with it.

**How this was moved.** Each passage below is moved, not rewritten. Its source is driver-lab's
`DESIGN.md` at commit
[`6a58cb4`](https://github.com/curtisgalloway/driver-lab/blob/6a58cb427dc0f5ebbdecae68f8db036208d85512/DESIGN.md),
cited by line range. Three kinds of change were made: skill names follow the split
(`os-investigator` is now `cleanroom-investigator`; the clean-room procedure of driver-lab's
`spec-verifier` is now [`cleanroom-verifier`](skills/cleanroom-verifier/SKILL.md)); links point
at this repository's skills or at driver-lab files at that commit; and a passage that was a
fragment of a longer sentence is completed with the words it needs to stand alone, marked
*(recast)*. driver-lab's `evidence/LS8.md` lists every moved and reworded passage.

The evaluations that test the method (the ENC28J60 and e1000 campaigns) stay in driver-lab as a
frozen archive, with the documents that describe them:
[RECONSTRUCTION.md](https://github.com/curtisgalloway/driver-lab/blob/6a58cb427dc0f5ebbdecae68f8db036208d85512/RECONSTRUCTION.md),
[QEMU-DIFFERENTIAL.md](https://github.com/curtisgalloway/driver-lab/blob/6a58cb427dc0f5ebbdecae68f8db036208d85512/QEMU-DIFFERENTIAL.md)
and [EVAL-PLAN.md](https://github.com/curtisgalloway/driver-lab/blob/6a58cb427dc0f5ebbdecae68f8db036208d85512/EVAL-PLAN.md).
New rounds run from this repository.

## Terms

From driver-lab's design Terms (lines 68–71, 80 and 85); the rest of that list stays in driver-lab.
More in the [glossary](GLOSSARY.md).

- **Clean room:** a workflow separating source readers from implementers through checked reports.
- **Encumbered source:** source the workflow treats as unavailable for copying into the target.
- **Dirty side:** the contexts authorized to read encumbered driver or firmware source.
- **Clean side:** the contexts consuming cleared facts without reading that encumbered source.
- **Provenance map:** the exact reference-file list used by clean-room verifiers and output scans.
- **Ledger** *(clean-room sense; recast)*: a clean-room event log (line 85 named both senses; driver-lab
  keeps the evaluation answer key).

## Scope

From driver-lab's "Scope: specs and their quality" (lines 37–38). The split reversed the
location: `cleanroom-implementer` now lives here, and keeps the same two jobs.

`cleanroom-implementer` stays in this repository as the tool that produces candidate drivers
for the quality signals and as the handoff contract for consumers.

## The licensing wall

From driver-lab's "The problem and the two walls" (lines 122–144). The other half of that
section, the accuracy problem, stays in driver-lab's "The problem".

There is a separate risk when the reference is GPL or otherwise encumbered relative to the target. A
document that reproduces source structure, invented identifiers, or implementation text may be
unusable as a clean-room input even when its register values are correct. The repository therefore
preserves evidence of who read what and what crossed into the implementation context. Its rules are
a workflow for handling that boundary, not a legal determination about a particular project.

**The licensing wall controls transfer.** `cleanroom-investigator` reads encumbered source in a separate
context and returns original descriptions of facts. `cleanroom-spec` adds a file-based handoff,
independent boundary review, scanning, and provenance records. Its verifier checks five things:
mechanical overlap, possible reproduction, hardware-derived organization, source-reading
attractants, and the usage notice. It deliberately does not determine technical accuracy.

(From the accuracy paragraph, lines 136–138.) A boundary `PASS` is not an accuracy `PASS`, and an
accuracy `PASS` is not evidence that the source-access boundary was enforced. Keep the results
separate.

Source that the target may derive from takes a different route:
[`peripheral-spec`](https://github.com/curtisgalloway/driver-lab/blob/c2217166e81797d6235a564e1202d03a1cbcea6f/skills/peripheral-spec/SKILL.md) keeps direct code citations
and permits source reading. That route is deliberately unsuitable as a substitute for the clean-room
route on encumbered material. The skill tells an uncertain caller to use the clean-room route. This
document describes those repository rules, rather than deciding license compatibility.

(Since driver-lab's LS7 the peripheral-spec skill no longer names the clean-room route; the README of
this repository says when to use which.)

## Evidence model, behind the wall

From the third rule under driver-lab's "Every class rests on an assumption" (lines 258–262). driver-lab
keeps the rule up to "never how the model produces it"; the reason below is the clean-room one.
*(recast)*: An `[emulated]` fact states what was observed from outside the model, never how the
model produces it: the model's source is encumbered like any other, and the tag must not
carry it across the clean-room wall.

## The pieces, behind the wall

From driver-lab's "The pieces, grouped by role" (lines 328–422).

### Investigation

From the section's opening (lines 328–329) *(recast)*: the orchestrator delegates source reading;
an implementation context must not invoke these investigator roles to fill its own gaps.

[`cleanroom-investigator`](skills/cleanroom-investigator/SKILL.md) takes a hardware question, target identity, and
source revision, usually with a board expert's map. It produces tagged facts, original mechanism
prose, confidence limits, and pinned provenance. It refuses source excerpts, close structural
paraphrase, source-invented naming, and unmarked assumptions about ordering. Board research-fill and
`cleanroom-spec` consume its output; the verifier also loads its boundary rules.

(Since LS7, driver-lab's board research-fill loads `board-expert` instead; research-fill behind
the wall uses this skill through `BOARD-SPECS.md`.)

The four board stub skills are user-discoverable names for that same delegated role. They produce no
independent hardware database. `cleanroom-spec`, research-fill, and reference selection can invoke
the shared expert through a stub or directly. Source acquisition remains the expert's job, not a set
of source-reading commands performed by the clean-side orchestrator.

(driver-lab's open text now says board stubs are names for `board-expert`'s role and that none
ship today.)

### Authoring

[`cleanroom-spec`](skills/cleanroom-spec/SKILL.md) takes one peripheral, its board or generic IP
scope, reference provenance, and the target OS tree. It produces `docs/<device>-spec.md`, a source
map, boundary-scan evidence, and clean-room ledger entries. Its two
[templates](skills/cleanroom-spec/templates/) brief the spec author and boundary verifier. It
refuses to bring unverified draft text into the orchestrator context. `cleanroom-implementer`
consumes the landed document; `spec-verifier` supplies a separate accuracy pass.

(Since LS4 a third template, `PROVENANCE.md`, holds the private provenance attestation; since LS7
the accuracy pass behind the wall is `cleanroom-verifier`, which wraps `spec-verifier`.)

From the `peripheral-spec` paragraph (lines 377–378): the skill refuses the
encumbered-source use case and fabricated anchors; it does not load the clean-room investigation
role for its source-reading workflow.

From the `reference-driver-review` paragraph (lines 391–392) *(recast)*: `reference-driver-review`'s
checkers and later verification reuse the peripheral-spec route; it is not an alternative input channel
for a clean-room implementer.

### Verification

From driver-lab's "Verification" (lines 402–404) *(recast)*: the independent second reading
covers register maps and initialization sequences for clean-room driver specs. Agreement is
evidence of repeatability, not proof of truth.

### Implementation

[`cleanroom-implementer`](skills/cleanroom-implementer/SKILL.md) supplies standing rules, install
material, access blocking, and auditing for a consuming project. Its inputs are a landed spec,
prefetched public references, and the target OS tree. Implementation work produces target code; gaps
produce `docs/spec-gaps/<device>.md`. The supplied hook and audit scripts produce logs and audit
reports. The role refuses encumbered-source access, provenance-sidecar reading, and delegated source
investigation. Gaps go back through the orchestrator and authoring workflow.

A separate context is insufficient access isolation: subagents can inherit environment and
permissions. The install guidance therefore separates investigator/verifier processes and
implementation launch settings. Environment restrictions are the strongest boundary; hooks,
permissions, restricted agents, and instructions add defense and evidence. The installation material
targets Antigravity, while the scripts describe harness-neutral event handling. Verify actual
enforcement in the consuming harness; installing the plugin alone does not establish it.

### Evaluation

From driver-lab's "Evaluation" (line 428) *(recast)*: in the frozen campaigns, candidate production
used `cleanroom-spec`; claim checking used `spec-verifier`.

## A peripheral's lifecycle behind the wall

From driver-lab's "A peripheral's lifecycle" (lines 435–538). driver-lab keeps steps 1, 4 and 6
(renumbered 1 to 3) without their clean-room sentences, which are here; steps 2, 3 and 5 moved
whole and keep their numbers.

Follow an ENC28J60 Ethernet peripheral attached to a board supported by a vendor kernel, through a
differently licensed target OS port. The board attachment is illustrative; the evaluation corpus is
the existing pilot. Paths below are consuming-project artifacts unless explicitly under this plugin.
This walkthrough describes how to reach a measurement, not a completed ENC28J60 comparison.

### 1. Set the scope and establish the board map

From step 1 (lines 442–443): the person identifies the board revision, SPI attachment, peripheral
revision, vendor tree, and target OS. `cleanroom-spec` resolves any material forks using the
question catalog. The rest of the step is driver-lab's.

### 2. Investigate behind the boundary

The orchestrator chooses a scratch draft path and delegates to an investigator loading
`cleanroom-investigator` plus the appropriate board expert. The expert resolves the board, SoC, bus
attachment, and IP documents, then materializes reference sources in `~/src/<cache>/`. It records
actual commits rather than relying on a moving branch name.

The investigator uses the device tree for bus attachment and host-controller placement, translating
any mapped host addresses explicitly. It seeks hardware documentation for peripheral behavior, then
uses source to investigate remaining mechanisms. Source-only facts retain their caveats. Similar IP
is a lead to investigate, not evidence that every fact transfers unchanged to this instance.

The author writes the full draft at the scratch path and the exact reference-file list at
`docs/provenance/<device>-map.txt`. The reply contains only the draft path, a short summary, and
repository/commit provenance. The orchestrator has enough to route the next step without reading the
unverified document. The target-OS integration half can cite the target's own files directly.

### 3. Check what crosses the licensing wall

A fresh verifier receives the scratch path and provenance map and runs the five-check procedure from
`cleanroom-spec`. Its mandatory `leak_scan.py` comparison detects shared token sequences and
identifier reuse, allowing explicitly listed hardware nomenclature. The scanner reports locations,
lengths, and hashes rather than reproducing matched source passages.

A failure returns section and line references plus reasons, never offending text. A fresh author
repairs the scratch file, and another verification follows. After two failures on the same section,
the workflow stops and escalates the verdict to a person. If source is the only authority for a
mechanism, that person must decide whether and how it can be expressed within the workflow. The
absence of another authority does not permit relabeling a boundary failure as a pass.

On a boundary pass, the orchestrator lands `docs/<device>-spec.md`, hashes its contents, and appends
the revision and scan report to `docs/provenance-ledger.md`. Scan reports live under
`docs/provenance/`; transcripts are retained as evidence, by path rather than by copy,
because they live in the harness's protected state directory. The prescribed project index receives a
summary entry. This ledger records clean-room events, not the evaluation's list of requirements.

### 4. Establish accuracy separately

From step 4 (lines 499–501 and 521–522). The rest of the step (the record's location and
contents, the verdicts, adjudication) is driver-lab's.

Invoke `cleanroom-verifier` for the landed clean-room spec. It runs the boundary procedure unchanged and
then checks tagged facts against their documents, device trees, or pinned source. Its source reader
may compare source-observed behavior with the reference; the eventual implementer may not.

The current accuracy procedure has no common repair bound; the two-failure bound above is for the
boundary check, and extending it to accuracy is proposed work.

### 5. Implement without reopening the reference

A different implementer receives the cleared spec, its public references under `docs/references/`,
and the target OS tree. It builds the Ethernet driver in the restricted environment. If a reset
condition is missing, it appends a question to `docs/spec-gaps/<device>.md`, marks the code site
`TODO(spec-gap)`, and works on another part. It does not open the source map or ask a research agent
to answer the question directly.

The orchestrator routes that question to a fresh investigation, edits a scratch copy, verifies it,
lands the new spec revision, adds a new ledger line, and closes the gap. Editing a landed spec
without this loop invalidates its earlier hash-based evidence. Before driver merge, the workflow
requires an output scan against the original provenance map and audits of every implementation
session and its artifacts. A contaminated session's entire diff is discarded and regenerated in a
fresh restricted session, as `cleanroom-implementer` specifies.

### 6. Measure, preserve, and revisit

driver-lab's step 3, ["Measure, preserve, and revisit"](https://github.com/curtisgalloway/driver-lab/blob/main/DESIGN.md#3-measure-preserve-and-revisit), unchanged.

## Evaluation inputs behind the wall

From driver-lab's "Freeze the inputs and decisions" (lines 1004–1006); driver-lab now calls the
scan the source-overlap scan.

Run corpus drift checks, the ledger schema/freeze checks, and the clean-room scan prescribed by the
[pilot README](https://github.com/curtisgalloway/driver-lab/blob/6a58cb427dc0f5ebbdecae68f8db036208d85512/evals/enc28j60/README.md).
The gold ledger is itself a clean-side artifact; source quotations do not become acceptable merely
because they are in an evaluation file.

## Tools

From driver-lab's "What is shipped, what is unfinished, and what is proposed" (lines 1094–1095;
line 1085 also listed the implementation skill as shipped).

- [`leak_scan.py`](skills/cleanroom-investigator/scripts/leak_scan.py) checks source overlap and reused
  identifiers; human or agent judgment still evaluates structure and close paraphrase.

## Extending: choosing the route

From driver-lab's "Extending the system" (lines 1169–1170). driver-lab now says to use the
peripheral-spec skill and place the spec by its sources' licenses.

For a new peripheral driver spec, choose the clean-room or peripheral-spec skill based on the
reference relationship to the target.

## Limits

From driver-lab's "Limits and unresolved boundaries" (lines 1188–1191).

A clean-room boundary check is about the wall, not accuracy. Mechanical dissimilarity and session
audits provide evidence about a particular process and its outputs; they cannot establish that a
model never encountered reference code during training. The source-access restrictions must also be
installed and tested in the actual harness. Prompt instructions alone do not provide isolation.
