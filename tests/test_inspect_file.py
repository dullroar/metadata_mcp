"""Regression tests for the compact, read-only inspect_file MCP tool."""

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SERVER_PATH = Path(__file__).resolve().parents[1] / "server.py"
SPEC = importlib.util.spec_from_file_location("metadata_mcp_server", SERVER_PATH)
assert SPEC and SPEC.loader
server = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(server)


class InspectFileTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.file = self.root / "example.py"
        self.file.write_text("first = 1\nsecond = 2\n", encoding="utf-8")

    def tearDown(self):
        self.tempdir.cleanup()

    def git(self, *arguments):
        return subprocess.run(
            ["git", "-C", str(self.root), *arguments],
            capture_output=True,
            text=True,
            check=True,
        )

    def initialise_repo(self):
        self.git("init", "--quiet")
        self.git("config", "user.name", "Test Author")
        self.git("config", "user.email", "test@example.invalid")
        self.git("add", "example.py")
        self.git("commit", "--quiet", "-m", "Add example")

    def test_regular_file_includes_stat_and_non_repo_result(self):
        result = server.inspect_file(str(self.file))

        self.assertEqual(result["filesystem"]["status"], "ok")
        self.assertEqual(result["filesystem"]["kind"], "file")
        self.assertEqual(result["filesystem"]["size_bytes"], len("first = 1\nsecond = 2\n"))
        self.assertIn("modified_at", result["filesystem"]["timestamps"])
        self.assertIn(result["content_type"]["status"], {"ok", "fallback"})
        self.assertEqual(result["git"]["status"], "not_repository")

    def test_missing_path_and_directory_are_reported_without_throwing(self):
        missing = server.inspect_file(str(self.root / "does-not-exist"))
        directory = server.inspect_file(str(self.root))

        self.assertEqual(missing["filesystem"]["status"], "missing")
        self.assertEqual(missing["content_type"]["status"], "not_applicable")
        self.assertEqual(directory["filesystem"]["kind"], "directory")
        self.assertEqual(directory["content_type"]["status"], "not_applicable")

    def test_symlink_attributes_are_explicit(self):
        link = self.root / "example-link.py"
        try:
            link.symlink_to(self.file)
        except OSError as exc:
            self.skipTest(f"Symlinks unavailable in this environment: {exc}")

        result = server.inspect_file(str(link))

        self.assertEqual(result["filesystem"]["kind"], "symlink")
        self.assertTrue(result["filesystem"]["symlink_target_exists"])
        self.assertEqual(result["content_type"]["status"], "ok")

    def test_extension_fallback_is_labeled_when_file_command_is_missing(self):
        with patch.object(server.shutil, "which", return_value=None):
            result = server.inspect_file(str(self.file))

        content_type = result["content_type"]
        self.assertEqual(content_type["status"], "fallback")
        self.assertEqual(content_type["detection"], "extension_fallback")
        self.assertIn("unavailable", content_type["note"])

    def test_git_summary_status_and_last_commit(self):
        self.initialise_repo()

        clean = server.inspect_file(str(self.file))
        self.assertEqual(clean["git"]["status"], "ok")
        self.assertTrue(clean["git"]["tracked"])
        self.assertEqual(clean["git"]["worktree_state"], "clean")
        self.assertEqual(clean["git"]["last_commit"]["author"]["name"], "Test Author")
        self.assertEqual(clean["git"]["last_commit"]["subject"], "Add example")

        self.file.write_text("first = 1\nsecond = 3\n", encoding="utf-8")
        modified = server.inspect_file(str(self.file))
        self.assertEqual(modified["git"]["worktree_state"], "modified")

    def test_git_untracked_and_ignored_states(self):
        self.initialise_repo()
        untracked = self.root / "untracked.txt"
        untracked.write_text("new", encoding="utf-8")
        (self.root / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
        self.git("add", ".gitignore")
        self.git("commit", "--quiet", "-m", "Ignore generated file")
        ignored = self.root / "ignored.txt"
        ignored.write_text("generated", encoding="utf-8")

        self.assertEqual(server.inspect_file(str(untracked))["git"]["worktree_state"], "untracked")
        ignored_result = server.inspect_file(str(ignored))["git"]
        self.assertEqual(ignored_result["worktree_state"], "ignored")
        self.assertFalse(ignored_result["tracked"])

    def test_blame_is_bounded_and_requires_complete_valid_range(self):
        self.initialise_repo()

        blamed = server.inspect_file(str(self.file), blame_start_line=1, blame_end_line=2)
        self.assertEqual(blamed["git"]["blame"]["status"], "ok")
        self.assertEqual([line["line"] for line in blamed["git"]["blame"]["lines"]], [1, 2])
        self.assertEqual(blamed["git"]["blame"]["lines"][0]["author"]["name"], "Test Author")

        incomplete = server.inspect_file(str(self.file), blame_start_line=1)
        reversed_range = server.inspect_file(str(self.file), blame_start_line=2, blame_end_line=1)
        self.assertEqual(incomplete["git"]["blame"]["status"], "invalid_request")
        self.assertEqual(reversed_range["git"]["blame"]["status"], "invalid_request")

    def test_content_type_failure_does_not_hide_filesystem_or_git(self):
        self.initialise_repo()
        with patch.object(server, "_content_type_info", side_effect=RuntimeError("simulated failure")):
            result = server.inspect_file(str(self.file))

        self.assertEqual(result["filesystem"]["status"], "ok")
        self.assertEqual(result["content_type"]["status"], "error")
        self.assertEqual(result["git"]["status"], "ok")


if __name__ == "__main__":
    unittest.main()
