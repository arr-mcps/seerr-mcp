#!/usr/bin/env python3
"""Generate the `_TOOL_REGISTRY` literal for seerr_mcp.py from the vendored
Seerr OpenAPI spec at tests/data/seerr_openapi.yml.

Usage:
    uv run python scripts/generate_registry.py            # print to stdout
    uv run python scripts/generate_registry.py -o tmp     # print to tmp

The registry lists one entry per JSON-producing endpoint. Deprecated
`/blacklist/*` aliases (sunset 2026-06-01) are skipped in favour of the
`/blocklist/*` routers. `GET /settings/discover/reset` is a mutative GET, so it
is emitted with `force_write: True` to override the GET->READONLY annotation.

Tool naming is `seerr_<verb>_<resource>` derived from method + path, with a
curated override map for flagship/action endpoints and collision fixes. If two
endpoints would collide, the script fails loudly - add an override.
"""

from __future__ import annotations

import re
import sys

import yaml

SPEC_PATH = "tests/data/seerr_openapi.yml"

EXCLUDED_PATHS = {"/blacklist", "/blacklist/{tmdbId}"}

# (method, path) -> explicit tool name. Flagship/action endpoints and any name
# collisions the generic derivation would produce.
NAME_OVERRIDES = {
    ("POST", "/request/{requestId}/{status}"): "seerr_set_request_status",
    ("POST", "/issue/{issueId}/{status}"): "seerr_set_issue_status",
    ("POST", "/media/{mediaId}/{status}"): "seerr_set_media_status",
    ("POST", "/request/{requestId}/retry"): "seerr_retry_request",
    ("PUT", "/user"): "seerr_batch_update_users",
    ("GET", "/settings/discover/reset"): "seerr_reset_discover_sliders",
    ("POST", "/settings/main/regenerate"): "seerr_regenerate_api_key",
    ("POST", "/settings/jobs/{jobId}/run"): "seerr_run_job",
    ("POST", "/settings/jobs/{jobId}/cancel"): "seerr_cancel_job",
    ("POST", "/settings/jobs/{jobId}/schedule"): "seerr_schedule_job",
    ("POST", "/settings/cache/{cacheId}/flush"): "seerr_flush_cache",
    ("POST", "/settings/cache/dns/{dnsEntry}/flush"): "seerr_flush_dns_cache",
    ("POST", "/settings/initialize"): "seerr_initialize_app",
    ("GET", "/auth/me"): "seerr_get_me",
    ("POST", "/auth/logout"): "seerr_logout",
    ("POST", "/auth/plex"): "seerr_login_plex",
    ("POST", "/auth/jellyfin"): "seerr_login_jellyfin",
    ("POST", "/auth/local"): "seerr_login_local",
    ("POST", "/auth/jellyfin/quickconnect/initiate"): "seerr_initiate_jellyfin_quickconnect",
    ("GET", "/auth/jellyfin/quickconnect/check"): "seerr_check_jellyfin_quickconnect",
    ("POST", "/auth/jellyfin/quickconnect/authenticate"): "seerr_authenticate_jellyfin_quickconnect",
    ("POST", "/auth/reset-password"): "seerr_request_password_reset",
    ("POST", "/auth/reset-password/{guid}"): "seerr_reset_password",
    ("POST", "/user/import-from-plex"): "seerr_import_plex_users",
    ("POST", "/user/import-from-jellyfin"): "seerr_import_jellyfin_users",
    ("POST", "/user/registerPushSubscription"): "seerr_register_push_subscription",
    ("GET", "/user/{userId}/pushSubscriptions"): "seerr_list_user_push_subscriptions",
    ("GET", "/user/{userId}/pushSubscription/{endpoint}"): "seerr_get_user_push_subscription",
    ("DELETE", "/user/{userId}/pushSubscription/{endpoint}"): "seerr_delete_user_push_subscription",
    ("GET", "/settings/discover"): "seerr_list_discover_sliders",
    ("POST", "/settings/discover"): "seerr_update_discover_sliders",
    ("POST", "/settings/discover/add"): "seerr_add_discover_slider",
    ("PUT", "/settings/discover/{sliderId}"): "seerr_update_discover_slider",
    ("DELETE", "/settings/discover/{sliderId}"): "seerr_delete_discover_slider",
    ("GET", "/settings/notifications/pushover/sounds"): "seerr_list_pushover_sounds",
}

# (method, path) -> true for mutative GETs that must not be readOnly.
MUTATIVE = {("GET", "/settings/discover/reset")}

METHOD_VERB_SINGLE = {"GET": "get", "POST": "create", "PUT": "update", "DELETE": "delete"}

TYPE_MAP = {"number": "int", "integer": "int", "boolean": "bool", "string": "str"}


def _resource_from_path(path: str) -> str:
    segments = [s for s in path.split("/") if s]
    segments = [re.sub(r"[^a-zA-Z0-9_]", "_", s) for s in segments if not re.fullmatch(r"\{.*\}", s)]
    resource = "_".join(segments)
    resource = re.sub(r"_+", "_", resource).strip("_").lower()
    return resource or "root"


