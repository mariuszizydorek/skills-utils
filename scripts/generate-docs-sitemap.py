#!/usr/bin/env python3
"""Generate docs sitemap entries in docs/index.html.

This script updates the block between:
  <!-- DOCS_SITEMAP_START -->
  <!-- DOCS_SITEMAP_END -->
with links to .md and .html files found in docs/.
"""

from __future__ import annotations

from pathlib import Path


START_MARKER = "<!-- DOCS_SITEMAP_START -->"
END_MARKER = "<!-- DOCS_SITEMAP_END -->"


def build_entries(docs_dir: Path) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for path in sorted(docs_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.name.startswith("."):
            continue
        if path.name == "index.html":
            continue
        if path.suffix.lower() not in {".md", ".html"}:
            continue
        rel = path.relative_to(docs_dir).as_posix()
        entries.append((rel, path.suffix.lower().lstrip(".")))
    return entries


def generate_block(entries: list[tuple[str, str]]) -> str:
    lines = []
    for rel, ext in entries:
        lines.append(
            f'          <li><a href="./{rel}">{rel}</a><span class="doc-tag">{ext}</span></li>'
        )
    if not lines:
        lines.append("          <li>No docs files found.</li>")
    return "\n".join(lines)


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    docs_dir = repo_root / "docs"
    index_path = docs_dir / "index.html"
    content = index_path.read_text(encoding="utf-8")

    start = content.find(START_MARKER)
    end = content.find(END_MARKER)
    if start == -1 or end == -1 or end < start:
        raise SystemExit("Could not find sitemap markers in docs/index.html")

    entries = build_entries(docs_dir)
    generated = generate_block(entries)

    block_start = start + len(START_MARKER)
    new_content = f"{content[:block_start]}\n{generated}\n          {content[end:]}"
    index_path.write_text(new_content, encoding="utf-8")
    print(f"Updated sitemap with {len(entries)} entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
