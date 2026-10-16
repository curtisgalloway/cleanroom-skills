#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 contributors
# SPDX-License-Identifier: Apache-2.0
"""
Tests for the fix-round role: the handoff template and the fix implementer agent.

Run:  python3 -m unittest discover -s skills/cleanroom-implementer/tests -v

test_frontmatter_matches_the_implementer is the one that matters most. The
fix implementer writes driver code exactly as the implementer does, so it
must carry the same wall: the same tool list, the same disallowed tools, the
same skill preload and the same cleanroom hook. If someone loosens one file
and not the other, a fix round would run with a weaker wall than the round
before it, and this test goes red.

The rest pin what lets a fix round start fresh: a handoff template with every
section the next round needs and within its line budget, an agent brief that
names its four pinned inputs and forbids the predecessor's transcript, and
the skill text that tells every implementer to write the handoff.
"""

import pathlib
import re
import unittest

HERE = pathlib.Path(__file__).resolve().parent
SKILL_DIR = HERE.parent
REPO = SKILL_DIR.parent.parent
TEMPLATE = SKILL_DIR / "assets" / "handoff-template.md"
SKILL = SKILL_DIR / "SKILL.md"
AGENTS = REPO / "claude-code-agents"
IMPLEMENTER = AGENTS / "cleanroom-implementer.md"
FIXER = AGENTS / "cleanroom-fix-implementer.md"

# The sections a fix round reads, in the order the template gives them.
REQUIRED_SECTIONS = [
    "Branch and commits",
    "Spec",
    "Files changed",
    "Build and test",
    "Test harnesses",
    "Findings addressed",
    "Open questions",
    "Gotchas",
    "Do not redo",
]
HANDOFF_BUDGET_LINES = 150


def frontmatter(path):
    """Return the YAML frontmatter lines of an agent file, without the fences."""
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "---", f"{path} does not start with frontmatter"
    end = lines.index("---", 1)
    return lines[1:end]


def without_identity(lines):
    """Drop `name:` and `description:` (with its folded continuation lines)."""
    out, skipping = [], False
    for line in lines:
        if re.match(r"(name|description):", line):
            skipping = line.startswith("description:")
            continue
        if skipping and line.startswith("  "):
            continue
        skipping = False
        out.append(line)
    return out


class TestHandoffTemplate(unittest.TestCase):

    def setUp(self):
        self.text = TEMPLATE.read_text(encoding="utf-8")

    def test_has_every_required_section_in_order(self):
        headings = re.findall(r"^## (.+)$", self.text, flags=re.MULTILINE)
        self.assertEqual(headings, REQUIRED_SECTIONS)

    def test_fits_its_own_budget(self):
        """An empty template must leave most of the 150 lines for content."""
        self.assertLess(len(self.text.splitlines()), HANDOFF_BUDGET_LINES // 2)

    def test_asks_for_hashes_and_counts(self):
        self.assertIn("sha256", self.text)
        self.assertRegex(self.text, r"passed.*failed")
        self.assertIn("Base commit", self.text)

    def test_keeps_blocked_paths_out(self):
        """A handoff naming a blocked path would be an attractant on the clean side."""
        self.assertIn("never the blocked path", self.text)

    def test_spdx_header(self):
        self.assertIn("SPDX-License-Identifier: Apache-2.0", self.text)


class TestFixImplementerAgent(unittest.TestCase):

    def test_frontmatter_matches_the_implementer(self):
        self.assertEqual(without_identity(frontmatter(FIXER)),
                         without_identity(frontmatter(IMPLEMENTER)))

    def test_identity(self):
        fm = "\n".join(frontmatter(FIXER))
        self.assertIn("name: cleanroom-fix-implementer", fm)
        self.assertIn("200k tokens", fm)

    def test_wall_lines_present(self):
        """Guard the comparison above against both files losing a line together."""
        fm = frontmatter(FIXER)
        self.assertIn("tools: Read, Grep, Glob, Edit, Write, Bash", fm)
        self.assertIn("disallowedTools: WebFetch, WebSearch, Agent, Skill, mcp__*", fm)
        self.assertIn("  - cleanroom-implementer", fm)
        self.assertTrue(any("cleanroom_hook.py" in line and "env -u CLEANROOM_ROLE" in line
                            for line in fm))

    def test_brief_names_four_pinned_inputs(self):
        body = FIXER.read_text(encoding="utf-8")
        for needle in ("spec", "handoff", "sha256", "final.json", "verified.json",
                       "base commit"):
            self.assertIn(needle, body)
        self.assertRegex(body, r"spec's sha256 and\s+the handoff's sha256")

    def test_never_reads_the_predecessor_transcript(self):
        body = FIXER.read_text(encoding="utf-8")
        self.assertRegex(body, r"Never ask for, search for or read the\s+previous "
                               r"implementer's transcript")

    def test_writes_the_next_handoff(self):
        body = FIXER.read_text(encoding="utf-8")
        self.assertIn("round-<N+1>.md", body)
        self.assertIn("test-first", body)


class TestSkillText(unittest.TestCase):

    def setUp(self):
        self.text = SKILL.read_text(encoding="utf-8")

    def test_every_run_writes_a_handoff(self):
        self.assertIn("## Closing a run: the handoff", self.text)
        self.assertIn("assets/handoff-template.md", self.text)
        self.assertIn("docs/handoffs/<device>-round-<N>.md", self.text)

    def test_threshold_rule_for_orchestrators(self):
        self.assertIn("## Fix rounds", self.text)
        self.assertIn("200k tokens of context", self.text)
        self.assertIn("never resume it", self.text)

    def test_threshold_rule_has_a_fallback_without_a_count(self):
        # Some harnesses report no context size; the rule must still decide.
        self.assertIn("reports no context size", self.text)
        readme = (AGENTS / "README.md").read_text(encoding="utf-8")
        self.assertIn("reports no context size", readme)

    def test_implementer_agent_writes_the_handoff(self):
        self.assertIn("handoff-template.md", IMPLEMENTER.read_text(encoding="utf-8"))

    def test_agents_readme_lists_the_fix_implementer(self):
        readme = (AGENTS / "README.md").read_text(encoding="utf-8")
        self.assertIn("| `cleanroom-fix-implementer` |", readme)


if __name__ == "__main__":
    unittest.main()
