<!--
SPDX-FileCopyrightText: 2026 Curtis Galloway
SPDX-License-Identifier: Apache-2.0
Fill-in prompt for the independent verifier subagent; substitute every <angle-bracket> placeholder.
-->

Independently verify the clean-room spec at <path-to-spec> (sha256 <candidate-sha256>, version
v<N>; round: <first review | recheck of v<M>, prior record <prior-record-path>>). You did not write
it; do not fix it. First confirm the file's sha256 matches; if it does not, stop and return
"MISMATCH" with the hash you computed.
Load `cleanroom-investigator` — it is the canonical statement of allowed/forbidden and ships the scanner.
Obtain the source at the exact pinned commit (<repo>@<commit>) using the file map in the sidecar
docs/provenance/<device>-map.txt; verifying against any other revision is verifying against the
wrong text. You are a designated clean-room reader; run with CLEANROOM_ROLE=verifier if hooks are
installed.

1. MECHANICAL: run
     python3 <cleanroom-investigator>/scripts/leak_scan.py <path-to-spec> \
         --against <files from the sidecar map> \
         [--vendor-region <file>:<start>-<end> for each vendor-table line in the map] \
         [--whitelist <nomenclature file> --require-citations]
   Save the full report to docs/provenance/<device>-scan-<date>.txt. Review every finding. An
   identifier hit, whatever its case, that is the name a cited public reference (databook,
   standard, datasheet) uses goes into the whitelist file as `<identifier>  # <reference>,
   <section or table>`; check each new entry's citation yourself against that reference. A name
   found only in source-OS code fails whatever its case, and so does any entry without a citation
   (--require-citations makes the scanner report those). Record which entries you added, with
   their citations.
2. LEAK JUDGMENT: confirm the spec contains NO source code from <repo(s)>: no verbatim or
   near-verbatim code in any language, no struct/enum/#define/macro/function bodies or initializer
   tables, no copied code comments, no prose that tracks a function statement-by-statement, and no
   quoted phrase that follows the source's wording: outside the usage notice, every phrase in
   quotation marks must be a cited standard, databook or binding name (no scanner catches short
   quotes). You may
   open the sidecar-map files at the pinned commit to compare. NEVER quote source code or the
   offending spec text — cite spec section + line range only.
3. STRUCTURE: registers are grouped per the databook's organization and sections follow hardware
   function — the spec does not mirror the source driver's file/function decomposition. Constants
   and sequence steps carry provenance tags; [source-observed] orderings/constants carry their
   required caveats ("order not known to be required" / "re-derive on hardware").
4. ATTRACTANTS: the spec body contains NO source-tree file paths and no "<source OS> does X in
   file Y" narration — facts read as hardware facts; the sidecar map exists at
   docs/provenance/<device>-map.txt and the spec's attestation carries only <repo>@<commit>.
5. NOTICE: first run
     python3 <cleanroom-investigator>/scripts/notice_check.py <path-to-spec>
   and record its output; any finding is a FAIL. It checks mechanically that the notice from
   <cleanroom-spec>/templates/usage-notice.md sits between its markers above the first "##"
   section, carries all seven clauses with nothing left unfilled and no version or hash, and that
   the spec names a filled <repo>@<commit> pin. Then judge what a script cannot: that the notice
   is the template's text, not a reworded or weakened copy, and that it still instructs consumers
   (human or agent) NOT to read the original source, names the spec + its cited public references
   as the only implementation inputs, routes gaps through the spec-gap protocol (docs/spec-gaps/),
   forbids verifying [source-observed] facts against the source and opening docs/provenance/, and
   contains the pre-merge-gate and hash-match clauses. A notice the script passes can still fail.

Write the review record to docs/provenance/<device>-transfer-review-v<N>-round<K>.md, where K
counts this candidate's reviews from 1, a new file for this round: never append to an earlier round's record. Use exactly this shape, and quote neither source
nor spec text in it:

    # Transfer review: <device> v<N>, round <K>
    - Candidate: <path-to-spec>  sha256:<full hash>
    - Round: first review | recheck of v<M> (prior record: <path>)
    - Pins: <repo>@<commit>
    - Scan report: <scan-report path>
    - Notice check: clean | <findings>
    - Verdict: PASS | FAIL
    ## Findings
    | # | Check (1-5) | Section | Lines | Reason (one line) |
    ## Prior findings
    | Prior # | resolved / still open | Note |

"Findings" says "None." on a PASS. "Prior findings" appears on a recheck only, with one row per
finding in the prior record. A recheck still runs all five checks on the whole candidate.

Return exactly: "MISMATCH + <computed sha256>" (and write no record), "PASS + <record path>",
or "FAIL + <record path>" + a list of {section, line range, one-line reason} + whether the usage
notice is missing or deficient.
