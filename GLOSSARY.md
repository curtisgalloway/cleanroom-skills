<!--
SPDX-FileCopyrightText: 2026 contributors
SPDX-License-Identifier: Apache-2.0
-->

# Glossary

Terms used in this repository. Rows marked *(driver-lab)* are shared with driver-lab's glossary.

| Term | Meaning |
| --- | --- |
| Agent | An AI assistant with tools: here, an investigator, a spec writer, a verifier or an implementer. |
| Subagent | An agent started by another agent for one task, with its own fresh context; the starting agent sees only what it returns. |
| Skill | Instructions and optional scripts that guide an agent through a task (a `SKILL.md` and supporting files). |
| Plugin / marketplace | A bundle of skills / the listing a coding agent installs plugins from. |
| Hook | A script the coding agent's harness runs before or after a tool call; `cleanroom-implementer`'s hook blocks reads of encumbered source. |
| Specification (spec) | A document describing hardware precisely enough to write a driver from. *(driver-lab)* |
| Driver | Software through which an operating system controls a device. *(driver-lab)* |
| Encumbered source | Source whose license you may not copy from into the target OS, such as a GPL driver for a differently licensed kernel. |
| Clean-room boundary (the wall) | Separation of source-reading and implementation contexts, controlling which evidence crosses. *(driver-lab)* |
| Dirty side / clean side | The agents allowed to read encumbered source (investigator, verifier) / the agents that write code and must never read it (implementer). |
| Board expert | A driver-lab skill (`board-expert`) that supplies per-board facts: memory map, interrupts, clocks, which source trees to read. |
| Provenance tag | The label on each fact saying where it came from: `[databook]`, `[standard]`, `[DT]` (device tree), `[source-observed]`, `[inference]`. |
| Leak scan | `leak_scan.py`: a mechanical check that a spec or driver shares no long token runs or code identifiers with the source behind the wall. |
| Transfer review | The clean-room gate a spec passes before anyone else may read it: a mechanical leak scan plus checks for copied code, structure, attractants, and the usage notice. It does not judge accuracy. *(driver-lab)* |
| Attractant | Anything in a clean-room spec that would pull a reader back to the encumbered source, such as a source file path or "the driver does X in function Y" narration. *(driver-lab)* |
| Provenance ledger | A record of where facts came from and what crossed the clean-room boundary. *(driver-lab)* |
| Provenance attestation | `PROVENANCE.md`, filled by `cleanroom-spec` for each landed spec: who ran the method, the sources behind the wall, which agent saw what, pins, verifier reports and the spec's hash. The user's private record, never published; distinct from the provenance ledger, which it cites. *(driver-lab)* |
| Pin | An exact revision of a source tree or document that a spec's facts were read from (`<repo>@<commit>`). |
| Spec gap / spec error | A question a spec leaves unanswered, filed by an implementer / a place where the spec is wrong. *(driver-lab)* |
| Bubblewrap (`bwrap`) | A Linux tool that runs a program in a private view of the file system, showing it only the directories it is given; the clean-room sandbox (`cleanroom_sandbox.sh`) is built on it. *(driver-lab)* |
| Portability scan | `portability_scan.py` from public-skills: checks that agent-facing scripts make no assumption a different coding agent would break. |
| SPDX | The standard short identifiers for licenses (`GPL-2.0-only`, `MIT`, `Apache-2.0`), used in file headers and license fields. *(driver-lab)* |
