#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Curtis Galloway
# SPDX-License-Identifier: Apache-2.0
"""
Tests for scripts/cleanroom_hook.py.

Run:  python3 -m unittest discover -s skills/cleanroom-implementer/tests -v

Each case drives the hook the way Antigravity does: a PreToolUse event on
stdin with the call nested under `toolCall` and the workspace in
`workspacePaths`. Flat `tool_name`/`tool_input` payloads are exercised too,
because the same script is meant to keep working on other harnesses.

Four invariants here are deliberate design decisions that a well-meaning
future edit would break:

  - allow is ALWAYS explicit (test_allow_is_explicit, and the malformed-input
    case). Antigravity does not accept empty stdout as permission to proceed,
    so a silent hook can wedge every tool call in the session.
  - written content is not scanned (test_edit_content_is_not_scanned,
    test_code_edit_content_is_not_scanned).
  - malformed input allows rather than blocks.
  - a deny is emitted in every dialect at once
    (test_deny_speaks_every_harness_dialect).
"""

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
HOOK = HERE.parent / "scripts" / "cleanroom_hook.py"
FIX = HERE / "fixtures"

BLOCKED_PATH = "/home/dev/src/linux/drivers/tty/serial/widgetron.c"
ALLOW = {"decision": "allow"}


class HookCase(unittest.TestCase):

    def fire(self, tool, args, role=None, policy=None, shape="antigravity",
             project_var="CLEANROOM_PROJECT_DIR", extra_env=None, setup=None,
             event_extra=None):
        """Send one PreToolUse event; return (rc, stderr, log_entries).

        stdout and the temp workspace land on self for the cases that assert
        on them.
        """
        with tempfile.TemporaryDirectory() as tmp:
            if setup is not None:
                setup(pathlib.Path(tmp))
            env = dict(os.environ)
            for var in ("CLEANROOM_PROJECT_DIR", "GEMINI_PROJECT_DIR",
                        "CLAUDE_PROJECT_DIR", "CLEANROOM_ROLE",
                        "CLEANROOM_POLICY", "CLEANROOM_BLOCK_EXIT_CODE"):
                env.pop(var, None)
            if project_var:
                env[project_var] = tmp
            if role is not None:
                env["CLEANROOM_ROLE"] = role
            if policy is not None:
                env["CLEANROOM_POLICY"] = str(policy)
            env.update(extra_env or {})

            if shape == "antigravity":
                event = {"toolCall": {"name": tool, "args": args},
                         "stepIdx": 4,
                         "conversationId": "agy-test-session",
                         "workspacePaths": [tmp]}
            else:
                event = {"tool_name": tool, "tool_input": args,
                         "session_id": "test-session"}
            event.update(event_extra or {})

            proc = subprocess.run([sys.executable, str(HOOK)],
                                  input=json.dumps(event),
                                  capture_output=True, text=True, env=env)
            self.stdout = proc.stdout
            log = pathlib.Path(tmp) / "docs" / "provenance" / "hook-blocks.jsonl"
            entries = []
            if log.is_file():
                entries = [json.loads(ln) for ln in
                           log.read_text().splitlines() if ln.strip()]
            return proc.returncode, proc.stderr, entries


class TestBlocking(HookCase):

    def test_blocked_path_without_role(self):
        rc, err, log = self.fire("view_file", {"TargetFile": BLOCKED_PATH})
        self.assertEqual(rc, 2, err)
        self.assertIn("BLOCKED", err)
        self.assertIn("spec-gap", err)
        self.assertEqual(len(log), 1)
        self.assertEqual(log[0]["action"], "blocked")

    def test_blocked_url_via_url_reader(self):
        rc, err, log = self.fire(
            "read_url_content",
            {"Url": "https://git.kernel.org/pub/scm/linux/x.c"})
        self.assertEqual(rc, 2, err)
        self.assertEqual(log[0]["action"], "blocked")

    def test_search_query_is_checked_against_urls(self):
        rc, err, _ = self.fire(
            "search_web", {"query": "widgetron driver site:kernel.org"})
        self.assertEqual(rc, 2, err)

    def test_unknown_mcp_tool_is_checked_for_urls(self):
        """The shipped hooks.json wires matcher '.*' precisely for this."""
        rc, err, _ = self.fire(
            "mcp__fetcher__get",
            {"target": "https://kernel.org/doc/widgetron.html"})
        self.assertEqual(rc, 2, err)


