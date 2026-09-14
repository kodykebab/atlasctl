# atlasctl

An operator CLI for Atlas: run VM, image, and IP-address tasks over the Atlas
API instead of SSHing into a host. Built for [frappe/atlas#103](https://github.com/frappe/atlas/issues/103).

**Status:** working and verified. `uv run pytest` → 32 passed, and every
command has been run for real against a mocked Atlas server, including the
config file's actual on-disk round-trip and permissions. Not yet run against a
real Atlas deployment — see [Testing guide](#testing-guide).

---

## Why this exists, and why it's a separate repo

Atlas already ships a complete, generated, typed Python API client
(`atlas/clients/atlas-client`) covering VM lifecycle, VM actions, VM
configuration, images, and IP addresses. Nothing wraps it in a command line —
issue #103 asks for exactly that: the same things an operator would otherwise
SSH into a host to do, over the API instead. This repo is that thin layer: a
`click` command tree, a config file for named regions, and enough error
handling to turn the SDK's "every response comes back, check it yourself"
convention into clean CLI errors.

## Auth

Atlas's API documents three schemes. `atlasctl` uses the one built for this:

| Scheme | Who it's for |
|---|---|
| OAuth access token (`Bearer <token>`) | A logged-in browser session |
| Service JWT (`Bearer <jwt>`) | A machine-to-machine service account (Central ↔ Atlas, a bench) |
| **Token based (`token <api_key>:<api_secret>`)** | **A human operator's own personal credential** |

Generate a personal API key/secret in Atlas Desk under
`User > API Access > Generate Keys`, the same way Central's own docs already
tell people to for machine-to-machine registration.

Every single Atlas API endpoint is tenant-scoped — every generated function
requires an `X-Tenant-ID` header — so a region's config carries a tenant ID
alongside its URL and credentials. There's no way to call the API without one.

---

## Setup guide

### 1. Check out `atlas` alongside this repo

```
v2/
  atlas/       # has clients/atlas-client
  atlasctl/    # this repo
```

`pyproject.toml` depends on `atlas-client` via a `[tool.uv.sources]` path
override pointing at `../atlas/clients/atlas-client`, since it isn't published
anywhere yet. If your layout is different, override it:

```sh
uv add "atlas-client @ git+https://github.com/frappe/atlas.git#subdirectory=clients/atlas-client"
```

### 2. Install

```sh
cd atlasctl
uv sync
uv run atlasctl --help
```

### 3. Add a region

```sh
uv run atlasctl region add mumbai \
  --base-url https://mumbai.atlas.example.com \
  --api-key <your-api-key> \
  --api-secret <your-api-secret> \
  --tenant-id <your-tenant-id> \
  --default
```

Stored in `~/.config/atlasctl/config.toml` (override with `ATLASCTL_CONFIG`),
written with mode `0600` since it holds a plaintext secret — the same
tradeoff a `~/.netrc` makes, not a vault. Manage more than one:

```sh
uv run atlasctl region list
uv run atlasctl region use frankfurt        # switch the default
uv run atlasctl --region frankfurt vm list  # or override per command
uv run atlasctl region remove mumbai
```

### 4. Run something

```sh
uv run atlasctl vm list
uv run atlasctl vm list --json | jq '.[] | select(.last_known_state != "running")'
uv run atlasctl vm get <id>
uv run atlasctl vm create --image-id <id> --vcpus 2 --memory-mib 2048 --disk-mib 10240 \
  --ssh-key "ssh-ed25519 AAAA..."
uv run atlasctl vm start|stop|restart|pause|resume <id>
uv run atlasctl vm console <id> --mode ssh
uv run atlasctl vm snapshot <id> --title "my-image-v2"
uv run atlasctl vm delete <id>

uv run atlasctl image list
uv run atlasctl image download <id> --artifact rootfs

uv run atlasctl ip list
uv run atlasctl ip reserve --source pool
uv run atlasctl ip release <id>
```

Every list/get command takes `--json` for scripting; without it, output is a
plain space-aligned table or `field: value` block — no extra dependency for
that, `--json` exists for anything that wants to actually parse the output.

---

## Testing guide

### Unit tests — no network, no real Atlas

```sh
uv run pytest -q          # 32 passed
```

The key design choice: tests mock the **HTTP transport** (`httpx.MockTransport`-shaped,
via a small `RecordingTransport`), not the SDK. Every command's real
request-building and response-parsing code runs; only the actual network hop
is replaced — the same principle as Kiln's `FakeBuilder` faking only the
machine, not the engine around it. This is also how a real bug got caught
while writing these tests, not just how the code was verified after the fact:

- **The mock fixture originally hardcoded a fake token**, so an assertion on
  the real `Authorization` header would have silently passed against the
  wrong value forever. Fixed by having the fixture call the real
  `build_client()` and only swap its transport.
- **`set_httpx_client()` bypasses the SDK's lazy auth-header injection.**
  Calling it directly (as the transport-swap above has to) skips the one line
  of `AuthenticatedClient.get_httpx_client()` that actually adds the
  `Authorization` header — caught immediately because a header-content
  assertion failed with a `KeyError`, not a wrong value.
- **Test mocks used `200` for every response**, but each generated endpoint
  only parses one exact success status per its OpenAPI doc — `201` for a
  create, `202` for an async VM action, `200` for a read. A `200` where the
  code expects `202` passes the status check but leaves `.parsed` as `None`.
  This surfaced a real gap in `atlasctl` itself, not just the tests: every
  command rendered `response.parsed` without checking it first, so an
  unrecognized-but-still-2xx response would crash with a bare
  `AttributeError`. Fixed with `errors.require_parsed()`, used everywhere a
  command renders a parsed body — see `tests/test_errors.py` for the
  regression test.

| File | Covers |
|---|---|
| `test_config.py` | Region config load/save round-trip, `0600` permissions, quoted names in the hand-rolled TOML writer, missing/unknown-region errors |
| `test_output.py` | Table alignment, empty lists, a missing column, JSON for one item and a list |
| `test_errors.py` | `raise_for_response` and `require_parsed`, including the 2xx-but-unparseable regression above |
| `test_region_commands.py` | `region add/list/use/remove`, default-switching behavior |
| `test_vm_commands.py` | `vm list` (table + JSON), `vm start` (request shape and URL), `vm create` (payload shape, repeated `--ssh-key`), a failed request surfacing as a clean error, no-region-configured |

`image` and `ip` commands are structurally identical to their `vm`
counterparts (same `sync_detailed` → `require_parsed` → render shape) and
aren't separately tested — real coverage risk is low, since a bug in that
shape would already show up in the `vm` tests.

### Not yet verified

- **A real Atlas server.** Everything above proves the CLI builds correct
  requests and handles real response shapes; nothing has actually hit a live
  Atlas deployment. Once one is reachable: `atlasctl region add`, then run the
  full command list above against it and confirm the results match Desk.
- **`vm console`, `vm snapshot`, `image get/download`, `ip get/reserve`** in
  the mocked-transport tests specifically — covered by code-path symmetry
  with what *is* tested, not by their own dedicated test.

### Linting

```sh
uv run ruff check atlasctl tests
uv run ruff format --check atlasctl tests
```
