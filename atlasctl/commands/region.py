"""Add, list, switch between, and remove configured regions."""

from __future__ import annotations

import click

from atlasctl.config import Region, save_config
from atlasctl.state import CliState


@click.group()
def region() -> None:
    """Manage named Atlas regions: where each one is, and how to authenticate to it."""


@region.command("add")
@click.argument("name")
@click.option("--base-url", required=True, help="e.g. https://mumbai.atlas.example.com")
@click.option("--api-key", required=True)
@click.option("--api-secret", required=True)
@click.option("--tenant-id", required=True, type=int, help="Every Atlas API call is tenant-scoped.")
@click.option("--default", "make_default", is_flag=True, help="Make this the default region.")
@click.pass_obj
def add(
    state: CliState,
    name: str,
    base_url: str,
    api_key: str,
    api_secret: str,
    tenant_id: int,
    make_default: bool,
) -> None:
    """Add or replace a region named NAME."""
    config = state.config
    config.regions[name] = Region(
        name=name, base_url=base_url, api_key=api_key, api_secret=api_secret, tenant_id=tenant_id
    )
    if make_default or config.default is None:
        config.default = name
    save_config(config)
    suffix = " (default)" if config.default == name else ""
    click.echo(f"added region {name!r}{suffix}")


@region.command("list")
@click.pass_obj
def list_regions(state: CliState) -> None:
    """List every configured region."""
    if not state.config.regions:
        click.echo("no regions configured. Run `atlasctl region add`.")
        return
    for name, one_region in state.config.regions.items():
        marker = "*" if name == state.config.default else " "
        click.echo(f"{marker} {name}  {one_region.base_url}  tenant={one_region.tenant_id}")


@region.command("use")
@click.argument("name")
@click.pass_obj
def use(state: CliState, name: str) -> None:
    """Make NAME the default region."""
    state.config.get(name)  # raises AtlasCtlError if NAME is unknown
    state.config.default = name
    save_config(state.config)
    click.echo(f"default region is now {name!r}")


@region.command("remove")
@click.argument("name")
@click.pass_obj
def remove(state: CliState, name: str) -> None:
    """Remove a configured region."""
    state.config.get(name)  # raises AtlasCtlError if NAME is unknown
    del state.config.regions[name]
    if state.config.default == name:
        state.config.default = None
    save_config(state.config)
    click.echo(f"removed region {name!r}")
