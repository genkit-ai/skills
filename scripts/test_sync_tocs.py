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
    is_reference_file,
    parse_skill_frontmatter,
)


class TestSyncTocs(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_toc_lifecycle_links_and_fenced_headings(self):
        short_doc = "# Short\n\n## Section\nBody\n"
        self.assertEqual(generate_reference_content(short_doc), short_doc)

        lines = ["# Guide", "", "Overview.", "## [Original](https://example.com) \u2014 `v1`", "```python", "## Ignored Fence Heading", "```"]
        lines += [f"Line {i}" for i in range(105)]
        generated = generate_reference_content("\n".join(lines) + "\n")
        self.assertIn("- [Original - v1](#original--v1): Lines 9-117", generated)
        self.assertNotIn("Ignored Fence Heading", generated.split("---")[0])
        self.assertEqual(generate_reference_content(generated), generated)

        # Shrink to exactly 100 non-TOC content lines (104 raw lines with old TOC+separator)
        shrunk_100 = "\n".join(generated.splitlines()[:104]) + "\n"
        self.assertNotIn("Lines ", generate_reference_content(shrunk_100))

    def test_hygiene_reference_filter_and_caution(self):
        anc = self.temp_dir / "references" / "skills"
        self.assertFalse(is_reference_file(anc / "demo" / "SKILL.md", anc))
        self.assertTrue(is_reference_file(anc / "demo" / "references" / "a.md", anc))

        prose_caution = self.temp_dir / "bad.md"
        prose_caution.write_text("> **Caution:** triggers LeakR\n```bash\nunclosed\n", encoding="utf-8")
        self.assertEqual(len(check_hygiene_for_file(prose_caution)), 2)

        fenced_caution = self.temp_dir / "ok.md"
        fenced_caution.write_text("```python\n# Caution: allowed inside fence\n```\n", encoding="utf-8")
        self.assertEqual(check_hygiene_for_file(fenced_caution), [])

    def test_checklint_rules(self):
        # 1. Mid-file '---' block with YAML-like 'key: value' line triggers SNIPPET_UNCLOSED
        bogus_yaml = self.temp_dir / "bogus_yaml.md"
        bogus_yaml.write_text(
            "# Evals\n\n- [Sec](#sec): Lines 7-20\n\n---\n\n## Sec\n\nFields: `a`, `b`\n\n```yaml\n---\nmodel: m\n---\n```\n",
            encoding="utf-8",
        )
        errs = check_hygiene_for_file(bogus_yaml)
        self.assertTrue(any("SNIPPET_UNCLOSED" in e and "Fields:" in e for e in errs), errs)

        # Bolding '**Fields:**' resolves the mid-file frontmatter false positive
        fixed_yaml = self.temp_dir / "fixed_yaml.md"
        fixed_yaml.write_text(
            "# Evals\n\n- [Sec](#sec): Lines 7-20\n\n---\n\n## Sec\n\n**Fields:** `a`, `b`\n\n```yaml\n---\nmodel: m\n---\n```\n",
            encoding="utf-8",
        )
        self.assertEqual(check_hygiene_for_file(fixed_yaml), [])

        # 2. SNIPPET_EM_DASH in fenced code blocks and single/double-backtick inline code spans
        em_dash_doc = self.temp_dir / "em_dash.md"
        em_dash_doc.write_text(
            "# Doc\n\nInline `bad \u2014 dash` and ``also `bad` \u2013 dash`` here.\n\n```python\n# comment \u2014 dash\n```\n",
            encoding="utf-8",
        )
        errs = check_hygiene_for_file(em_dash_doc)
        self.assertEqual(sum("SNIPPET_EM_DASH" in e for e in errs), 3, errs)

        # 3. LINK_RELATIVE_G3DOC, LIST_NO_LINE, WHITESPACE_TRAILING, and LINE_OVER_80
        lint_doc = self.temp_dir / "lint_errors.md"
        lint_doc.write_text(
            "# Doc\n\n"
            "See [SKILL.md](../SKILL.md#imports).\n\n"
            "Trailing space here. \n\n"
            "No blank line before list:\n"
            "- Item one\n\n"
            + ("word " * 18).strip()
            + "\n\n"
            + "- "
            + (" single-line list item under 200 chars is exempt " * 2).strip()
            + "\n",
            encoding="utf-8",
        )
        errs = check_hygiene_for_file(lint_doc)
        self.assertTrue(any("LINK_RELATIVE_G3DOC" in e for e in errs), errs)
        self.assertTrue(any("WHITESPACE_TRAILING" in e for e in errs), errs)
        self.assertTrue(any("LIST_NO_LINE" in e for e in errs), errs)
        self.assertEqual(sum("LINE_OVER_80" in e for e in errs), 1, errs)

        # 4. LINK_ID (double-hyphen H2 slugs, '{{var}}' H2 headings, '--' anchor links),
        #    LIST_NO_LINE after headings (while allowing indented code blocks with blank lines in lists),
        #    WHITESPACE_LINES (consecutive blank lines), and CURL_PIPE_SH
        ref_dir = self.temp_dir / "skills" / "demo" / "references"
        ref_dir.mkdir(parents=True, exist_ok=True)
        extra_lint = ref_dir / "guide.md"
        extra_lint.write_text(
            "# Guide\n\n"
            "## Notes & Gotchas\n"
            "- Missing blank line after heading\n"
            "  ```python\n"
            "  x = 1\n\n"
            "  y = 2\n"
            "  ```\n"
            "- Valid continuation bullet after indented fence\n\n\n"
            "## `{{variable}}` Sent Literally\n\n"
            "See [bad](other.md#bad--anchor).\n\n"
            "- Install: `curl -LsSf https://astral.sh/uv/install.sh | sh`\n"
            "- Allowed native CLI: `curl -sL cli.genkit.dev | bash`\n",
            encoding="utf-8",
        )
        errs = check_hygiene_for_file(extra_lint)
        self.assertEqual(sum("LINK_ID" in e for e in errs), 3, errs)
        self.assertEqual(sum("LIST_NO_LINE" in e for e in errs), 1, errs)
        self.assertEqual(sum("WHITESPACE_LINES" in e for e in errs), 1, errs)
        self.assertEqual(sum("CURL_PIPE_SH" in e for e in errs), 1, errs)

    def test_frontmatter_validation(self):
        valid = "---\nname: demo\ndescription: >-\n Para 1.\n\n Para 2.\n---\n"
        fm, err = parse_skill_frontmatter(valid)
        self.assertIsNone(err)
        self.assertEqual(fm["description"], "Para 1.\nPara 2.")

        _, empty_err = parse_skill_frontmatter('---\nname: demo\ndescription: ""\n---\n')
        self.assertIn("Missing 'description'", empty_err)

        _, too_long_err = parse_skill_frontmatter(f"---\nname: demo\ndescription: {'x' * 1025}\n---\n")
        self.assertIn("1024", too_long_err)

    def test_staged_mode_uses_git_index(self):
        subprocess.run(["git", "init"], cwd=self.temp_dir, capture_output=True, check=True)
        ref = self.temp_dir / "skills" / "demo" / "references" / "doc.md"
        ref.parent.mkdir(parents=True)
        ref.write_text("\n".join(["# Doc", "## Sec"] + [f"L{i}" for i in range(105)]) + "\n", encoding="utf-8")
        subprocess.run(["git", "add", "skills/demo/references/doc.md"], cwd=self.temp_dir, check=True)

        script = [sys.executable, str(REPO_ROOT / "scripts" / "sync_tocs.py"), "--staged"]
        self.assertEqual(subprocess.run(script, cwd=self.temp_dir, capture_output=True, text=True).returncode, 0)
        staged = subprocess.run(["git", "show", ":skills/demo/references/doc.md"], cwd=self.temp_dir, capture_output=True, text=True, check=True).stdout
        self.assertIn("- [Sec](#sec): Lines ", staged)

        # Broken staged index must fail even if fixed unstaged on disk
        bad = self.temp_dir / "skills" / "demo" / "bad.md"
        bad.write_text("```bash\nunclosed\n", encoding="utf-8")
        subprocess.run(["git", "add", "skills/demo/bad.md"], cwd=self.temp_dir, check=True)
        bad.write_text("```bash\nclosed\n```\n", encoding="utf-8")
        self.assertEqual(subprocess.run(script, cwd=self.temp_dir, capture_output=True, text=True).returncode, 1)


if __name__ == "__main__":
    unittest.main()
