#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Curtis Galloway
# SPDX-License-Identifier: Apache-2.0
"""
cleanroom_hook.py - PreToolUse hook enforcing the clean-room source ban in
implementation sessions.

Wire it into Antigravity's hooks.json with matcher `.*` so MCP and
provider-specific tools are covered too:

  <workspace>/.agents/hooks.json     per project -> assets/antigravity-hooks.json
  ~/.gemini/config/hooks.json        every project (older builds:
                                     ~/.gemini/antigravity-cli/hooks.json)

Reads the hook event JSON from stdin, checks the tool's target (file path,
shell command, URL, search query) against the clean-room policy, and:

  - no match           -> allow, silent
  - match, role set    -> allow but LOG the access. Dirty-side processes
                          (investigator/verifier) run with
                          CLEANROOM_ROLE=investigator|verifier; their
                          source reads are authorized and recorded, so the
                          log is a complete, attributed record of every
                          encumbered-source access in the project.
  - match, no role     -> DENY. The sanctioned alternative (file a spec-gap)
                          goes back to the model, and the attempt is logged.

ALLOW IS EXPLICIT, ALWAYS. Antigravity's PreToolUse contract does not accept
an empty object or empty stdout as permission to proceed - a hook that stays
silent can wedge every tool call in the session. So every allow path here,
including the malformed-input path, prints {"decision": "allow"}.

And ONLY that. The allow deliberately omits Claude Code's
hookSpecificOutput.permissionDecision: "allow", which is not a no-op there -
it auto-approves the call and consumes the user's permission prompt. Deny
broadcasts to every dialect because withholding permission is safe to
repeat; allow does not, because granting it is not. Keep that asymmetry if
you edit this.

DENY is emitted three ways at once - {"decision": "deny", "reason": ...} on
stdout, the reason on stderr, and exit code 2 - because Antigravity honors
the decision object and treats a non-zero exit as a block, while other
harnesses read only one of the two. Exit 2 is the default because it fails
closed; set CLEANROOM_BLOCK_EXIT_CODE=0 if a build objects to it.

Antigravity nests the call as {"toolCall": {"name": ..., "args": {...}}} and
names arguments in PascalCase (run_command takes CommandLine, Cwd). Tool
vocabularies differ between builds and harnesses, so nothing here is keyed on
a tool-name table: targets are found by ARGUMENT KEY, case-folded. Path-ish
and command-ish keys are matched against the full policy, every other key
against URLs and checkout roots only. An unrecognized tool is still checked.

Project dir: $CLEANROOM_PROJECT_DIR, then the event's `workspacePaths[0]` /
`cwd`, then legacy $GEMINI_PROJECT_DIR / $CLAUDE_PROJECT_DIR, then the
working directory walked up to the nearest harness config dir.

Policy: $CLEANROOM_POLICY, then <project>/{.agents,.agent,.gemini,.claude}/
cleanroom-policy.json, then built-in defaults.

FIREWALL BY NAME (LS-R18). Independently of the policy file, the implementer is
denied the dirty-side skills (board-expert, hardware-investigator,
cleanroom-investigator) and the GPL spec repository (hardware-specs-gpl),
however installed: plugin cache, linked checkout, symlink, a clone under any
directory. The names are built into this script, so a workspace policy that
omits them cannot switch the firewall off; a policy may ADD names under
"blocked_names". Matching is by NAME, case-folded, over the target text and,
where the filesystem is visible, over what the target resolves to (symlinks,
"..", globs, variables, "cd" then a relative read, a recursive search rooted
above a blocked directory). hardware-specs-docs and hardware-specs-permissive
are allowed to the implementer by design. See the limits listed in the
cleanroom-implementer skill: a shell can always build a name this script
cannot see, which is what the sandbox tier is for.

Written/edited CONTENT is deliberately not scanned (a doc comment mentioning
"trusted-firmware-a" must not block the edit); content-level leaks are the
job of session_audit.py and the pre-merge output scan.

Never breaks the session on malformed JSON or a logging failure (those allow). A
cap overrun or an error while checking denies the implementer (fail closed).
"""

import fnmatch
import glob
import itertools
import json
import os
import re
import shlex
import sys
import time
import urllib.parse

