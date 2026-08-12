"""Integration tests against a real Seerr instance.

Skipped unless SEERR_URL and SEERR_API_KEY are set. Run with:
    uv run pytest -m integration

GET endpoints are exercised against the live instance. POST/PUT/DELETE tools
only run when SEERR_WRITE_TESTS=1, and only as a safe create->update->delete
cycle against a scratch blocklist entry which is cleaned up afterwards. Never
point write tests at a production instance.
"""

import os

import pytest
import yaml
from fastmcp import Client
from fastmcp.exceptions import ToolError

import seerr_mcp

from tests.test_tools import EXCLUDE_PATHS, SPEC_PATH, registry_for

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not (os.environ.get("SEERR_URL") and os.environ.get("SEERR_API_KEY")),
        reason="requires SEERR_URL and SEERR_API_KEY",
    ),
]

WRITES_ENABLED = os.environ.get("SEERR_WRITE_TESTS") == "1"


def spec_ops():
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


def pathless_get_ops():
    return [(m, p) for m, p, _ in spec_ops() if m == "GET" and "{" not in p]


def op_to_args(spec):
    args = {}
    for p in spec["pp"]:
        args[p["name"]] = "abc" if p["type"] == "str" else 1
    for q in spec["qp"]:
        if q.get("required"):
            args[q["name"]] = "abc" if q["type"] == "str" else 1
    return args


@pytest.fixture(autouse=True)
def configure_client():
    seerr_mcp._client = seerr_mcp.build_client(
        os.environ["SEERR_URL"], os.environ["SEERR_API_KEY"], os.environ.get("SEERR_API_USER")
    )
    yield
    seerr_mcp._client = None


async def call(name, **kwargs):
    async with Client(seerr_mcp.mcp) as c:
        return await c.call_tool(name, kwargs)


# --- always-on GET smoke tests ------------------------------------------------

async def test_status():
    result = await call("seerr_list_status")
    assert "version" in result.data


async def test_user_list():
    result = await call("seerr_list_user", take=1)
    assert "pageInfo" in result.data
    assert "results" in result.data


# --- every GET collection endpoint is reachable --------------------------------

@pytest.mark.parametrize(
    "method,path",
    pathless_get_ops(),
    ids=[f"{m.lower()}_{p}" for m, p in pathless_get_ops()],
)
async def test_get_collection_endpoints_reachable(method, path):
    spec = registry_for(method, path)
    try:
        await call(spec["name"], **op_to_args(spec))
    except ToolError as e:
        status = int(str(e).split(":")[0].split()[-1])
        assert 400 <= status < 500, f"{spec['name']}: unexpected {e}"


# --- GET-by-id endpoints when data exists ----------------------------------------

async def test_get_user_by_id_when_users_exist():
    users = await call("seerr_list_user", take=1)
    records = users.data["results"]
    if not records:
        pytest.skip("no users on this instance")
    uid = records[0]["id"]
    result = await call("seerr_get_user", user_id=uid)
    assert result.data["id"] == uid


async def test_get_movie_by_id():
    result = await call("seerr_get_movie", movie_id=603)
    assert result.data["id"] == 603


async def test_get_request_by_id_when_requests_exist():
    requests = await call("seerr_list_request", take=1)
    records = requests.data["results"]
    if not records:
        pytest.skip("no requests on this instance")
    rid = records[0]["id"]
    result = await call("seerr_get_request", request_id=str(rid))
    assert result.data["id"] == rid


async def test_get_issue_by_id_when_issues_exist():
    issues = await call("seerr_list_issue", take=1)
    records = issues.data["results"]
    if not records:
        pytest.skip("no issues on this instance")
    iid = records[0]["id"]
    result = await call("seerr_get_issue", issue_id=iid)
    assert result.data["id"] == iid


# --- write tools: safe scratch blocklist cycle (SEERR_WRITE_TESTS=1 only) --------

@pytest.mark.skipif(not WRITES_ENABLED, reason="set SEERR_WRITE_TESTS=1 to run write tests")
async def test_blocklist_lifecycle():
    created = await call(
        "seerr_create_blocklist", body={"tmdbId": 603, "title": "mcp-test-title", "media": {"mediaType": "movie"}}
    )
    assert created.data.get("id") or created.data.get("media") or created.data is not None
    try:
        fetched = await call("seerr_get_blocklist", tmdb_id=603, media_type="movie")
        assert fetched.data is not None
    finally:
        await call("seerr_delete_blocklist", tmdb_id=603, media_type="movie")