def _verb(method: str, path: str, has_params: bool) -> str:
    if method == "GET":
        return "list" if not has_params else "get"
    return METHOD_VERB_SINGLE[method]


def _snake(name: str) -> str:
    name = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name)
    name = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", "_", name)
    name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    return name.lower().strip("_")


def _derive_name(method: str, path: str) -> str:
    explicit = NAME_OVERRIDES.get((method, path))
    if explicit:
        return explicit
    has_params = "{" in path
    verb = _verb(method, path, has_params)
    resource = _resource_from_path(path)
    return f"seerr_{verb}_{resource}"


def _params(kind: str, op: dict, taken: set[str]) -> list[dict]:
    out = []
    for prm in op.get("parameters", []) or []:
        if prm.get("in") != kind:
            continue
        schema = prm.get("schema", {}) or {}
        ptype = TYPE_MAP.get(schema.get("type"), "str")
        default = schema.get("default")
        name = _snake(prm["name"])
        if name in taken:
            name = f"{name}_q"
        taken.add(name)
        out.append(
            {
                "name": name,
                "wire": prm["name"],
                "type": ptype,
                "required": bool(prm.get("required")) and kind == "query",
                "default": None if default is None else default,
            }
        )
    return out


def _body_kind(op: dict) -> str:
    rb = op.get("requestBody")
    if not rb:
        return "none"
    schema = rb.get("content", {}).get("application/json", {}).get("schema", {}) or {}
    if schema.get("type") == "array":
        return "list"
    return "dict"


def _doc(op: dict, method: str) -> str:
    summary = op.get("summary") or op.get("description") or ""
    summary = " ".join(summary.split())
    if method in ("POST", "PUT"):
        return f"{summary} WRITE: this modifies your Seerr instance."
    if method == "DELETE":
        return f"{summary} DESTRUCTIVE: this deletes data."
    return summary


def _quote(v):
    if isinstance(v, bool):
        return "True" if v else "False"
    return repr(v)


def build_entries() -> list[dict]:
    d = yaml.safe_load(open(SPEC_PATH))
    entries = []
    seen_names: dict[str, str] = {}
    for path, methods in d["paths"].items():
        if path in EXCLUDED_PATHS:
            continue
        for method, op in methods.items():
            if method in ("head", "options", "parameters"):
                continue
            name = _derive_name(method.upper(), path)
            if name in seen_names:
                raise SystemExit(f"collision: {name} for {method.upper()} {path} and {seen_names[name]}")
            seen_names[name] = f"{method.upper()} {path}"
            taken: set[str] = set()
            pp = _params("path", op, taken)
            qp = _params("query", op, taken)
            entry = {
                "name": name,
                "method": method.upper(),
                "path": path,
                "pp": pp,
                "qp": qp,
                "bk": _body_kind(op),
                "doc": _doc(op, method.upper()),
            }
            if (method.upper(), path) in MUTATIVE:
                entry["force_write"] = True
            entries.append(entry)
    return entries


def render(entries: list[dict]) -> str:
    lines = ["_TOOL_REGISTRY: list[dict[str, Any]] = ["]
    for e in entries:
        lines.append(" {'name': %s," % _quote(e["name"]))
        lines.append("  'method': %s," % _quote(e["method"]))
        lines.append("  'path': %s," % _quote(e["path"]))
        if e["pp"]:
            lines.append("  'pp': [")
            for p in e["pp"]:
                lines.append("          {'name': %s, 'wire': %s, 'type': %s}," % (_quote(p["name"]), _quote(p["wire"]), _quote(p["type"])))
            lines.append("         ],")
        else:
            lines.append("  'pp': [],")
        if e["qp"]:
            lines.append("  'qp': [")
            for q in e["qp"]:
                req = ", 'required': True" if q["required"] else ""
                lines.append(
                    "          {'name': %s, 'wire': %s, 'type': %s, 'default': %s%s},"
                    % (_quote(q["name"]), _quote(q["wire"]), _quote(q["type"]), _quote(q["default"]), req)
                )
            lines.append("         ],")
        else:
            lines.append("  'qp': [],")
        lines.append("  'bk': %s," % _quote(e["bk"]))
        if e.get("force_write"):
            lines.append("  'force_write': True,")
        lines.append("  'doc': %s," % _quote(e["doc"]))
        lines.append(" },")
    lines.append("]")
    return "\n".join(lines)


def main() -> None:
    entries = build_entries()
    text = render(entries)
    if "-o" in sys.argv:
        out = sys.argv[sys.argv.index("-o") + 1]
        with open(out, "w") as f:
            f.write(text + "\n")
    else:
        print(text)
    print(f"\n# {len(entries)} tools generated from {SPEC_PATH}", file=sys.stderr)


if __name__ == "__main__":
    main()