class TestToolVocabularies(HookCase):
    """Nothing keys off a tool-name table; argument names carry the load.

    Antigravity names its arguments in PascalCase (CommandLine, TargetFile)
    and has renamed tools between releases, so these cases are the guard
    against someone reintroducing a per-tool lookup.
    """

    def test_run_command_pascalcase_commandline(self):
        rc, err, log = self.fire("run_command", {
            "CommandLine": "git clone https://github.com/torvalds/linux",
            "Cwd": "/home/dev/src/widgetron-port",
            "WaitMsBeforeAsync": 0})
        self.assertEqual(rc, 2, err)
        self.assertEqual(log[0]["tool"], "run_command")

    def test_run_command_cwd_into_a_checkout(self):
        rc, err, _ = self.fire("run_command", {
            "CommandLine": "rg widgetron_reset .",
            "Cwd": "/home/dev/src/linux/drivers/net"})
        self.assertEqual(rc, 2, err)

    def test_view_file_target_file(self):
        rc, err, _ = self.fire("view_file", {"TargetFile": BLOCKED_PATH})
        self.assertEqual(rc, 2, err)

    def test_grep_search_search_directory(self):
        rc, err, _ = self.fire("grep_search", {
            "Query": "widgetron_reset",
            "SearchDirectory": "/home/dev/src/u-boot/drivers"})
        self.assertEqual(rc, 2, err)

    def test_read_file_snake_case_still_works(self):
        rc, err, _ = self.fire("read_file", {"file_path": BLOCKED_PATH})
        self.assertEqual(rc, 2, err)

    def test_path_list_is_checked(self):
        rc, err, _ = self.fire("read_many_files", {
            "paths": ["docs/widgetron-spec.md", BLOCKED_PATH]})
        self.assertEqual(rc, 2, err)

    def test_flat_payload_shape_still_works(self):
        """Other harnesses send tool_name/tool_input at the top level."""
        rc, err, _ = self.fire("Read", {"file_path": BLOCKED_PATH},
                               shape="flat")
        self.assertEqual(rc, 2, err)


class TestAllowing(HookCase):

    def test_allow_is_explicit(self):
        """Antigravity rejects empty stdout; silence would wedge the session."""
        rc, err, log = self.fire("view_file",
                                 {"TargetFile": "docs/widgetron-spec.md"})
        self.assertEqual(rc, 0, err)
        self.assertEqual(err, "")
        self.assertEqual(json.loads(self.stdout), ALLOW)
        self.assertEqual(log, [], "benign calls must not be logged")

    def test_allow_does_not_auto_approve(self):
        """Allow speaks only Antigravity's dialect, deliberately.

        Deny is broadcast to every harness because withholding permission is
        safe to repeat. Allow is not: Claude Code's
        hookSpecificOutput.permissionDecision "allow" auto-approves the call
        and consumes the user's permission prompt, so broadcasting it would
        turn "no objection" into "granted" on every benign call the hook sees.
        """
        rc, err, _ = self.fire("view_file",
                               {"TargetFile": "docs/widgetron-spec.md"})
        self.assertEqual(rc, 0, err)
        payload = json.loads(self.stdout)
        self.assertEqual(payload, ALLOW, "allow must carry nothing extra")
        self.assertNotIn(
            "permissionDecision", json.dumps(payload),
            "emitting Claude Code's allow field would skip the user's prompt")

    def test_investigator_role_allows_and_logs(self):
        rc, err, log = self.fire("view_file", {"TargetFile": BLOCKED_PATH},
                                 role="investigator")
        self.assertEqual(rc, 0, err)
        self.assertEqual(json.loads(self.stdout), ALLOW)
        self.assertEqual(len(log), 1, "authorized reads must still be logged")
        self.assertEqual(log[0]["action"], "allowed-role")
        self.assertEqual(log[0]["role"], "investigator")

    def test_verifier_role_allows(self):
        rc, err, log = self.fire("view_file", {"TargetFile": BLOCKED_PATH},
                                 role="verifier")
        self.assertEqual(rc, 0, err)
        self.assertEqual(log[0]["action"], "allowed-role")

    def test_unrecognized_role_still_blocks(self):
        rc, err, _ = self.fire("view_file", {"TargetFile": BLOCKED_PATH},
                               role="implementer")
        self.assertEqual(rc, 2, err)

    def test_edit_content_is_not_scanned(self):
        """Deliberate: a comment naming a blocked project must not block.

        Content-level leaks belong to session_audit and the output scan.
        Scanning written content here would false-positive on prose.
        """
        rc, err, log = self.fire("edit_file", {
            "TargetFile": "src/devices/widgetron/driver.rs",
            "old_string": "// TODO",
            "new_string": "// Ported clean-room; do not consult "
                          "trusted-firmware-a or linux/drivers/ for this.",
        })
        self.assertEqual(rc, 0, err)
        self.assertEqual(log, [])

    def test_code_edit_content_is_not_scanned(self):
        """Same exemption, and it matters more here.

        Unrecognized argument keys are scanned for URLs, so Antigravity's
        CodeEdit has to be exempt by name or every citation in a doc comment
        would block the write that adds it.
        """
        rc, err, log = self.fire("write_file", {
            "TargetFile": "docs/references/README.md",
            "CodeEdit": "Mirror list (pre-fetched, do not fetch): "
                        "https://kernel.org/doc/, https://bootlin.com/",
        })
        self.assertEqual(rc, 0, err)
        self.assertEqual(log, [])

    def test_malformed_input_allows_explicitly(self):
        """Bad input must not wedge the session - in either direction.

        Exit 0 alone is not enough: Antigravity needs the decision object,
        so the allow payload has to be printed even on the error path.
        """
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ)
            env["CLEANROOM_PROJECT_DIR"] = tmp
            proc = subprocess.run([sys.executable, str(HOOK)],
                                  input="this is not json",
                                  capture_output=True, text=True, env=env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout), ALLOW)


