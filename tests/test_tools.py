"""Offline tests: one per Seerr v1 endpoint, plus error-path tests.

No network. The list of operations is generated from the vendored spec at
tests/data/seerr_openapi.yml (same skip rules as the authoring script), and
each tool call is checked against the exact HTTP request it should produce
(method, path incl. path-param substitution, query params) via
httpx.MockTransport, using FastMCP's in-memory Client (see
https://gofastmcp.com/development/tests).
"""

import json
import os

import httpx
import pytest
import pytest_asyncio
import yaml
from fastmcp import Client
from fastmcp.exceptions import ToolError

import seerr_mcp

SPEC_PATH = os.path.join(os.path.dirname(__file__), "data", "seerr_openapi.yml")

# Deprecated aliases the server deliberately does not wrap (prefer /blocklist).
EXCLUDE_PATHS = {"/blacklist", "/blacklist/{tmdbId}"}


def spec_ops():
    """(method, path, op) for every endpoint the server is expected to wrap."""
    d = yaml.safe_load(open(SPEC_PATH))
    ops = []
    for p, methods in d["paths"].items():
        for m, op in methods.items():
            if m in ("head", "parameters"):
                continue
            if p in EXCLUDE_PATHS:
                continue
            ops.append((m.upper(), p, op))
    return ops


def registry_for(method, path):
    for spec in seerr_mcp._TOOL_REGISTRY:
        if spec["method"] == method and spec["path"] == path:
            return spec
    raise AssertionError(f"no registry entry for {method} {path}")


def op_to_args(spec):
    """Build call args for a tool from its registry entry: path params and
    required query params get a sentinel value per their declared type."""
    args = {}
    for p in spec["pp"]:
        args[p["name"]] = "abc" if p["type"] == "str" else 1
    for q in spec["qp"]:
        if q.get("required"):
            args[q["name"]] = "abc" if q["type"] == "str" else 1
    return args


def expected_path(spec):
    path = spec["path"]
    for p in spec["pp"]:
        path = path.replace("{" + p["wire"] + "}", "abc" if p["type"] == "str" else "1")
    return "/api/v1" + path


class Recorder:
    """Captures the single request made during a test and replays a canned response."""

    def __init__(self):
        self.method = None
        self.url = None
        self.headers = None
        self.params = None
        self.json = None
        self.response = httpx.Response(200, json={"success": True})

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.method = request.method
        self.url = request.url
        self.headers = request.headers
        self.params = request.url.params
        self.json = json.loads(request.content) if request.content else None
        return self.response


@pytest.fixture
def recorder():
    return Recorder()


@pytest_asyncio.fixture
async def server(recorder, monkeypatch):
    transport = httpx.MockTransport(recorder.handler)
    client = seerr_mcp.build_client("https://seerr.example.com", "test-key", transport=transport)
    monkeypatch.setattr(seerr_mcp, "_client", client)
    yield seerr_mcp.mcp
    await client.aclose()


async def call(server, tool, **kwargs):
    async with Client(server) as c:
        return await c.call_tool(tool, kwargs)


# --- one test per endpoint ---------------------------------------------------

@pytest.mark.parametrize(
    "method,path",
    [(m, p) for m, p, _ in spec_ops()],
    ids=[f"{m.lower()}_{p}" for m, p, _ in spec_ops()],
)
async def test_endpoint_mapping(server, recorder, method, path):
    spec = registry_for(method, path)
    await call(server, spec["name"], **op_to_args(spec))
    assert recorder.method == method
    assert recorder.url.path == expected_path(spec)


# --- coverage: registry == spec ---------------------------------------------

def test_registry_covers_spec_exactly():
    spec_ops_set = {(m, p) for m, p, _ in spec_ops()}
    registry_ops = {(s["method"], s["path"]) for s in seerr_mcp._TOOL_REGISTRY}
    assert registry_ops == spec_ops_set


def test_all_registered_tools_have_unique_names():
    names = [s["name"] for s in seerr_mcp._TOOL_REGISTRY]
    assert len(names) == len(set(names))


# --- query params --------------------------------------------------------------

async def test_query_params_use_wire_names(server, recorder):
    await call(server, "seerr_list_request", take=20, skip=0, sort="modified", sort_direction="asc", requested_by=2)
    assert recorder.params["take"] == "20"
    assert recorder.params["skip"] == "0"
    assert recorder.params["sort"] == "modified"
    assert recorder.params["sortDirection"] == "asc"
    assert recorder.params["requestedBy"] == "2"


