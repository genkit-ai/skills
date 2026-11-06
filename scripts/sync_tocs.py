#!/usr/bin/env python3
"""Deterministic TOC generator and markdown hygiene validator for skills.

Synchronizes Table of Contents (TOC) with GFM anchors and line range hints in
reference markdown files, and enforces CommonMark code fence balance, LeakR
keyword avoidance, and SKILL.md frontmatter byte-size limits.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
import sys
from typing import Iterator

def get_repo_root() -> Path:
    """Finds the root of the active Git repository or falls back to script parent."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        p = Path(res.stdout.strip())
        if p.is_dir():
            return p
    except (subprocess.CalledProcessError, OSError):
        pass
    return Path(__file__).resolve().parent.parent


def get_skills_root(repo_root: Path) -> Path:
    return repo_root / "skills"


def is_reference_file(path: Path, skills_root: Path) -> bool:
    """Returns True if path is strictly skills/<skill>/references/<file>.md."""
    try:
        rel = path.resolve().relative_to(skills_root.resolve())
    except ValueError:
        return False
    return (
        len(rel.parts) == 3
        and rel.parts[1] == "references"
        and rel.parts[2].endswith(".md")
    )


TOC_LINE_RE = re.compile(r"^- \[(.+)\]\(#(.+)\): Lines (\d+)-(\d+)$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]*\)")
CAUTION_RE = re.compile(r"\bCaution:")


def iter_non_fenced(lines: list[str]) -> Iterator[tuple[int, str, bool]]:
    """Yields (idx, line, in_fence) tracking CommonMark fenced code blocks.

    Handles both backtick (```) and tilde (~~~) fences of length >= 3.
    """
    in_fence: tuple[str, int] | None = None
    for idx, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            ch = stripped[0]
            ticks = len(stripped) - len(stripped.lstrip(ch))
            rest = stripped[ticks:].strip()
            if ticks >= 3:
                if in_fence is None:
                    in_fence = (ch, ticks)
                    yield idx, line, True
                    continue
                if ch == in_fence[0] and ticks >= in_fence[1] and rest == "":
                    in_fence = None
                    yield idx, line, True
                    continue
        yield idx, line, (in_fence is not None)


def check_fences_balanced(text: str) -> tuple[bool, int | None]:
    """Returns (True, None) if code fences are balanced, or (False, open_line_1_based)."""
    in_fence: tuple[str, int] | None = None
    fence_start_line: int | None = None
    for idx, line in enumerate(text.splitlines(), start=1):
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            ch = stripped[0]
            ticks = len(stripped) - len(stripped.lstrip(ch))
            rest = stripped[ticks:].strip()
            if ticks >= 3:
                if in_fence is None:
                    in_fence = (ch, ticks)
                    fence_start_line = idx
                elif ch == in_fence[0] and ticks >= in_fence[1] and rest == "":
                    in_fence = None
                    fence_start_line = None
    if in_fence is not None:
        return False, fence_start_line
    return True, None


def gfm_base_slug(heading_text: str) -> str:
    """Computes base GitHub Flavored Markdown anchor slug."""
    s = MARKDOWN_LINK_RE.sub(r"\1", heading_text)
    s = s.strip().lower().replace("`", "")
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r" ", "-", s)
    return s


def display_title_from_h2(raw_h2: str) -> str:
    """Formats H2 heading text for TOC display title."""
    text = MARKDOWN_LINK_RE.sub(r"\1", raw_h2[3:].strip())
    # Remove backticks and brackets so markdown link syntax stays valid,
    # and replace Unicode em-dashes with hyphens.
    text = (
        text.replace("`", "")
        .replace("[", "")
        .replace("]", "")
        .replace("\u2014", "-")
    )
    return text


def strip_existing_toc(lines: list[str]) -> list[str]:
    """Removes existing TOC lines."""
    return [l for l in lines if not TOC_LINE_RE.match(l)]