DEFAULT_POLICY = {
    "checkout_roots": [
        "~/src/linux", "~/linux", "~/src/u-boot",
        "~/src/arm-trusted-firmware", "~/src/trusted-firmware-a",
    ],
    "blocked_path_patterns": [
        "/linux/drivers/", "/linux/arch/", "/linux/include/",
        "/linux/kernel/", "/linux/sound/", "/linux/net/", "/linux/block/",
        "/linux/fs/", "/linux/mm/", "linux.git", "linux-stable",
        "linux-next", "/u-boot/", "u-boot.git", "arm-trusted-firmware",
        "trusted-firmware-a", "/optee", "raspberrypi/linux",
    ],
    "blocked_url_patterns": [
        "kernel.org", "bootlin.com", "kernel.googlesource.com",
        "android.googlesource.com/kernel", "github.com/torvalds",
        "github.com/raspberrypi/linux", "github.com/u-boot",
        "github.com/ARM-software/arm-trusted-firmware", "source.denx.de",
        "git.trustedfirmware.org", "review.trustedfirmware.org",
        "sources.debian.org/src/linux",
    ],
    "blocked_names": [],
    "authorized_roles": ["investigator", "verifier"],
    "log_file": "docs/provenance/hook-blocks.jsonl",
    "gap_hint": "docs/spec-gaps/<device>.md",
}

# LS-R18: names the implementer may never read, built in on purpose (see the
# module docstring). The policy's "blocked_names" only adds to these.
FIREWALL_NAMES = (
    "board-expert", "hardware-investigator", "cleanroom-investigator",
    "hardware-specs-gpl",
)

# Keys whose value is a working directory: a base for relative paths, not a
# directory being searched.
CWD_KEYS = {"cwd", "workdir", "workingdirectory"}

# Commands that do not read the contents of a directory argument. Every other
# command that is handed an existing directory is treated as able to read
# everything under it. Names are still checked for these.
NO_SCAN_COMMANDS = {
    "ls", "cd", "pushd", "popd", "pwd", "echo", "printf", "mkdir", "test",
    "[", "stat", "true", "false", "export", "unset",
    # Build tools take "." as a project argument all the time; they run
    # workspace-controlled files, a documented limit. git is handled by
    # git: every subcommand scans except those in GIT_NO_SCAN below.
    "cargo", "make", "git",
}

# git subcommands that do not print file or history content. Every other
# subcommand, including an unknown one or a user alias, scans the working
# directory like a recursive search: fail closed, since `log -p`, `show`,
# `archive`, `reflog -p`, `notes show` and aliases all read content.
GIT_NO_SCAN = {
    "status", "add", "commit", "fetch", "push", "pull", "init", "config",
    "remote", "branch", "tag", "rev-parse", "mv", "rm", "worktree",
}

# git global options that take a separate argument (`git -C dir log`).
GIT_ARG_OPTIONS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}


def _git_subcommand(words):
    """The subcommand of a `git ...` word list, or None when there is none."""
    skip = False
    for word in words[1:]:
        if skip:
            skip = False
            continue
        if word in GIT_ARG_OPTIONS:
            skip = True
            continue
        if word.startswith("-"):
            continue
        return word.lower()
    return None

# Recursive search tools: with no path argument they read the working
# directory.
SEARCH_TOOLS = {"grep", "egrep", "fgrep", "rg", "ag", "ack", "find", "fd",
                "fdfind", "tree", "locate"}

# Bound on filesystem work per tool call: a hook must stay fast.
# SCAN_DEPTH is a documented limit (deeper than that is not looked at). The
# other caps FAIL CLOSED: when one truncates what the firewall can check, the
# implementer is denied and told to narrow the call (_LimitExceeded).
SCAN_DEPTH = 4
SCAN_ENTRIES = 3000
GLOB_NAMES = 5000
BRACE_RESULTS = 32
NESTING = 3

# Argument keys that mark a tool call as a search over files. A call with
# one of these and no path of its own reads the working directory.
SEARCH_ARG_KEYS = {"pattern", "query", "regex", "glob", "search", "searchterm",
                   "search_term", "q", "include", "includes"}


class _LimitExceeded(Exception):
    """A cap truncated what the firewall can check; the call is denied."""

