# seerr-mcp

Part of the [arr-mcps](https://github.com/SavageCore/arr-mcps) collection.
MCP server exposing [Seerr](https://github.com/seerr-team/seerr)'s v1 REST API
([OpenAPI 3.0.2](https://seerr-team.github.io/)) as tools, so an LLM can read
and manage a Seerr instance: search and discovery, media requests and their
approval workflow, users, issues, watchlists and blocklists, Plex/Jellyfin/Emby
and Sonarr/Radarr integration settings, notification agents, scheduled jobs,
and more. Full surface — reads **and** writes, with destructive tools flagged.

Built with [FastMCP](https://gofastmcp.com).

## Getting an API key

Generate one in Seerr **Settings > General**. Auth is the `X-Api-Key` header.
An optional `X-API-User` header can impersonate a specific user id (defaults
to user 1, the admin account the key belongs to).

## Install

Download a wheel from the [latest release](https://github.com/SavageCore/seerr-mcp/releases/latest)
and install it as a `uv` tool (no repo checkout needed):

```bash
uv tool install seerr_mcp-*.whl
```

This puts a `seerr-mcp` command on your PATH. Register it with Claude Code:

```bash
claude mcp add seerr \
  --env SEERR_URL=http://your-seerr-host \
  --env SEERR_API_KEY=<key> \
  -- seerr-mcp
```

### From source

```bash
uv sync
cp .env.example .env   # fill in SEERR_URL and SEERR_API_KEY
```

```bash
claude mcp add seerr \
  --env SEERR_URL=http://your-seerr-host \
  --env SEERR_API_KEY=<key> \
  -- uv run --directory /path/to/seerr-mcp seerr-mcp
```

## Config

| Env var | Required | Default |
|---|---|---|
| `SEERR_URL` | yes | - |
| `SEERR_API_KEY` | yes* | none (no `X-Api-Key` header sent if unset) |
| `SEERR_API_USER` | no | none (no `X-API-User` header; API key acts as user 1) |

\* Every API endpoint requires auth; practically you must set it, but the
server still starts without one so errors surface from the API rather than at
startup.

## Tools

**15 resource-scoped tools**, each covering multiple Seerr v1 endpoints (208
total) via an `operation` parameter. Call a tool with `operation` set to one
of its listed operations and an `arguments` dict matching that operation's
parameters — the tool's own description (visible to your MCP client) lists
every operation, its signature, and a one-line doc. This keeps the full REST
surface available while costing a fraction of the context budget of
registering all 208 endpoints as separate tools. Seerr is settings-heavy, so
its grouping is its own (not shared with the radarr/sonarr/bookshelf taxonomy).

| Tool | Operations | Kind |
|---|---|---|
| `seerr_settings_general` | 51 | reads + writes |
| `seerr_settings_notifications` | 31 | reads + writes |
| `seerr_users` | 30 | reads + writes |
| `seerr_discover` | 28 | read-only |
| `seerr_media_titles` | 13 | read-only |
| `seerr_auth` | 10 | reads + writes |
| `seerr_issues` | 10 | reads + writes |
| `seerr_requests` | 8 | reads + writes |
| `seerr_blocklist` | 6 | reads + writes |
| `seerr_media_records` | 5 | reads + writes |
| `seerr_service_arr` | 5 | read-only |
| `seerr_override_rules` | 4 | reads + writes |
| `seerr_search` | 3 | read-only |
| `seerr_system_status` | 2 | read-only |
| `seerr_watchlist` | 2 | reads + writes |

Example: `seerr_requests(operation="seerr_get_request", arguments={"request_id": "42"})`.
Endpoint-level naming (`seerr_<verb>_<resource>`) is preserved as the
`operation` value, so the full endpoint list is still discoverable from each
group tool's description at runtime.

## Development

```bash
make help  # list all commands
```

| Command | Does |
|---|---|
| `make sync` | `uv sync` |
| `make test` | Offline tests - one per endpoint, mocked HTTP |
| `make test-integration` | Tests against the live instance (needs `SEERR_URL`/`SEERR_API_KEY`) |
| `make build` | Build wheel + sdist into `dist/` |
| `make bump-patch` / `bump-minor` / `bump-major` | Bump the version in `pyproject.toml` + `uv.lock` |
| `make clean` | Remove build artifacts |

The release workflow (`.github/workflows/release.yml`) builds and publishes to
[Releases](https://github.com/SavageCore/seerr-mcp/releases) whenever a `v*`
tag is pushed - so the usual flow is `make bump-patch`, commit, then tag and
push.

The offline suite covers every endpoint (mocked HTTP). The integration suite
exercises GET endpoints against your live instance; POST/PUT/DELETE only run
when `SEERR_WRITE_TESTS=1`, as a safe create→delete cycle against a scratch
blocklist entry that is cleaned up afterwards.