def generate_reference_content(orig_text: str) -> str:
    """Generates expected content with synchronized TOC for a reference markdown file."""
    raw_lines = strip_existing_toc(orig_text.splitlines())

    first_h2: int | None = None
    for idx, line, in_fence in iter_non_fenced(raw_lines):
        if not in_fence and line.startswith("## "):
            first_h2 = idx
            break

    if first_h2 is None:
        return orig_text

    check_idx = first_h2 - 1
    while check_idx >= 0 and raw_lines[check_idx].strip() == "":
        check_idx -= 1
    if check_idx >= 0 and raw_lines[check_idx].strip() == "---":
        check_idx -= 1
        while check_idx >= 0 and raw_lines[check_idx].strip() == "":
            check_idx -= 1
    insert_idx = check_idx + 1

    intro_lines = raw_lines[:insert_idx]
    while intro_lines and intro_lines[-1].strip() == "":
        intro_lines.pop()

    body_lines = raw_lines[first_h2:]
    prefix = (intro_lines + [""]) if intro_lines else []
    cleaned = prefix + body_lines

    # Remove TOC if content (excluding TOC and separator) is 100 lines or fewer
    if len(cleaned) <= 100:
        if any(TOC_LINE_RE.match(l) for l in orig_text.splitlines()):
            return "\n".join(cleaned) + "\n"
        return orig_text

    seen_slugs: dict[str, int] = {}
    for _, line, in_fence in iter_non_fenced(intro_lines):
        if not in_fence:
            m = HEADING_RE.match(line)
            if m:
                base = gfm_base_slug(m.group(2))
                seen_slugs[base] = seen_slugs.get(base, 0) + 1

    h2_entries: list[tuple[int, str, str]] = []
    for idx, line, in_fence in iter_non_fenced(body_lines):
        if not in_fence:
            m = HEADING_RE.match(line)
            if m:
                lvl = len(m.group(1))
                base = gfm_base_slug(m.group(2))
                cnt = seen_slugs.get(base, 0)
                seen_slugs[base] = cnt + 1
                anchor = base if cnt == 0 else f"{base}-{cnt}"
                if lvl == 2 and line.startswith("## "):
                    h2_entries.append(
                        (idx, display_title_from_h2(line), anchor)
                    )

    if not h2_entries:
        return orig_text

    sections: list[tuple[str, str, int, int]] = []
    for i, (h_idx, title, anchor) in enumerate(h2_entries):
        if i + 1 < len(h2_entries):
            next_h_idx = h2_entries[i + 1][0]
            end_idx = next_h_idx - 1
            while end_idx > h_idx and (
                body_lines[end_idx].strip() == ""
                or body_lines[end_idx].strip() == "---"
            ):
                end_idx -= 1
        else:
            end_idx = len(body_lines) - 1
            while end_idx > h_idx and body_lines[end_idx].strip() == "":
                end_idx -= 1
        sections.append((title, anchor, h_idx, end_idx))

    body_offset = len(prefix) + len(sections) + 3
    toc_lines = [
        f"- [{title}](#{anchor}): Lines {body_offset + h_idx + 1}-{body_offset + end_idx + 1}"
        for title, anchor, h_idx, end_idx in sections
    ]

    final_lines = prefix + toc_lines + ["", "---", ""] + body_lines
    return "\n".join(final_lines) + "\n"


def unquote_yaml_scalar(val: str) -> str:
    """Strips matching single or double outer quotes from a single-line YAML scalar."""
    if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
        return val[1:-1]
    return val


def parse_skill_frontmatter(
    text: str,
) -> tuple[dict[str, str] | None, str | None]:
    """Parses SKILL.md frontmatter in stdlib Python."""
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.DOTALL)
    if not m:
        return (
            None,
            "Missing YAML frontmatter with opening and closing '---' delimiters",
        )
    fm_text = m.group(1)
    name: str | None = None
    desc_lines: list[str] = []
    in_desc = False
    desc_folded = False

    for line in fm_text.splitlines():
        if line.startswith("name:"):
            name = unquote_yaml_scalar(line.split(":", 1)[1].strip())
            in_desc = False
        elif line.startswith("description:"):
            rest = line.split(":", 1)[1].strip()
            if rest in (">-", ">", "|-", "|", ""):
                in_desc = True
                desc_folded = rest.startswith(">")
                desc_lines = []
            else:
                in_desc = False
                unquoted = unquote_yaml_scalar(rest).strip()
                desc_lines = [unquoted] if unquoted else []
        elif in_desc:
            if line.startswith((" ", "\t")) or not line.strip():
                desc_lines.append(line.strip())
            else:
                in_desc = False

    while desc_lines and not desc_lines[-1]:
        desc_lines.pop()
    while desc_lines and not desc_lines[0]:
        desc_lines.pop(0)

    if not name:
        return None, "Missing 'name' field in frontmatter"
    if not desc_lines:
        return None, "Missing 'description' field in frontmatter"

    if desc_folded:
        paragraphs: list[str] = []
        current: list[str] = []
        for dl in desc_lines:
            if dl:
                current.append(dl)
            elif current:
                paragraphs.append(" ".join(current))
                current = []
        if current:
            paragraphs.append(" ".join(current))
        desc = "\n".join(paragraphs)
    else:
        desc = "\n".join(desc_lines)
    desc_bytes = len(desc.encode("utf-8"))
    if desc_bytes > 1024:
        return (
            None,
            f"Description exceeds 1024 UTF-8 bytes limit (got {desc_bytes} bytes)",
        )

    return {"name": name, "description": desc}, None


