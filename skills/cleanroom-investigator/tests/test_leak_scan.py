#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Curtis Galloway
# SPDX-License-Identifier: Apache-2.0
"""
Tests for scripts/leak_scan.py, run against wholly synthetic fixtures.

Run:  python3 -m unittest discover -s skills/cleanroom-investigator/tests -v
  or: python3 skills/cleanroom-investigator/tests/test_leak_scan.py

The load-bearing case is test_report_never_reproduces_source_text: the
scanner's whole premise is that its report can be filed as evidence and
handed to a verifier without itself becoming a leak. Bare identifier names
are the one sanctioned exception.
"""

import pathlib
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
SCANNER = HERE.parent / "scripts" / "leak_scan.py"
FIX = HERE / "fixtures"
SOURCE = FIX / "fake_source"


def run_scan(*args):
    """Run leak_scan.py and return (returncode, stdout+stderr)."""
    proc = subprocess.run(
        [sys.executable, str(SCANNER)] + [str(a) for a in args],
        capture_output=True, text=True)
    return proc.returncode, proc.stdout + proc.stderr


class TestLeakScan(unittest.TestCase):

    def test_leaky_spec_is_flagged(self):
        """Transcribed source must trip both checks and exit 1."""
        rc, out = run_scan(FIX / "leaky_spec.md", "--against", SOURCE)
        self.assertEqual(rc, 1, out)
        self.assertIn("FINDINGS", out)
        self.assertNotIn("[runs] 0 shared run(s)", out)
        self.assertIn("purple_latch_timeout", out)
        self.assertIn("widgetron_bringup_sequence", out)

    def test_clean_spec_passes(self):
        """Same facts re-expressed as hardware facts must scan clean."""
        rc, out = run_scan(FIX / "clean_spec.md", "--against", SOURCE)
        self.assertEqual(rc, 0, out)
        self.assertIn("verdict: clean", out)

    def test_report_never_reproduces_source_text(self):
        """The report cites locations and digests, never matched text.

        Bare identifiers are deliberately exempt, so these assertions use
        multi-token sequences that can only appear if verbatim text was
        echoed, plus an all-caps token the identifier lint does not print.
        """
        rc, out = run_scan(FIX / "leaky_spec.md", "--against", SOURCE)
        self.assertEqual(rc, 1, out)
        for verbatim in ("widgetron_write(wp,", "& STATUS_RESET_BUSY",
                         "ETIMEDOUT", "unsigned int"):
            self.assertNotIn(verbatim, out,
                             f"scanner reproduced source text: {verbatim!r}")
        self.assertIn("candidate L", out)
        self.assertIn("sha1:", out)

    def test_whitelist_suppresses_databook_nomenclature(self):
        """Whitelisted all-caps names stop being reported."""
        _, before = run_scan(FIX / "leaky_spec.md", "--against", SOURCE)
        self.assertIn("WIDGETRON_CTRL", before)
        _, after = run_scan(FIX / "leaky_spec.md", "--against", SOURCE,
                            "--whitelist", FIX / "nomenclature-whitelist.txt")
        self.assertIn("[idents] 0 ALL-CAPS", after)
        self.assertNotIn("WIDGETRON_CTRL", after)
        self.assertIn("purple_latch_timeout", after,
                      "whitelisting databook names must not mask "
                      "source-invented ones")

    def test_numeric_overlap_alone_does_not_trigger(self):
        """Register tables legitimately share numbers with the source."""
        rc, out = run_scan(FIX / "clean_spec.md", "--against", SOURCE)
        self.assertEqual(rc, 0, out)
        self.assertIn("[runs] 0 shared run(s)", out)

    def test_bad_shingle_size_is_usage_error(self):
        rc, out = run_scan(FIX / "clean_spec.md", "--against", SOURCE,
                           "--k", "20", "--min-run", "10")
        self.assertEqual(rc, 2, out)
        self.assertIn("--k must be <= --min-run", out)

    def test_missing_source_path_is_error(self):
        rc, out = run_scan(FIX / "clean_spec.md", "--against",
                           HERE / "no-such-directory")
        self.assertEqual(rc, 2, out)

    def test_files_skipped_under_a_directory_are_reported(self):
        # A directory is filtered by extension, so a Kconfig or a .yaml
        # binding beside the C files was once left out without a word and
        # its absence read as a clean scan (2026-10, 20 of 25 files read).
        # Naming such a file outright still scans it.
        with tempfile.TemporaryDirectory() as tmp:
            src = pathlib.Path(tmp) / "src"
            src.mkdir()
            (src / "drv.c").write_text("int fake_probe(void) { return 0; }\n")
            (src / "Kconfig").write_text("config FAKE_DEVICE\n")
            (src / "binding.yaml").write_text("compatible: fake,device\n")
            rc, out = run_scan(FIX / "clean_spec.md", "--against", src)
            self.assertEqual(rc, 0, out)
            self.assertIn("1 source file(s)", out)
            self.assertIn("[skipped] 2 file(s)", out)
            self.assertIn("Kconfig", out)
            self.assertIn("binding.yaml", out)
            rc, out = run_scan(FIX / "clean_spec.md", "--against",
                               src / "drv.c", src / "Kconfig")
            self.assertIn("2 source file(s)", out)
            self.assertNotIn("[skipped]", out)


