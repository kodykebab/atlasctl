from __future__ import annotations

import pytest

from atlasctl.cli import run


def test_run_turns_any_exception_into_a_clean_system_exit(monkeypatch):
    # Regression: run() used to only catch AtlasCtlError and click.ClickException,
    # so an httpx network error (or, as found separately, a corrupted config
    # file's tomllib.TOMLDecodeError) reached the operator as a raw traceback.
    # A plain RuntimeError stands in here for "any exception type nobody
    # explicitly listed" -- the whole point of the fix is that the type
    # shouldn't matter.
    def boom(*args, **kwargs):
        raise RuntimeError("connection refused")

    monkeypatch.setattr("atlasctl.cli.main", boom)

    with pytest.raises(SystemExit) as excinfo:
        run()

    assert "error: connection refused" in str(excinfo.value)


def test_run_still_shows_click_usage_errors_as_click_does(monkeypatch):
    import click

    def boom(*args, **kwargs):
        raise click.UsageError("bad flag")

    monkeypatch.setattr("atlasctl.cli.main", boom)

    with pytest.raises(SystemExit) as excinfo:
        run()

    assert excinfo.value.code == 2  # click.UsageError's own exit code
