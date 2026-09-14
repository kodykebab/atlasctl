"""System and Machine images."""

from __future__ import annotations

import click
from atlas_client.api.images import delete_image, download_image, get_image, list_images
from atlas_client.models import DownloadImageArtifact, ListImagesImageTypeType0

from atlasctl.client import build_client
from atlasctl.enums import enum_choices
from atlasctl.errors import raise_for_response, require_parsed
from atlasctl.output import render_detail, render_json, render_table
from atlasctl.state import CliState

_LIST_COLUMNS = ["id", "title", "image_type", "status", "platform", "operating_system"]


@click.group()
def image() -> None:
    """List, inspect, download, and delete images."""


@image.command("list")
@click.option(
    "--image-type",
    "image_type",
    type=click.Choice(enum_choices(ListImagesImageTypeType0)),
)
@click.option("--limit", default=20, show_default=True)
@click.option("--offset", default=0, show_default=True)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def image_list(
    state: CliState, image_type: str | None, limit: int, offset: int, as_json: bool
) -> None:
    """List images visible to the current tenant (System images plus owned Machine images)."""
    region = state.region()
    response = list_images.sync_detailed(
        client=build_client(region),
        x_tenant_id=region.tenant_id,
        limit=limit,
        offset=offset,
        image_type=ListImagesImageTypeType0(image_type) if image_type else None,
    )
    page = require_parsed(response)
    click.echo(render_json(page.items) if as_json else render_table(page.items, _LIST_COLUMNS))


@image.command("get")
@click.argument("image_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def image_get(state: CliState, image_id: str, as_json: bool) -> None:
    """Show one image's artifact metadata and transfer state."""
    region = state.region()
    response = get_image.sync_detailed(
        image_id, client=build_client(region), x_tenant_id=region.tenant_id
    )
    item = require_parsed(response)
    click.echo(render_json(item) if as_json else render_detail(item))


@image.command("download")
@click.argument("image_id")
@click.option(
    "--artifact",
    type=click.Choice(enum_choices(DownloadImageArtifact)),
    default=DownloadImageArtifact.ROOTFS.value,
    show_default=True,
)
@click.pass_obj
def image_download(state: CliState, image_id: str, artifact: str) -> None:
    """Print a signed download URL for one image artifact."""
    region = state.region()
    response = download_image.sync_detailed(
        image_id,
        client=build_client(region),
        artifact=DownloadImageArtifact(artifact),
        x_tenant_id=region.tenant_id,
    )
    click.echo(render_detail(require_parsed(response)))


@image.command("delete")
@click.argument("image_id")
@click.pass_obj
def image_delete(state: CliState, image_id: str) -> None:
    """Retire an image. A cleanup job reclaims its stored artifacts."""
    region = state.region()
    response = delete_image.sync_detailed(
        image_id, client=build_client(region), x_tenant_id=region.tenant_id
    )
    raise_for_response(response)
    click.echo(f"retiring {image_id}")
