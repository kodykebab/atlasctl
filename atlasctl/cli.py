"""The command line. `click` groups mirror atlas_client's own tag groups
(vm lifecycle/actions/configuration, images, IP addresses) so the command
tree reads the same way the API it calls is documented.
"""

from __future__ import annotations

import click

from atlasctl.commands import image, ip, region, vm
from atlasctl.config import load_config
from atlasctl.state import CliState


@click.group()
@click.option(
    "--region", "region_name", default=None, help="Use this region instead of the default."
)
@click.pass_context
def main(ctx: click.Context, region_name: str | None) -> None:
    """Operator CLI for Atlas: run VM/image/IP tasks over the API, no SSH required."""
    ctx.obj = CliState(config=load_config(), region_name=region_name)


main.add_command(region.region)
main.add_command(vm.vm)
main.add_command(image.image)
main.add_command(ip.ip)


def run() -> None:
    """The installed console-script entry point (see pyproject.toml).

    click.ClickException gets click's own formatting (usage errors, bad
    options). Everything else -- AtlasCtlError, a network failure, a
    corrupted config file, anything -- becomes the same one-line message.
    This is the tool's single top-level boundary; its whole job is making
    sure no failure of any kind reaches the operator as a raw traceback, so
    the catch here is deliberately broad rather than an allowlist that the
    next new failure mode would just slip through.
    """
    try:
        main(standalone_mode=False)
    except click.ClickException as error:
        error.show()
        raise SystemExit(error.exit_code) from error
    except Exception as error:
        raise SystemExit(f"error: {error}") from error


if __name__ == "__main__":
    run()