async def test_required_query_param_is_sent(server, recorder):
    await call(server, "seerr_list_search", query="dune")
    assert recorder.params["query"] == "dune"


async def test_empty_optional_params_are_omitted(server, recorder):
    await call(server, "seerr_list_request")
    assert "requestedBy" not in recorder.params
    assert recorder.params["sort"] == "added"  # has a default, so sent
    assert recorder.params["mediaType"] == "all"  # has a default, so sent


async def test_int_path_param_substitution(server, recorder):
    await call(server, "seerr_get_movie", movie_id=603)
    assert recorder.url.path == "/api/v1/movie/603"


async def test_string_path_param_substitution(server, recorder):
    await call(server, "seerr_get_blocklist", tmdb_id="603", media_type="movie")
    assert recorder.url.path == "/api/v1/blocklist/603"
    assert recorder.params["mediaType"] == "movie"


async def test_endpoint_path_param_needs_url_encoding(server, recorder):
    await call(server, "seerr_get_user_push_subscription", user_id=1, endpoint="https://push.example.com/abc")
    assert recorder.url.raw_path == b"/api/v1/user/1/pushSubscription/https%3A//push.example.com/abc"


# --- request bodies ------------------------------------------------------------

async def test_body_sent_as_json(server, recorder):
    body = {"mediaType": "movie", "mediaId": 603, "seasons": [1]}
    await call(server, "seerr_create_request", body=body)
    assert recorder.json == body


async def test_array_body_sent_as_json(server, recorder):
    body = [{"id": 1, "type": 0, "enabled": True}]
    await call(server, "seerr_update_discover_sliders", body=body)
    assert recorder.json == body


async def test_get_requests_have_no_body(server, recorder):
    await call(server, "seerr_list_status")
    assert recorder.json is None


# --- auth header ---------------------------------------------------------------

async def test_api_key_sent_as_x_api_key_header(server, recorder):
    await call(server, "seerr_list_status")
    assert recorder.headers["x-api-key"] == "test-key"


async def test_api_user_sent_when_configured(monkeypatch):
    recorder = Recorder()
    transport = httpx.MockTransport(recorder.handler)
    client = seerr_mcp.build_client("https://seerr.example.com", "test-key", api_user="2", transport=transport)
    monkeypatch.setattr(seerr_mcp, "_client", client)
    await call(seerr_mcp.mcp, "seerr_list_status")
    assert recorder.headers["x-api-user"] == "2"
    await client.aclose()


async def test_no_api_key_means_no_auth_header(recorder, monkeypatch):
    transport = httpx.MockTransport(recorder.handler)
    client = seerr_mcp.build_client("https://seerr.example.com", None, transport=transport)
    monkeypatch.setattr(seerr_mcp, "_client", client)
    await call(seerr_mcp.mcp, "seerr_list_status")
    assert "x-api-key" not in recorder.headers
    await client.aclose()


# --- base path ------------------------------------------------------------------

async def test_base_path_is_api_v1(server, recorder):
    await call(server, "seerr_list_status")
    assert recorder.url.path == "/api/v1/status"


# --- error paths -----------------------------------------------------------------

async def test_404_error_message_reaches_caller(server, recorder):
    recorder.response = httpx.Response(404, json={"message": "Request not found"})
    with pytest.raises(ToolError, match="Request not found"):
        await call(server, "seerr_get_request", request_id="999")


async def test_401_error_surfaces_status(server, recorder):
    recorder.response = httpx.Response(401, json={"message": "Unauthorized"})
    with pytest.raises(ToolError, match="401"):
        await call(server, "seerr_list_status")


async def test_400_error_surfaces_status(server, recorder):
    recorder.response = httpx.Response(400, json={"message": "Invalid request"})
    with pytest.raises(ToolError, match="400"):
        await call(server, "seerr_create_request", body={})


async def test_non_json_error_body_does_not_crash(server, recorder):
    recorder.response = httpx.Response(502, text="<html>Bad Gateway</html>")
    with pytest.raises(ToolError, match="502"):
        await call(server, "seerr_list_status")


# --- main() ------------------------------------------------------------------

def test_main_requires_seerr_url(monkeypatch):
    monkeypatch.delenv("SEERR_URL", raising=False)
    with pytest.raises(SystemExit):
        seerr_mcp.main()