class TestDenyContract(HookCase):
    """One script has to satisfy more than one harness's block protocol."""

    def test_deny_speaks_every_harness_dialect(self):
        rc, err, _ = self.fire("view_file", {"TargetFile": BLOCKED_PATH})
        self.assertEqual(rc, 2, err)
        payload = json.loads(self.stdout)
        # Antigravity reads the decision object.
        self.assertEqual(payload["decision"], "deny")
        self.assertIn("spec-gap", payload["reason"])
        self.assertTrue(payload["continue"],
                        "block the call, not the whole session")
        # Claude Code reads hookSpecificOutput.
        self.assertEqual(
            payload["hookSpecificOutput"]["permissionDecision"], "deny")
        # A non-zero exit is a block everywhere, and fails closed.
        self.assertIn("BLOCKED", err)

    def test_block_exit_code_is_overridable(self):
        """For a build that objects to a non-zero exit from a hook."""
        rc, _, log = self.fire("view_file", {"TargetFile": BLOCKED_PATH},
                               extra_env={"CLEANROOM_BLOCK_EXIT_CODE": "0"})
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(self.stdout)["decision"], "deny")
        self.assertEqual(log[0]["action"], "blocked",
                         "an overridden exit code is still a block")


class TestEventPlumbing(HookCase):

    def test_workspace_paths_locate_the_project(self):
        """No project-dir variable exists in Antigravity; the event carries it."""
        rc, err, log = self.fire("view_file", {"TargetFile": BLOCKED_PATH},
                                 project_var=None)
        self.assertEqual(rc, 2, err)
        self.assertEqual(len(log), 1,
                         "log must land under workspacePaths[0]")

    def test_log_records_where_to_audit(self):
        """The pre-merge audit needs the session's own paths, not a guess."""
        rc, err, log = self.fire(
            "view_file", {"TargetFile": BLOCKED_PATH},
            event_extra={"transcriptPath": "/tmp/agy/session.jsonl",
                         "artifactDirectoryPath": "/tmp/agy/brain/abc"})
        self.assertEqual(rc, 2, err)
        self.assertEqual(log[0]["transcript"], "/tmp/agy/session.jsonl")
        self.assertEqual(log[0]["artifacts"], "/tmp/agy/brain/abc")

    def test_conversation_id_is_recorded(self):
        _, _, log = self.fire("view_file", {"TargetFile": BLOCKED_PATH})
        self.assertEqual(log[0]["session_id"], "agy-test-session")


class TestPolicyPlumbing(HookCase):

    def test_custom_policy_file_is_honored(self):
        path = "/home/dev/src/acme-vendor-blob-sdk/hal/widgetron.c"
        rc, _, _ = self.fire("view_file", {"TargetFile": path})
        self.assertEqual(rc, 0, "not blocked by the built-in defaults")
        rc, err, log = self.fire("view_file", {"TargetFile": path},
                                 policy=FIX / "custom-policy.json")
        self.assertEqual(rc, 2, err)
        self.assertIn("acme-vendor-blob-sdk", log[0]["pattern"])

    def test_policy_is_found_in_the_workspace_agents_dir(self):
        """<workspace>/.agents/cleanroom-policy.json, no env var needed."""
        def setup(root):
            cfg = root / ".agents"
            cfg.mkdir()
            (cfg / "cleanroom-policy.json").write_text(json.dumps({
                "checkout_roots": [],
                "blocked_path_patterns": ["acme-vendor-blob-sdk"],
                "blocked_url_patterns": [],
            }))
        rc, err, log = self.fire(
            "view_file",
            {"TargetFile": "/home/dev/src/acme-vendor-blob-sdk/hal/w.c"},
            project_var=None, setup=setup)
        self.assertEqual(rc, 2, err)
        self.assertIn("acme-vendor-blob-sdk", log[0]["pattern"])

    def test_legacy_project_dir_variables_still_work(self):
        for var in ("GEMINI_PROJECT_DIR", "CLAUDE_PROJECT_DIR"):
            with self.subTest(var=var):
                rc, err, log = self.fire(
                    "Read", {"file_path": BLOCKED_PATH}, shape="flat",
                    project_var=var)
                self.assertEqual(rc, 2, err)
                self.assertEqual(len(log), 1)


FIREWALLED = ("board-expert", "hardware-investigator", "cleanroom-investigator",
              "hardware-specs-gpl")


def firewall_paths(name):
    """The same target as installed in each way a skill or checkout lands."""
    if name == "hardware-specs-gpl":
        return [
            f"/home/dev/src/{name}/specs/widgetron.md",
            f"/home/dev/work/{name}",
            f"/home/dev/Downloads/{name}-main/README.md",
        ]
    return [
        f"/home/dev/.claude/skills/{name}/SKILL.md",
        f"/home/dev/.claude/plugins/cache/mkt/plug/1.2.3/skills/{name}/SKILL.md",
        f"/home/dev/src/driver-lab/skills/{name}/SKILL.md",
        f"/home/dev/.gemini/skills/{name}/references/x.md",
    ]


