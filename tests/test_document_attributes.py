"""Tests for Pandoc-backed semantic document attributes."""

import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SERVER_PATH = Path(__file__).resolve().parents[1] / "server.py"
SPEC = importlib.util.spec_from_file_location("metadata_mcp_document_server", SERVER_PATH)
assert SPEC and SPEC.loader
server = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(server)


class FakePandoc:
    def __init__(self, document=None, inputs=None, error=None):
        self.document = document or {"meta": {}}
        self.inputs = inputs or ["markdown", "html", "ipynb"]
        self.error = error

    def get_pandoc_version(self):
        return "3.1.3"

    def get_pandoc_formats(self):
        return self.inputs, ["json"]

    def convert_file(self, path, to, format=None):
        if self.error:
            raise self.error
        return json.dumps(self.document)


class DocumentAttributeUnitTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.markdown = self.root / "document.md"
        self.markdown.write_text("# Example\n", encoding="utf-8")

    def tearDown(self):
        self.tempdir.cleanup()

    def test_normalizes_scalar_list_and_custom_attributes(self):
        metadata = {
            "title": {"t": "MetaInlines", "c": [{"t": "Str", "c": "A"}, {"t": "Space"}, {"t": "Str", "c": "Title"}]},
            "author": {"t": "MetaList", "c": [{"t": "MetaString", "c": "Ada"}, {"t": "MetaString", "c": "Lin"}]},
            "published": {"t": "MetaBool", "c": True},
            "custom-field": {"t": "MetaString", "c": "42"},
            "jupyter": {"t": "MetaMap", "c": {"kernelspec": {"t": "MetaMap", "c": {}}}},
        }
        fake = FakePandoc({"meta": metadata})

        with patch.object(server, "_load_pypandoc", return_value=(fake, None)):
            result = server.read_document_attributes(str(self.markdown))

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["source_format"], "markdown")
        self.assertEqual(result["attributes"], {
            "title": "A Title",
            "author": ["Ada", "Lin"],
            "published": True,
            "custom-field": "42",
        })
        self.assertEqual(result["omitted_attributes"][0]["key"], "jupyter")
        self.assertIn("warnings", result)

    def test_full_metadata_opt_in_preserves_nested_ast(self):
        metadata = {"nested": {"t": "MetaMap", "c": {"value": {"t": "MetaString", "c": "kept"}}}}
        fake = FakePandoc({"meta": metadata})

        with patch.object(server, "_load_pypandoc", return_value=(fake, None)):
            result = server.read_document_attributes(str(self.markdown), include_full_metadata=True)

        self.assertEqual(result["attributes"], {})
        self.assertEqual(result["full_metadata"], metadata)

    def test_missing_dependency_is_explicit(self):
        with patch.object(server, "_load_pypandoc", return_value=(None, "pypandoc is not installed")):
            result = server.read_document_attributes(str(self.markdown))

        self.assertEqual(result["status"], "unavailable")
        self.assertIn("Pandoc", result["message"])

    def test_reader_selection_and_unsupported_format_errors(self):
        explicit = self.root / "no-extension"
        explicit.write_text("# Example\n", encoding="utf-8")
        fake = FakePandoc()
        with patch.object(server, "_load_pypandoc", return_value=(fake, None)):
            result = server.read_document_attributes(str(explicit), source_format="markdown")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["source_format"], "markdown")

        unsupported = server.read_document_attributes(str(explicit))
        self.assertEqual(unsupported["status"], "unsupported")

    def test_pdf_and_ooxml_route_to_exiftool_without_loading_pandoc(self):
        pdf = self.root / "report.pdf"
        docx = self.root / "report.docx"
        pdf.write_bytes(b"%PDF")
        docx.write_bytes(b"PK")

        with patch.object(server, "_load_pypandoc") as loader:
            pdf_result = server.read_document_attributes(str(pdf))
            docx_result = server.read_document_attributes(str(docx))

        self.assertEqual(pdf_result["status"], "not_applicable")
        self.assertEqual(docx_result["status"], "not_applicable")
        self.assertEqual(pdf_result["recommended_tool"], "read_metadata")
        loader.assert_not_called()

    def test_unavailable_reader_and_parse_failure_are_isolated(self):
        unavailable = FakePandoc(inputs=["html"])
        with patch.object(server, "_load_pypandoc", return_value=(unavailable, None)):
            reader_result = server.read_document_attributes(str(self.markdown))
        self.assertEqual(reader_result["status"], "unsupported")

        broken = FakePandoc(error=RuntimeError("bad input"))
        with patch.object(server, "_load_pypandoc", return_value=(broken, None)):
            parse_result = server.read_document_attributes(str(self.markdown))
        self.assertEqual(parse_result["status"], "error")
        self.assertIn("bad input", parse_result["error"])

    def test_project_templates_are_identical_and_documented(self):
        claude = (SERVER_PATH.parent / "sample-CLAUDE.md").read_bytes()
        agents = (SERVER_PATH.parent / "sample-AGENTS.md").read_bytes()
        readme = (SERVER_PATH.parent / "README.md").read_text(encoding="utf-8")

        self.assertEqual(claude, agents)
        self.assertIn("sample-CLAUDE.md", readme)
        self.assertIn("sample-AGENTS.md", readme)
        self.assertIn("remove the prefix", readme)


@unittest.skipUnless(
    importlib.util.find_spec("pypandoc") is not None and shutil.which("pandoc") is not None,
    "pypandoc and a local Pandoc executable are required for integration tests",
)
class DocumentAttributeIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_markdown_frontmatter_is_extracted_by_local_pandoc(self):
        path = self.root / "proposal.md"
        path.write_text(
            "---\ntitle: Proposal\nauthor: Ada Example\ntags: [metadata, pandoc]\ncustom-field: 42\n---\n\n# Body\n",
            encoding="utf-8",
        )

        result = server.read_document_attributes(str(path))

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["attributes"]["title"], "Proposal")
        self.assertEqual(result["attributes"]["author"], "Ada Example")
        self.assertEqual(result["attributes"]["tags"], ["metadata", "pandoc"])
        self.assertEqual(result["attributes"]["custom-field"], "42")

    def test_html_title_and_standard_meta_attributes_are_extracted(self):
        path = self.root / "about.html"
        path.write_text(
            '<html lang="en"><head><title>About us</title><meta name="author" content="Ada"><meta name="description" content="Example site"></head><body><h1>About</h1></body></html>',
            encoding="utf-8",
        )

        result = server.read_document_attributes(str(path))

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["attributes"]["title"], "About us")
        self.assertEqual(result["attributes"]["author"], "Ada")
        self.assertEqual(result["attributes"]["description"], "Example site")
        self.assertEqual(result["attributes"]["lang"], "en")


if __name__ == "__main__":
    unittest.main()
