<!--
SPDX-FileCopyrightText: 2026 Curtis Galloway
SPDX-License-Identifier: Apache-2.0
The normative clean-room usage notice (cleanroom-spec, "Required structure", item 1).
Copy everything between the begin and end markers, markers included, to the top of the spec,
below its title and above its first "##" section. Replace <device> and change nothing else.
Do not add a version or a hash: the hash-match clause points at the ledger, so the notice never
goes stale. skills/cleanroom-investigator/scripts/notice_check.py checks this text mechanically.
-->

<!-- cleanroom-usage-notice:begin -->
**Clean-room usage notice.** This <device> spec was produced from encumbered source by a designated clean-room reader and independently verified. Everyone who uses it, human or agent, follows the rules below.

**Do not read the source.** Do not read the original source-OS or firmware code yourself, for any reason.

**Only inputs.** This spec plus its cited public references are the only implementation inputs.

**Gaps.** On any gap, file a spec-gap: append the question to `docs/spec-gaps/<device>.md`, mark the code site `TODO(spec-gap)`, and continue with other work. Never open the source: the urge to "check the driver" is itself a spec-gap.

**Source-observed facts.** Facts tagged `[source-observed]` are never verified against the source. Verify them on hardware or file a spec-gap.

**Provenance directory.** Do not open `docs/provenance/`. It exists for verifiers and counsel, not implementers.

**Pre-merge gate.** Code written from this spec must pass the pre-merge gate, the output scan plus clean session audits (see the ledger), before it lands.

**Hash match.** If the content hash of this spec no longer matches its latest ledger PASS line, treat the spec as unverified: it has been edited since verification.
<!-- cleanroom-usage-notice:end -->