class TestFirewallByName(HookCase):
    """LS-R18: the dirty-side skills and the GPL spec repository are blocked
    by name, however installed. Investigator and verifier stay allowed."""

    def test_path_forms_denied_for_the_implementer(self):
        for name in FIREWALLED:
            for path in firewall_paths(name):
                with self.subTest(path=path):
                    rc, err, log = self.fire("view_file", {"TargetFile": path})
                    self.assertEqual(rc, 2, err)
                    self.assertIn(name, log[0]["pattern"])
                    self.assertEqual(log[0]["action"], "blocked")

    def test_path_forms_allowed_for_investigator_and_verifier(self):
        for name in FIREWALLED:
            for role in ("investigator", "verifier"):
                path = firewall_paths(name)[0]
                with self.subTest(path=path, role=role):
                    rc, err, log = self.fire(
                        "view_file", {"TargetFile": path}, role=role)
                    self.assertEqual(rc, 0, err)
                    self.assertEqual(json.loads(self.stdout), ALLOW)
                    self.assertEqual(log[0]["action"], "allowed-role")

    def test_command_forms(self):
        for name in FIREWALLED:
            path = firewall_paths(name)[0]
            cmds = [f"cat {path}", f"ls -R {os.path.dirname(path)}",
                    f"cp -r {os.path.dirname(path)} /tmp/copy",
                    f"cd {os.path.dirname(path)} && cat SKILL.md"]
            if name == "hardware-specs-gpl":
                cmds.append(f"git clone https://github.com/someone/{name}.git")
            for cmd in cmds:
                with self.subTest(cmd=cmd):
                    rc, err, _ = self.fire("run_command", {"CommandLine": cmd})
                    self.assertEqual(rc, 2, err)
                    rc, err, log = self.fire(
                        "run_command", {"CommandLine": cmd},
                        role="investigator")
                    self.assertEqual(rc, 0, err)
                    self.assertEqual(log[0]["action"], "allowed-role")

    def test_search_forms(self):
        for name in FIREWALLED:
            d = os.path.dirname(firewall_paths(name)[0])
            with self.subTest(name=name):
                rc, err, _ = self.fire("grep_search", {
                    "Query": "reset", "SearchDirectory": d})
                self.assertEqual(rc, 2, err)
                rc, err, _ = self.fire("Grep", {"pattern": "reset",
                                                "path": d}, shape="flat")
                self.assertEqual(rc, 2, err)
                rc, err, _ = self.fire("Glob", {
                    "pattern": f"**/{name}/**/*.md"}, shape="flat")
                self.assertEqual(rc, 2, err)
                rc, err, _ = self.fire("run_command", {
                    "CommandLine": f"find / -type d -name {name}"})
                self.assertEqual(rc, 2, err)

    def test_loading_by_name_or_delegating_by_name(self):
        """The Skill tool and subagent prompts carry the name in a key the
        hook has no path semantics for; the name is still the target."""
        for name in FIREWALLED:
            with self.subTest(name=name):
                rc, err, _ = self.fire("Skill", {"skill": name},
                                       shape="flat")
                self.assertEqual(rc, 2, err)
                rc, err, _ = self.fire("Agent", {
                    "prompt": f"Load the {name} skill and tell me the bus map"},
                    shape="flat")
                self.assertEqual(rc, 2, err)
                rc, err, _ = self.fire("mcp__git__get_file", {
                    "owner": "someone", "repo": name, "path": "README.md"})
                self.assertEqual(rc, 2, err)
                rc, err, _ = self.fire("Skill", {"skill": name},
                                       shape="flat", role="verifier")
                self.assertEqual(rc, 0, err)

    def test_case_and_url_encoding(self):
        for target in ("/home/dev/.claude/skills/Board-Expert/SKILL.md",
                       "/HOME/DEV/SRC/HARDWARE-SPECS-GPL/x.md",
                       "file:///home/dev/.claude/skills/board%2Dexpert/SKILL.md",
                       "/home/dev/.claude/skills/board%2dexpert/SKILL.md"):
            with self.subTest(target=target):
                rc, err, _ = self.fire("view_file", {"TargetFile": target})
                self.assertEqual(rc, 2, err)

    def test_traversal_still_names_the_target(self):
        for target in ("/home/dev/.claude/skills/other/../board-expert/SKILL.md",
                       "/home/dev/src/./hardware-specs-gpl/../hardware-specs-gpl/a"):
            with self.subTest(target=target):
                rc, err, _ = self.fire("view_file", {"TargetFile": target})
                self.assertEqual(rc, 2, err)

    def test_allowed_neighbors(self):
        """Docs and permissive spec repositories, and the other clean-room
        skills, are allowed to the implementer by design."""
        for target in ("/home/dev/src/hardware-specs-docs/specs/widgetron.md",
                       "/home/dev/src/hardware-specs-permissive/specs/w.md",
                       "/home/dev/.claude/skills/cleanroom-implementer/SKILL.md",
                       "/home/dev/.claude/skills/peripheral-spec/SKILL.md",
                       "/home/dev/.claude/skills/cleanroom-spec/SKILL.md",
                       "docs/widgetron-spec.md"):
            with self.subTest(target=target):
                rc, err, log = self.fire("view_file", {"TargetFile": target})
                self.assertEqual(rc, 0, err)
                self.assertEqual(log, [])

    def test_written_content_naming_a_skill_is_still_not_scanned(self):
        rc, err, log = self.fire("write_file", {
            "TargetFile": "docs/NOTES.md",
            "CodeEdit": "Never load board-expert or read hardware-specs-gpl."})
        self.assertEqual(rc, 0, err)
        self.assertEqual(log, [])

    def test_a_custom_policy_cannot_drop_the_firewall(self):
        """The firewall is not a policy key: a workspace policy that predates
        it (or omits it) must not silently turn it off."""
        rc, err, _ = self.fire(
            "view_file",
            {"TargetFile": "/home/dev/.claude/skills/board-expert/SKILL.md"},
            policy=FIX / "custom-policy.json")
        self.assertEqual(rc, 2, err)

    def test_policy_can_add_names(self):
        def setup(root):
            cfg = root / ".agents"
            cfg.mkdir()
            (cfg / "cleanroom-policy.json").write_text(json.dumps({
                "blocked_names": ["acme-dirty-skill"]}))
        rc, err, log = self.fire(
            "view_file",
            {"TargetFile": "/home/dev/.claude/skills/acme-dirty-skill/a.md"},
            project_var=None, setup=setup)
        self.assertEqual(rc, 2, err)
        self.assertIn("acme-dirty-skill", log[0]["pattern"])


