import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_LINK = re.compile(r"\[[^]]+\]\(([^)]+)\)")


class DocumentationTests(unittest.TestCase):
    def test_every_relative_markdown_link_resolves(self):
        failures = []
        for document in sorted(ROOT.rglob("*.md")):
            for target in MARKDOWN_LINK.findall(document.read_text(encoding="utf-8")):
                if target.startswith(("http://", "https://", "#", "mailto:")):
                    continue
                path = target.split("#", 1)[0]
                if path and not (document.parent / path).resolve().exists():
                    failures.append(f"{document.relative_to(ROOT)} -> {target}")
        self.assertEqual(failures, [])

    def test_public_entry_points_cover_required_operator_topics(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        index = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
        for required in (
            "Quick start",
            "Current status",
            "Human approval gates",
            "docs/OPERATOR_GUIDE.md",
            "docs/CAPABILITIES.md",
            "docs/PRIVACY.md",
        ):
            self.assertIn(required, readme)
        for document in ("OPERATOR_GUIDE.md", "CAPABILITIES.md", "PRIVACY.md", "CLI.md", "DEMO.md"):
            self.assertIn(document, index)

    def test_capability_matrix_is_truthful_about_live_boundaries(self):
        matrix = (ROOT / "docs" / "CAPABILITIES.md").read_text(encoding="utf-8")
        self.assertIn("One approved real Claude export conversion | `RECORDED`", matrix)
        self.assertIn("Real Claude export schema compatibility | `UNKNOWN`", matrix)
        self.assertIn("Consumer ChatGPT reconstruction writes | `UNSUPPORTED`", matrix)
        self.assertIn("Synthetic end-to-end migration demo | `VERIFIED`", matrix)
        self.assertNotIn("real Claude export schema compatibility | `VERIFIED`", matrix)

    def test_privacy_guide_contains_every_permanent_gate(self):
        guide = (ROOT / "docs" / "PRIVACY.md").read_text(encoding="utf-8")
        for gate in (
            "real-export access",
            "private network transmission",
            "browser automation",
            "assistant writes",
            "content reduction",
            "destructive behavior",
            "production dependencies",
            "release publication",
        ):
            self.assertIn(gate, guide)

    def test_stale_validator_only_status_is_removed(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("currently provides an experimental assistant-neutral ContextPack", readme)
        self.assertNotIn("current implementation validates synthetic ContextPack documents only", readme)


if __name__ == "__main__":
    unittest.main()