# Harness config directories, in policy-resolution order: Antigravity
# workspace, Antigravity rules, shared ~/.gemini layout, Claude Code.
CONFIG_DIRS = (".agents", ".agent", ".gemini", ".claude")

# Argument keys whose values are filesystem paths. Keys are compared
# case-folded, which is what makes Antigravity's PascalCase (TargetFile,
# AbsolutePath, Cwd) and snake_case tool vocabularies land in one set.
PATH_KEYS = {
    "file_path", "filepath", "absolute_path", "absolutepath", "path",
    "paths", "dir_path", "dirpath", "directory", "directorypath",
    "notebook_path", "target_file", "targetfile", "file", "files",
    "relative_path", "relativepath", "relativefilepath", "search_directory",
    "searchdirectory", "root", "cwd", "workdir", "workingdirectory",
}

# Argument keys whose values are shell command lines.
COMMAND_KEYS = {
    "command", "commands", "commandline", "command_line", "cmd", "script",
    "shell_command", "safe_to_autorun_command",
}

# Argument keys carrying authored text. NEVER matched: blocking an edit
# because its prose names a forbidden project is a false positive, and
# content-level leaks belong to session_audit.py and the output scan.
CONTENT_KEYS = {
    "content", "contents", "text", "body", "old_string", "new_string",
    "old_str", "new_str", "codeedit", "code_edit", "replacement", "patch",
    "diff", "instruction", "message", "summary", "explanation",
}

ALLOW = {"decision": "allow"}


def _find_root(start):
    """Walk up from `start` to the nearest harness config dir (or .git)."""
    cur = os.path.abspath(start)
    while True:
        for marker in CONFIG_DIRS + (".git",):
            if os.path.isdir(os.path.join(cur, marker)):
                return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return os.path.abspath(start)
        cur = parent


def project_dir(cwd_hint=None):
    explicit = os.environ.get("CLEANROOM_PROJECT_DIR")
    if explicit:
        return explicit
    if cwd_hint:
        return _find_root(cwd_hint)
    for var in ("GEMINI_PROJECT_DIR", "CLAUDE_PROJECT_DIR"):
        val = os.environ.get(var)
        if val:
            return val
    return _find_root(os.getcwd())


LIST_KEYS = ("checkout_roots", "blocked_path_patterns", "blocked_url_patterns",
             "blocked_names", "authorized_roles")


def _sanitize(pol):
    """Keep a malformed workspace policy from crashing the hook or opening it.

    The implementer can write a workspace policy file. A list key that is not
    a list of strings falls back to the built-in default (a crash would exit 1,
    which is not a block on every harness), and a blank entry in
    authorized_roles is dropped: the unset role is the empty string, so a
    blank entry would authorize every implementer.
    """
    for key in LIST_KEYS:
        val = pol.get(key)
        if not isinstance(val, list) or not all(isinstance(v, str)
                                                for v in val):
            pol[key] = list(DEFAULT_POLICY[key])
    pol["authorized_roles"] = [r.strip().lower() for r in
                               pol["authorized_roles"] if r.strip()]
    return pol


def load_policy(cwd_hint=None):
    root = project_dir(cwd_hint)
    candidates = [os.environ.get("CLEANROOM_POLICY")]
    for cfg in CONFIG_DIRS:
        candidates.append(os.path.join(root, cfg, "cleanroom-policy.json"))
    for cfg in CONFIG_DIRS:
        candidates.append(os.path.join(cfg, "cleanroom-policy.json"))
    for cand in candidates:
        if cand and os.path.isfile(cand):
            try:
                with open(cand, encoding="utf-8") as f:
                    pol = dict(DEFAULT_POLICY)
                    pol.update(json.load(f))
                    return _sanitize(pol)
            except Exception:
                pass
    return _sanitize(dict(DEFAULT_POLICY))


def norm(s):
    return str(s).lower().replace("\\", "/")


def match(text, pol, use_paths=True, use_urls=True, use_roots=True):
    """Return the matched pattern label, or None."""
    t = norm(text)
    if not t:
        return None
    if use_roots:
        for root in pol.get("checkout_roots", []):
            r = norm(os.path.expanduser(root)).rstrip("/")
            if r and r in t:
                return f"checkout_root:{root}"
    if use_paths:
        for p in pol.get("blocked_path_patterns", []):
            if norm(p) in t:
                return f"path:{p}"
    if use_urls:
        for u in pol.get("blocked_url_patterns", []):
            if norm(u) in t:
                return f"url:{u}"
    return None