def make_tree(root):
    """A workspace holding a skills directory and a spec checkout, as the
    firewall must treat them even when the command never names them."""
    for rel in ("skills/board-expert/SKILL.md",
                "skills/hardware-investigator/SKILL.md",
                "skills/peripheral-spec/SKILL.md",
                "store/hardware-specs-gpl/specs/x.md",
                "src/main.rs"):
        f = root / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("x\n")
    (root / "refs").symlink_to(root / "skills" / "board-expert")
    (root / "gpl").symlink_to(root / "store" / "hardware-specs-gpl")
    (root / "deep" / "a" / "b").mkdir(parents=True)
    (root / "deep" / "a" / "b" / "alias").symlink_to(
        root / "skills" / "board-expert")


class TestFirewallWithoutNamingThePath(HookCase):
    """Reads that never write the blocked name, or write it only through
    something the shell or the filesystem resolves."""

    def deny(self, tool, args, **kw):
        rc, err, _ = self.fire(tool, args, setup=make_tree, **kw)
        self.assertEqual(rc, 2, f"{args}: {err}")

    def allow(self, tool, args, **kw):
        rc, err, log = self.fire(tool, args, setup=make_tree, **kw)
        self.assertEqual(rc, 0, f"{args}: {err}")
        self.assertEqual(log, [])

    def cmd(self, line, **kw):
        self.deny("run_command", {"CommandLine": line}, **kw)

    def ok(self, line, **kw):
        self.allow("run_command", {"CommandLine": line}, **kw)

    def test_symlink_resolved(self):
        self.deny("view_file", {"TargetFile": "refs/SKILL.md"})
        self.deny("view_file", {"TargetFile": "gpl/specs/x.md"})
        self.cmd("cat refs/SKILL.md")
        self.cmd("cat gpl/specs/x.md")

    def test_symlink_below_the_search_root(self):
        self.deny("grep_search", {"Query": "reset", "SearchDirectory": "deep"})

    def test_glob_expanded_on_disk(self):
        self.cmd("cat skills/b*/SKILL.md")
        self.cmd("cat skills/*/SKILL.md")
        self.cmd("cat store/hardware-*-gpl/specs/x.md")
        self.deny("view_file", {"TargetFile": "skills/board-e?pert/SKILL.md"})

    def test_glob_that_matches_only_allowed_entries(self):
        self.ok("cat skills/peri*/SKILL.md")
        self.ok("cat src/*.rs")

    def test_cd_then_relative_read(self):
        self.cmd("cd skills/board-expert && cat SKILL.md")
        self.cmd("cd refs && cat SKILL.md")
        self.cmd("cd gpl; cat specs/x.md")
        self.cmd("pushd refs; cat ./SKILL.md")

    def test_cwd_argument_inside_a_blocked_tree(self):
        self.deny("run_command", {"CommandLine": "cat SKILL.md", "Cwd": "refs"})
        self.deny("run_command", {"CommandLine": "cat specs/x.md",
                                  "Cwd": "gpl"})

    def test_recursive_search_from_an_ancestor(self):
        self.cmd("grep -r reset skills")
        self.cmd("rg reset .")
        self.cmd("cd skills && rg reset")
        self.cmd("find store -type f -exec cat {} +")
        self.cmd("tar cf - store")
        self.cmd("cp -r skills /tmp/s")

    def test_listing_a_directory_is_not_reading_it(self):
        self.ok("ls skills")
        self.ok("ls .")
        self.ok("grep -r main src")

    def test_environment_and_shell_variables(self):
        self.cmd("cat skills/$FW_NAME/SKILL.md",
                 extra_env={"FW_NAME": "board-expert"})
        self.cmd("cat skills/${FW_NAME}/SKILL.md",
                 extra_env={"FW_NAME": "Board-Expert"})
        self.cmd("X=board; cat skills/${X}-expert/SKILL.md")
        self.cmd("D=refs cat $D/SKILL.md")
        self.cmd("D=skills; cd $D/board-expert && cat SKILL.md")

    def test_quoting_and_braces(self):
        self.cmd("cat skills/board-'expert'/SKILL.md")
        self.cmd('cat skills/"board"-expert/SKILL.md')
        self.cmd("cat skills/board-\\expert/SKILL.md")
        self.cmd("cat skills/{board,x}-expert/SKILL.md")

    def test_nested_shells_and_substitution(self):
        self.cmd("bash -c 'cd refs; cat SKILL.md'")
        self.cmd('sh -c "cat skills/b*/SKILL.md"')
        self.cmd("echo $(cat refs/SKILL.md)")
        self.cmd("echo `cat gpl/specs/x.md`")
        self.cmd("cat < refs/SKILL.md")

    def test_relative_paths_and_dotdot(self):
        self.deny("view_file", {"TargetFile": "src/../refs/SKILL.md"})
        self.deny("view_file", {"TargetFile": "./deep/a/b/alias/SKILL.md"})

    def test_benign_commands_in_the_same_tree(self):
        self.ok("cat src/main.rs")
        self.ok("cd src && cat main.rs")
        self.allow("view_file", {"TargetFile": "skills/peripheral-spec/SKILL.md"})

    def test_roles_may_still_read_through_the_same_routes(self):
        for cmd in ("cat refs/SKILL.md", "cd refs && cat SKILL.md",
                    "grep -r reset skills"):
            with self.subTest(cmd=cmd):
                rc, err, log = self.fire("run_command", {"CommandLine": cmd},
                                         setup=make_tree, role="investigator")
                self.assertEqual(rc, 0, err)
                self.assertEqual(log[0]["action"], "allowed-role")