# Invented device: a source file and two candidates, written to a temp dir so
# the shared fixtures above are untouched. SuperSpeed and xHCI stand in for
# public mixed-case standard terms; purple_latch_timeout is source-invented.
WIDGET_SOURCE = """\
/* SYNTHETIC TEST FIXTURE - invented device. */
static int SuperSpeed;
static int xHCI;
static int purple_latch_timeout;
"""
STANDARD_ONLY_SPEC = "The gizmo reports SuperSpeed and xHCI capability bits.\n"
WITH_INVENTED_SPEC = (STANDARD_ONLY_SPEC
                      + "It also has a purple_latch_timeout field.\n")


class TestWhitelistCitations(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = pathlib.Path(tmp.name)
        (self.dir / "src").mkdir()
        (self.dir / "src" / "gizmo.c").write_text(WIDGET_SOURCE)
        (self.dir / "standard_only.md").write_text(STANDARD_ONLY_SPEC)
        (self.dir / "with_invented.md").write_text(WITH_INVENTED_SPEC)

    def scan(self, candidate, whitelist_text, *flags):
        wl = self.dir / "whitelist.txt"
        wl.write_text(whitelist_text)
        return run_scan(self.dir / candidate, "--against", self.dir / "src",
                        "--whitelist", wl, *flags)

    def test_no_whitelist_flags_mixed_case_standard_terms(self):
        """Baseline: without an entry these are high-signal hits."""
        rc, out = run_scan(self.dir / "standard_only.md", "--against",
                           self.dir / "src")
        self.assertEqual(rc, 1, out)
        self.assertIn("[idents] 2 high-signal", out)

    def test_cited_mixed_case_entries_suppress_hits(self):
        rc, out = self.scan(
            "standard_only.md",
            "SuperSpeed  # USB 3.2 spec, section 3.1\n"
            "xHCI  # xHCI spec, section 1.1\n")
        self.assertEqual(rc, 0, out)
        self.assertIn("[idents] 0 high-signal", out)
        self.assertIn("[whitelist] 0 uncited", out)

    def test_citation_may_contain_hash_and_whitelist_is_case_insensitive(self):
        rc, out = self.scan(
            "standard_only.md",
            "# a comment-only line is not an entry\n"
            "superspeed  # USB 3.2 spec, table #4\n"
            "XHCI\t#\txHCI spec, section 1.1 # see also errata\n")
        self.assertEqual(rc, 0, out)
        self.assertIn("[whitelist] 0 uncited", out)

    def test_uncited_entries_are_listed_but_still_suppress_by_default(self):
        rc, out = self.scan(
            "standard_only.md",
            "SuperSpeed\n"
            "xHCI   #   \n"
            "# comment only\n")
        self.assertEqual(rc, 0, out)
        self.assertIn("[idents] 0 high-signal", out)
        self.assertIn("[whitelist] 2 uncited entr(ies)", out)
        self.assertIn("  - SuperSpeed  (whitelist L1)", out)
        self.assertIn("  - xHCI  (whitelist L2)", out)
        self.assertIn("verdict: clean", out)
        self.assertIn("2 uncited whitelist entr(ies)", out)

    def test_crlf_whitelist_and_hash_only_comment(self):
        rc, out = self.scan(
            "standard_only.md",
            "SuperSpeed  # USB 3.2 spec, section 3.1\r\n"
            "xHCI  ##\r\n",
            "--require-citations")
        self.assertEqual(rc, 1, out)
        self.assertIn("[whitelist] 1 uncited entr(ies)", out)
        self.assertIn("  - xHCI  (whitelist L2)", out)

    def test_require_citations_stops_uncited_entries_suppressing(self):
        rc, out = self.scan(
            "standard_only.md",
            "SuperSpeed\n"
            "xHCI  # xHCI spec, section 1.1\n",
            "--require-citations")
        self.assertEqual(rc, 1, out)
        self.assertIn("[whitelist] 1 uncited entr(ies)", out)
        self.assertIn("[idents] 1 high-signal", out)
        self.assertIn("  - SuperSpeed  (in ", out)
        self.assertIn("1 uncited whitelist entr(ies)", out)

    def test_require_citations_reports_uncited_entry_absent_from_candidate(self):
        """An uncited entry is a finding even when nothing uses it."""
        rc, out = self.scan(
            "standard_only.md",
            "SuperSpeed  # USB 3.2 spec, section 3.1\n"
            "xHCI  # xHCI spec, section 1.1\n"
            "unused_name\n",
            "--require-citations")
        self.assertEqual(rc, 1, out)
        self.assertIn("  - unused_name  (whitelist L3)", out)
        self.assertIn("[idents] 0 high-signal", out)

    def test_cited_entry_absent_from_candidate_is_harmless(self):
        rc, out = self.scan(
            "standard_only.md",
            "SuperSpeed  # USB 3.2 spec, section 3.1\n"
            "xHCI  # xHCI spec, section 1.1\n"
            "NeverUsedTerm  # Example spec, section 9\n",
            "--require-citations")
        self.assertEqual(rc, 0, out)
        self.assertIn("[whitelist] 0 uncited", out)

    def test_source_only_mixed_case_identifier_is_still_a_finding(self):
        rc, out = self.scan(
            "with_invented.md",
            "SuperSpeed  # USB 3.2 spec, section 3.1\n"
            "xHCI  # xHCI spec, section 1.1\n",
            "--require-citations")
        self.assertEqual(rc, 1, out)
        self.assertIn("[idents] 1 high-signal", out)
        self.assertIn("  - purple_latch_timeout  (in ", out)

    def test_cited_entry_appearing_twice_uncited_is_not_reported(self):
        """A cited entry wins over a bare duplicate of the same name."""
        rc, out = self.scan(
            "standard_only.md",
            "SuperSpeed\n"
            "superspeed  # USB 3.2 spec, section 3.1\n"
            "xHCI  # xHCI spec, section 1.1\n",
            "--require-citations")
        self.assertEqual(rc, 0, out)
        self.assertIn("[whitelist] 0 uncited", out)


# Invented device with an embedded vendor patch table. Line 6-9 is the table;
# 0x1234 is also a register offset the code uses, so it is not table-only,
# and 0x00ff falls under the default --vendor-min-value.
VENDOR_SOURCE = """\
#define FAKE_PATCH_BASE 0x1234
static void fake_apply(void) {
    fake_write(0x1234, 1);
}
static const unsigned short fake_patch[] = {
    0xbeef, 0x1234,
    0x00ff, 0xc0de,
    0x7a7a,
};
"""


class TestVendorRegion(unittest.TestCase):
    """--vendor-region: a spec that breaks a vendor table down value by value
    shares numbers with the source, not token runs, so checks 1 and 2 pass it
    (an RTL8125B transfer FAIL that leak_scan missed, 2026-10)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = pathlib.Path(self.tmp.name)
        self.src = root / "fake_patch.c"
        self.src.write_text(VENDOR_SOURCE)
        self.leaky = root / "leaky.md"
        self.leaky.write_text(
            "## Patch\n\nWord 0 is 0xBEEF.\n\nWord 3 is 0C0DEh.\n")
        self.clean = root / "clean.md"
        self.clean.write_text(
            "## Registers\n\nThe patch base is 0x1234; mask 0xFF.\n")
        self.region = f"{self.src}:6-9"

    def tearDown(self):
        self.tmp.cleanup()

    def test_table_only_values_are_findings(self):
        rc, out = run_scan(self.leaky, "--against", self.src,
                           "--vendor-region", self.region)
        self.assertEqual(rc, 1, out)
        self.assertIn("[vendor] 2 value(s)", out)
        self.assertIn("candidate L3", out)
        self.assertIn("candidate L5", out)

    def test_same_candidate_is_clean_without_the_region(self):
        rc, out = run_scan(self.leaky, "--against", self.src)
        self.assertEqual(rc, 0, out)

    def test_values_used_outside_the_table_or_small_do_not_count(self):
        rc, out = run_scan(self.clean, "--against", self.src,
                           "--vendor-region", self.region)
        self.assertEqual(rc, 0, out)
        self.assertIn("[vendor] 0 value(s)", out)

    def test_report_never_prints_table_values(self):
        rc, out = run_scan(self.leaky, "--against", self.src,
                           "--vendor-region", self.region)
        self.assertEqual(rc, 1, out)
        self.assertNotIn("sha1", out.split("[vendor]")[1],
                         "a digest of a 16-bit value is reversible")
        self.assertNotIn("beef", out.lower())
        self.assertNotIn("c0de", out.lower())

    def test_bad_region_spec_is_usage_error(self):
        for spec in (str(self.src), f"{self.src}:9-6", "nofile.c:1-2"):
            rc, out = run_scan(self.leaky, "--against", self.src,
                               "--vendor-region", spec)
            self.assertEqual(rc, 2, f"{spec}: {out}")
            self.assertIn("--vendor-region", out)
            self.assertNotIn("unrecognized arguments", out)

    def test_range_past_end_of_file_is_usage_error(self):
        rc, out = run_scan(self.leaky, "--against", self.src,
                           "--vendor-region", f"{self.src}:6-500")
        self.assertEqual(rc, 2, out)
        self.assertIn("runs past", out)

    def test_region_file_must_be_scanned(self):
        other = pathlib.Path(self.tmp.name) / "other.c"
        other.write_text("int other;\n")
        rc, out = run_scan(self.leaky, "--against", other,
                           "--vendor-region", self.region)
        self.assertEqual(rc, 2, out)
        self.assertIn("not among the --against sources", out)

    def test_each_region_must_contribute(self):
        # One good region does not cover for a mistyped second one.
        rc, out = run_scan(self.leaky, "--against", self.src,
                           "--vendor-region", self.region,
                           "--vendor-region", f"{self.src}:2-2")
        self.assertEqual(rc, 2, out)
        self.assertIn(f"{self.src}:2-2", out)

    def test_code_literal_forms_are_read(self):
        # Separators, C/Rust suffixes and Verilog sized literals, as an
        # output scan of driver code would meet them.
        code = pathlib.Path(self.tmp.name) / "new_driver.rs"
        code.write_text("const A: u16 = 0xBE_EF_u16;\n"
                        "const B: u32 = 0xC0DEu;\n"
                        "// 16'h7A7A\n")
        rc, out = run_scan(code, "--against", self.src,
                           "--vendor-region", self.region)
        self.assertEqual(rc, 1, out)
        self.assertIn("[vendor] 3 value(s)", out)

    def test_min_value_is_inclusive_and_adjustable(self):
        rc, out = run_scan(self.clean, "--against", self.src,
                           "--vendor-region", self.region,
                           "--vendor-min-value", "0xff")
        self.assertEqual(rc, 1, out)
        self.assertIn("[vendor] 1 value(s)", out)

    def test_inert_region_is_an_error_not_a_clean_scan(self):
        # Lines 1-4 hold only 0x1234, which the code also uses.
        rc, out = run_scan(self.leaky, "--against", self.src,
                           "--vendor-region", f"{self.src}:1-4")
        self.assertEqual(rc, 2, out)
        self.assertIn("inert", out)


if __name__ == "__main__":
    unittest.main()