def check_hygiene_for_file(path: Path, text: str | None = None) -> list[str]:
    """Validates CommonMark fences, LeakR Caution keyword, and frontmatter."""
    errors: list[str] = []
    if text is None:
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as e:
            return [f"{path}: Failed to read file: {e}"]

    # 1. Check code fences
    balanced, start_line = check_fences_balanced(text)
    if not balanced:
        errors.append(
            f"{path}:{start_line}: Unclosed CommonMark code fence starting here"
        )

    # 2. Check LeakR Caution keyword (skipping fenced code blocks)
    for idx, line, in_fence in iter_non_fenced(text.splitlines()):
        if not in_fence and CAUTION_RE.search(line):
            errors.append(
                f"{path}:{idx + 1}: Found forbidden LeakR keyword 'Caution:'. Use 'Warning:' or 'Note:' instead."
            )

    # 3. Check SKILL.md frontmatter if applicable
    if path.name == "SKILL.md":
        fm, err = parse_skill_frontmatter(text)
        if err:
            errors.append(f"{path}: Invalid SKILL.md frontmatter: {err}")
        elif fm and fm["name"] != path.parent.name:
            errors.append(
                f"{path}: SKILL.md name '{fm['name']}' does not match directory '{path.parent.name}'"
            )

    return errors


def get_staged_skill_md_files(repo_root: Path | None = None) -> list[Path]:
    """Returns staged markdown files under skills/ via git diff --cached."""
    root = repo_root or get_repo_root()
    try:
        res = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, OSError) as e:
        err_msg = e.stderr if isinstance(e, subprocess.CalledProcessError) else str(e)
        print(f"Error querying git staged files: {err_msg}", file=sys.stderr)
        return []

    staged: list[Path] = []
    for line in res.stdout.splitlines():
        p = line.strip()
        if p.startswith("skills/") and p.endswith(".md"):
            staged.append(root / p)
    return staged