def make_wide_tree(root):
    for i in range(250):
        d = root / "wide" / f"a{i:03d}"
        d.mkdir(parents=True)
    (root / "wide" / "board-expert").mkdir()
    (root / "docs-only" / "hardware-specs-docs").mkdir(parents=True)
    (root / "docs-only" / "hardware-specs-docs" / "x.md").write_text("x\n")


class TestFirewallReviewFindings(HookCase):
    """Cases found by the review-swarm over the first version of the firewall."""

    def run_cmd(self, line, setup=make_wide_tree, **kw):
        return self.fire("run_command", {"CommandLine": line}, setup=setup,
                         **kw)

    def test_assignments_after_export_are_tracked(self):
        for line in ("export a=board- b=expert; cat wide/${a}${b}/x",
                     "export a=board-; export b=expert; cat wide/${a}${b}/x",
                     "declare a=board- b=expert; cat wide/$a$b/x",
                     "readonly a=board- b=expert; cat wide/$a$b/x"):
            with self.subTest(line=line):
                rc, err, _ = self.run_cmd(line)
                self.assertEqual(rc, 2, err)

    def test_mid_word_hash_is_not_a_comment(self):
        rc, err, _ = self.run_cmd("echo a#b ; cat wide/b*")
        self.assertEqual(rc, 2, err)
        rc, err, _ = self.run_cmd("echo $# ; cat wide/board-e*t")
        self.assertEqual(rc, 2, err)

    def test_glob_with_more_matches_than_the_filesystem_cap(self):
        """The blocked entry sorts after 250 others; every match is checked
        by name even though only the first few are resolved."""
        rc, err, _ = self.run_cmd("cat wide/*")
        self.assertEqual(rc, 2, err)

    def test_glob_matching_only_allowed_siblings_is_allowed(self):
        rc, err, log = self.run_cmd("cat docs-only/hardware-specs-*/x.md")
        self.assertEqual(rc, 0, err)
        self.assertEqual(log, [])

    def test_blank_role_in_a_workspace_policy_does_not_authorize(self):
        """The implementer can write the workspace policy; an empty role
        string must not make the unset-role default an authorized one."""
        def setup(root):
            cfg = root / ".agents"
            cfg.mkdir()
            (cfg / "cleanroom-policy.json").write_text(
                json.dumps({"authorized_roles": ["", " "]}))
        rc, err, log = self.fire(
            "view_file",
            {"TargetFile": "/home/dev/.claude/skills/board-expert/SKILL.md"},
            project_var=None, setup=setup)
        self.assertEqual(rc, 2, err)
        self.assertEqual(log[0]["action"], "blocked")

    def test_malformed_policy_values_fall_back_to_defaults(self):
        """A null or wrongly typed list must not crash the hook (a crash is
        exit 1, which is not a block on every harness)."""
        def setup(root):
            cfg = root / ".agents"
            cfg.mkdir()
            (cfg / "cleanroom-policy.json").write_text(json.dumps({
                "blocked_path_patterns": None, "checkout_roots": "x",
                "blocked_url_patterns": 7, "authorized_roles": None}))
        rc, err, _ = self.fire(
            "view_file",
            {"TargetFile": "/home/dev/.claude/skills/board-expert/SKILL.md"},
            project_var=None, setup=setup)
        self.assertEqual(rc, 2, err)
        rc, err, _ = self.fire(
            "view_file", {"TargetFile": BLOCKED_PATH},
            project_var=None, setup=setup)
        self.assertEqual(rc, 2, err)

    def test_command_text_naming_a_skill_is_denied_even_as_prose(self):
        """Known false positive, chosen: a command line is judged whole. A
        commit message or heredoc that names a firewalled skill is denied
        (the same text through Write/Edit is exempt); the implementer can
        say 'the dirty-side skills' instead."""
        rc, err, _ = self.run_cmd('git commit -m "drop board-expert mention"')
        self.assertEqual(rc, 2, err)


