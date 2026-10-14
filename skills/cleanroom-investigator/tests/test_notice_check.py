#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Curtis Galloway
# SPDX-License-Identifier: Apache-2.0
"""
Tests for scripts/notice_check.py.

Run:  python3 -m unittest discover -s skills/cleanroom-investigator/tests -v
  or: python3 skills/cleanroom-investigator/tests/test_notice_check.py

The notice under test is built from the shipped template, cleanroom-spec's
templates/usage-notice.md, by substituting <device>. The template and the
script therefore cannot drift: edit one without the other and test_filled_
template_passes fails. The device is invented; no spec content is real.
"""

import pathlib
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
CHECKER = HERE.parent / "scripts" / "notice_check.py"
TEMPLATE = (HERE.parent.parent / "cleanroom-spec" / "templates"
            / "usage-notice.md")

PIN = "widgetron-os@0123abcd"


def filled_notice(device="widgetron"):
    """The template's notice block, markers included, for one device."""
    text = TEMPLATE.read_text(encoding="utf-8")
    start = text.index("<!-- cleanroom-usage-notice:begin -->")
    end_marker = "<!-- cleanroom-usage-notice:end -->"
    end = text.index(end_marker) + len(end_marker)
    return text[start:end].replace("<device>", device)


def make_spec(notice=None, pin=PIN, before_notice=""):
    """A minimal invented spec: title, notice, one section, attestation."""
    if notice is None:
        notice = filled_notice()
    return (f"# Widgetron spec\n\n{before_notice}{notice}\n\n"
            f"## Registers\n\nA table goes here.\n\n"
            f"## Clean-room attestation\n\nPinned provenance: {pin}\n")