def read_staged_file(repo_root: Path, rel_posix: str) -> str | None:
    """Reads staged UTF-8 content directly from the Git index (:path)."""
    try:
        res = subprocess.run(
            ["git", "show", f":{rel_posix}"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
        return res.stdout
    except (subprocess.CalledProcessError, OSError, UnicodeDecodeError) as e:
        err_msg = e.stderr if isinstance(e, subprocess.CalledProcessError) else str(e)
        print(f"Error reading staged content for {rel_posix}: {err_msg}", file=sys.stderr)
        return None


def run_fix(
    target_files: list[Path] | None = None, repo_root: Path | None = None
) -> int:
    """Updates TOCs in reference files."""
    root = repo_root or get_repo_root()
    skills_root = get_skills_root(root)

    if target_files is not None:
        missing = [p for p in target_files if not p.is_file()]
        if missing:
            for p in missing:
                print(f"Error: Target file not found: {p}", file=sys.stderr)
            return 1
        files = [p for p in target_files if is_reference_file(p, skills_root)]
    else:
        files = sorted(skills_root.glob("*/references/*.md"))

    fixed_count = 0
    for path in files:
        if not path.is_file():
            continue
        orig = path.read_text(encoding="utf-8")
        updated = generate_reference_content(orig)
        if updated != orig:
            path.write_text(updated, encoding="utf-8")
            rel = path.relative_to(root).as_posix()
            print(f"Updated TOC in {rel}")
            fixed_count += 1

    if fixed_count == 0:
        print("All reference TOCs are up to date.")
    else:
        print(f"Fixed {fixed_count} file(s).")
    return 0


def run_staged(repo_root: Path | None = None) -> int:
    """Fixes drifted TOCs in staged reference files, restages, and checks hygiene."""
    root = repo_root or get_repo_root()
    skills_root = get_skills_root(root)
    staged = get_staged_skill_md_files(root)
    if not staged:
        return 0

    all_errors: list[str] = []

    for path in staged:
        rel = path.relative_to(root).as_posix()
        staged_text = read_staged_file(root, rel)
        if staged_text is None:
            all_errors.append(f"{rel}: Failed to read staged file from Git index")
            continue

        if is_reference_file(path, skills_root):
            updated = generate_reference_content(staged_text)
            if updated != staged_text:
                disk_text = path.read_text(encoding="utf-8") if path.is_file() else None
                if disk_text != staged_text:
                    all_errors.append(
                        f"{rel}: Staged TOC is out of date, and file has unstaged changes. "
                        "Stage all edits or run 'python3 scripts/sync_tocs.py --fix'."
                    )
                else:
                    path.write_text(updated, encoding="utf-8")
                    try:
                        subprocess.run(["git", "add", rel], cwd=root, check=True)
                    except (subprocess.CalledProcessError, OSError) as e:
                        all_errors.append(f"{rel}: Failed to stage updated TOC: {e}")
                        continue
                    staged_text = updated
                    print(f"[sync_tocs] Updated and restaged TOC for {rel}")

        errs = check_hygiene_for_file(path, text=staged_text)
        all_errors.extend(errs)

    if all_errors:
        print("\nPre-commit hygiene check failed:", file=sys.stderr)
        for err in all_errors:
            print(f"  ERROR: {err}", file=sys.stderr)
        return 1

    return 0


def run_check(
    target_files: list[Path] | None = None, repo_root: Path | None = None
) -> int:
    """Read-only check across skills markdown files."""
    root = repo_root or get_repo_root()
    skills_root = get_skills_root(root)
    all_errors: list[str] = []
    toc_drift: list[str] = []

    if target_files is not None:
        missing = [p for p in target_files if not p.is_file()]
        if missing:
            for p in missing:
                print(f"Error: Target file not found: {p}", file=sys.stderr)
            return 1
        ref_files = [p for p in target_files if is_reference_file(p, skills_root)]
        hygiene_files = [p for p in target_files if p.suffix == ".md"]
    else:
        ref_files = sorted(skills_root.glob("*/references/*.md"))
        hygiene_files = sorted(skills_root.glob("**/*.md"))

    # 1. Check TOC drift across reference files
    for path in ref_files:
        orig = path.read_text(encoding="utf-8")
        updated = generate_reference_content(orig)
        if updated != orig:
            rel = path.relative_to(root).as_posix()
            toc_drift.append(rel)
            all_errors.append(f"{rel}: TOC is out of date")

    # 2. Check hygiene across markdown files
    for path in hygiene_files:
        errs = check_hygiene_for_file(path)
        all_errors.extend(errs)

    if all_errors:
        print("Skills validation failed:", file=sys.stderr)
        for err in all_errors:
            print(f"  ERROR: {err}", file=sys.stderr)
        if toc_drift:
            print(
                "\nTo automatically fix TOC drift, run:\n  python3 scripts/sync_tocs.py --fix",
                file=sys.stderr,
            )
        return 1

    print("All skills markdown files verified successfully.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync TOCs and validate skills markdown hygiene."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--fix",
        action="store_true",
        help="Update TOCs in reference files",
    )
    group.add_argument(
        "--staged",
        action="store_true",
        help="Fix and restage TOCs in staged files, then check hygiene",
    )
    group.add_argument(
        "--check",
        action="store_true",
        help="Read-only validation of TOCs and markdown hygiene",
    )
    parser.add_argument(
        "files",
        nargs="*",
        type=Path,
        help="Optional specific files to fix or check",
    )

    args = parser.parse_args()

    if args.staged and args.files:
        parser.error(
            "Positional file arguments are not supported with --staged (files are determined from git staged index)"
        )

    target_files = [f.resolve() for f in args.files] if args.files else None

    if args.fix:
        return run_fix(target_files)
    elif args.staged:
        return run_staged()
    elif args.check:
        return run_check(target_files)

    return 0


if __name__ == "__main__":
    sys.exit(main())