def load_hook_module():
    import importlib.util
    spec = importlib.util.spec_from_file_location("cleanroom_hook_under_test",
                                                  HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestFirewallFailsClosedOnLimits(unittest.TestCase):
    """A cap that truncates what the firewall can check must deny the
    implementer (and say how to narrow the call), not allow."""

    def setUp(self):
        self.hook = load_hook_module()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = pathlib.Path(self._tmp.name).resolve()
        (self.root / "d").mkdir()
        for i in range(20):
            (self.root / "d" / f"f{i:02d}.txt").write_text("x\n")
        self.pol = dict(self.hook.DEFAULT_POLICY)

    def pick(self, command):
        return self.hook.pick_target(
            "run_command", {"CommandLine": command}, self.pol,
            cwd=str(self.root))

    def test_scan_budget_exhausted_is_a_deny(self):
        self.hook.SCAN_ENTRIES = 5
        _, hit = self.pick("grep -r x d")
        self.assertTrue(hit and hit.startswith("limit:"), hit)

    def test_scan_budget_not_exhausted_is_clean(self):
        _, hit = self.pick("grep -r x d")
        self.assertIsNone(hit)

    def test_glob_name_cap_is_a_deny(self):
        self.hook.GLOB_NAMES = 5
        _, hit = self.pick("cat d/*.txt")
        self.assertTrue(hit and hit.startswith("limit:"), hit)

    def test_brace_cap_is_a_deny(self):
        self.hook.BRACE_RESULTS = 3
        _, hit = self.pick("cat {a,b,c,d,e}.txt")
        self.assertTrue(hit and hit.startswith("limit:"), hit)

    def test_nesting_cap_is_a_deny(self):
        import shlex
        cmd = "cat d/f00.txt"
        for _ in range(self.hook.NESTING + 2):
            cmd = "sh -c " + shlex.quote(cmd)
        _, hit = self.pick(cmd)
        self.assertTrue(hit and hit.startswith("limit:"), hit)

    def run_main(self, role=None):
        import contextlib
        import io
        event = {"toolCall": {"name": "run_command",
                              "args": {"CommandLine": "grep -r x d"}},
                 "workspacePaths": [str(self.root)]}
        env = {"CLEANROOM_PROJECT_DIR": str(self.root)}
        if role:
            env["CLEANROOM_ROLE"] = role
        old_env = dict(os.environ)
        os.environ.pop("CLEANROOM_ROLE", None)
        os.environ.update(env)
        err, out = io.StringIO(), io.StringIO()
        old_in = sys.stdin
        sys.stdin = io.StringIO(json.dumps(event))
        try:
            with contextlib.redirect_stderr(err), \
                    contextlib.redirect_stdout(out):
                try:
                    self.hook.main()
                except SystemExit as e:
                    code = e.code
        finally:
            sys.stdin = old_in
            os.environ.clear()
            os.environ.update(old_env)
        return code, err.getvalue(), out.getvalue()

    def test_deny_message_says_to_narrow_the_path(self):
        self.hook.SCAN_ENTRIES = 5
        code, err, _ = self.run_main()
        self.assertEqual(code, 2, err)
        self.assertIn("narrower path", err)

    def test_investigator_is_unaffected_by_the_limit(self):
        self.hook.SCAN_ENTRIES = 5
        code, err, out = self.run_main(role="investigator")
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out), ALLOW)

    def test_unexpected_error_in_the_check_is_a_deny(self):
        def boom(*a, **k):
            raise RuntimeError("boom")
        self.hook.pick_target = boom
        code, err, _ = self.run_main()
        self.assertEqual(code, 2, err)
        self.assertIn("internal error", err)
        self.assertNotIn("too broad", err)


