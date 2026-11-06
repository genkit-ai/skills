#!/usr/bin/env python3
"""Unit tests for scripts/sync_tocs.py."""

from __future__ import annotations

import contextlib
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.sync_tocs import (
    check_fences_balanced,
    check_hygiene_for_file,
    display_title_from_h2,
    generate_reference_content,
    get_staged_skill_md_files,
    gfm_base_slug,
    iter_non_fenced,
    parse_skill_frontmatter,
    run_check,
    run_fix,
    run_staged,
    strip_existing_toc,
)


class TestGFMSlugAndTitle(unittest.TestCase):
    def test_gfm_base_slug(self):
        self.assertEqual(gfm_base_slug("Install"), "install")
        self.assertEqual(
            gfm_base_slug("Server: add the a2ui() middleware"),
            "server-add-the-a2ui-middleware",
        )
        self.assertEqual(
            gfm_base_slug("Client: render surfaces (Flutter + genui)"),
            "client-render-surfaces-flutter--genui",
        )
        self.assertEqual(gfm_base_slug("Hello `code` world"), "hello-code-world")
        self.assertEqual(gfm_base_slug("What's Next?"), "whats-next")

    def test_display_title_from_h2(self):
        self.assertEqual(display_title_from_h2("## Simple Title"), "Simple Title")
        self.assertEqual(
            display_title_from_h2("## Title with `code`"),
            "Title with code",
        )
        self.assertEqual(
            display_title_from_h2("## Title with [link]"),
            "Title with link",
        )
        self.assertEqual(
            display_title_from_h2("## Title with \u2014 em-dash"),
            "Title with - em-dash",
        )


class TestCommonMarkFences(unittest.TestCase):
    def test_iter_non_fenced(self):
        lines = [
            "## Heading 1",
            "```python",
            "## Fake Heading Inside Fence",
            "```",
            "## Heading 2",
            "~~~bash",
            "## Fake Heading In Tildes",
            "~~~",
            "## Heading 3",
        ]
        non_fenced = [
            (idx, line)
            for idx, line, in_fence in iter_non_fenced(lines)
            if not in_fence
        ]
        self.assertEqual(
            non_fenced,
            [
                (0, "## Heading 1"),
                (4, "## Heading 2"),
                (8, "## Heading 3"),
            ],
        )

    def test_check_fences_balanced(self):
        balanced, open_line = check_fences_balanced("```python\nprint(1)\n```\n")
        self.assertTrue(balanced)
        self.assertIsNone(open_line)

        unbalanced, open_line = check_fences_balanced(
            "Line 1\n```python\nprint(1)\n"
        )
        self.assertFalse(unbalanced)
        self.assertEqual(open_line, 2)


