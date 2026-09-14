"""Build an authenticated Atlas API client from a Region.

Atlas's API documents three auth schemes (see the OpenAPI spec's
`securitySchemes`): an OAuth access token, a Central/Atlas service JWT, and
Frappe's own `token <api_key>:<api_secret>` scheme. The first two are for a
logged-in browser session or a machine-to-machine service account; the third
is the standard way a human generates a personal credential for their own
scripts (`User > API Access > Generate Keys` in Desk) — the right default for
an operator's CLI.
"""

from __future__ import annotations

from atlas_client import AuthenticatedClient

from atlasctl.config import Region


def build_client(region: Region) -> AuthenticatedClient:
    """Return a client authenticated as `region`'s API key, using Frappe's token scheme."""
    return AuthenticatedClient(
        base_url=region.base_url,
        token=f"{region.api_key}:{region.api_secret}",
        prefix="token",
    )
