"""Render a response model, or a list of them, as a table or as JSON.

Every generated model has a `to_dict()` — that's the one thing both renderers
need, so neither has to know Atlas's actual response shapes.
"""

from __future__ import annotations

import json
from typing import Any, Protocol


class ToDict(Protocol):
    def to_dict(self) -> dict[str, Any]: ...


def _cell(value: Any) -> str:
    """Render one field value for a human. A field that is present but None
    (a nullable field the generated models always include, such as
    IPAddressResponse.virtual_machine_id when unattached) renders blank, not
    as the literal text "None"."""
    return "" if value is None else str(value)


def render_json(item: ToDict | list[ToDict]) -> str:
    """Dump one item, or a list of them, as indented JSON."""
    if isinstance(item, list):
        return json.dumps([row.to_dict() for row in item], indent=2, default=str)
    return json.dumps(item.to_dict(), indent=2, default=str)


def render_table(items: list[ToDict], columns: list[str]) -> str:
    """Render `columns` from each item as simple space-aligned text.

    Deliberately dependency-free: no rich/tabulate, just aligned columns. Good
    enough for a terminal, and `--json` exists for anything that wants to
    parse the output.
    """
    if not items:
        return "(none)"

    rows = [[_cell(row.to_dict().get(column)) for column in columns] for row in items]
    widths = [
        max(len(columns[index]), *(len(row[index]) for row in rows))
        for index in range(len(columns))
    ]

    def format_row(values: list[str]) -> str:
        return "  ".join(value.ljust(width) for value, width in zip(values, widths, strict=True))

    lines = [
        format_row([column.upper() for column in columns]),
        format_row(["-" * w for w in widths]),
    ]
    lines.extend(format_row(row) for row in rows)
    return "\n".join(lines)


def render_detail(item: ToDict) -> str:
    """Render one item as aligned `field: value` lines."""
    data = item.to_dict()
    width = max((len(key) for key in data), default=0)
    return "\n".join(f"{key.ljust(width)}  {_cell(value)}" for key, value in data.items())