class TestFrontmatterParser(unittest.TestCase):
    def test_valid_folded_frontmatter(self):
        text = (
            "---\n"
            "name: test-skill\n"
            "description: >-\n"
            "  This is a multiline\n"
            "  description for test-skill.\n"
            "metadata:\n"
            "  version: '1.0.0'\n"
            "---\n\n# Body\n"
        )
        fm, err = parse_skill_frontmatter(text)
        self.assertIsNone(err)
        self.assertIsNotNone(fm)
        self.assertEqual(fm["name"], "test-skill")
        self.assertEqual(
            fm["description"],
            "This is a multiline description for test-skill.",
        )

    def test_folded_frontmatter_with_blank_lines(self):
        text = (
            "---\n"
            "name: blank-line-skill\n"
            "description: >-\n"
            "  First paragraph line one\n"
            "  and line two.\n"
            "\n"
            "  Second paragraph after blank line.\n"
            "metadata:\n"
            "  version: '1.0.0'\n"
            "---\n\n# Body\n"
        )
        fm, err = parse_skill_frontmatter(text)
        self.assertIsNone(err)
        self.assertIsNotNone(fm)
        self.assertEqual(fm["name"], "blank-line-skill")
        self.assertEqual(
            fm["description"],
            "First paragraph line one and line two.\nSecond paragraph after blank line.",
        )

    def test_valid_quoted_frontmatter(self):
        text = (
            "---\n"
            "name: \"quoted-skill\"\n"
            "description: Quoted skill name description.\n"
            "---\n"
        )
        fm, err = parse_skill_frontmatter(text)
        self.assertIsNone(err)
        self.assertIsNotNone(fm)
        self.assertEqual(fm["name"], "quoted-skill")

    def test_valid_single_line_frontmatter(self):
        text = (
            "---\n"
            "name: single-line\n"
            "description: Direct single line description.\n"
            "---\n"
        )
        fm, err = parse_skill_frontmatter(text)
        self.assertIsNone(err)
        self.assertIsNotNone(fm)
        self.assertEqual(fm["name"], "single-line")
        self.assertEqual(
            fm["description"], "Direct single line description."
        )

    def test_missing_frontmatter(self):
        text = "# No frontmatter here\n"
        fm, err = parse_skill_frontmatter(text)
        self.assertIsNone(fm)
        self.assertIn("Missing YAML frontmatter", err)

    def test_missing_name(self):
        text = "---\ndescription: Only description\n---\n"
        fm, err = parse_skill_frontmatter(text)
        self.assertIsNone(fm)
        self.assertIn("Missing 'name'", err)

    def test_missing_description(self):
        text = "---\nname: my-skill\n---\n"
        fm, err = parse_skill_frontmatter(text)
        self.assertIsNone(fm)
        self.assertIn("Missing 'description'", err)

    def test_description_too_large(self):
        long_desc = "x" * 1025
        text = f"---\nname: my-skill\ndescription: {long_desc}\n---\n"
        fm, err = parse_skill_frontmatter(text)
        self.assertIsNone(fm)
        self.assertIn("Description exceeds 1024 UTF-8 bytes", err)


class TestReferenceTOCGeneration(unittest.TestCase):
    def test_short_file_no_toc(self):
        short_lines = ["# Title", "", "Some description", "", "## Section 1", "Body 1"]
        content = "\n".join(short_lines) + "\n"
        res = generate_reference_content(content)
        self.assertEqual(res, content)

    def test_long_file_generates_toc(self):
        # Create a document > 100 lines with 2 sections
        lines = ["# Long Document", "", "Overview paragraph."]
        lines.append("## First Section")
        for i in range(60):
            lines.append(f"Content line {i}")
        lines.append("## Second Section")
        for i in range(60):
            lines.append(f"More content {i}")

        content = "\n".join(lines) + "\n"
        generated = generate_reference_content(content)

        # Must have TOC inserted
        self.assertIn("- [First Section](#first-section): Lines ", generated)
        self.assertIn("- [Second Section](#second-section): Lines ", generated)
        self.assertIn("---\n\n## First Section", generated)

        # Idempotence test
        second_run = generate_reference_content(generated)
        self.assertEqual(generated, second_run)

    def test_shrinking_file_removes_toc(self):
        # Generate long doc with TOC first
        lines = ["# Shrinking Document", "", "Intro"]
        lines.append("## Sec 1")
        for i in range(120):
            lines.append(f"Line {i}")
        long_content = "\n".join(lines) + "\n"
        with_toc = generate_reference_content(long_content)
        self.assertIn("- [Sec 1](#sec-1): Lines ", with_toc)

        # Now shrink it to <= 100 lines
        shrunk_lines = [
            l for idx, l in enumerate(with_toc.splitlines()) if idx < 30
        ]
        # Ensure it contains ## Sec 1
        shrunk_content = "\n".join(shrunk_lines) + "\n"
        without_toc = generate_reference_content(shrunk_content)
        self.assertNotIn("- [Sec 1](#sec-1):", without_toc)
        self.assertNotIn("---", without_toc)


    def test_heading_rename_and_new_section_updates_toc(self):
        lines = ["# Guide", "", "Overview."]
        lines.append("## Original Heading")
        for i in range(60):
            lines.append(f"Body A {i}")
        lines.append("## Second Heading")
        for i in range(60):
            lines.append(f"Body B {i}")

        initial = generate_reference_content("\n".join(lines) + "\n")
        self.assertIn("- [Original Heading](#original-heading): Lines ", initial)

        # Rename first heading (including em-dash and code ticks), insert new middle section
        edited = initial.replace(
            "## Original Heading",
            "## Updated Heading \u2014 `v2`",
        ).replace(
            "## Second Heading",
            "## Inserted Middle Section\nMid line 1\nMid line 2\n\n## Second Heading",
        )
        resynced = generate_reference_content(edited)

        self.assertNotIn("Original Heading", resynced)
        self.assertIn(
            "- [Updated Heading - v2](#updated-heading--v2): Lines 11-71",
            resynced,
        )
        self.assertIn(
            "- [Inserted Middle Section](#inserted-middle-section): Lines 72-74",
            resynced,
        )
        self.assertIn(
            "- [Second Heading](#second-heading): Lines 76-136",
            resynced,
        )
        out_lines = resynced.splitlines()
        self.assertEqual(out_lines[10], "## Updated Heading \u2014 `v2`")
        self.assertEqual(out_lines[71], "## Inserted Middle Section")
        self.assertEqual(out_lines[75], "## Second Heading")


