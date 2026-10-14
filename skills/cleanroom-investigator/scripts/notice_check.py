#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Curtis Galloway
# SPDX-License-Identifier: Apache-2.0
"""
notice_check.py - mechanical clean-room usage-notice check (stdlib only).

Checks that a clean-room spec carries the usage notice that
cleanroom-spec/templates/usage-notice.md prescribes, and that the spec names
its source pin. A writer runs it before returning the spec; the verifier runs
it first and then judges what a script cannot (whether the prose says what the
clauses mean). It never reads the source and never prints spec text beyond the
label and path it is complaining about.

Usage: notice_check.py <spec.md>...

Per spec it reports one message per problem:

  - the begin or end marker is missing, repeated, or out of order
  - the begin marker is not before the first "##" heading
  - one of the seven clause labels is missing inside the block
  - a <placeholder> is left inside the block (HTML comments and <http...>
    autolinks are ignored)
  - the spec-gap path is missing or does not match
    docs/spec-gaps/[A-Za-z0-9._-]+\\.md
  - the block names a version (v4) or a 40/64-hex hash; the notice points at
    the ledger instead, so it cannot go stale
  - no filled <repo>@<commit> pin appears outside the notice (the attestation
    that required-structure item 12 places at the end of the spec)

Exit codes: 0 = clean, 1 = findings, 2 = usage or I/O error.
"""

import argparse
import pathlib
import re
import sys

BEGIN = "<!-- cleanroom-usage-notice:begin -->"
END = "<!-- cleanroom-usage-notice:end -->"

# Each clause starts a paragraph with this exact bold label.
LABELS = (
    "**Do not read the source.**",
    "**Only inputs.**",
    "**Gaps.**",
    "**Source-observed facts.**",
    "**Provenance directory.**",
    "**Pre-merge gate.**",
    "**Hash match.**",
)

HEADING_RE = re.compile(r"^#{2,6}[ \t]", re.MULTILINE)
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
AUTOLINK_RE = re.compile(r"<https?://[^<>\s]*>")
PLACEHOLDER_RE = re.compile(r"<[^<>\n]+>")
GAP_TOKEN_RE = re.compile(r"docs/spec-gaps/[^\s`]*")
GAP_PATH_RE = re.compile(r"docs/spec-gaps/[A-Za-z0-9._-]+\.md")
VERSION_RE = re.compile(r"\bv\d+\b", re.IGNORECASE)
HASH_RE = re.compile(r"(?<![0-9A-Fa-f])(?:[0-9A-Fa-f]{64}|[0-9A-Fa-f]{40})"
                     r"(?![0-9A-Fa-f])")
PIN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]*@[0-9a-f]{7,64}(?![0-9A-Za-z])")


def die(msg):
    print(f"notice_check: error: {msg}", file=sys.stderr)
    sys.exit(2)


def line_of(text, offset):
    """1-based line number of a character offset."""
    return text.count("\n", 0, offset) + 1


def blank_comments(text):
    """Replace HTML comments with spaces, keeping offsets and newlines."""
    return COMMENT_RE.sub(
        lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)


def check_text(text):
    """Return a list of (line, message) findings for one spec's text."""
    findings = []

    begins = [m.start() for m in re.finditer(re.escape(BEGIN), text)]
    ends = [m.start() for m in re.finditer(re.escape(END), text)]
    if not begins:
        findings.append((1, f"missing begin marker {BEGIN}"))
    if not ends:
        findings.append((1, f"missing end marker {END}"))
    if len(begins) > 1:
        findings.append((line_of(text, begins[1]),
                         "begin marker appears more than once"))
    if len(ends) > 1:
        findings.append((line_of(text, ends[1]),
                         "end marker appears more than once"))
    if not begins or not ends:
        return findings
    if ends[0] < begins[0]:
        findings.append((line_of(text, ends[0]),
                         "end marker comes before the begin marker"))
        return findings

    block_start = begins[0] + len(BEGIN)
    block_end = ends[0]
    block = text[block_start:block_end]
    block_line = line_of(text, block_start)

    heading = HEADING_RE.search(text)
    if heading and heading.start() < begins[0]:
        findings.append((line_of(text, heading.start()),
                         "a ## heading comes before the notice; the notice "
                         "belongs at the top of the document"))

    # Labels are tested on the block with HTML comments blanked, so a clause
    # hidden inside a comment does not count: consumers would not see it.
    shown = blank_comments(block)
    for label in LABELS:
        if not re.search(r"^" + re.escape(label), shown, re.MULTILINE):
            findings.append((block_line, f"missing clause {label}"))

    visible = AUTOLINK_RE.sub(lambda m: " " * len(m.group(0)),
                              blank_comments(block))

    for m in PLACEHOLDER_RE.finditer(visible):
        findings.append((line_of(text, block_start + m.start()),
                         f"unfilled placeholder {m.group(0)} in the notice"))

    gaps = list(GAP_TOKEN_RE.finditer(visible))
    if not gaps:
        findings.append((block_line,
                         "no spec-gap path docs/spec-gaps/<device>.md "
                         "in the notice"))
    for m in gaps:
        token = m.group(0).rstrip(".,;:)\"'*")
        if "<" in token or ">" in token:
            continue  # already reported as an unfilled placeholder
        if not GAP_PATH_RE.fullmatch(token):
            findings.append((line_of(text, block_start + m.start()),
                             f"malformed spec-gap path {token!r}; expected "
                             "docs/spec-gaps/<name>.md with name made of "
                             "letters, digits, '.', '_' and '-'"))

    for m in VERSION_RE.finditer(visible):
        findings.append((line_of(text, block_start + m.start()),
                         f"version token {m.group(0)!r} in the notice; the "
                         "notice names no version"))
    for m in HASH_RE.finditer(visible):
        findings.append((line_of(text, block_start + m.start()),
                         "hash in the notice; the notice names no hash"))

    outside = text[:begins[0]] + " " * (ends[0] + len(END) - begins[0]) \
        + text[ends[0] + len(END):]
    outside = blank_comments(outside)
    if not PIN_RE.search(outside):
        if "@<commit>" in outside:
            findings.append((line_of(text, outside.index("@<commit>")),
                             "attestation pin <repo>@<commit> is not filled"))
        else:
            findings.append((1, "no filled <repo>@<commit> pin outside the "
                                "notice (required-structure item 12)"))
    return findings


def main():
    ap = argparse.ArgumentParser(
        description="Mechanical check of a clean-room spec's usage notice "
                    "and source pin.")
    ap.add_argument("spec", nargs="+", help="spec file(s) to check")
    args = ap.parse_args()

    total = 0
    for spec in args.spec:
        try:
            text = pathlib.Path(spec).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            die(f"cannot read {spec}: {e}")
        findings = check_text(text)
        total += len(findings)
        for line, msg in findings:
            print(f"{spec}:{line}: {msg}")
        if not findings:
            print(f"{spec}: notice ok")
    print("verdict:", f"FINDINGS - {total} problem(s)" if total else "clean")
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
