<!--
SPDX-FileCopyrightText: 2026 contributors
SPDX-License-Identifier: Apache-2.0
-->

# Board specs behind the wall

**Terms.** A *board spec* is driver-lab's per-hardware Markdown file (a board, SoC, companion chip
or IP block) that `board-expert` reads; its format is driver-lab's `board-expert/SPEC-FORMAT.md`.
A *root* is a directory of specs with a `board-specs.yaml` marker; the *cache* is the directory
where the expert clones reference source; a *provenance tag* (`[databook]`, `[DT]`, …) says what
backs a fact. *The wall*, *encumbered source* and the *dirty* and *clean side* are in the
[glossary](../../GLOSSARY.md).

driver-lab's board-spec format and its `board-spec-scaffold` skill are neutral: they say nothing
about the wall. The rules below used to sit inside them and moved here in driver-lab's
license-split milestone LS7, unchanged apart from names, except where noted in driver-lab's
`evidence/LS7.md`. They apply whenever a board spec is written, cached into, or read behind the
wall. `SKILL.md` beside this file covers running `board-expert` as the investigator.

## What a spec is, behind the wall

*(From `SPEC-FORMAT.md`, "What a spec is, and is not".)*

A spec is the artifact allowed to cross the clean-room wall. It may live in the target OS tree next to
the code it describes, so everything in it must already be safe there: facts cited to a datasheet,
standard, project documentation, or device tree; facts the `cleanroom-spec` verifier has PASSed; facts
measured on hardware; and pointers to where the encumbered source lives. It carries the *where* and
the *what*. The *how* (investigation method, report format, no-source-code rule) belongs to
`cleanroom-investigator` and is not repeated in a spec.

A spec is not a place for source-invented identifiers.

## The `[source-observed]` class

*(From `SPEC-FORMAT.md`: the provenance-tag list, the inference example, series, variants, the tag
rules and anchored IP resolution; and from `board-spec-scaffold` and its templates.)*
`SPEC-FORMAT.md` says only that this class is "defined by an extension"; this is the definition.
driver-lab's `spec_check.py` still accepts the tag and fails a tail clause that carries it without
`TODO (verify on hardware)`.

- `[source-observed]` — established only by code or by the shape of a tree: a driver's behavior,
  a module file name, a kernel version string, a third-party prebuilt tree's file listing. Always
  with `TODO (verify on hardware)`. It is one of the investigator's tags, alongside `[databook]`,
  `[standard]`, `[DT]` and `[inference]`.
- "The driver programs this register before releasing reset" is `[source-observed]`; "the hardware
  requires this ordering" is `[inference]`.
- A `resources.series` entry is a map (`[DT]`, `[source-observed]`), never an authority.
- A `variants:` row known only from the shape of a prebuilt tree says so with
  `tag: source-observed` and names the source in `source`.
- An IP spec resolved through a board (anchored mode): a fact present only in the board's tree is
  tagged `[source-observed]` with the tree named, because it may be a vendor addition rather than
  the IP's behavior.
- In an IP spec's *Programming model*, orderings taken only from a driver are `[source-observed]`
  and say "order not known to be required".
- When writing a spec, `[source-observed]` carries the TODO, as `[press]`, `[inference]` and
  `[emulated]` do.

## Encumbered designs and device models

*(From `SPEC-FORMAT.md`, the `[rtl]` and `[emulated]` classes.)*

- `[rtl]`: when the design is not public, it is encumbered source like any other: the facts cross
  the wall, the text does not.
- `[emulated]`: phrased as what was observed from outside the model, never as the model's
  mechanism: the model's source is encumbered like any other, and the tag must not become a
  channel for it.

## Clean-room rules for spec content

*(From `SPEC-FORMAT.md`, the section of this name.)*

These are `cleanroom-investigator`'s caching rule applied to a file that may sit in the target tree:

- Only facts that are datasheet-, standard-, documentation-, or DT-cited, verifier-PASSed, or
  measured on hardware belong in a spec. `[source-observed]` and `[press]` are allowed only with
  `TODO (verify on hardware)`; so is `[emulated]`, and only beside another class or as an
  `[inference]` premise, phrased as an observation from outside the model (the model's source is
  encumbered, and its function and variable names stay on the other side of the wall).
- **Device-tree content is hardware description, not source.** Node names, labels, `compatible`
  strings, property names, and values (addresses, interrupt tuples, clock names, pin groups) are
  hardware facts, tagged `[DT]`, and may be read from a device tree and written into a spec by the
  spec's author directly. Driver and firmware *code* is different: only the research subagent reads
  it, and it returns facts and mechanism prose, never excerpts.
- **What an author may do to a driver file** before the research subagent exists, to decide which
  files matter: list a directory, check that a path exists at a ref, and grep a file for a
  `compatible` string, a symbol name, or a register name. The author may not read a driver's body,
  and a grep hit is a pointer, not a fact.
- No source excerpts, no source-invented identifiers (function, struct, and variable names from
  driver code), no reconstructed file organization.
- An overlay in a vendor layer may cite NDA documents. Facts from it reach the report tagged with
  their layer, so the clean-room verifier can see that a citation is not publicly checkable. They are
  never copied into a public-layer spec.
- A public-layer root contains no `access: internal` entry, no `via:` naming a private skill, and no
  private hostname. The public-skills repository's privacy rules apply to every public root.

## Writing a board spec behind the wall

*(From `board-spec-scaffold`: its conventions and its research-fill step.)* Run the scaffold as
written, with these added to its counterparts and winning where they differ:

- **Clean-room first.** Every fact carries a provenance tag, at the end of its bullet; anything
  unverified is `TODO (verify on hardware)`; no source excerpts, ever. A spec may end up in the
  target OS tree, so it must already be safe there. Device trees are hardware description, not
  source: you may read them and copy node names, compatibles, and values into a spec as `[DT]`
  facts. Driver and firmware code is source: only the research-fill subagent reads it. To decide
  which files matter before that subagent exists, you may list a directory, check that a path
  exists at a ref, and grep a driver file for a `compatible` string, a symbol, or a register name;
  you may not read a driver's body, and a grep hit is a pointer, not a fact.
- **Research-fill.** Spawn a subagent with the harness's delegation tool, have it load
  `cleanroom-investigator` plus `board-expert` (so a sibling SoC or IP spec is available to it), and
  ask it to return the addressing model / boot hand-off / GIC / UART / timer / clock facts as a
  clean-room report, each fact tagged, plus ready-to-paste `instances:` rows in the format's shape.
  It may clone into `~/src/<cache>/` as `cleanroom-investigator` directs. Driver and firmware code
  is read only by that subagent; you may read device trees yourself.

## Stubs and vendor skills behind the wall

*(From the scaffold's `stub-SKILL.md` and `vendor-board-tools-SKILL.md` templates.)*

- A `<board>-expert` stub used behind the wall says, in its description, "board-expert does the
  work, cleanroom-investigator supplies the method and the clean-room no-source-code rule", and in
  its body: spawn a subagent, have it load `board-expert` and `cleanroom-investigator`, and give it
  `spec: <id>` along with the question. The subagent clones and reads reference source in its own
  cache; you receive clean-room facts back, never source.
- A `<vendor>-board-tools` skill is loaded alongside `board-expert` and `cleanroom-investigator` in
  the expert subagent, never in the main agent.
