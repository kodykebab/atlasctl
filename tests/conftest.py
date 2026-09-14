from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest
from click.testing import CliRunner

from atlasctl.cli import main
from atlasctl.config import Config, Region, save_config

TEST_REGION = Region(
    name="test",
    base_url="https://atlas.example.com",
    api_key="key123",
    api_secret="secret456",
    tenant_id=42,
)


@pytest.fixture
def config_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "config.toml"
    monkeypatch.setenv("ATLASCTL_CONFIG", str(path))
    return path


@pytest.fixture
def configured(config_path: Path) -> Region:
    """A config file with one region ("test"), already the default."""
    save_config(Config(regions={"test": TEST_REGION}, default="test"))
    return TEST_REGION


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class RecordingTransport(httpx.BaseTransport):
    """A transport that records every request and returns a canned response."""

    def __init__(self, handler: Callable[[httpx.Request], httpx.Response]) -> None:
        self.handler = handler
        self.requests: list[httpx.Request] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self.handler(request)


@pytest.fixture
def mock_transport(monkeypatch: pytest.MonkeyPatch):
    """Patch atlasctl.client.build_client to return a client wired to a fake transport.

    Real generated request-building and response-parsing code runs — only the
    actual network hop is replaced, the same way FakeBuilder in Kiln replaces
    only the machine, not the engine around it.
    """
    recorder = RecordingTransport(handler=lambda request: httpx.Response(200, json={}))

    def _install(handler: Callable[[httpx.Request], httpx.Response]) -> RecordingTransport:
        recorder.handler = handler
        return recorder

    def fake_build_client(region):
        # Reuse the real build_client so the actual auth header gets built the
        # same way it would against a real server -- only the transport (the
        # network hop itself) is faked.
        from atlasctl.client import build_client

        client = build_client(region)
        # set_httpx_client bypasses get_httpx_client()'s lazy auth-header
        # injection entirely, so it has to be redone here explicitly using the
        # same client.prefix/token/auth_header_name production code would use.
        headers = {client.auth_header_name: f"{client.prefix} {client.token}"}
        client.set_httpx_client(
            httpx.Client(transport=recorder, base_url=region.base_url, headers=headers)
        )
        return client

    monkeypatch.setattr("atlasctl.commands.vm.build_client", fake_build_client)
    monkeypatch.setattr("atlasctl.commands.image.build_client", fake_build_client)
    monkeypatch.setattr("atlasctl.commands.ip.build_client", fake_build_client)
    return _install


def run_cli(runner: CliRunner, *args: str) -> object:
    return runner.invoke(main, args, catch_exceptions=False)


def json_response(status: int, body: dict) -> httpx.Response:
    return httpx.Response(status, content=json.dumps(body).encode())