class TestFirewallFormParity(HookCase):
    """The same target is judged the same way whichever form carries it."""

    def deny(self, tool, args, **kw):
        rc, err, _ = self.fire(tool, args, setup=make_tree, **kw)
        self.assertEqual(rc, 2, f"{tool} {args}: {err}")

    def allow(self, tool, args, **kw):
        rc, err, log = self.fire(tool, args, setup=make_tree, **kw)
        self.assertEqual(rc, 0, f"{tool} {args}: {err}")
        self.assertEqual(log, [])

    def test_pattern_only_search_tools_scan_the_working_directory(self):
        """Grep and Glob with no path read the working directory, as a bare
        `grep -r pat` does."""
        self.deny("grep_search", {"Query": "reset"})
        self.deny("Grep", {"pattern": "reset"})
        self.deny("Glob", {"pattern": "**/*.md"})
        self.deny("Grep", {"pattern": "reset", "glob": "*.md"})

    def test_pattern_only_search_with_a_path_uses_that_path(self):
        self.allow("grep_search", {"Query": "reset", "SearchDirectory": "src"})
        self.allow("Grep", {"pattern": "reset", "path": "src"})
        self.deny("Grep", {"pattern": "reset", "path": "skills"})

    def test_pattern_only_search_in_a_clean_workspace_is_allowed(self):
        rc, err, log = self.fire("grep_search", {"Query": "reset"})
        self.assertEqual(rc, 0, err)
        self.assertEqual(log, [])

    def test_pattern_only_search_follows_a_cwd_argument(self):
        self.deny("Grep", {"pattern": "reset", "cwd": "refs"})
        self.allow("Grep", {"pattern": "reset", "cwd": "src"})

    def test_unknown_argument_key_that_is_a_symlink_is_resolved(self):
        self.deny("mcp__fs__open", {"location": "refs"})
        self.deny("mcp__fs__open", {"uri": "gpl/specs/x.md"})
        self.allow("mcp__fs__open", {"location": "src/main.rs"})

    def test_siblings_of_a_blocked_name_are_judged_alike_in_every_form(self):
        for name in ("board-expert-notes", "hardware-specs-gpl-main",
                     "x-board-expert", "hardware-specs-gpl.git"):
            with self.subTest(name=name):
                self.deny("view_file", {"TargetFile": f"/a/{name}/f"})
                self.deny("run_command", {"CommandLine": f"cat /a/{name}/f"})
                self.deny("grep_search", {"Query": "x",
                                          "SearchDirectory": f"/a/{name}"})
                self.deny("mcp__git__get", {"repo": name})

    def test_build_and_version_control_commands_do_not_scan_a_directory(self):
        self.allow("run_command", {"CommandLine": "git -C . status"})
        self.allow("run_command", {"CommandLine": "git add ."})
        self.allow("run_command", {"CommandLine": "cargo build --manifest-path ."})
        self.deny("run_command", {"CommandLine": "git grep reset ."})


class TestSecondReviewFindings(HookCase):
    """The second review-swarm on the fail-closed commit (LS11 re-review)."""

    def deny(self, tool, args, **kw):
        rc, err, _ = self.fire(tool, args, setup=make_tree, **kw)
        self.assertEqual(rc, 2, f"{tool} {args}: {err}")
        return err

    def allow(self, tool, args, **kw):
        rc, err, log = self.fire(tool, args, setup=make_tree, **kw)
        self.assertEqual(rc, 0, f"{tool} {args}: {err}")
        self.assertEqual(log, [])

    def test_brace_groups_beyond_the_expansion_rounds_are_a_deny(self):
        """Four comma groups used to leave a literal group behind, so the
        name the shell builds was never formed."""
        err = self.deny("run_command", {
            "CommandLine": "cat skills/board-e{x,x}{p,p}{e,e}{r,r}t/SKILL.md"})
        self.assertIn("brace expansion", err)

    def test_git_commands_that_read_content_scan_the_directory(self):
        for line in ("git show", "git log -p", "git log -p -- .",
                     "git archive HEAD", "git -C . diff",
                     "git cat-file -p HEAD:x", "git whatchanged"):
            with self.subTest(line=line):
                self.deny("run_command", {"CommandLine": line})

    def test_git_commands_that_read_nothing_still_do_not_scan(self):
        for line in ("git status", "git add .", "git commit -m x",
                     "git -C src log -p"):
            with self.subTest(line=line):
                self.allow("run_command", {"CommandLine": line})

    def test_a_search_expression_is_not_expanded_as_a_path(self):
        hook = load_hook_module()
        hook.GLOB_NAMES = 5
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp).resolve()
            (root / "d").mkdir()
            for i in range(10):
                (root / f"f{i}.txt").write_text("x\n")
            _, hit = hook.pick_target(
                "Grep", {"pattern": "*", "path": "d"},
                dict(hook.DEFAULT_POLICY), cwd=str(root))
        self.assertIsNone(hit)

    def test_a_malformed_event_is_a_deny_not_a_crash(self):
        rc, err, _ = self.fire("Bash", {"command": "ls"}, shape="claude",
                               project_var=None, event_extra={"cwd": 5})
        self.assertEqual(rc, 2, err)
        self.assertIn("internal error", err)
        self.assertNotIn("too broad", err)

    def test_a_cap_overrun_for_an_authorized_role_is_not_logged_as_access(self):
        def many(root):
            make_tree(root)
            for i in range(3500):
                (root / "src" / f"f{i}.txt").write_text("x\n")
        rc, err, log = self.fire("run_command", {"CommandLine": "grep -r x src"},
                                 role="investigator", setup=many)
        self.assertEqual(rc, 0, err)
        self.assertEqual(log, [])


if __name__ == "__main__":
    unittest.main()
