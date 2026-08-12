# AGENTS.md — seerr-mcp

MCP server exposing Seerr's v1 REST API (OpenAPI 3.0.2) as tools so an LLM can
read and manage a Seerr instance: search and discovery, media requests and
approvals, users, issues, watchlists and blocklists, Plex/Jellyfin/Emby and
Sonarr/Radarr settings, notification agents, jobs, and more. Full surface —
reads and writes. Uses FastMCP, `uv` for deps.

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
- Tool naming: `seerr_<verb>_<resource>` derived from method + path (e.g.
  `seerr_list_request`, `seerr_create_request`, `seerr_delete_request`,
  `seerr_set_request_status`). Flagship/action endpoint overrides and collision
  fixes live in `NAME_OVERRIDES` in `scripts/generate_registry.py`.

## Annotations convention
- GET endpoints: `readOnlyHint=True` (`READONLY`).
- POST/PUT: `readOnlyHint=False`, `destructiveHint=False` (`WRITE`).
- DELETE: `readOnlyHint=False`, `destructiveHint=True` (`DESTRUCTIVE`).
- Exception: `GET /settings/discover/reset` is a mutative GET and carries
  `force_write: True` in its registry entry → annotated `WRITE`. Keep the
  three `ToolAnnotations` constants; never mark a write read-only.

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
