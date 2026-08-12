# seerr_openapi.yml

Seerr v1 OpenAPI spec, vendored from the Seerr repo so the tool registry and
tests stay reproducible and work offline.

- Source: `seerr-api.yml`
- Branch: `develop`, pinned to commit
  `39ff48c650d30ced0516574c55914d0bd26c9983`
- The `_TOOL_REGISTRY` in `seerr_mcp.py` is generated from this file. To
  refresh: download a newer `seerr-api.yml`, regenerate the registry with
  `uv run python scripts/generate_registry.py`, update the SHA here and in
  `seerr_mcp.py`/`AGENTS.md`, and re-run the tests.
