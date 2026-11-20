"""Terminal output: plain text, colour only on a TTY and only when NO_COLOR is unset."""

from __future__ import annotations

import os
import sys

_STYLES = {"dim": "2", "bold": "1", "ok": "32", "warn": "33", "err": "31", "info": "36"}
SYMBOLS = {"ok": "✔", "missing": "✘", "drift": "!", "outdated": "↑", "skipped": "·", "error": "✘"}


def _color() -> bool:
    return sys.stdout.isatty() and "NO_COLOR" not in os.environ


def paint(text: str, style: str | None) -> str:
    if not style or not _color():
        return text
    return f"\033[{_STYLES[style]}m{text}\033[0m"


def line(text: str = "", style: str | None = None) -> None:
    print(paint(text, style), flush=True)


def heading(text: str) -> None:
    line()
    line(text, "bold")


def status(state: str, label: str, detail: str = "") -> None:
    style = {"ok": "ok", "missing": "err", "error": "err", "drift": "warn", "outdated": "warn"}.get(state)
    sym = SYMBOLS.get(state, "?")
    line(f"  {paint(sym, style)} {label:<28} {detail}".rstrip())


def table(rows: list[list[str]], headers: list[str]) -> None:
    widths = [max(len(str(r[i])) for r in [headers, *rows]) for i in range(len(headers))]
    fmt = "  " + "  ".join(f"{{:<{w}}}" for w in widths)
    line(fmt.format(*headers), "bold")
    for row in rows:
        line(fmt.format(*row))