class TestHygieneChecks(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_caution_leakr_keyword_detected(self):
        p = Path(self.temp_dir) / "test.md"
        p.write_text("> **Caution:** Do not use this.\n", encoding="utf-8")
        errs = check_hygiene_for_file(p)
        self.assertTrue(any("Caution:" in e for e in errs))

    def test_caution_inside_fenced_code_block_allowed(self):
        p = Path(self.temp_dir) / "code_sample.md"
        p.write_text(
            "# Sample\n\n```python\n# Caution: internal comment in sample\nprint('Caution: ok')\n```\n",
            encoding="utf-8",
        )
        errs = check_hygiene_for_file(p)
        self.assertEqual(errs, [])

    def test_unclosed_fence_detected(self):
        p = Path(self.temp_dir) / "test.md"
        p.write_text("```bash\necho hello\n", encoding="utf-8")
        errs = check_hygiene_for_file(p)
        self.assertTrue(any("Unclosed CommonMark code fence" in e for e in errs))

    def test_skill_name_mismatch_detected(self):
        skill_dir = Path(self.temp_dir) / "my-skill"
        skill_dir.mkdir()
        p = skill_dir / "SKILL.md"
        p.write_text(
            "---\nname: different-name\ndescription: Test description\n---\n",
            encoding="utf-8",
        )
        errs = check_hygiene_for_file(p)
        self.assertTrue(any("does not match directory" in e for e in errs))


class TestGitIntegration(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        subprocess.run(["git", "init"], cwd=self.temp_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=self.temp_dir, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.temp_dir, check=True)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_staged_mode_updates_and_restages_drifted_toc(self):
        ref_dir = Path(self.temp_dir) / "skills" / "test-skill" / "references"
        ref_dir.mkdir(parents=True)
        ref_file = ref_dir / "doc.md"

        lines = ["# Title", "", "Intro paragraph."]
        lines.append("## Section 1")
        for i in range(60):
            lines.append(f"Line {i}")
        lines.append("## Section 2")
        for i in range(60):
            lines.append(f"Line {i}")
        ref_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

        # Stage file
        subprocess.run(["git", "add", "skills/test-skill/references/doc.md"], cwd=self.temp_dir, check=True)

        # Run sync_tocs.py --staged inside the temp git repo
        script_path = REPO_ROOT / "scripts" / "sync_tocs.py"
        res = subprocess.run(
            [sys.executable, str(script_path), "--staged"],
            cwd=self.temp_dir,
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0, f"Error: {res.stderr}")

        # Staged version should now contain TOC
        staged_content = subprocess.run(
            ["git", "show", ":skills/test-skill/references/doc.md"],
            cwd=self.temp_dir,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        self.assertIn("- [Section 1](#section-1): Lines ", staged_content)

    def test_staged_mode_blocks_unclosed_fence(self):
        skill_dir = Path(self.temp_dir) / "skills" / "test-skill"
        skill_dir.mkdir(parents=True)
        broken_file = skill_dir / "broken.md"
        broken_file.write_text("```bash\nunclosed\n", encoding="utf-8")
        subprocess.run(["git", "add", "skills/test-skill/broken.md"], cwd=self.temp_dir, check=True)

        script_path = REPO_ROOT / "scripts" / "sync_tocs.py"
        res = subprocess.run(
            [sys.executable, str(script_path), "--staged"],
            cwd=self.temp_dir,
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 1)
        self.assertIn("Unclosed CommonMark code fence", res.stderr)

    def test_staged_mode_blocks_caution_leakr(self):
        skill_dir = Path(self.temp_dir) / "skills" / "test-skill"
        skill_dir.mkdir(parents=True)
        broken_file = skill_dir / "leakr.md"
        broken_file.write_text("> **Caution:** LeakR keyword\n", encoding="utf-8")
        subprocess.run(["git", "add", "skills/test-skill/leakr.md"], cwd=self.temp_dir, check=True)

        script_path = REPO_ROOT / "scripts" / "sync_tocs.py"
        res = subprocess.run(
            [sys.executable, str(script_path), "--staged"],
            cwd=self.temp_dir,
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 1)
        self.assertIn("Found forbidden LeakR keyword 'Caution:'", res.stderr)

    def test_get_staged_skill_md_files_handles_os_error(self):
        err_buf = io.StringIO()
        with mock.patch("scripts.sync_tocs.subprocess.run", side_effect=FileNotFoundError("git not found")):
            with contextlib.redirect_stderr(err_buf):
                staged = get_staged_skill_md_files(Path(self.temp_dir))
        self.assertEqual(staged, [])
        self.assertIn("git not found", err_buf.getvalue())

    def test_run_check_detects_drift_with_posix_paths(self):
        ref_dir = Path(self.temp_dir) / "skills" / "my-skill" / "references"
        ref_dir.mkdir(parents=True)
        doc = ref_dir / "guide.md"
        lines = ["# Guide", "", "Intro", "## Section A"] + [f"Line {i}" for i in range(105)]
        doc.write_text("\n".join(lines) + "\n", encoding="utf-8")

        err_buf = io.StringIO()
        with contextlib.redirect_stderr(err_buf):
            ret = run_check(repo_root=Path(self.temp_dir))
        self.assertEqual(ret, 1)
        self.assertIn("skills/my-skill/references/guide.md: TOC is out of date", err_buf.getvalue())
        self.assertIn("python3 scripts/sync_tocs.py --fix", err_buf.getvalue())

    def test_run_check_with_target_files(self):
        skill_dir = Path(self.temp_dir) / "skills" / "target-skill"
        ref_dir = skill_dir / "references"
        ref_dir.mkdir(parents=True)
        doc = ref_dir / "doc.md"
        doc.write_text("# Doc\n\n## Section\nContent\n", encoding="utf-8")

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ret = run_check(target_files=[doc], repo_root=Path(self.temp_dir))
        self.assertEqual(ret, 0)

    def test_run_check_with_missing_target_file(self):
        missing = Path(self.temp_dir) / "nonexistent.md"
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            ret = run_check(target_files=[missing], repo_root=Path(self.temp_dir))
        self.assertEqual(ret, 1)
        self.assertIn("Target file not found", buf.getvalue())

    def test_run_fix_with_missing_target_file(self):
        missing = Path(self.temp_dir) / "nonexistent.md"
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            ret = run_fix(target_files=[missing], repo_root=Path(self.temp_dir))
        self.assertEqual(ret, 1)
        self.assertIn("Target file not found", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
