<!--
SPDX-FileCopyrightText: 2026 contributors
SPDX-License-Identifier: Apache-2.0

Handoff template for a clean-room implementer run (cleanroom-implementer, "Closing a run: the
handoff"). Copy to docs/handoffs/<device>-round-<N>.md, fill every section, delete these
comments. Budget: about 150 lines. Write facts the next round needs, not a narrative of this
one. Clean side only: no source paths, no blocked paths, no text from any dirty-side output.
-->

# Handoff: <device>, round <N>

Written <date> by <agent and model> at the end of round <N> (`initial` or `fix`).

## Branch and commits

- Branch: `<branch>` in `<target tree>`
- Base commit this round started from: `<sha>`
- Commits this round, oldest first: `<sha> <subject>`, ...
- Head the next round starts from: `<sha>`

## Spec

- Landed spec: `docs/<device>-spec.md`, sha256 `<hash>`
- Spec gaps filed this round: `docs/spec-gaps/<device>.md` lines <n>, ... (or "none")

## Files changed

One line each: path, and what it now does. Every file in `git diff --stat <base>..<head>`.

- `<path>`: <one line>

## Build and test

Exact commands, run from `<directory>`, with the counts they gave at the head above.

- Build: `<command>` (clean: <yes/no>, warnings: <n>)
- Tests: `<command>`: <passed> passed, <failed> failed, <skipped> skipped
- Other checks run (lint, format, leak scan): `<command>`: <result>

## Test harnesses

Where the tests for this driver live and how they reach the device: fakes, mock registers,
fixtures, hardware-in-the-loop entry points.

- `<path>`: <what it covers>

## Findings addressed

Fix rounds only. One line per finding id from the findings file: fixed (commit, test that pins
it), or not fixed and why. Initial round: "none".

- `<id>`: <fixed in `<sha>`, test `<name>`> | <not fixed: reason>

## Open questions

Questions for the orchestrator that are not spec gaps (a spec gap goes in the gap file).

- <question> (or "none")

## Gotchas

What cost time this round and will cost it again: a hook block (say what kind of call and the
gap it led to; never the blocked path), a toolchain or build-system quirk, a flaky test, a
command that needs a path argument in a big tree.

- <gotcha>: <the workaround>

## Do not redo

Work the next round must not repeat: approaches tried and rejected (with the reason), analysis
already settled, files already verified correct.

- <item>: <why it is settled>