class TestNoticeCheck(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def run_check(self, text, name="spec.md"):
        path = pathlib.Path(self._tmp.name) / name
        path.write_text(text, encoding="utf-8")
        proc = subprocess.run([sys.executable, str(CHECKER), str(path)],
                              capture_output=True, text=True)
        return proc.returncode, proc.stdout + proc.stderr

    def assert_finding(self, text, message):
        rc, out = self.run_check(text)
        self.assertEqual(rc, 1, out)
        self.assertIn(message, out)
        return out

    def test_filled_template_passes(self):
        rc, out = self.run_check(make_spec())
        self.assertEqual(rc, 0, out)
        self.assertIn("verdict: clean", out)

    def test_template_is_not_itself_a_clean_spec(self):
        """The unfilled template keeps its <device> placeholder."""
        text = TEMPLATE.read_text(encoding="utf-8")
        self.assert_finding(make_spec(notice=text[text.index(
            "<!-- cleanroom-usage-notice:begin -->"):]),
            "unfilled placeholder <device>")

    def test_each_missing_label_fails_with_its_own_message(self):
        notice = filled_notice()
        lines = notice.split("\n")
        labels = ("**Do not read the source.**", "**Only inputs.**",
                  "**Gaps.**", "**Source-observed facts.**",
                  "**Provenance directory.**", "**Pre-merge gate.**",
                  "**Hash match.**")
        for label in labels:
            with self.subTest(label=label):
                kept = [l for l in lines if not l.startswith(label)]
                self.assertEqual(len(kept), len(lines) - 1)
                text = make_spec(notice="\n".join(kept))
                _, out = self.run_check(text)
                self.assertIn(f"missing clause {label}", out)
                others = [l for l in labels if l != label]
                for other in others:
                    self.assertNotIn(f"missing clause {other}", out)

    def test_clause_hidden_in_a_comment_does_not_count(self):
        notice = filled_notice()
        hidden = "\n".join(
            "<!-- " + l + " -->" if l.startswith("**Hash match.**") else l
            for l in notice.split("\n"))
        self.assertNotEqual(hidden, notice)
        self.assert_finding(make_spec(notice=hidden),
                            "missing clause **Hash match.**")

    def test_repeated_and_reversed_markers(self):
        notice = filled_notice()
        self.assert_finding(make_spec(notice=notice + "\n" + notice),
                            "marker appears more than once")
        begin = "<!-- cleanroom-usage-notice:begin -->"
        end = "<!-- cleanroom-usage-notice:end -->"
        swapped = notice.replace(begin, "@@").replace(end, begin).replace(
            "@@", end)
        self.assert_finding(make_spec(notice=swapped),
                            "end marker comes before the begin marker")

    def test_quoted_spec_gap_path_is_accepted(self):
        notice = filled_notice().replace(
            "`docs/spec-gaps/widgetron.md`", '"docs/spec-gaps/widgetron.md"')
        rc, out = self.run_check(make_spec(notice=notice))
        self.assertEqual(rc, 0, out)

    def test_missing_markers(self):
        notice = filled_notice()
        begin = "<!-- cleanroom-usage-notice:begin -->"
        end = "<!-- cleanroom-usage-notice:end -->"
        self.assert_finding(make_spec(notice=notice.replace(begin, "")),
                            "missing begin marker")
        self.assert_finding(make_spec(notice=notice.replace(end, "")),
                            "missing end marker")

    def test_leftover_placeholder(self):
        text = make_spec(notice=filled_notice().replace(
            "**Pre-merge gate.**", "**Pre-merge gate.** <ledger path>"))
        self.assert_finding(text, "unfilled placeholder <ledger path>")

    def test_comment_and_autolink_are_not_placeholders(self):
        notice = filled_notice().replace(
            "**Only inputs.**",
            "**Only inputs.** <!-- <editor note> --> See <https://example.org/x>.")
        rc, out = self.run_check(make_spec(notice=notice))
        self.assertEqual(rc, 0, out)

    def test_malformed_spec_gap_path(self):
        for bad in ("docs/spec-gaps/wid getron.md", "docs/spec-gaps/widgetron.txt",
                    "docs/spec-gaps/dir/widgetron.md",
                    "docs/spec-gaps/widget$ron.md"):
            with self.subTest(path=bad):
                notice = filled_notice().replace(
                    "docs/spec-gaps/widgetron.md", bad)
                _, out = self.run_check(make_spec(notice=notice))
                self.assertIn("malformed spec-gap path", out)

    def test_missing_spec_gap_path(self):
        notice = filled_notice().replace("docs/spec-gaps/widgetron.md",
                                         "the gap file")
        self.assert_finding(make_spec(notice=notice), "no spec-gap path")

    def test_version_token(self):
        notice = filled_notice().replace("**Only inputs.**",
                                         "**Only inputs.** (spec v4)")
        self.assert_finding(make_spec(notice=notice), "version token 'v4'")

    def test_hash(self):
        digest = "ab" * 32
        for text in (digest, digest[:40]):
            with self.subTest(length=len(text)):
                notice = filled_notice().replace(
                    "**Hash match.**", f"**Hash match.** ({text})")
                self.assert_finding(make_spec(notice=notice),
                                    "hash in the notice")

    def test_notice_after_a_section_fails(self):
        text = ("# Widgetron spec\n\n## Overview\n\nIntro.\n\n"
                f"{filled_notice()}\n\nPinned provenance: {PIN}\n")
        self.assert_finding(text, "a ## heading comes before the notice")

    def test_missing_pin(self):
        self.assert_finding(make_spec(pin="none yet"), "no filled")

    def test_unfilled_pin(self):
        self.assert_finding(make_spec(pin="widgetron-os@<commit>"),
                            "attestation pin <repo>@<commit> is not filled")

    def test_pin_inside_the_notice_does_not_count(self):
        notice = filled_notice().replace("**Only inputs.**",
                                         f"**Only inputs.** {PIN}")
        self.assert_finding(make_spec(notice=notice, pin="none"), "no filled")

    def test_missing_file_is_usage_error(self):
        proc = subprocess.run(
            [sys.executable, str(CHECKER), str(HERE / "no-such-spec.md")],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertIn("notice_check: error: cannot read", proc.stderr)

    def test_every_spec_is_reported(self):
        good = pathlib.Path(self._tmp.name) / "good.md"
        bad = pathlib.Path(self._tmp.name) / "bad.md"
        good.write_text(make_spec(), encoding="utf-8")
        bad.write_text(make_spec(pin="none"), encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(CHECKER), str(good), str(bad)],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertIn("good.md: notice ok", proc.stdout)
        self.assertIn("bad.md:1: no filled", proc.stdout)


if __name__ == "__main__":
    unittest.main()
