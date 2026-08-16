"""Seed data for the Scene 42 demo scenario (SPEC §2.1 / §4.8).

Rooftop confrontation: Emma Carter and Daniel shoot on the rooftop of
Shibuya Tower with an ARRI Alexa 35 and a lighting kit, under Kenji Sato's
camera operation — the scene a sudden rain forecast puts at risk.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Actor, Crew, Equipment, Location, Manager, Scene

SCENE_42_BLOCK = {"scene_id": "SC-042", "start": "2026-09-02T14:00", "end": "2026-09-02T18:00"}


def seed_scene_42(session: Session) -> Scene:
    """Populate the Scene 42 scenario. Idempotent: safe to call multiple times."""
    existing = session.get(Scene, "SC-042")
    if existing:
        return existing

    talent_agency = Manager(id="MGR-001", name="Talent Agency — Emma Carter's Agent")
    daniels_manager = Manager(id="MGR-002", name="Talent Agency — Daniel's Agent")
    location_manager = Manager(id="LOCMGR-001", name="Shibuya Tower Building Management")
    studio_b_manager = Manager(id="LOCMGR-002", name="Studio B Facilities")

    emma = Actor(
        id="ACT-001",
        name="Emma Carter",
        manager=talent_agency,
        availability=[
            {
                "scene_id": "SC-038",
                "start": "2026-09-01T09:00",
                "end": "2026-09-01T13:00",
            },
            SCENE_42_BLOCK,
        ],
        status="confirmed",
    )
    daniel = Actor(
        id="ACT-002",
        name="Daniel",
        manager=daniels_manager,
        availability=[SCENE_42_BLOCK],
        status="confirmed",
    )

    alexa_35 = Equipment(
        id="EQ-001",
        name="ARRI Alexa 35",
        vendor="Cinema Rental Tokyo",
        availability=[SCENE_42_BLOCK],
        daily_cost=1200,
    )
    lighting_kit = Equipment(
        id="EQ-004",
        name="Lighting Kit",
        vendor="Cinema Rental Tokyo",
        availability=[SCENE_42_BLOCK],
        daily_cost=400,
    )

    rooftop = Location(
        id="LOC-003",
        name="Rooftop, Shibuya Tower",
        type="outdoor",
        manager=location_manager,
        availability=[SCENE_42_BLOCK],
        daily_cost=3000,
        weather_dependent=True,
        status="available",
    )
    # Indoor alternative for Scene 42's rooftop (SPEC §9.6/§9.7/§9.10's "Studio
    # B" replan transcript) — Location MCP's find_alternative_locations()
    # (SPEC §5.3) surfaces this as a substitute when LOC-003 is weather-risked.
    studio_b = Location(
        id="LOC-STUDIO-B",
        name="Studio B",
        type="indoor",
        manager=studio_b_manager,
        availability=[],
        daily_cost=2200,
        weather_dependent=False,
        status="available",
    )

    kenji = Crew(
        id="CREW-001",
        name="Kenji Sato",
        role="Camera Operator",
        availability=[SCENE_42_BLOCK],
        overtime_rate_per_hour=150,
    )

    scene_38 = Scene(
        scene_id="SC-038",
        name="Alleyway Chase",
        type="outdoor",
        duration_hours=4,
        location=None,
        scheduled=datetime(2026, 9, 1, 9, 0),
        actors=[emma],
        equipment=[],
        crew=[],
    )
    scene_39 = Scene(
        scene_id="SC-039",
        name="Subway Escape",
        type="indoor",
        duration_hours=3,
        location=None,
        scheduled=datetime(2026, 9, 1, 13, 0),
        actors=[],
        equipment=[],
        crew=[],
    )
    scene_40 = Scene(
        scene_id="SC-040",
        name="Safehouse Planning",
        type="indoor",
        duration_hours=4,
        location=None,
        scheduled=datetime(2026, 9, 1, 16, 0),
        actors=[daniel],
        equipment=[],
        crew=[kenji],
    )

    scene = Scene(
        scene_id="SC-042",
        name="Rooftop confrontation",
        type="outdoor",
        duration_hours=4,
        location=rooftop,
        scheduled=datetime(2026, 9, 2, 14, 0),
        actors=[emma, daniel],
        equipment=[alexa_35, lighting_kit],
        crew=[kenji],
    )

    session.add(scene)
    session.add(scene_38)
    session.add(scene_39)
    session.add(scene_40)
    session.add(studio_b)  # not linked via any Scene relationship, so add() explicitly
    session.commit()
    return scene


if __name__ == "__main__":
    from app.db import get_session, init_db

    init_db()
    with get_session() as db:
        seed_scene_42(db)
    print("Seeded Scene 42 (SC-042) into the Production Resource Graph.")
