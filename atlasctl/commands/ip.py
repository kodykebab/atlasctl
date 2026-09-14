"""Reserved public IP addresses."""

from __future__ import annotations

import click
from atlas_client.api.ip_addresses import (
    get_ip_address,
    list_ip_addresses,
    release_ip_address,
    reserve_ip_address,
)
from atlas_client.models import ReserveIPAddressPayload, ReserveIPAddressPayloadSource

from atlasctl.client import build_client
from atlasctl.enums import enum_choices
from atlasctl.errors import raise_for_response, require_parsed
from atlasctl.output import render_detail, render_json, render_table
from atlasctl.state import CliState

_LIST_COLUMNS = ["id", "address", "state", "virtual_machine_id"]


@click.group()
def ip() -> None:
    """List, reserve, and release IP addresses."""


@ip.command("list")
@click.option("--limit", default=20, show_default=True)
@click.option("--offset", default=0, show_default=True)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def ip_list(state: CliState, limit: int, offset: int, as_json: bool) -> None:
    """List IP addresses reserved by the current tenant."""
    region = state.region()
    response = list_ip_addresses.sync_detailed(
        client=build_client(region), x_tenant_id=region.tenant_id, limit=limit, offset=offset
    )
    page = require_parsed(response)
    click.echo(render_json(page.items) if as_json else render_table(page.items, _LIST_COLUMNS))


@ip.command("get")
@click.argument("ip_address_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def ip_get(state: CliState, ip_address_id: str, as_json: bool) -> None:
    """Show one IP address's attachment state and VM assignment."""
    region = state.region()
    response = get_ip_address.sync_detailed(
        ip_address_id, client=build_client(region), x_tenant_id=region.tenant_id
    )
    item = require_parsed(response)
    click.echo(render_json(item) if as_json else render_detail(item))


@ip.command("reserve")
@click.option(
    "--source",
    type=click.Choice(enum_choices(ReserveIPAddressPayloadSource)),
    default=ReserveIPAddressPayloadSource.POOL.value,
    show_default=True,
)
@click.pass_obj
def ip_reserve(state: CliState, source: str) -> None:
    """Reserve one IP address for the current tenant."""
    region = state.region()
    response = reserve_ip_address.sync_detailed(
        client=build_client(region),
        body=ReserveIPAddressPayload(source=ReserveIPAddressPayloadSource(source)),
        x_tenant_id=region.tenant_id,
    )
    click.echo(render_detail(require_parsed(response)))


@ip.command("release")
@click.argument("ip_address_id")
@click.pass_obj
def ip_release(state: CliState, ip_address_id: str) -> None:
    """Return an unattached IP address to the shared pool."""
    region = state.region()
    response = release_ip_address.sync_detailed(
        ip_address_id, client=build_client(region), x_tenant_id=region.tenant_id
    )
    raise_for_response(response)
    click.echo(f"released {ip_address_id}")
