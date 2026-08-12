# AGENTS.md — seerr-mcp

MCP server exposing Seerr's v1 REST API (OpenAPI 3.0.2) as tools so an LLM can
read and manage a Seerr instance: search and discovery, media requests and
approvals, users, issues, watchlists and blocklists, Plex/Jellyfin/Emby and
Sonarr/Radarr settings, notification agents, jobs, and more. Full surface —
reads and writes. Uses FastMCP, `uv` for deps.

Exposed as **15 resource-scoped portmanteau tools**, not one tool per endpoint — see "Tool registry and the spec" below. A prior version registered all 208 endpoints individually; that blew the MCP context budget (~208 tools × ~250 tokens ≈ 52k tokens just for this one server) and has been retired. Seerr's own domain shape (settings-heavy — `seerr_settings_general` + `seerr_settings_notifications` alone cover 82/208 endpoints) means its `_GROUPS` taxonomy is its own, not shared with radarr/sonarr/bookshelf.

## Testing
- Offline suite: `make test` (or `uv run pytest`)
- Live integration (needs `SEERR_URL`/`SEERR_API_KEY`): `make test-integration`
  - GET endpoints run against the live instance.
  - POST/PUT/DELETE only run when `SEERR_WRITE_TESTS=1`, as a safe
    create→delete cycle against a scratch blocklist entry, then cleanup.
    Never point write tests at a production instance.

## Tool registry and the spec
- `_TOOL_REGISTRY` in `seerr_mcp.py` is generated from the vendored spec at
  `tests/data/seerr_openapi.yml` (pinned to seerr-team/seerr develop HEAD
  `39ff48c650d30ced0516574c55914d0bd26c9983`). It lists every JSON-producing
  endpoint under `/api/v1`.
- Excluded on purpose: the deprecated `/blacklist/*` aliases (sunset
  2026-06-01) — the `/blocklist/*` routers cover the same handlers. `_req`
  JSON-decodes every response.
- To add a tool or refresh coverage, regenerate the registry from a newer
  `seerr-api.yml`:
  ```
  uv run python scripts/generate_registry.py
  ```
  then splice the printed `_TOOL_REGISTRY` into `seerr_mcp.py`, update the SHA
  in `tests/data/README.md`/`seerr_mcp.py`/`AGENTS.md`, and re-run the tests.
  Do not hand-edit the registry.
- Endpoint function naming (internal, no longer an MCP tool name):
  `seerr_<verb>_<resource>` derived from method + path (e.g.
  `seerr_list_request`, `seerr_create_request`, `seerr_delete_request`,
  `seerr_set_request_status`). Flagship/action endpoint overrides and collision
  fixes live in `NAME_OVERRIDES` in `scripts/generate_registry.py`.

## Portmanteau registration — **do not go back to one tool per endpoint**
- `_GROUPS` buckets every `_TOOL_REGISTRY` name into one of 15 resource groups (`seerr_requests`, `seerr_settings_notifications`, `seerr_discover`, ...). `register_tools()` registers exactly one MCP tool per group via `_register_group`, which wraps the group's endpoint functions in a single `dispatch(operation, arguments)` closure. The endpoint functions themselves are unchanged — they're plain callables looked up by name, not separately-registered tools.
- `operation` is typed `Literal[<the group's endpoint names>]`, so FastMCP/pydantic validates it against the real endpoint list before `dispatch` ever runs — an invalid operation never reaches the group tool's body.
- Adding a new endpoint: add its entry to `_TOOL_REGISTRY` as before, then add its name to exactly one group in `_GROUPS`. `tests/test_tools.py::test_all_registry_names_grouped` fails if you forget.
- New resource area big enough to need its own group (rare): add a new `_GROUPS` key. Keep the total group count at or under ~15 — that ceiling is the entire point of this pattern.
- If you're tempted to add a per-endpoint `@mcp.tool` or an extra `mcp.add_tool` call outside `_register_group`, don't — every endpoint must be reachable only via its group's `operation` enum. A 208-tool server (one per endpoint) previously cost ~52k tokens of system-prompt budget on every session start; the 15-tool grouped version costs roughly a tenth of that.

## Annotations convention
- A group tool is `readOnlyHint=True` (`READONLY`) only when *every* operation in it is a GET that isn't also `force_write` (e.g. `seerr_system_status`, `seerr_media_titles`). Mixed groups carry no hints.
- Exception carried into the group logic: `GET /settings/discover/reset` (`seerr_reset_discover_sliders`) is a mutative GET and carries `force_write: True` in its registry entry — `_register_group` treats it as a non-GET when deciding a group's annotation, and its operation line in the group tool's description gets a `(WRITE — a GET that mutates state)` note. It happens to live in `seerr_settings_general`, which is already mixed, so this doesn't currently change that group's annotation — but keep the logic if you ever isolate it into its own group.
- Per-operation write/destructive notes survive in the group tool's description: each operation line still ends with its original one-line doc, and destructive/write endpoints keep a `WRITE:`/`DESTRUCTIVE:` note in that doc string (see `_TOOL_REGISTRY`'s `doc` field).
- `READONLY`/`WRITE`/`DESTRUCTIVE` constants are kept for reference and for any future per-operation annotation work, but only `READONLY` is actually applied today (to all-GET, non-force_write groups).

## Auth and base path
- Auth: `X-Api-Key` header (generate in Seerr Settings > General). Not bearer.
  Optional `X-API-User` header impersonates a user id (default: user 1);
  wire it via the `SEERR_API_USER` env var in `build_client`.
- `build_client` appends `/api/v1` to the origin; every registered tool carries
  its spec path (`/status`, `/request`, ...). `_req` raises `ToolError` with
  the API status and message on `>=400`.

## Release workflow
Always use the `make bump-*` targets to bump the version (`uv version --bump
patch|minor|major`), which updates `pyproject.toml` and `uv.lock` together. Do
NOT edit the version by hand.

- Bump: `make bump-patch` (or `bump-minor` / `bump-major`)
- Commit message is **just the version**, e.g. `0.1.2` — nothing else.
- Tag it `v<version>` (e.g. `v0.1.2`).
- Push main and the tag:
  ```
  git push origin main
  git push origin v<version>
  ```
- If a copy of the server is used by opencode under
  `/home/savagecore/Documents/christopfarr/mcp/seerr-mcp`, sync it. If it is
  deployed to the Proxmox host, follow the pattern in the other `-mcp`
  servers: push tags, sync the project copy, then
  `ssh root@192.168.50.3 -- 'cd /root/seerr-mcp && git fetch origin && git reset --hard origin/main && uv tool install --force .'`.

## Initial state
Version starts at `0.0.0` in the initial commit. No tag on the scaffold
commit; releases begin at the first `make bump-*`.
