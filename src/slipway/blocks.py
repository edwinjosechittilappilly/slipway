"""Managed blocks inside user-owned Markdown files (AGENTS.md, CLAUDE.md, ...).

A block looks like:

    <!-- slipway:begin rules sha256=0123abcd -->
    ...content...
    <!-- slipway:end rules -->

The hash in the begin marker is the hash of the content Slipway wrote. If the content no longer matches, the user
edited the block, so Slipway leaves it alone unless forced. The hash travels with the file, so this works on any
machine and for teammates, without local state.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class BlockResult:
    action: str  # created | updated | unchanged | edited | removed | absent
    path: Path


def _digest(content: str) -> str:
    return hashlib.sha256(content.strip().encode()).hexdigest()[:16]


def _pattern(block_id: str) -> re.Pattern[str]:
    return re.compile(
        rf"<!-- slipway:begin {re.escape(block_id)}(?: sha256=(?P<hash>[0-9a-f]+))? -->\n"
        rf"(?P<body>.*?)\n?<!-- slipway:end {re.escape(block_id)} -->",
        re.DOTALL,
    )


def render(block_id: str, content: str) -> str:
    body = content.strip()
    return f"<!-- slipway:begin {block_id} sha256={_digest(body)} -->\n{body}\n<!-- slipway:end {block_id} -->"


def inspect(path: Path, block_id: str, content: str) -> str:
    """Return created | unchanged | updated | edited without writing (what upsert would do)."""
    if not path.exists():
        return "created"
    match = _pattern(block_id).search(path.read_text(encoding="utf-8"))
    if not match:
        return "created"
    body = match.group("body").strip()
    if body == content.strip():
        return "unchanged"
    if match.group("hash") and match.group("hash") == _digest(body):
        return "updated"
    return "edited"


def upsert(path: Path, block_id: str, content: str, force: bool = False, dry_run: bool = False) -> BlockResult:
    action = inspect(path, block_id, content)
    if action == "unchanged" or (action == "edited" and not force):
        return BlockResult(action, path)
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    block = render(block_id, content)
    pattern = _pattern(block_id)
    if pattern.search(text):
        new = pattern.sub(lambda _m: block, text, count=1)
    else:
        new = f"{text.rstrip(chr(10))}\n\n{block}\n" if text.strip() else f"{block}\n"
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(new, encoding="utf-8")
    return BlockResult("updated" if action == "edited" else action, path)


def remove(path: Path, block_id: str, dry_run: bool = False) -> BlockResult:
    if not path.exists():
        return BlockResult("absent", path)
    text = path.read_text(encoding="utf-8")
    match = _pattern(block_id).search(text)
    if not match:
        return BlockResult("absent", path)
    # Join the text around the block with one blank line; leave the rest of the user's file untouched.
    before, after = text[: match.start()].rstrip("\n"), text[match.end() :].lstrip("\n")
    new = f"{before}\n\n{after}" if before and after else (f"{before}\n" if before else after)
    if not dry_run:
        path.write_text(new, encoding="utf-8")
    return BlockResult("removed", path)
