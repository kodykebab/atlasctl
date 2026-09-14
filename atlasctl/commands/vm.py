"""VM lifecycle, actions, and configuration — the bulk of an operator's day."""

from __future__ import annotations

import click
from atlas_client.api.vm_actions import (
    create_virtual_machine_console_token,
    create_virtual_machine_snapshot,
    pause_virtual_machine,
    restart_virtual_machine,
    resume_virtual_machine,
    start_virtual_machine,
    stop_virtual_machine,
)
from atlas_client.api.vm_lifecycle import (
    create_virtual_machine,
    delete_virtual_machine,
    get_virtual_machine,
    list_virtual_machines,
)
from atlas_client.models import (
    ConsoleTokenPayload,
    ConsoleTokenPayloadMode,
    CreateVirtualMachinePayload,
    CreateVirtualMachinePayloadEgress,
    SnapshotPayload,
    SnapshotPayloadImageType,
)

from atlasctl.client import build_client
from atlasctl.enums import enum_choices
from atlasctl.errors import raise_for_response, require_parsed
from atlasctl.output import render_detail, render_json, render_table
from atlasctl.state import CliState

_LIST_COLUMNS = ["id", "last_known_state", "vcpus", "memory_mib", "disk_mib", "image_id"]


@click.group()
def vm() -> None:
    """List, create, and act on virtual machines."""


@vm.command("list")
@click.option("--limit", default=20, show_default=True)
@click.option("--offset", default=0, show_default=True)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def vm_list(state: CliState, limit: int, offset: int, as_json: bool) -> None:
    """List VMs in the current tenant, newest first."""
    region = state.region()
    response = list_virtual_machines.sync_detailed(
        client=build_client(region), x_tenant_id=region.tenant_id, limit=limit, offset=offset
    )
    page = require_parsed(response)
    click.echo(render_json(page.items) if as_json else render_table(page.items, _LIST_COLUMNS))


@vm.command("get")
@click.argument("virtual_machine_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def vm_get(state: CliState, virtual_machine_id: str, as_json: bool) -> None:
    """Show one VM's stored record, desired state, and current state."""
    region = state.region()
    response = get_virtual_machine.sync_detailed(
        virtual_machine_id, client=build_client(region), x_tenant_id=region.tenant_id
    )
    item = require_parsed(response)
    click.echo(render_json(item) if as_json else render_detail(item))


@vm.command("create")
@click.option("--image-id", required=True)
@click.option("--vcpus", required=True, type=int)
@click.option("--memory-mib", required=True, type=int)
@click.option("--disk-mib", required=True, type=int)
@click.option("--hostname", default="")
@click.option(
    "--egress",
    type=click.Choice(enum_choices(CreateVirtualMachinePayloadEgress)),
    default=CreateVirtualMachinePayloadEgress.UPLINK.value,
    show_default=True,
)
@click.option("--ssh-key", "ssh_keys", multiple=True, help="Repeatable.")
@click.option("--privileged", is_flag=True)
@click.pass_obj
def vm_create(
    state: CliState,
    image_id: str,
    vcpus: int,
    memory_mib: int,
    disk_mib: int,
    hostname: str,
    egress: str,
    ssh_keys: tuple[str, ...],
    privileged: bool,
) -> None:
    """Create a VM."""
    region = state.region()
    body = CreateVirtualMachinePayload(
        image_id=image_id,
        vcpus=vcpus,
        memory_mib=memory_mib,
        disk_mib=disk_mib,
        hostname=hostname,
        egress=CreateVirtualMachinePayloadEgress(egress),
        ssh_keys=list(ssh_keys),
        is_privileged=privileged,
    )
    response = create_virtual_machine.sync_detailed(
        client=build_client(region), body=body, x_tenant_id=region.tenant_id
    )
    click.echo(render_detail(require_parsed(response)))


@vm.command("delete")
@click.argument("virtual_machine_id")
@click.pass_obj
def vm_delete(state: CliState, virtual_machine_id: str) -> None:
    """Start VM termination. Poll `vm get` until it 404s to confirm cleanup."""
    region = state.region()
    response = delete_virtual_machine.sync_detailed(
        virtual_machine_id, client=build_client(region), x_tenant_id=region.tenant_id
    )
    raise_for_response(response)
    click.echo(f"terminating {virtual_machine_id}")


def _action_command(name: str, verb: str, module) -> click.Command:
    """Build one thin start/stop/restart/pause/resume command. They're all identical."""

    @click.command(name)
    @click.argument("virtual_machine_id")
    @click.pass_obj
    def action(state: CliState, virtual_machine_id: str) -> None:
        region = state.region()
        response = module.sync_detailed(
            virtual_machine_id, client=build_client(region), x_tenant_id=region.tenant_id
        )
        raise_for_response(response)
        click.echo(f"{verb} {virtual_machine_id}")

    action.help = f"{name.capitalize()} a VM. Poll `vm get` to observe completion."
    return action


vm.add_command(_action_command("start", "starting", start_virtual_machine))
vm.add_command(_action_command("stop", "stopping", stop_virtual_machine))
vm.add_command(_action_command("restart", "restarting", restart_virtual_machine))
vm.add_command(_action_command("pause", "pausing", pause_virtual_machine))
vm.add_command(_action_command("resume", "resuming", resume_virtual_machine))


@vm.command("console")
@click.argument("virtual_machine_id")
@click.option(
    "--mode",
    type=click.Choice(enum_choices(ConsoleTokenPayloadMode)),
    default=ConsoleTokenPayloadMode.TTY.value,
    show_default=True,
)
@click.pass_obj
def vm_console(state: CliState, virtual_machine_id: str, mode: str) -> None:
    """Mint a single-use console token (expires in 60 seconds)."""
    region = state.region()
    response = create_virtual_machine_console_token.sync_detailed(
        virtual_machine_id,
        client=build_client(region),
        body=ConsoleTokenPayload(mode=ConsoleTokenPayloadMode(mode)),
        x_tenant_id=region.tenant_id,
    )
    click.echo(render_detail(require_parsed(response)))


@vm.command("snapshot")
@click.argument("virtual_machine_id")
@click.option("--title", required=True)
@click.option(
    "--image-type",
    type=click.Choice(enum_choices(SnapshotPayloadImageType)),
    default=SnapshotPayloadImageType.MACHINE.value,
    show_default=True,
)
@click.option("--memory-snapshot", is_flag=True, help="Also record VM shape for warm starts.")
@click.pass_obj
def vm_snapshot(
    state: CliState, virtual_machine_id: str, title: str, image_type: str, memory_snapshot: bool
) -> None:
    """Snapshot a VM's disk into a reusable image."""
    region = state.region()
    response = create_virtual_machine_snapshot.sync_detailed(
        virtual_machine_id,
        client=build_client(region),
        body=SnapshotPayload(
            title=title,
            image_type=SnapshotPayloadImageType(image_type),
            memory_snapshot=memory_snapshot,
        ),
        x_tenant_id=region.tenant_id,
    )
    click.echo(render_detail(require_parsed(response)))
