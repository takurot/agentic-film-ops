from pathlib import Path

from sqlalchemy.orm import Session

from app.db import create_db_engine, init_db
from app.mcp_client import MCPStdioClient
from app.models import Actor
from app.seed import seed_scene_42


async def test_all_six_stdio_servers_share_the_configured_file_database(tmp_path: Path) -> None:
    """Exercise initialize/list/call over real stdio for every production server."""
    db_path = tmp_path / "stdio-contract.db"
    engine = create_db_engine(db_path)
    init_db(engine)
    with Session(engine) as session:
        seed_scene_42(session)
        session.add(
            Actor(
                id="ACT-STDIO-ONLY",
                name="Stdio Contract Actor",
                availability=[],
                status="confirmed",
            )
        )
        session.commit()
    engine.dispose()

    client = MCPStdioClient(db_path=db_path, latency_scale=0, timeout_seconds=10)
    try:
        await client.start()
        results = {
            "actor": await client.call("actor", "get_actor", {"actor_id": "ACT-STDIO-ONLY"}),
            "equipment": await client.call(
                "equipment", "get_equipment", {"equipment_id": "EQ-001"}
            ),
            "location": await client.call("location", "get_location", {"location_id": "LOC-003"}),
            "script": await client.call("script", "get_scene", {"scene_id": "SC-042"}),
            "weather": await client.call("weather", "get_forecast", {"location_id": "LOC-003"}),
            "budget": await client.call("budget", "get_current_budget", {}),
        }
    finally:
        await client.close()

    assert results["actor"]["id"] == "ACT-STDIO-ONLY"
    assert results["equipment"]["equipment_id"] == "EQ-001"
    assert results["location"]["id"] == "LOC-003"
    assert results["script"]["scene_id"] == "SC-042"
    assert results["weather"]["location_id"] == "LOC-003"
    assert "total_budget" in results["budget"]
