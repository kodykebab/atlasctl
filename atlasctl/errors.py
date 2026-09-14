"""The one exception type atlasctl raises on purpose."""

from __future__ import annotations

from typing import TypeVar

T = TypeVar("T")


class AtlasCtlError(Exception):
    """A user-facing failure: bad config, a bad flag, or a failed API call."""


def raise_for_response(response) -> None:
    """Turn a non-2xx API response into a clean AtlasCtlError.

    The generated client returns every response, successful or not, rather
    than raising — callers are expected to check `status_code`. This is the
    one place that check happens, so every command gets the same error shape.
    """
    if 200 <= response.status_code < 300:
        return
    detail = response.content.decode(errors="replace").strip()
    raise AtlasCtlError(f"{response.status_code}: {detail[:500] or '(no response body)'}")


def require_parsed(response) -> T:
    """Return `response.parsed`, raising if the status was bad or the body was unparseable.

    Each generated endpoint only populates `.parsed` for the one exact status
    code its OpenAPI doc names (201 for a create, 202 for an async action, 200
    for a read, ...) — a 2xx response on a code that particular function
    doesn't recognize still passes `raise_for_response` but leaves `.parsed`
    as `None`. Rendering that `None` crashes deep inside `output.py` with an
    unhelpful AttributeError; this turns it into one clear error instead.
    """
    raise_for_response(response)
    if response.parsed is None:
        raise AtlasCtlError(
            f"Atlas returned {response.status_code} with a body this version of atlasctl "
            "doesn't recognize. Run with an updated atlas-client, or inspect the raw response."
        )
    return response.parsed
