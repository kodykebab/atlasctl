"""The object every command receives via `@click.pass_obj`."""

from __future__ import annotations

from dataclasses import dataclass

from atlasctl.config import Config, Region


@dataclass
class CliState:
    """What every command needs: the loaded config and any --region override."""

    config: Config
    region_name: str | None

    def region(self) -> Region:
        return self.config.get(self.region_name)
