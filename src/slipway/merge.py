"""The 3-way rule for config records (omp modelRoles, task.agentModelOverrides, modelPresets, ...).

For every key: compare the live value, the value Slipway last wrote, and the manifest value.

| live | last  | manifest | result                                        |
|------|-------|----------|-----------------------------------------------|
| =M   | any   | M        | in sync (adopt: remember M as last written)   |
| none | none  | M        | set M                                         |
| L    | L     | M        | update to M (user never touched it)           |
| none | L     | M        | drift: user removed it; keep removed          |
| U    | L/none| M        | drift: user value U wins                      |
| L    | L     | (gone)   | remove (manifest dropped the key)             |
| U    | L     | (gone)   | forget; user's value stays                    |

`force=True` turns every drift row into "write M".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

MISSING: Any = object()


@dataclass
class MergeResult:
    value: dict[str, Any]
    written: dict[str, Any]
    changes: list[str] = field(default_factory=list)
    drift: list[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.changes)


def merge_record(
    live: dict[str, Any], last: dict[str, Any], desired: dict[str, Any], force: bool = False
) -> MergeResult:
    value = dict(live)
    written: dict[str, Any] = {}
    result = MergeResult(value, written)
    for key in sorted(set(desired) | set(last)):
        want = desired.get(key, MISSING)
        prev = last.get(key, MISSING)
        have = live.get(key, MISSING)
        if want is MISSING:
            if have is not MISSING and have == prev:
                del value[key]
                result.changes.append(f"remove {key}")
            continue
        if have == want:
            written[key] = want
        elif have is MISSING and (prev is MISSING or force):
            value[key] = want
            written[key] = want
            result.changes.append(f"set {key} = {_short(want)}")
        elif have is not MISSING and (have == prev or force):
            value[key] = want
            written[key] = want
            result.changes.append(f"update {key}: {_short(have)} -> {_short(want)}")
        elif have is MISSING:
            written[key] = prev
            result.drift.append(f"{key}: removed locally (manifest wants {_short(want)})")
        else:
            if prev is not MISSING:
                written[key] = prev
            result.drift.append(f"{key}: local {_short(have)} (manifest wants {_short(want)})")
    return result


def _short(value: Any) -> str:
    text = value if isinstance(value, str) else repr(value)
    return text if len(text) <= 60 else text[:57] + "..."
