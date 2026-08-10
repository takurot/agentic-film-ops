"""Pydantic schemas mirroring the SPEC §4 JSON shapes.

The ORM models (app/models.py) hold relationships as objects; these schemas
flatten them back to the plain ID references / lists that SPEC §4 defines,
for use as API response bodies (Issue #29).
"""

from datetime import datetime

from pydantic import BaseModel

from app.models import Actor, Crew, Equipment, Location, Scene


class AvailabilityBlock(BaseModel):
    scene_id: str
    start: datetime
    end: datetime


class ActorSchema(BaseModel):
    id: str
    name: str
    manager: str | None
    availability: list[AvailabilityBlock]
    status: str


class EquipmentSchema(BaseModel):
    id: str
    name: str
    vendor: str
    availability: list[AvailabilityBlock]
    daily_cost: float


class LocationSchema(BaseModel):
    id: str
    name: str
    type: str
    manager: str | None
    availability: list[AvailabilityBlock]
    daily_cost: float
    weather_dependent: bool


class CrewSchema(BaseModel):
    id: str
    name: str
    role: str
    availability: list[AvailabilityBlock]
    overtime_rate_per_hour: float


class SceneSchema(BaseModel):
    scene_id: str
    name: str
    type: str
    duration_hours: float
    actors: list[str]
    location: str | None
    equipment: list[str]
    crew: list[str]
    scheduled: datetime


def actor_to_schema(actor: Actor) -> ActorSchema:
    return ActorSchema(
        id=actor.id,
        name=actor.name,
        manager=actor.manager.id if actor.manager else None,
        availability=actor.availability,
        status=actor.status,
    )


def equipment_to_schema(equipment: Equipment) -> EquipmentSchema:
    return EquipmentSchema(
        id=equipment.id,
        name=equipment.name,
        vendor=equipment.vendor,
        availability=equipment.availability,
        daily_cost=equipment.daily_cost,
    )


def location_to_schema(location: Location) -> LocationSchema:
    return LocationSchema(
        id=location.id,
        name=location.name,
        type=location.type,
        manager=location.manager.id if location.manager else None,
        availability=location.availability,
        daily_cost=location.daily_cost,
        weather_dependent=location.weather_dependent,
    )


def crew_to_schema(crew: Crew) -> CrewSchema:
    return CrewSchema(
        id=crew.id,
        name=crew.name,
        role=crew.role,
        availability=crew.availability,
        overtime_rate_per_hour=crew.overtime_rate_per_hour,
    )


def scene_to_schema(scene: Scene) -> SceneSchema:
    return SceneSchema(
        scene_id=scene.scene_id,
        name=scene.name,
        type=scene.type,
        duration_hours=scene.duration_hours,
        actors=[a.id for a in scene.actors],
        location=scene.location.id if scene.location else None,
        equipment=[e.id for e in scene.equipment],
        crew=[c.id for c in scene.crew],
        scheduled=scene.scheduled,
    )