def _firewall_names(pol):
    extra = pol.get("blocked_names") or []
    if not isinstance(extra, list):
        extra = []
    return FIREWALL_NAMES + tuple(norm(n) for n in extra if n)


def _name_in(text, names):
    """First firewalled name in `text` (case-folded, URL-decoded), or None."""
    t = norm(text)
    forms = [t]
    if "%" in t:
        forms.append(norm(urllib.parse.unquote(t)))
    for form in forms:
        for n in names:
            if n in form:
                return n
    return None


def _expand_vars(text, env):
    def sub(m):
        key = m.group(1) or m.group(2)
        if key in env:
            return env[key]
        return os.environ.get(key, m.group(0))
    return re.sub(r"\$(?:(\w+)|\{(\w+)\})", sub, text)


def _braces(word):
    """Expand one level of {a,b} groups, bounded; the word itself if none."""
    out = [word]
    for _ in range(3):
        nxt = []
        changed = False
        for w in out:
            m = re.search(r"\{([^{}]*,[^{}]*)\}", w)
            if not m:
                nxt.append(w)
                continue
            changed = True
            for alt in m.group(1).split(","):
                nxt.append(w[:m.start()] + alt + w[m.end():])
        if len(nxt) > BRACE_RESULTS:
            raise _LimitExceeded("brace expansion")
        out = nxt
        if not changed:
            return out
    # Groups were still being expanded when the rounds ran out: what is left
    # is not the word the shell builds.
    if any(re.search(r"\{[^{}]*,[^{}]*\}", w) for w in out):
        raise _LimitExceeded("brace expansion")
    return out


class _Scan:
    """Shared filesystem budget for one tool call."""

    def __init__(self):
        self.entries = SCAN_ENTRIES
        # Set while checking a git content-reading command: git's own
        # object store holds hashes, not the working tree it versions.
        self.skip_git = False


def _scan_dir(root, names, budget):
    """Find a firewalled name under `root`, to a bounded depth and size.

    Looks at entry names and at where symlinks point; does not descend
    through symlinks. Returns the name or None. Raises _LimitExceeded when the
    entry budget runs out (the depth limit is a documented limit instead).
    """
    stack = [(root, 0)]
    while stack:
        cur, level = stack.pop()
        try:
            entries = os.listdir(cur)
        except OSError:
            continue
        for entry in entries:
            budget.entries -= 1
            if budget.entries < 0:
                raise _LimitExceeded("directory scan")
            full = os.path.join(cur, entry)
            hit = _name_in(entry, names)
            if hit:
                return hit
            if budget.skip_git and entry == ".git":
                continue
            if os.path.islink(full):
                hit = _name_in(os.path.realpath(full), names)
                if hit:
                    return hit
            elif level < SCAN_DEPTH and os.path.isdir(full):
                stack.append((full, level + 1))
    return None


def _glob_component_hit(token, names):
    """A glob component that could only mean a firewalled name.

    Requires three literal characters so that "*" or "b*" does not block
    every listing; those are caught instead by expanding on disk.
    """
    for comp in norm(token).split("/"):
        if not any(c in comp for c in "*?["):
            continue
        if len([c for c in comp if c not in "*?[]"]) < 3:
            continue
        for n in names:
            if fnmatch.fnmatchcase(n, comp):
                return n
    return None


def _check_token(token, names, base, env, scan, budget):
    """Check one path-like token. Returns (hit_name_or_None, exists)."""
    tok = _expand_vars(token, env)
    tok = os.path.expanduser(tok)
    if tok.startswith("file://"):
        tok = tok[len("file://"):]
    hit = _name_in(tok, names)
    if not hit and base is None:
        # No filesystem to expand against: a glob that could only mean a
        # firewalled name is judged by its pattern. With a filesystem the
        # expansion below decides, so "hardware-specs-*" still reads the
        # allowed sibling repositories.
        hit = _glob_component_hit(tok, names)
    if hit or base is None or not tok:
        return hit, False
    if "%" in tok:
        tok = urllib.parse.unquote(tok)
    full = tok if os.path.isabs(tok) else os.path.join(base, tok)
    if any(c in tok for c in "*?["):
        cands = sorted(itertools.islice(glob.iglob(full), GLOB_NAMES + 1))
        if len(cands) > GLOB_NAMES:
            raise _LimitExceeded("glob expansion")
        for cand in cands:
            hit = _name_in(cand, names)
            if hit:
                return hit, True
    else:
        cands = [full]
    exists = False
    for cand in cands:
        if not os.path.lexists(cand):
            continue
        exists = True
        real = os.path.realpath(cand)
        hit = _name_in(real, names)
        if hit:
            return hit, True
        if scan and os.path.isdir(real):
            hit = _scan_dir(real, names, budget)
            if hit:
                return hit, True
    return None, exists


