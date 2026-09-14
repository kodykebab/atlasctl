from __future__ import annotations

import httpx
import pytest

from atlasctl.errors import AtlasCtlError
from tests.conftest import json_response, run_cli

VM = {
    "id": "vm-001",
    "tenant_id": 42,
    "image_id": "img-1",
    "vcpus": 2,
    "memory_mib": 2048,
    "disk_mib": 10240,
    "created_at": 1_700_000_000,
    "sleep_after_idle_seconds": 0,
}
VM_LIST_ITEM = {**VM, "last_known_state": "running", "state_synced_at": 1_700_000_100}


def test_vm_list_renders_a_table(configured, runner, mock_transport):
    captured = mock_transport(
        lambda request: json_response(
            200, {"items": [VM_LIST_ITEM], "limit": 20, "offset": 0, "has_more": False}
        )
    )

    result = run_cli(runner, "vm", "list")

    assert result.exit_code == 0, result.output
    assert "vm-001" in result.output
    assert "running" in result.output
    request = captured.requests[0]
    assert request.url.path == "/api/atlas/virtual-machines"
    assert request.headers["X-Tenant-ID"] == "42"
    assert request.headers["Authorization"] == "token key123:secret456"


def test_vm_list_json_output_is_parseable(configured, runner, mock_transport):
    mock_transport(
        lambda request: json_response(
            200, {"items": [VM_LIST_ITEM], "limit": 20, "offset": 0, "has_more": False}
        )
    )

    result = run_cli(runner, "vm", "list", "--json")

    import json

    parsed = json.loads(result.output)
    assert parsed[0]["id"] == "vm-001"


def test_vm_start_sends_the_action_request(configured, runner, mock_transport):
    captured = mock_transport(lambda request: json_response(202, VM))

    result = run_cli(runner, "vm", "start", "vm-001")

    assert result.exit_code == 0, result.output
    assert "starting vm-001" in result.output
    request = captured.requests[0]
    assert request.method == "POST"
    assert request.url.path == "/api/atlas/virtual-machines/vm-001/actions/start"


def test_vm_create_sends_the_configured_shape(configured, runner, mock_transport):
    captured = mock_transport(lambda request: json_response(201, VM))

    result = run_cli(
        runner,
        "vm",
        "create",
        "--image-id",
        "img-1",
        "--vcpus",
        "2",
        "--memory-mib",
        "2048",
        "--disk-mib",
        "10240",
        "--ssh-key",
        "ssh-ed25519 AAAA one",
        "--ssh-key",
        "ssh-ed25519 AAAA two",
    )

    assert result.exit_code == 0, result.output
    import json

    body = json.loads(captured.requests[0].content)
    assert body["image_id"] == "img-1"
    assert body["ssh_keys"] == ["ssh-ed25519 AAAA one", "ssh-ed25519 AAAA two"]
    assert body["egress"] == "uplink"


def test_a_failed_request_surfaces_as_a_clean_error(configured, runner, mock_transport):
    mock_transport(lambda request: httpx.Response(404, content=b"not found"))

    with pytest.raises(AtlasCtlError, match="404"):
        run_cli(runner, "vm", "get", "vm-missing")


def test_no_region_configured_is_a_clean_error(config_path, runner):
    with pytest.raises(AtlasCtlError, match="no region given"):
        run_cli(runner, "vm", "list")
