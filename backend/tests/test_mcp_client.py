import os
from pathlib import Path

import pytest
from mcp.types import CallToolResult, TextContent

from app.mcp_client import (
    MCPProtocolError,
    MCPStdioClient,
    MCPToolError,
    build_child_environment,
    decode_tool_result,
)


def test_child_environment_is_allowlisted_and_does_not_forward_gemini_secret(tmp_path) -> None:
    parent = {
        "PATH": os.environ.get("PATH", ""),
        "GEMINI_API_KEY": "must-not-reach-mcp",
        "AWS_SECRET_ACCESS_KEY": "also-secret",
        "LANG": "en_US.UTF-8",
    }

    child = build_child_environment(
        parent,
        backend_root=Path(__file__).parents[1],
        db_path=tmp_path / "contract.db",
        latency_scale=0,
    )

    assert child["FILMOPS_DB_PATH"] == str((tmp_path / "contract.db").resolve())
    assert child["FILMOPS_LATENCY_SCALE"] == "0"
    assert child["PYTHONPATH"] == str(Path(__file__).parents[1].resolve())
    assert "GEMINI_API_KEY" not in child
    assert "AWS_SECRET_ACCESS_KEY" not in child


def test_child_environment_rejects_memory_database() -> None:
    with pytest.raises(ValueError, match="file-backed SQLite"):
        build_child_environment(
            {},
            backend_root=Path(__file__).parents[1],
            db_path=Path(":memory:"),
            latency_scale=0,
        )


def test_decode_tool_result_prefers_structured_content() -> None:
    result = CallToolResult(
        content=[TextContent(type="text", text='{"ignored": true}')],
        structuredContent={"location_id": "LOC-003", "available": True},
        isError=False,
    )

    assert decode_tool_result(result) == {"location_id": "LOC-003", "available": True}


@pytest.mark.parametrize(
    "result",
    [
        CallToolResult(content=[], isError=False),
        CallToolResult(content=[TextContent(type="text", text="not-json")], isError=False),
        CallToolResult(
            content=[
                TextContent(type="text", text="{}"),
                TextContent(type="text", text="{}"),
            ],
            isError=False,
        ),
        CallToolResult(
            content=[TextContent(type="text", text="[]")],
            isError=False,
        ),
    ],
)
def test_decode_tool_result_rejects_malformed_protocol_results(result: CallToolResult) -> None:
    with pytest.raises(MCPProtocolError):
        decode_tool_result(result)


def test_decode_tool_result_rejects_tool_error_without_disclosing_raw_text() -> None:
    result = CallToolResult(
        content=[TextContent(type="text", text="secret provider diagnostic")],
        isError=True,
    )

    with pytest.raises(MCPToolError, match="MCP_TOOL_FAILED") as exc_info:
        decode_tool_result(result)

    assert "secret provider diagnostic" not in str(exc_info.value)


@pytest.mark.parametrize("server", ["../actor", "actor;rm", "unknown"])
async def test_stdio_client_rejects_unknown_server_before_starting_process(
    server: str, tmp_path
) -> None:
    client = MCPStdioClient(db_path=tmp_path / "contract.db")

    with pytest.raises(MCPProtocolError, match="MCP_SERVER_NOT_ALLOWED"):
        await client.call(server, "get_actor", {"actor_id": "ACT-001"})


async def test_stdio_client_rejects_unknown_tool_before_calling_session(tmp_path) -> None:
    client = MCPStdioClient(db_path=tmp_path / "contract.db")

    with pytest.raises(MCPProtocolError, match="MCP_TOOL_NOT_ALLOWED"):
        await client.call("actor", "arbitrary_tool", {})