def _segments(command):
    """Split a command line into segments of shell words.

    Quotes, backslashes and $( ) / backtick boundaries are handled by the
    tokenizer, so a name split by quotes or an escape comes out whole.
    """
    text = command.replace("\n", " ; ").replace("`", " ; ")
    try:
        lex = shlex.shlex(text, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        lex.commenters = ""  # a mid-word # is not a comment to the shell
        words = list(lex)
    except ValueError:
        words = re.split(r"[\s'\"]+", text)
    segs, cur = [], []
    for w in words:
        if w and all(c in ";&|()" for c in w):
            if cur:
                segs.append(cur)
            cur = []
        elif w and all(c in "<>" for c in w):
            continue
        elif w:
            cur.append(w)
    if cur:
        segs.append(cur)
    return segs


ASSIGN_BUILTINS = {"export", "declare", "local", "readonly", "typeset"}


def _record_assignments(words, env):
    """Record leading NAME=value words, also after export/declare/etc.

    Returns the words left once the assignments (and the builtin that
    introduced them) are consumed.
    """
    while words:
        if re.match(r"[A-Za-z_]\w*=", words[0]):
            key, _, val = words[0].partition("=")
            env[key] = _expand_vars(val, env)
            words = words[1:]
        elif (os.path.basename(words[0]) in ASSIGN_BUILTINS and
              len(words) > 1):
            words = words[1:]
            while words and words[0].startswith("-"):
                words = words[1:]
        else:
            break
    return words


def _firewall_command(command, names, base, env, budget, depth=0):
    hit = _name_in(command, names)
    if hit:
        return hit
    cur = base
    for words in _segments(command):
        words = _record_assignments(words, env)
        if not words:
            continue
        head = os.path.basename(words[0]).lower()
        searches = any(os.path.basename(w).lower() in SEARCH_TOOLS
                       for w in words)
        git_read = (head == "git" and
                    _git_subcommand(words) not in GIT_NO_SCAN)
        scan = head not in NO_SCAN_COMMANDS or searches or git_read
        budget.skip_git = git_read and not searches
        any_exists = False
        for word in words:
            for variant in _braces(word):
                pieces = [variant]
                if variant.startswith("-") and "=" in variant:
                    pieces = [variant.partition("=")[2]]
                elif variant.startswith("-"):
                    continue
                for piece in pieces:
                    if re.search(r"[\s;|&]|\$\(", piece):
                        if depth >= NESTING:
                            raise _LimitExceeded("nested shell strings")
                        hit = _firewall_command(piece, names, cur, env,
                                                budget, depth + 1)
                        if hit:
                            return hit
                    hit, exists = _check_token(
                        piece, names, cur, env, scan, budget)
                    if hit:
                        return hit
                    any_exists = any_exists or (
                        exists and piece is not words[0])
        if head in ("cd", "pushd") and cur is not None and len(words) > 1:
            target = os.path.expanduser(_expand_vars(words[1], env))
            full = target if os.path.isabs(target) else os.path.join(
                cur, target)
            if os.path.isdir(full):
                cur = os.path.realpath(full)
        elif (searches or git_read) and not any_exists and cur is not None:
            hit = _scan_dir(cur, names, budget)
            if hit:
                return hit
        budget.skip_git = False
    return None


def firewall_hit(key, text, pol, base=None, scan_dirs=True, budget=None):
    """Name-based firewall check for one argument. Returns 'name:<n>' or None.

    `base` is the directory relative paths resolve against; None means the
    filesystem is not consulted (the audit of a record from another machine).
    Path keys and command keys get the full treatment; any other key is
    matched by name, which is what stops the Skill tool, a subagent prompt and
    a repository argument from naming a firewalled target. A short value with
    no whitespace under such a key is also resolved on disk like a path
    (symlinks, realpath), without scanning below it, unless the key is a
    search expression (a pattern is not a path).
    """
    names = _firewall_names(pol)
    budget = budget or _Scan()
    if key in COMMAND_KEYS:
        hit = _firewall_command(text, names, base, {}, budget)
    elif key in PATH_KEYS:
        hit, _ = _check_token(text, names, base, {},
                              scan_dirs and key not in CWD_KEYS, budget)
    else:
        hit = _name_in(text, names)
        if (not hit and base is not None and len(text) < 1024 and
                key not in SEARCH_ARG_KEYS and not re.search(r"\s", text)):
            # An argument of a tool the hook has no table for may still be a
            # path (a symlink to a firewalled directory, say): resolve it the
            # way a path key is, without scanning below it.
            hit, _ = _check_token(text, names, base, {}, False, budget)
    return f"name:{hit}" if hit else None


def _strings(node, key=None):
    """Yield (case-folded key, string) for every string leaf in a tree."""
    if isinstance(node, str):
        yield key, node
    elif isinstance(node, dict):
        for k, v in node.items():
            yield from _strings(v, str(k).lower())
    elif isinstance(node, (list, tuple)):
        for v in node:
            yield from _strings(v, key)


def pick_target(tool, tool_input, pol, cwd=None):
    """Return (target_text, matched_pattern_or_None) for this tool call.

    Keyed on argument names, not tool names, so one policy covers
    Antigravity's vocabulary (and PascalCase), MCP tools, and whatever a
    future build renames.

    `cwd` is the directory the call runs in. With it, the firewall also
    follows symlinks, globs and relative reads on disk; without it (the
    session audit) it matches names in the text only.
    """
    base = cwd
    if base is not None:
        for key, text in _strings(tool_input):
            if key in CWD_KEYS and text:
                full = os.path.expanduser(text)
                if not os.path.isabs(full):
                    full = os.path.join(base, full)
                if os.path.isdir(full):
                    base = os.path.realpath(full)
                    hit = _name_in(base, _firewall_names(pol))
                    if hit:
                        return text, f"name:{hit}"
                break
    budget = _Scan()
    first = ""
    try:
        has_path = searches = False
        for key, text in _strings(tool_input):
            if not text:
                continue
            if not first:
                first = text
            if key in CONTENT_KEYS:
                continue
            if key in PATH_KEYS or key in COMMAND_KEYS:
                hit = match(text, pol)
                has_path = has_path or (key not in CWD_KEYS)
            else:
                # Unknown keys (search queries, prompts carrying URLs, MCP
                # arguments): URLs and checkout roots only. Path patterns
                # over arbitrary prose would false-positive.
                hit = match(text, pol, use_paths=False)
                searches = searches or key in SEARCH_ARG_KEYS
            hit = hit or firewall_hit(key, text, pol, base, budget=budget)
            if hit:
                return text, hit
        if searches and not has_path and base is not None:
            # Grep/Glob style call with a pattern and no path: it reads the
            # working directory, exactly as a bare `grep -r pat` does.
            hit = _scan_dir(base, _firewall_names(pol), budget)
            if hit:
                return first, f"name:{hit}"
    except _LimitExceeded as exc:
        return first, f"limit:{exc}"
    return first, None


def log_entry(pol, entry, cwd_hint=None):
    try:
        path = pol.get("log_file", DEFAULT_POLICY["log_file"])
        if not os.path.isabs(path):
            path = os.path.join(project_dir(cwd_hint), path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass  # logging is best-effort; never break the session


def allow():
    """Antigravity needs an explicit allow; silence can wedge the session."""
    sys.stdout.write(json.dumps(ALLOW))
    sys.exit(0)


def deny(reason):
    """Emit a deny in every dialect at once, then exit fail-closed."""
    payload = {
        "decision": "deny",           # Antigravity
        "reason": reason,
        "continue": True,             # block this call, not the session
        "systemMessage": "cleanroom: encumbered-source access blocked",
        "hookSpecificOutput": {       # Claude Code
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        },
    }
    sys.stdout.write(json.dumps(payload))
    sys.stderr.write(reason + "\n")
    try:
        code = int(os.environ.get("CLEANROOM_BLOCK_EXIT_CODE", "2"))
    except ValueError:
        code = 2
    sys.exit(code)


def parse_event(data):
    """Return (tool_name, tool_args, cwd_hint, session_id, extra_paths).

    Antigravity nests the call under `toolCall` and reports the workspace in
    `workspacePaths`; flat `tool_name`/`tool_input` payloads are accepted too
    so the same hook keeps working on other harnesses.
    """
    call = data.get("toolCall")
    if not isinstance(call, dict):
        call = data
    tool = ""
    for key in ("name", "tool_name", "toolName", "tool"):
        if isinstance(call.get(key), str) and call[key]:
            tool = call[key]
            break
    args = None
    for key in ("args", "arguments", "tool_input", "toolInput", "input",
                "parameters"):
        if key in call:
            args = call[key]
            break
    if args is None:
        args = {}

    cwd_hint = None
    paths = data.get("workspacePaths")
    if isinstance(paths, list) and paths and isinstance(paths[0], str):
        cwd_hint = paths[0]
    cwd_hint = cwd_hint or data.get("cwd") or None

    session = (data.get("conversationId") or data.get("session_id")
               or data.get("sessionId") or "")

    # Where this session's own record lives - worth logging, because the
    # pre-merge audit has to find it later.
    extra = {}
    for src, dst in (("transcriptPath", "transcript"),
                     ("transcript_path", "transcript"),
                     ("artifactDirectoryPath", "artifacts")):
        val = data.get(src)
        if isinstance(val, str) and val and dst not in extra:
            extra[dst] = val
    return tool, args, cwd_hint, session, extra


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        allow()
    if not isinstance(data, dict):
        allow()
    tool, args, cwd_hint, session, extra = "", {}, None, "", {}
    pol = None
    try:
        tool, args, cwd_hint, session, extra = parse_event(data)
        pol = load_policy(cwd_hint)
        target, hit = pick_target(tool, args, pol,
                                  cwd=cwd_hint or os.getcwd())
    except Exception as exc:  # fail closed: an unreadable call is not allowed
        target, hit = "", f"error:internal error ({type(exc).__name__})"
        if pol is None:
            pol = _sanitize(dict(DEFAULT_POLICY))
    if not hit:
        allow()

    role = os.environ.get("CLEANROOM_ROLE", "").strip().lower()
    authorized = role in [r.lower() for r in pol.get("authorized_roles", [])]
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "session_id": session,
        "cwd": cwd_hint or os.getcwd(),
        "tool": tool,
        "pattern": hit,
        "target": target[:300],
        "role": role or None,
        "action": "allowed-role" if authorized else "blocked",
    }
    entry.update(extra)
    unverified = hit.startswith(("limit:", "error:"))
    if authorized and unverified:
        allow()  # nothing encumbered was named: not an access to log
    log_entry(pol, entry, cwd_hint)
    if authorized:
        allow()

    if hit.startswith("error:"):
        deny(
            f"cleanroom: BLOCKED {tool} - the firewall hit an "
            f"{hit[len('error:'):]} and cannot verify this call, so it is "
            f"denied. Retry; if it repeats, report it (the hook has a bug). "
            f"This attempt was logged.")
    if hit.startswith("limit:"):
        deny(
            f"cleanroom: BLOCKED {tool} - {hit[len('limit:'):]} is too broad "
            f"for the firewall to verify. Give a narrower path (a specific "
            f"directory or file in your workspace) and try again. This "
            f"attempt was logged.")
    what = ("Encumbered source (Linux/U-Boot/TF-A/vendor firmware), the "
            "dirty-side skills (board-expert, hardware-investigator, "
            "cleanroom-investigator) and the GPL spec repository "
            "(hardware-specs-gpl) are")
    deny(
        f"cleanroom: BLOCKED {tool} - target matches '{hit}'. {what} "
        f"off-limits in "
        f"implementation sessions. If the spec is insufficient, append the "
        f"question to {pol.get('gap_hint')} as '- [open] <date> <section> "
        f"<question>', mark the code site TODO(spec-gap), and continue with "
        f"other work. This attempt was logged.")


if __name__ == "__main__":
    main()
