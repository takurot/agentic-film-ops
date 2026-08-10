from datetime import datetime

from app.models import Actor, Crew, Equipment, Location, Manager, Scene
from app.schemas import (
    actor_to_schema,
    crew_to_schema,
    equipment_to_schema,
    location_to_schema,
    scene_to_schema,
)


def test_actor_to_schema_matches_spec_shape():
    actor = Actor(
        id="ACT-001",
        name="Emma Carter",
        manager=Manager(id="MGR-001", name="Talent Agency"),
        availability=[],
        status="confirmed",
    )

    schema = actor_to_schema(actor)

    assert schema.model_dump() == {
        "id": "ACT-001",
        "name": "Emma Carter",
        "manager": "MGR-001",
        "availability": [],
        "status": "confirmed",
    }


def test_equipment_to_schema_matches_spec_shape():
    equipment = Equipment(
        id="EQ-001",
        name="ARRI Alexa 35",
        vendor="Cinema Rental Tokyo",
        availability=[],
        daily_cost=1200,
    )

    schema = equipment_to_schema(equipment)

    assert schema.model_dump() == {
        "id": "EQ-001",
        "name": "ARRI Alexa 35",
        "vendor": "Cinema Rental Tokyo",
        "availability": [],
        "daily_cost": 1200,
    }


def test_location_to_schema_matches_spec_shape():
    location = Location(
        id="LOC-003",
        name="Rooftop, Shibuya Tower",
        type="outdoor",
        manager=Manager(id="LOCMGR-001", name="Shibuya Tower Management"),
        availability=[],
        daily_cost=3000,
        weather_dependent=True,
    )

    schema = location_to_schema(location)

    assert schema.model_dump() == {
        "id": "LOC-003",
        "name": "Rooftop, Shibuya Tower",
        "type": "outdoor",
        "manager": "LOCMGR-001",
        "availability": [],
        "daily_cost": 3000,
        "weather_dependent": True,
    }


def test_crew_to_schema_matches_spec_shape():
    crew = Crew(
        id="CREW-001",
        name="Kenji Sato",
        role="Camera Operator",
        availability=[],
        overtime_rate_per_hour=150,
    )

    schema = crew_to_schema(crew)

    assert schema.model_dump() == {
        "id": "CREW-001",
        "name": "Kenji Sato",
        "role": "Camera Operator",
        "availability": [],
        "overtime_rate_per_hour": 150,
    }


def test_scene_to_schema_matches_spec_shape():
    scene = Scene(
        scene_id="SC-042",
        name="Rooftop confrontation",
        type="outdoor",
        duration_hours=4,
        location=Location(id="LOC-003", name="Rooftop", type="outdoor", daily_cost=3000),
        scheduled=datetime(2026, 9, 2, 14, 0),
        actors=[Actor(id="ACT-001", name="Emma Carter", status="confirmed")],
        equipment=[
            Equipment(
                id="EQ-001", name="ARRI Alexa 35", vendor="Cinema Rental Tokyo", daily_cost=1200
            )
        ],
        crew=[],
    )

    schema = scene_to_schema(scene)

    assert schema.model_dump() == {
        "scene_id": "SC-042",
        "name": "Rooftop confrontation",
        "type": "outdoor",
        "duration_hours": 4,
        "actors": ["ACT-001"],
        "location": "LOC-003",
        "equipment": ["EQ-001"],
        "crew": [],
        "scheduled": datetime(2026, 9, 2, 14, 0),
    }
