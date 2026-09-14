from __future__ import annotations

import json

from atlasctl.output import render_detail, render_json, render_table


class Row:
    def __init__(self, **fields):
        self._fields = fields

    def to_dict(self):
        return self._fields


def test_render_table_aligns_columns():
    rows = [Row(id="short", state="running"), Row(id="a-much-longer-id", state="stopped")]

    table = render_table(rows, ["id", "state"])
    lines = table.splitlines()

    assert lines[0].startswith("ID")
    assert lines[2].startswith("short")
    # the header and both data rows all end up the same width
    assert len({len(line) for line in lines}) == 1


def test_render_table_handles_an_empty_list():
    assert render_table([], ["id"]) == "(none)"


def test_render_table_uses_empty_string_for_a_missing_column():
    table = render_table([Row(id="x")], ["id", "missing"])
    assert "x" in table


def test_render_json_single_item():
    assert json.loads(render_json(Row(id="x", n=1))) == {"id": "x", "n": 1}


def test_render_json_list():
    assert json.loads(render_json([Row(id="a"), Row(id="b")])) == [{"id": "a"}, {"id": "b"}]


def test_render_detail_lists_every_field():
    detail = render_detail(Row(id="x", state="running"))
    assert "id" in detail
    assert "x" in detail
    assert "state" in detail
    assert "running" in detail


def test_render_table_shows_a_present_none_field_as_blank_not_the_word_none():
    # Regression: IPAddressResponse.virtual_machine_id is always present in
    # to_dict(), with value None when unattached -- str(None) used to render
    # the literal text "None" in that column instead of blank.
    table = render_table([Row(id="ip-1", virtual_machine_id=None)], ["id", "virtual_machine_id"])
    data_line = table.splitlines()[2]
    assert "None" not in data_line


def test_render_detail_shows_a_none_field_as_blank():
    detail = render_detail(Row(id="x", transfer_error=None))
    line = next(line for line in detail.splitlines() if line.startswith("transfer_error"))
    assert line.strip() == "transfer_error"
