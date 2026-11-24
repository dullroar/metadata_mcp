#!/usr/bin/env python3
"""Find secrets and forbidden files in staged blobs, commit ranges, tracked files or history.

Run me when: before a commit or a push (the hooks do it), in CI, before a merge, or to audit a repository for secrets.

Usage:
  secret_guard.py --staged              # pre-commit: the staged blobs
  secret_guard.py --range A..B          # every added line in every commit of the range
  secret_guard.py --new-ref SHA         # the commits of SHA that are on no remote branch (pre-push, new branch)
  secret_guard.py --tracked             # every tracked file at HEAD
  secret_guard.py --history             # every added line in all history (git log --all -p)
  secret_guard.py --paths FILE...       # the given files
Options: --root DIR (default: the Git top level), --format text|json.

Exit codes: 0 clean, 1 findings, 2 error (not a Git repository, a bad range, an unreadable file).

Exceptions:
- A line that contains "secret-guard: allow <reason>" is not a finding. The reason is required.
- The file .secret-guard-allow in the root has one exception on each line:
  "<fingerprint>  <path>  <reason>". The fingerprint is the SHA-256 hex digest of
  the UTF-8 bytes of "<path>" + NUL + "<matched text>". Each finding prints its fingerprint.

The generic assignment rule needs a value of 16 or more characters with an entropy of 3.5 or
more bits for each character. It ignores values that look like identifiers (letters, "_" and
"." with at most one digit), code (brackets) and file paths.

The output never contains a secret. It shows the first 4 characters, then "…", then the length.
A binary file (a NUL byte in the first 8 KiB) gets only the file-name check and is reported as
unscanned. Only the first 5 MiB of a text file are scanned; the rest is reported as unscanned.
In --range and --history modes, the guard reads the diff of each commit that is not a merge.
The commits that a merge brings in are scanned one by one. Standard library only. No network.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

ALLOW_FILE = ".secret-guard-allow"
BINARY_PROBE = 8 * 1024
MAX_SCAN = 5 * 1024 * 1024
GIT_LOG = ["-c", "core.quotepath=off", "log", "-p", "-U0", "--no-color", "--no-ext-diff",
           "--no-textconv", "--no-renames", "--submodule=short", "--format=%x01%H"]

INLINE_ALLOW = re.compile(r"secret-guard:\s*allow\b(.*)")
PLACEHOLDER_WORDS = ("example", "placeholder", "changeme", "dummy", "xxxx", "****")

# Each rule: (rule ID, regex, capture group of the secret value; 0 is the full match).
TOKEN_RULES: list[tuple[str, re.Pattern[str], int]] = [
    ("private-key", re.compile(r"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY(?: BLOCK)?-----"), 0),
    ("anthropic-key", re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{20,}"), 0),
    ("openai-key", re.compile(r"\bsk-(?!ant-)(?:proj-)?[A-Za-z0-9_\-]{20,}"), 0),
    ("github-token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}"), 0),
    ("github-pat", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{22,}"), 0),
    ("aws-access-key-id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), 0),
    ("aws-secret-key", re.compile(r"(?i)aws_secret_access_key[\"']?\s*[:=]\s*[\"']?([A-Za-z0-9/+=]{40})"), 1),
    ("google-api-key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}"), 0),
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}"), 0),
    ("slack-webhook", re.compile(r"https://hooks\.slack\.com/services/[A-Za-z0-9_]+/[A-Za-z0-9_]+/[A-Za-z0-9_]+"), 0),
    ("stripe-key", re.compile(r"\b(?:sk|rk)_live_[A-Za-z0-9]{16,}"), 0),
    ("huggingface-token", re.compile(r"\bhf_[A-Za-z0-9]{30,}"), 0),
    ("sendgrid-key", re.compile(r"\bSG\.[A-Za-z0-9_\-]{16,}\.[A-Za-z0-9_\-]{16,}"), 0),
    ("npm-auth-token", re.compile(r"_auth(?:Token)?\s*=\s*[\"']?([^\s\"']+)"), 1),
    ("pypi-token", re.compile(r"\bpypi-[A-Za-z0-9_\-]{50,}"), 0),
    ("azure-key", re.compile(r"\b(?:AccountKey|SharedAccessKey)=([^;\s\"'<>]{16,})"), 1),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"), 0),
    ("url-credential", re.compile(r"\b[A-Za-z][A-Za-z0-9+.\-]*://[^/\s:@\"'<>]+:([^/\s@\"'<>]+)@[^\s/\"'<>]+"), 1),
]
GENERIC_KEYS = r"password|passwd|pwd|secret|token|api_key|apikey|access_key|client_secret|private_key"
GENERIC_RULE = re.compile(
    r"(?i)(?<![A-Za-z0-9])[\w.\-]*(?:" + GENERIC_KEYS + r")[\w.\-]*[\"']?\s*(?::=|=>|[:=])\s*"
    r"(?P<q>[\"']?)(?P<v>[^\s\"'`,;]+)"
)
CODE_LIKE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$")
PATH_LIKE = re.compile(r"^[\w.\-]+(?:/[\w.\-]+)+/?$")

FORBIDDEN_NAMES = {"id_rsa", "id_dsa", "id_ecdsa", "id_ed25519", "credentials.json", ".netrc",
                   ".pypirc", ".git-credentials"}
FORBIDDEN_SUFFIXES = (".pem", ".key", ".p12", ".pfx", ".keystore", ".jks")
FORBIDDEN_PATHS = (".claude/settings.json", ".claude/settings.local.json", "review/canaries.key.json")


class GuardError(Exception):
    """An error that ends the run with exit code 2."""


@dataclass
class Finding:
    path: str
    line: int
    rule: str
    fingerprint: str
    redacted: str
    commit: str = ""
    note: str = ""


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list)
    unscanned: list[dict] = field(default_factory=list)
    allowed: int = 0
    scanned: int = 0


def fingerprint(path: str, match: str) -> str:
    return hashlib.sha256((path + "\0" + match).encode("utf-8")).hexdigest()


def redact(match: str) -> str:
    return f"{match[:4]}…{len(match)}"


def entropy(value: str) -> float:
    counts: dict[str, int] = {}
    for char in value:
        counts[char] = counts.get(char, 0) + 1
    total = len(value)
    return -sum(n / total * math.log2(n / total) for n in counts.values())


def is_placeholder(value: str, line: str = "", start: int = -1) -> bool:
    lowered = value.lower()
    if any(word in lowered for word in PLACEHOLDER_WORDS):
        return True
    if value.startswith(("<", "${", "{{")) or re.match(r"^\$[A-Za-z_(]", value):
        return True
    if start >= 0:
        before = line[:start]
        opened = before.rfind("<")
        if opened >= 0 and ">" not in before[opened:] and ">" in line[start:]:
            return True
        if before.endswith(("${", "$")):
            return True
    return False


def forbidden_name(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
        return True
    if name in FORBIDDEN_NAMES or name.lower().endswith(FORBIDDEN_SUFFIXES):
        return True
    if name.startswith("service-account") and name.endswith(".json"):
        return True
    return any(path == p or path.endswith("/" + p) for p in FORBIDDEN_PATHS)


class Scanner:
    def __init__(self, allow: dict[str, str]):
        self.allow = allow
        self.report = Report()

    def _add(self, path: str, line_no: int, rule: str, match: str, commit: str, line: str) -> None:
        inline = INLINE_ALLOW.search(line)
        note = ""
        if inline:
            reason = re.sub(r"(-->|\*/|#>)\s*$", "", inline.group(1)).strip()
            if reason:
                self.report.allowed += 1
                return
            note = "inline allow without a reason"
        fp = fingerprint(path, match)
        if fp in self.allow:
            self.report.allowed += 1
            return
        self.report.findings.append(Finding(path, line_no, rule, fp, redact(match), commit, note))

    def check_name(self, path: str, commit: str = "") -> None:
        if forbidden_name(path):
            self._add(path, 0, "forbidden-file", path, commit, "")

    def scan_line(self, path: str, line_no: int, line: str, commit: str = "") -> None:
        spans: list[tuple[int, int]] = []
        for rule, pattern, group in TOKEN_RULES:
            for m in pattern.finditer(line):
                value = m.group(group)
                start = m.start(group)
                if not value or is_placeholder(value, line, start) or is_placeholder(m.group(0)):
                    continue
                spans.append((start, m.end(group)))
                self._add(path, line_no, rule, value, commit, line)
        for m in GENERIC_RULE.finditer(line):
            value, start = m.group("v"), m.start("v")
            if any(s < m.end("v") and start < e for s, e in spans):
                continue
            if len(value) < 16 or entropy(value) < 3.5 or is_placeholder(value, line, start):
                continue
            digits = sum(c.isdigit() for c in value)
            if CODE_LIKE.match(value) and digits <= 1:
                continue  # an identifier or a word, such as "ReadableStreamDefaultController"
            if not m.group("q"):
                if any(c in value for c in "()[]{}") or "://" in value or value.startswith(("/", "./", "~")):
                    continue
                has_digit = digits > 0
                if PATH_LIKE.match(value) and (not has_digit or re.search(r"\.[A-Za-z]{1,5}$", value)):
                    continue
            self._add(path, line_no, "generic-secret", value, commit, line)

    def scan_blob(self, path: str, data: bytes, commit: str = "") -> None:
        self.check_name(path, commit)
        self.report.scanned += 1
        if b"\0" in data[:BINARY_PROBE]:
            self.report.unscanned.append({"path": path, "commit": commit, "reason": "binary",
                                          "bytes": len(data)})
            return
        if len(data) > MAX_SCAN:
            self.report.unscanned.append({"path": path, "commit": commit, "reason": "over 5 MiB",
                                          "bytes": len(data) - MAX_SCAN})
            data = data[:MAX_SCAN]
        text = data.decode("utf-8", errors="replace")
        for number, line in enumerate(text.split("\n"), 1):
            self.scan_line(path, number, line, commit)


def git(root: Path, args: list[str], data: bytes | None = None) -> bytes:
    proc = subprocess.run(["git", "-C", str(root), *args], input=data, capture_output=True)
    if proc.returncode != 0:
        raise GuardError(f"git {' '.join(args[:3])} failed: {proc.stderr.decode(errors='replace').strip()}")
    return proc.stdout


def find_root(given: str | None) -> Path:
    start = Path(given) if given else Path.cwd()
    if not start.is_dir():
        raise GuardError(f"not a directory: {start}")
    proc = subprocess.run(["git", "-C", str(start), "rev-parse", "--show-toplevel"],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise GuardError(f"not a Git repository: {start}")
    return Path(given).resolve() if given else Path(proc.stdout.strip())


def load_allow(root: Path) -> dict[str, str]:
    path = root / ALLOW_FILE
    allow: dict[str, str] = {}
    if not path.is_file():
        return allow
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = re.split(r"\s{2,}|\t", line, maxsplit=2)
        if len(parts) < 3 or not re.fullmatch(r"[0-9a-f]{64}", parts[0]) or not parts[2].strip():
            raise GuardError(f"{ALLOW_FILE}:{number}: need '<sha256>  <path>  <reason>'")
        allow[parts[0]] = parts[1]
    return allow


def cat_blobs(root: Path, objects: list[str]) -> list[bytes]:
    """Read many blobs with one git cat-file --batch call."""
    if not objects:
        return []
    out = git(root, ["cat-file", "--batch"], ("\n".join(objects) + "\n").encode())
    blobs, pos = [], 0
    for _ in objects:
        end = out.index(b"\n", pos)
        header = out[pos:end].split()
        if len(header) < 3:
            raise GuardError(f"cannot read object: {header[0].decode(errors='replace')}")
        size = int(header[2])
        blobs.append(out[end + 1:end + 1 + size])
        pos = end + 1 + size + 1
    return blobs


def scan_tracked(root: Path, scanner: Scanner) -> None:
    if subprocess.run(["git", "-C", str(root), "rev-parse", "--verify", "-q", "HEAD"],
                      capture_output=True).returncode != 0:
        return
    entries = []
    for item in git(root, ["ls-tree", "-r", "-z", "--full-tree", "HEAD"]).split(b"\0"):
        if not item:
            continue
        meta, path = item.split(b"\t", 1)
        mode, kind, sha = meta.split()
        name = path.decode("utf-8", errors="replace")
        if kind != b"blob":
            scanner.report.unscanned.append({"path": name, "commit": "", "reason": kind.decode(), "bytes": 0})
            continue
        entries.append((name, sha.decode()))
    for (name, _), data in zip(entries, cat_blobs(root, [sha for _, sha in entries])):
        scanner.scan_blob(name, data)


def scan_staged(root: Path, scanner: Scanner) -> None:
    out = git(root, ["diff", "--cached", "--name-only", "-z", "--diff-filter=ACMRT", "--no-renames"])
    names = [n.decode("utf-8", errors="replace") for n in out.split(b"\0") if n]
    blobs = cat_blobs(root, [":" + n for n in names])
    for name, data in zip(names, blobs):
        scanner.scan_blob(name, data)


def scan_paths(root: Path, paths: list[str], scanner: Scanner) -> None:
    for given in paths:
        path = Path(given)
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise GuardError(f"cannot read {given}: {exc.strerror}") from exc
        try:
            name = path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            name = path.as_posix()
        scanner.scan_blob(name, data)


def unquote(path: str) -> str:
    if not path.startswith('"'):
        return path
    raw = path[1:-1].encode("latin-1", errors="replace").decode("unicode_escape")
    return raw.encode("latin-1", errors="replace").decode("utf-8", errors="replace")


def header_path(line: str) -> str:
    rest = line[len("diff --git "):]
    if rest.startswith('"'):
        match = re.match(r'"((?:[^"\\]|\\.)*)" ', rest)
        first = unquote('"' + match.group(1) + '"') if match else rest
        return first[2:]
    return rest[2:2 + (len(rest) - 5) // 2]


def scan_log(root: Path, rev_args: list[str], scanner: Scanner) -> None:
    proc = subprocess.Popen(["git", "-C", str(root), *GIT_LOG, *rev_args, "--"],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.stdout is not None
    commit, path, line_no, deleted, budget = "", "", 0, False, 0
    for raw in proc.stdout:
        line = raw.decode("utf-8", errors="replace").rstrip("\n")
        if line.startswith("\x01"):
            commit, path = line[1:].strip(), ""
        elif line.startswith("diff --git "):
            path, deleted, budget = header_path(line), False, 0
            scanner.report.scanned += 1
        elif not path:
            continue
        elif line.startswith("deleted file mode"):
            deleted = True
        elif line.startswith("index "):
            if not deleted:
                scanner.check_name(path, commit)
        elif line.startswith("Binary files "):
            if not deleted:
                scanner.report.unscanned.append({"path": path, "commit": commit, "reason": "binary", "bytes": 0})
        elif line.startswith("@@"):
            match = re.match(r"@@ -\S+ \+(\d+)", line)
            line_no = int(match.group(1)) if match else 0
        elif line.startswith("+"):
            budget += len(raw)
            if budget > MAX_SCAN:
                if budget - len(raw) <= MAX_SCAN:
                    scanner.report.unscanned.append({"path": path, "commit": commit,
                                                     "reason": "over 5 MiB", "bytes": 0})
            else:
                scanner.scan_line(path, line_no, line[1:], commit)
            line_no += 1
        elif line.startswith(" "):
            line_no += 1
    proc.wait()
    if proc.returncode != 0:
        assert proc.stderr is not None
        raise GuardError(f"git log failed: {proc.stderr.read().decode(errors='replace').strip()}")


def verify_rev(root: Path, rev: str) -> None:
    if not rev or subprocess.run(["git", "-C", str(root), "rev-parse", "--verify", "-q", rev + "^{commit}"],
                                 capture_output=True).returncode != 0:
        raise GuardError(f"bad revision: {rev!r}")


def range_args(root: Path, spec: str) -> list[str]:
    if "..." in spec or ".." not in spec:
        raise GuardError(f"bad range: {spec!r} (use A..B)")
    base, head = spec.split("..", 1)
    verify_rev(root, base)
    verify_rev(root, head)
    return [f"{base}..{head}"]


def print_report(report: Report, fmt: str, mode: str) -> None:
    if fmt == "json":
        print(json.dumps({"mode": mode, "findings": [asdict(f) for f in report.findings],
                          "unscanned": report.unscanned, "allowed": report.allowed,
                          "scanned": report.scanned, "count": len(report.findings)}, indent=2))
        return
    for item in report.unscanned:
        where = f" in {item['commit'][:12]}" if item["commit"] else ""
        print(f"note: unscanned {item['path']}{where}: {item['reason']}", file=sys.stderr)
    for f in report.findings:
        where = f"{f.commit[:12]}:" if f.commit else ""
        note = f" ({f.note})" if f.note else ""
        print(f"{where}{f.path}:{f.line}: {f.rule} {f.redacted} fingerprint={f.fingerprint}{note}")
    print(f"secret-guard {mode}: {len(report.findings)} finding(s), {report.allowed} allowed, "
          f"{len(report.unscanned)} unscanned", file=sys.stderr)
    if report.findings:
        print(f"To accept a reviewed false positive, add '<fingerprint>  <path>  <reason>' to {ALLOW_FILE}.",
              file=sys.stderr)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Find secrets and forbidden files.")
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--staged", action="store_true")
    modes.add_argument("--range", metavar="A..B")
    modes.add_argument("--new-ref", metavar="SHA")
    modes.add_argument("--tracked", action="store_true")
    modes.add_argument("--history", action="store_true")
    modes.add_argument("--paths", nargs="+", metavar="FILE")
    parser.add_argument("--root")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)

    root = find_root(args.root)
    scanner = Scanner(load_allow(root))
    if args.staged:
        mode = "staged"
        scan_staged(root, scanner)
    elif args.range:
        mode = "range"
        scan_log(root, range_args(root, args.range), scanner)
    elif args.new_ref:
        mode = "new-ref"
        verify_rev(root, args.new_ref)
        scan_log(root, [args.new_ref, "--not", "--remotes"], scanner)
    elif args.tracked:
        mode = "tracked"
        scan_tracked(root, scanner)
    elif args.history:
        mode = "history"
        scan_log(root, ["--all"], scanner)
    else:
        mode = "paths"
        scan_paths(root, args.paths, scanner)
    print_report(scanner.report, args.format, mode)
    return 1 if scanner.report.findings else 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except GuardError as exc:
        print(f"secret-guard: error: {exc}", file=sys.stderr)
        sys.exit(2)
    except Exception as exc:  # noqa: BLE001 - never exit 0 after an unexpected exception
        print(f"secret-guard: error: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(2)
