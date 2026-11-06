#!/usr/bin/env python3
"""Core behavioral tests for scripts/sync_tocs.py."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.sync_tocs import (
    check_hygiene_for_file,
    generate_reference_content,
    parse_skill_frontmatter,
)


class TestSyncTocs(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_toc_lifecycle_and_fenced_headings(self):
        short_doc = "# Short\n\n## Section\nBody\n"
        self.assertEqual(generate_reference_content(short_doc), short_doc)

        lines = ["# Guide", "", "Overview.", "## Original \u2014 `v1`", "```python", "## Ignored Fence Heading", "```"]
        lines += [f"Line {i}" for i in range(105)]
        generated = generate_reference_content("\n".join(lines) + "\n")
        self.assertIn("- [Original - v1](#original--v1): Lines 9-117", generated)
        self.assertNotIn("Ignored Fence Heading", generated.split("---")[0])
        self.assertEqual(generate_reference_content(generated), generated)

        shrunk = "\n".join(generated.splitlines()[:25]) + "\n"
        self.assertNotIn("Lines ", generate_reference_content(shrunk))

    def test_hygiene_fences_and_caution(self):
        prose_caution = self.temp_dir / "bad.md"
        prose_caution.write_text("> **Caution:** triggers LeakR\n```bash\nunclosed\n", encoding="utf-8")
        errs = check_hygiene_for_file(prose_caution)
        self.assertEqual(len(errs), 2)

        fenced_caution = self.temp_dir / "ok.md"
        fenced_caution.write_text("```python\n# Caution: allowed inside fence\n```\n", encoding="utf-8")
        self.assertEqual(check_hygiene_for_file(fenced_caution), [])

    def test_frontmatter_validation(self):
        valid = "---\nname: demo\ndescription: >-\n  Para 1.\n\n  Para 2.\n---\n"
        fm, err = parse_skill_frontmatter(valid)
        self.assertIsNone(err)
        self.assertEqual(fm["description"], "Para 1.\nPara 2.")

        _, too_long_err = parse_skill_frontmatter(f"---\nname: demo\ndescription: {'x' * 1025}\n---\n")
        self.assertIn("1024", too_long_err)

    def test_staged_mode_restages_toc(self):
        subprocess.run(["git", "init"], cwd=self.temp_dir, capture_output=True, check=True)
        ref = self.temp_dir / "skills" / "demo" / "references" / "doc.md"
        ref.parent.mkdir(parents=True)
        ref.write_text("\n".join(["# Doc", "## Sec"] + [f"L{i}" for i in range(105)]) + "\n", encoding="utf-8")
        subprocess.run(["git", "add", "skills/demo/references/doc.md"], cwd=self.temp_dir, check=True)

        res = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "sync_tocs.py"), "--staged"],
            cwd=self.temp_dir,
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0, res.stderr)
        staged = subprocess.run(
            ["git", "show", ":skills/demo/references/doc.md"],
            cwd=self.temp_dir,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        self.assertIn("- [Sec](#sec): Lines ", staged)


if __name__ == "__main__":
    unittest.main()
