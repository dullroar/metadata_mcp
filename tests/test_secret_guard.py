#!/usr/bin/env python3
"""Tests for scripts/secret_guard.py. Usage: python3 tests/test_secret_guard.py

Every synthetic secret is built at run time from parts. This file holds no literal secret,
so the guard does not find its own tests.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

GUARD = Path(__file__).resolve().parent.parent / "scripts" / "secret_guard.py"
ENV = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
       "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@example.invalid",
       "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@example.invalid"}


def mix(n: int, alphabet: str = "aZ3kQ9mX7pL2wR5t") -> str:
    """A high-entropy string of length n with no placeholder words."""
    return (alphabet * (n // len(alphabet) + 1))[:n]


def J(*parts: str) -> str:
    return "".join(parts)


# One synthetic sample for each content rule. The key is the expected rule ID.
SAMPLES = {
    "private-key": J("-----BEGIN ", "RSA ", "PRIVATE KEY-----"),
    "anthropic-key": J("sk-", "ant-", mix(40)),
    "openai-key": J("sk-", "proj-", mix(40)),
    "github-token": J("gh", "p_", mix(36)),
    "github-pat": J("github", "_pat_", mix(40)),
    "aws-access-key-id": J("AK", "IA", "QZ7K3M9X2W5R8T4N"),
    "aws-secret-key": J("aws_secret", "_access_key = ", mix(40, "aZ3k/Q9m+X7pL2wR")),
    "google-api-key": J("AI", "za", mix(35)),
    "slack-token": J("xo", "xb-", mix(30)),
    "slack-webhook": J("https://hooks.", "slack.com/services/", "T0ABC/", "B0DEF/", mix(24)),
    "stripe-key": J("sk", "_live_", mix(24)),
    "huggingface-token": J("h", "f_", mix(34)),
    "sendgrid-key": J("S", "G.", mix(22), ".", mix(43)),
    "npm-auth-token": J("//registry.npmjs.org/:_auth", "Token=", mix(36)),
    "pypi-token": J("py", "pi-", mix(60)),
    "azure-key": J("DefaultEndpointsProtocol=https;Account", "Key=", mix(44), ";"),
    "jwt": J("ey", "J", mix(20), ".ey", "J", mix(30), ".", mix(43)),
    "url-credential": J("postgres://", "app:", mix(18), "@db.internal:5432/x"),
    "generic-secret": J("client_", "secret = \"", mix(24), "\""),
}


class GuardCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "repo"
        self.root.mkdir()
        self.git("init", "-q", "-b", "main")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def git(self, *args: str) -> str:
        return subprocess.run(["git", "-C", str(self.root), *args], env=ENV, check=True,
                              capture_output=True, text=True).stdout.strip()

    def write(self, rel: str, content: str | bytes) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
        return path

    def commit(self, message: str = "c") -> str:
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", message)
        return self.git("rev-parse", "HEAD")

    def guard(self, *args: str) -> tuple[int, dict, str]:
        proc = subprocess.run([sys.executable, str(GUARD), "--root", str(self.root), "--format", "json", *args],
                              env=ENV, capture_output=True, text=True)
        data = json.loads(proc.stdout) if proc.stdout.strip() else {}
        return proc.returncode, data, proc.stdout + proc.stderr

    def text_guard(self, *args: str) -> tuple[int, str]:
        proc = subprocess.run([sys.executable, str(GUARD), "--root", str(self.root), *args],
                              env=ENV, capture_output=True, text=True)
        return proc.returncode, proc.stdout + proc.stderr

    def rules(self, data: dict) -> list[str]:
        return [f["rule"] for f in data.get("findings", [])]


class TestRules(GuardCase):
    def test_each_rule(self) -> None:
        for rule, sample in SAMPLES.items():
            with self.subTest(rule=rule):
                path = self.write("sample.txt", f"x {sample}\n")
                code, data, _ = self.guard("--paths", str(path))
                self.assertEqual(code, 1, rule)
                self.assertIn(rule, self.rules(data))

    def test_private_key_kinds(self) -> None:
        for kind in ("", "EC ", "DSA ", "OPENSSH ", "ENCRYPTED "):
            path = self.write("k.txt", J("-----BEGIN ", kind, "PRIVATE KEY-----\n"))
            self.assertIn("private-key", self.rules(self.guard("--paths", str(path))[1]))
        path = self.write("k.txt", J("-----BEGIN PGP ", "PRIVATE KEY BLOCK-----\n"))
        self.assertIn("private-key", self.rules(self.guard("--paths", str(path))[1]))

    def test_generic_formats(self) -> None:
        value = mix(24)
        lines = [J("pass", "word: ", value), J('{"api', '_key": "', value, '"}'), J("export TO", "KEN=", value),
                 J("[db]\npass", "wd = ", value), J("access", "_key = '", value, "'")]
        for line in lines:
            with self.subTest(line=line[:12]):
                path = self.write("config.yaml", line + "\n")
                self.assertIn("generic-secret", self.rules(self.guard("--paths", str(path))[1]))

    def test_generic_needs_length_and_entropy(self) -> None:
        for value in ("short9Xa", "a" * 30, "abababababababababab", "compute_session_from_header",
                      "scripts/check_session.py", "docs/guides/session-handling/"):
            path = self.write("c.py", J("tok", "en = ", value, "\n"))
            code, data, _ = self.guard("--paths", str(path))
            self.assertEqual(code, 0, value)
        path = self.write("c.py", J("tok", "en = make_token(request.headers)\n"))
        self.assertEqual(self.guard("--paths", str(path))[0], 0)
        path = self.write("t.jsonl", J('{"tok', 'en":"ReadableStreamDefaultController"}', "\n"))
        self.assertEqual(self.guard("--paths", str(path))[0], 0)

    def test_placeholders(self) -> None:
        lines = [
            J("pass", "word = \"<your-password-here>\""),
            J("pass", "word = \"${DB_PASSWORD}\""),
            J("pass", "word = $DB_PASSWORD_FROM_ENVIRONMENT"),
            J("api", "_key = \"", mix(10), "example", mix(10), "\""),
            J("sk-", "ant-", "placeholder", mix(30)),
            J("AK", "IA", "IOSFODNN7EXAMPLE"),
            J("tok", "en: ", "xxxx", mix(20)),
            J("sec", "ret = \"****", mix(20), "\""),
            J("pass", "word = changeme", mix(16)),
            J("tok", "en = dummy", mix(16)),
            J("postgres://", "user:<password>@host/db"),
            J("postgres://", "user:${PGPASS}@host/db"),
        ]
        for line in lines:
            with self.subTest(line=line[:16]):
                path = self.write("p.txt", line + "\n")
                code, data, _ = self.guard("--paths", str(path))
                self.assertEqual(code, 0, data)


class TestExceptions(GuardCase):
    def test_inline_allow_needs_reason(self) -> None:
        sample = SAMPLES["anthropic-key"]
        path = self.write("a.md", f"{sample} <!-- secret-guard: allow offline test sentinel -->\n")
        code, data, _ = self.guard("--paths", str(path))
        self.assertEqual((code, data["allowed"]), (0, 1))
        path = self.write("a.md", f"{sample} <!-- secret-guard: allow -->\n")
        code, data, _ = self.guard("--paths", str(path))
        self.assertEqual(code, 1)
        self.assertIn("without a reason", data["findings"][0]["note"])

    def test_fingerprint_allow(self) -> None:
        sample = SAMPLES["anthropic-key"]
        path = self.write("tests/fixture.txt", f"key {sample}\n")
        code, data, _ = self.guard("--paths", str(path))
        self.assertEqual(code, 1)
        fp = data["findings"][0]["fingerprint"]
        expected = hashlib.sha256(("tests/fixture.txt\0" + sample).encode()).hexdigest()
        self.assertEqual(fp, expected)
        self.write(".secret-guard-allow", f"# header\n{fp}  tests/fixture.txt  offline test sentinel\n")
        code, data, _ = self.guard("--paths", str(path))
        self.assertEqual((code, data["allowed"]), (0, 1))
        # The same text in another file is still a finding: the path is part of the fingerprint.
        other = self.write("other.txt", f"key {sample}\n")
        self.assertEqual(self.guard("--paths", str(other))[0], 1)

    def test_allow_entry_needs_reason(self) -> None:
        self.write(".secret-guard-allow", "0" * 64 + "  some/path\n")
        path = self.write("x.txt", "clean\n")
        self.assertEqual(self.guard("--paths", str(path))[0], 2)


class TestFiles(GuardCase):
    def test_forbidden_names(self) -> None:
        bad = [".env", ".env.local", "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519", "cert.pem", "tls.key",
               "a.p12", "a.pfx", "a.keystore", "a.jks", "credentials.json", "service-account-prod.json",
               ".netrc", ".pypirc", ".git-credentials", ".claude/settings.json",
               ".claude/settings.local.json", "review/canaries.key.json", "sub/dir/.env"]
        for name in bad:
            with self.subTest(name=name):
                path = self.write(name, "clean\n")
                code, data, _ = self.guard("--paths", str(path))
                self.assertEqual(code, 1, name)
                self.assertEqual(self.rules(data), ["forbidden-file"])
        for name in (".env.example", "id_rsa.pub", "notes.md", "settings.json"):
            path = self.write(name, "clean\n")
            self.assertEqual(self.guard("--paths", str(path))[0], 0, name)

    def test_npmrc_with_token(self) -> None:
        path = self.write(".npmrc", J("//registry.npmjs.org/:_auth", "Token=", mix(36), "\n"))
        self.assertIn("npm-auth-token", self.rules(self.guard("--paths", str(path))[1]))
        path = self.write(".npmrc", J("//registry.npmjs.org/:_auth", "Token=${NPM_TOKEN}\n"))
        self.assertEqual(self.guard("--paths", str(path))[0], 0)

    def test_binary_file(self) -> None:
        sample = SAMPLES["anthropic-key"]
        path = self.write("blob.bin", b"\0\1\2" + sample.encode())
        code, data, _ = self.guard("--paths", str(path))
        self.assertEqual(code, 0)
        self.assertEqual(data["unscanned"][0]["reason"], "binary")
        path = self.write("blob.pem", b"\0\1\2")
        code, data, _ = self.guard("--paths", str(path))
        self.assertEqual(self.rules(data), ["forbidden-file"])

    def test_large_file(self) -> None:
        sample = SAMPLES["anthropic-key"]
        head = ("clean line\n" * 10).encode()
        big = head + sample.encode() + b"\n" + b"y" * (5 * 1024 * 1024) + b"\n" + sample.encode()
        path = self.write("big.txt", big)
        code, data, _ = self.guard("--paths", str(path))
        self.assertEqual(code, 1)
        self.assertEqual(len(data["findings"]), 1)
        self.assertEqual(data["unscanned"][0]["reason"], "over 5 MiB")
        self.assertGreater(data["unscanned"][0]["bytes"], 0)

    def test_unreadable_file(self) -> None:
        code, _, _ = self.guard("--paths", str(self.root / "missing.txt"))
        self.assertEqual(code, 2)


class TestModes(GuardCase):
    def test_tracked(self) -> None:
        self.write("clean.txt", "clean\n")
        self.commit()
        self.assertEqual(self.guard("--tracked")[0], 0)
        self.write("src/app.py", f"KEY = '{SAMPLES['github-token']}'\n")
        self.write("deploy/.env", "A=1\n")
        self.commit()
        code, data, _ = self.guard("--tracked")
        self.assertEqual(code, 1)
        self.assertEqual(sorted(self.rules(data)), ["forbidden-file", "github-token"])

    def test_staged(self) -> None:
        self.write("clean.txt", "clean\n")
        self.commit()
        self.write("leak.txt", SAMPLES["stripe-key"] + "\n")
        self.assertEqual(self.guard("--staged")[0], 0)  # not staged yet
        self.git("add", "leak.txt")
        code, data, _ = self.guard("--staged")
        self.assertEqual((code, self.rules(data)), (1, ["stripe-key"]))
        # The staged blob counts, not the working tree file.
        self.write("leak.txt", "clean now\n")
        self.assertEqual(self.guard("--staged")[0], 1)

    def test_range_added_and_removed(self) -> None:
        base = self.commit("base")
        self.write("leak.txt", "a\n" + SAMPLES["slack-token"] + "\n")
        leak = self.commit("add")
        (self.root / "leak.txt").unlink()
        head = self.commit("remove")
        code, data, _ = self.guard("--range", f"{base}..{head}")
        self.assertEqual(code, 1)
        finding = data["findings"][0]
        self.assertEqual((finding["rule"], finding["commit"], finding["line"], finding["path"]),
                         ("slack-token", leak, 2, "leak.txt"))
        self.assertEqual(self.guard("--tracked")[0], 0)  # HEAD is clean
        self.assertEqual(self.guard("--range", f"{leak}..{head}")[0], 0)  # only deletions

    def test_range_forbidden_file_and_spaces(self) -> None:
        base = self.commit("base")
        self.write("conf/id_ed25519", "x\n")
        self.write("my dir/notes file.txt", SAMPLES["huggingface-token"] + "\n")
        head = self.commit("add")
        code, data, _ = self.guard("--range", f"{base}..{head}")
        found = {(f["rule"], f["path"]) for f in data["findings"]}
        self.assertEqual(found, {("forbidden-file", "conf/id_ed25519"),
                                 ("huggingface-token", "my dir/notes file.txt")})

    def test_history(self) -> None:
        self.write("a.txt", SAMPLES["google-api-key"] + "\n")
        self.commit()
        self.git("checkout", "-q", "-b", "side")
        self.write("b.txt", SAMPLES["pypi-token"] + "\n")
        self.commit()
        self.git("rm", "-q", "a.txt", "b.txt")
        self.commit()
        self.git("checkout", "-q", "main")
        code, data, _ = self.guard("--history")
        self.assertEqual(code, 1)
        self.assertEqual(sorted(self.rules(data)), ["google-api-key", "pypi-token"])

    def test_new_ref(self) -> None:
        self.write("a.txt", SAMPLES["sendgrid-key"] + "\n")
        head = self.commit()
        code, data, _ = self.guard("--new-ref", head)
        self.assertEqual((code, self.rules(data)), (1, ["sendgrid-key"]))

    def test_bad_range_and_not_a_repo(self) -> None:
        self.commit()
        self.assertEqual(self.guard("--range", "nope..HEAD")[0], 2)
        self.assertEqual(self.guard("--range", "HEAD")[0], 2)
        self.assertEqual(self.guard("--new-ref", "nope")[0], 2)
        outside = Path(self.tmp.name) / "plain"
        outside.mkdir()
        proc = subprocess.run([sys.executable, str(GUARD), "--root", str(outside), "--tracked"],
                              env=ENV, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)


class TestRedaction(GuardCase):
    def test_secret_never_printed(self) -> None:
        body = "\n".join(f"{rule} {value}" for rule, value in SAMPLES.items()) + "\n"
        path = self.write("all.txt", body)
        self.commit()
        for args in (["--paths", str(path)], ["--tracked"], ["--history"]):
            for runner in (self.guard, self.text_guard):
                result = runner(*args)
                output = result[-1]
                self.assertEqual(result[0], 1)
                for rule, value in SAMPLES.items():
                    secret = value.split("= ")[-1].strip('"')
                    if len(secret) >= 16:
                        self.assertNotIn(secret[4:], output, rule)
        code, data, _ = self.guard("--paths", str(path))
        sample = SAMPLES["anthropic-key"]
        redacted = [f["redacted"] for f in data["findings"] if f["rule"] == "anthropic-key"]
        self.assertEqual(redacted, [f"{sample[:4]}…{len(sample)}"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
