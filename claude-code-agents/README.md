<!--
SPDX-FileCopyrightText: 2026 contributors
SPDX-License-Identifier: Apache-2.0
portability-scan: intentional - Claude Code install notes for Claude Code assets.
-->

# Claude Code agent definitions for the clean-room roles

**Terms.** An *agent definition* is a Markdown file with YAML frontmatter that Claude Code loads as
a named subagent. Its frontmatter can restrict the subagent's tools and attach hooks that run only
while it runs. A *hook* is a command the harness runs before each tool call that can block the call.
The *wall*, the *dirty side* and *encumbered source* are in the [glossary](../GLOSSARY.md).

Five thin wrappers. The investigator's agent is named `cleanroom-source-investigator`, not after
its skill: the implementer's hook denies any recursive search of a directory that holds a file
named `cleanroom-investigator`, and `.claude/agents/` is inside the project. Each one preloads its skill, takes its per-run inputs from the launch prompt,
and stops when an input is missing. The role text stays in the skills, so Codex and Antigravity
keep working from the skills alone.

| Agent | Role | Skill it wraps |
| --- | --- | --- |
| `cleanroom-implementer` | writes driver code from a landed spec | `cleanroom-implementer` |
| `cleanroom-fix-implementer` | fixes listed review findings, starting fresh from the previous round's handoff | `cleanroom-implementer` (its "Fix rounds" section) |
| `cleanroom-source-investigator` | reads source, returns facts or writes a spec draft | `cleanroom-investigator` (`cleanroom-spec`'s template for a spec run) |
| `cleanroom-transfer-reviewer` | the five-check review before a spec lands | `cleanroom-spec/templates/verifier-prompt.md` |
| `cleanroom-technical-reader` | the accuracy pass (numbers, sequencing, or both on a recheck) | `cleanroom-verifier`, with driver-lab's `spec-verifier` |

## Install (per project)

Copy all five into the project; a plugin cannot ship them. Claude Code ignores `hooks:` in an agent
loaded from a plugin, so the implementer would load there with no hook. That is why this directory
is not named `agents/`, which a plugin loads automatically. Run from the project root, with
`<cleanroom-skills>` replaced by your checkout or plugin directory:

```bash
mkdir -p .claude/agents .claude/hooks
cp <cleanroom-skills>/claude-code-agents/cleanroom-*.md .claude/agents/
cp <cleanroom-skills>/skills/cleanroom-implementer/scripts/cleanroom_hook.py .claude/hooks/
cp <cleanroom-skills>/skills/cleanroom-implementer/assets/cleanroom-policy.json .claude/
```

Then:

1. Edit `.claude/cleanroom-policy.json`: `checkout_roots` must list **every** local copy of
   encumbered source on the machine, the reference driver checkout and any extracted tarball
   included.
2. Check the `skills:` names against what `/skills` lists. A skill installed from a plugin may be
   listed with a plugin prefix (`cleanroom-skills:cleanroom-implementer`); use that name. Each
   agent stops with "skill not loaded" when its preload failed. Install the dirty-side skills
   (`cleanroom-investigator`, `board-expert`) at user level or through the plugin, **never under
   the project's `.claude/skills/`**: a directory there named after one makes the implementer's
   hook deny every recursive search from the project root, the same trap as an agent file of that
   name.
3. Do **not** also install `cleanroom_hook.py` as a session-wide hook in `settings.json`. The
   investigator and verifiers run in the same session and process, so a session-wide hook would
   block them and `CLEANROOM_ROLE` cannot tell them apart. The implementer's frontmatter hook is
   the one that matters.
4. **Provoke it.** In an interactive session, launch `cleanroom-implementer` with a brief that asks
   it to read one file under a `checkout_roots` entry. The read must be denied, and a `blocked`
   line must appear in `docs/provenance/hook-blocks.jsonl`. Then do the same with
   `cleanroom-fix-implementer`: it carries its own copy of the hook in its own frontmatter, so one
   agent's block line says nothing about the other's. Do this after every install and every
   Claude Code upgrade. Without those lines, the hook is not running.

## Launch

Name the agent in the delegation tool call (`subagent_type: cleanroom-implementer`), or with an
@-mention: `@"cleanroom-implementer (agent)"`. The launch prompt carries every per-run input:

- **implementer**: the landed spec path and its sha256, the target tree, the work. Write the brief
  from the landed spec and your own plan, never from dirty-side output.
- **fix implementer**: the landed spec path and its sha256, the previous round's handoff
  (`docs/handoffs/<device>-round-<N>.md`) and its sha256, the findings to fix (a review-swarm
  `final.json` or `verified.json`, or a plain numbered list), and the base commit the previous
  round produced. Never the predecessor's transcript.
- **source investigator**: for a spec, the filled `cleanroom-spec/templates/spec-subagent-prompt.md`; for
  a question, the question, board and IP, pins, and where the source is.
- **transfer reviewer**: the filled `cleanroom-spec/templates/verifier-prompt.md` (candidate path
  and sha256, version and round, pins, sidecar map, whitelist).
- **technical reader**: candidate path and sha256, version, round (with the prior record on a
  recheck), scope (`numbers`, `sequencing`, or `combined` for a recheck), pins, sidecar map, cited
  references, and a record path unique to that round and scope. A first review launches two, one
  per scope.

### Fix rounds: fresh agent or resume?

Every implementer run ends by writing a short handoff (`docs/handoffs/<device>-round-<N>.md`,
from `cleanroom-implementer`'s `assets/handoff-template.md`). When review findings come back:

- If the implementer that wrote the code has passed about **200k tokens of context**, launch a
  fresh `cleanroom-fix-implementer` from its handoff. Do not resume it.
- A small follow-up (a question about its work, a one-line fix) may still resume it.

Why: in a bring-up project, one implementer resumed for four review-fix rounds grew past 600k
tokens and re-read its whole context on every tool call, using 15% of the night's subagent tokens
on its own. Use the harness's own count of the agent's context where it gives one.

## What these definitions enforce, and what they cannot

Checked against Claude Code v2.1.300 on 2026-10-14.

Enforced:

- **No web tools, no MCP tools, no delegation tool and no Skill tool in the implementer.** A probe
  agent with `tools: Read, Grep, Glob, Bash` and the implementer's `disallowedTools` line reported
  only `Read` and `Bash` (this build has no `Grep` or `Glob` tools). It could not load `WebFetch`
  or `WebSearch`. The implementer adds `Edit` and `Write` to that list.
- **The `skills:` preload**: a subagent with the Skill tool removed still received its skill text.

Expected from Claude Code's documentation, not observed here:

- **The cleanroom hook on every implementer tool call**, while the implementer runs, in an
  interactive session, once the folder's workspace trust is accepted. Step 4 above is how you
  observe it. The hook command pins the project directory, so a working directory inside a
  nested git checkout still finds `.claude/cleanroom-policy.json`.

Not enforced:

- **A read allowlist.** Claude Code has no per-agent path rules (path rules live in settings and
  apply to the whole session), and the hook is a denylist: `checkout_roots`, path and URL
  patterns, and the dirty-side names. Any file not on those lists is readable, including a copy of
  the reference source somewhere unlisted. "Only the target tree, the landed specs and the brief"
  is an instruction here, not a wall.
- **The shell.** The implementer keeps `Bash` to build and test. The hook checks command lines by
  pattern, which catches `git clone`, `curl` to listed hosts and reads of listed paths. It cannot
  catch a fetch from an unlisted host, a path built at run time, or a script that does the read.
- **`claude -p` sessions.** Frontmatter hooks did not fire there in either launch form tried
  (`--agent`, and the agent launched as a subagent), inside a trusted folder. The tool
  restrictions still applied.
- **The wall's own files.** The implementer can `Write` `.claude/cleanroom-policy.json`,
  `.claude/hooks/cleanroom_hook.py` or its own agent file, and the hook does not guard them. The
  hook's built-in names survive a rewritten policy; nothing survives a rewritten hook. Review
  `git status` for those paths after every implementer run.
- **A missing `python3`.** The hook command then exits 127, a non-blocking error, and every call
  goes through. A missing hook *file* fails closed (exit 2).
- **The parent context.** A subagent shares its parent's process, environment and credentials. It
  starts with only its launch prompt, so a brief that carries dirty-side text carries it in.

For a real wall on a machine that holds the reference source, run the implementer as its own
process (`claude --agent cleanroom-implementer`) under `cleanroom-implementer`'s
`cleanroom_sandbox.sh`, and audit its strace log. Tool restrictions apply in that form; the hook
does not, and the sandbox takes its place. The sandbox recipe has been piloted with Codex, not yet
with Claude Code.
