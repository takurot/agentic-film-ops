from datetime import datetime

from app.models import Actor, Crew, Equipment, Location, Manager, Scene


def test_scene_links_to_actors_equipment_location_and_crew(session):
    manager = Manager(id="MGR-001", name="Talent Agency")
    actor = Actor(
        id="ACT-001",
        name="Emma Carter",
        manager=manager,
        availability=[],
        status="confirmed",
    )
    equipment = Equipment(
        id="EQ-001",
        name="ARRI Alexa 35",
        vendor="Cinema Rental Tokyo",
        availability=[],
        daily_cost=1200,
    )
    location = Location(
        id="LOC-003",
        name="Rooftop, Shibuya Tower",
        type="outdoor",
        manager=Manager(id="LOCMGR-001", name="Shibuya Tower Management"),
        availability=[],
        daily_cost=3000,
        weather_dependent=True,
    )
    crew = Crew(
        id="CREW-001",
        name="Kenji Sato",
        role="Camera Operator",
        availability=[],
        overtime_rate_per_hour=150,
    )
    scene = Scene(
        scene_id="SC-042",
        name="Rooftop confrontation",
        type="outdoor",
        duration_hours=4,
        location=location,
        scheduled=datetime(2026, 9, 2, 14, 0),
        actors=[actor],
        equipment=[equipment],
        crew=[crew],
    )

    session.add(scene)
    session.commit()

    fetched = session.get(Scene, "SC-042")
    assert [a.id for a in fetched.actors] == ["ACT-001"]
    assert [e.id for e in fetched.equipment] == ["EQ-001"]
    assert [c.id for c in fetched.crew] == ["CREW-001"]
    assert fetched.location.id == "LOC-003"
    assert fetched.location.manager.name == "Shibuya Tower Management"
    assert fetched.actors[0].manager.name == "Talent Agency"


def test_availability_round_trips_as_busy_block_list(session):
    actor = Actor(
        id="ACT-001",
        name="Emma Carter",
        availability=[
            {"scene_id": "SC-038", "start": "2026-09-01T09:00", "end": "2026-09-01T13:00"}
        ],
        status="confirmed",
    )
    session.add(actor)
    session.commit()

    fetched = session.get(Actor, "ACT-001")
    assert fetched.availability == [
        {"scene_id": "SC-038", "start": "2026-09-01T09:00", "end": "2026-09-01T13:00"}
    ]
