"""Named regions: where to reach one Atlas deployment and how to authenticate to it.

Every Atlas API call is tenant-scoped (every generated endpoint requires an
`X-Tenant-ID` header), so a region's config carries a tenant ID alongside its
URL and credentials — there is no way to call the API without one.

Stored as TOML at `ATLASCTL_CONFIG` (default `~/.config/atlasctl/config.toml`),
written with mode 0600 since it holds API secrets in plain text — the same
tradeoff a `~/.netrc` or `~/.aws/credentials` file makes, not a vault.
"""

from __future__ import annotations

import json
import os
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path

from atlasctl.errors import AtlasCtlError


@dataclass(frozen=True)
class Region:
    """One Atlas deployment: where it is, and how to authenticate to it."""

    name: str
    base_url: str
    api_key: str
    api_secret: str
    tenant_id: int


def config_path() -> Path:
    override = os.environ.get("ATLASCTL_CONFIG")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".config" / "atlasctl" / "config.toml"


@dataclass
class Config:
    """Every configured region, plus which one is the default."""

    regions: dict[str, Region]
    default: str | None = None

    def get(self, name: str | None) -> Region:
        """Return the named region, or the default when `name` is None."""
        selected = name or self.default
        if selected is None:
            raise AtlasCtlError(
                "no region given and no default set. Run `atlasctl region add` or pass --region."
            )
        if selected not in self.regions:
            raise AtlasCtlError(
                f"no region named {selected!r}. Configured: {', '.join(self.regions) or '(none)'}"
            )
        return self.regions[selected]


def load_config() -> Config:
    """Read the config file, or return an empty config if it doesn't exist yet."""
    path = config_path()
    if not path.is_file():
        return Config(regions={})

    data = tomllib.loads(path.read_text())
    regions = {name: Region(name=name, **fields) for name, fields in data.get("region", {}).items()}
    return Config(regions=regions, default=data.get("default"))


def save_config(config: Config) -> None:
    """Write the config file atomically, with owner-only permissions."""
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    if config.default:
        lines.append(f"default = {json.dumps(config.default)}")
        lines.append("")
    for region in config.regions.values():
        lines.append(f"[region.{json.dumps(region.name)}]")
        for key, value in asdict(region).items():
            if key == "name":
                continue
            lines.append(f"{key} = {_toml_value(value)}")
        lines.append("")

    temporary = path.with_suffix(".tmp")
    temporary.write_text("\n".join(lines))
    temporary.chmod(0o600)
    temporary.replace(path)


def _toml_value(value: object) -> str:
    """Render one TOML value. A string goes through json.dumps.

    TOML basic-string escaping and JSON string escaping agree on every
    character that matters here (`"`, `\\`, and every control character
    become `\\n`-style or `\\u00XX` escapes in both), so this handles a
    credential containing a newline, a tab, or any other control character
    correctly instead of only the two characters an earlier version of this
    function happened to think of.
    """
    if isinstance(value, str):
        return json.dumps(value)
    return str(value)
