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
REL_PARENT_LINK_RE = re.compile(r"\[[^\]]+\]\(\s*\.\./[^)]*\)")
LIST_ITEM_RE = re.compile(r"^(\s*(?:>\s*)?)(-\s+|\*\s+|\+\s+|\d+\.\s+)(.*)$")
YAML_KEY_VALUE_RE = re.compile(r"^[a-zA-Z0-9_-]+: ", re.MULTILINE)
INLINE_CODE_RE = re.compile(r"(`+)(?:(?!\1).)+\1")
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
    """Validates CommonMark fences, CheckLint rules, LeakR Caution keyword, and frontmatter."""
    errors: list[str] = []
    if text is None:
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as e:
            return [f"{path}: Failed to read file: {e}"]

    # 1. Check code fences (SNIPPET_UNCLOSED)
    balanced, start_line = check_fences_balanced(text)
    if not balanced:
        errors.append(
            f"{path}:{start_line}: Unclosed CommonMark code fence starting here [SNIPPET_UNCLOSED]"
        )

    # 2. Check for mid-file '---' pairs within first 1500 chars that match YAML key-value heuristic
    # and cause devsitelinter's YamlMetadataParser to skip code fences (SNIPPET_UNCLOSED).
    if not text.startswith("---\n") and not text.startswith("---\r\n"):
        first_hr = text[:1500].find("\n---\n")
        if first_hr != -1:
            second_hr = text.find("\n---\n", first_hr + 4)
            if second_hr != -1:
                between = text[first_hr + 5 : second_hr]
                m_kv = YAML_KEY_VALUE_RE.search(between)
                if m_kv:
                    hr_line = text[: first_hr + 1].count("\n") + 1
                    errors.append(
                        f"{path}:{hr_line}: Mid-file '---' block contains YAML-like line "
                        f"'{m_kv.group(0).strip()}' that hijacks frontmatter parsing [SNIPPET_UNCLOSED]"
                    )

    # 3. Line-level checks (LeakR Caution, SNIPPET_EM_DASH, LINK_RELATIVE_G3DOC,
    #    WHITESPACE_TRAILING, LIST_NO_LINE, LINE_OVER_80)
    raw_lines = text.splitlines()
    in_frontmatter = False
    in_list = False

    for idx, line, in_fence in iter_non_fenced(raw_lines):
        lno = idx + 1
        if idx == 0 and line == "---":
            in_frontmatter = True
            continue
        if in_frontmatter:
            if line == "---":
                in_frontmatter = False
            continue

        stripped = line.lstrip()
        is_fence_delimiter = (
            stripped.startswith("```") or stripped.startswith("~~~")
        ) and len(stripped) - len(stripped.lstrip(stripped[0])) >= 3

        if in_fence:
            if not is_fence_delimiter and ("\u2014" in line or "\u2013" in line):
                errors.append(
                    f"{path}:{lno}: Found em/en-dash inside fenced code block; use '-' instead [SNIPPET_EM_DASH]"
                )
            continue

        if CAUTION_RE.search(line):
            errors.append(
                f"{path}:{lno}: Found forbidden LeakR keyword 'Caution:'. Use 'Warning:' or 'Note:' instead."
            )

        for m_code in INLINE_CODE_RE.finditer(line):
            code_span = m_code.group(0)
            if "\u2014" in code_span or "\u2013" in code_span:
                errors.append(
                    f"{path}:{lno}: Found em/en-dash inside inline code span; use '-' instead [SNIPPET_EM_DASH]"
                )

        if line.endswith(" ") and (line.strip() == "" or not line.endswith("  ")):
            errors.append(
                f"{path}:{lno}: Trailing whitespace at end of line [WHITESPACE_TRAILING]"
            )

        line_without_code = INLINE_CODE_RE.sub("", line)
        if REL_PARENT_LINK_RE.search(line_without_code):
            errors.append(
                f"{path}:{lno}: Relative link uses '../' parent traversal [LINK_RELATIVE_G3DOC]"
            )

        is_list_first = bool(LIST_ITEM_RE.match(line))
        if is_list_first and idx > 0:
            prev = raw_lines[idx - 1]
            if (
                prev.strip() != ""
                and not LIST_ITEM_RE.match(prev)
                and not prev.lstrip().startswith("#")
                and not (prev.startswith("  ") and in_list)
                and not (line.lstrip().startswith(">") and prev.lstrip().startswith(">"))
            ):
                errors.append(
                    f"{path}:{lno}: List item must be preceded by a blank line [LIST_NO_LINE]"
                )

        if is_list_first:
            in_list = True
        elif line.strip() == "":
            in_list = False

        chk = line.rstrip("\\").rstrip(" \t") if line.endswith("\\") else line
        if len(chk) > 80:
            if (
                chk.lstrip().startswith("|")
                or chk.lstrip().startswith("#")
                or TOC_LINE_RE.match(chk)
                or chk.strip() in ("---", "***")
                or " " not in chk.strip()
            ):
                continue
            if any(
                len(m.group(0)) / len(chk) > 0.5
                for m in MARKDOWN_LINK_RE.finditer(chk)
            ):
                continue
            if is_list_first and len(chk) < 200:
                nxt = raw_lines[idx + 1] if idx + 1 < len(raw_lines) else ""
                if nxt == "" or LIST_ITEM_RE.match(nxt):
                    continue
            errors.append(
                f"{path}:{lno}: Line exceeds 80 characters ({len(chk)} chars) [LINE_OVER_80]"
            )

    # 4. Check SKILL.md frontmatter if applicable
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
