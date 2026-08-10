"""SQLAlchemy models for the Production Resource Graph (SPEC §4).

Scene is the graph's center; Actor / Equipment / Location / Crew connect to
it (many-to-many, since a resource can appear in multiple scenes over the
course of a production), and Actor / Location connect onward to a Manager.
"""

from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, String, Table
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


scene_actors = Table(
    "scene_actors",
    Base.metadata,
    Column("scene_id", ForeignKey("scenes.scene_id"), primary_key=True),
    Column("actor_id", ForeignKey("actors.id"), primary_key=True),
)

scene_equipment = Table(
    "scene_equipment",
    Base.metadata,
    Column("scene_id", ForeignKey("scenes.scene_id"), primary_key=True),
    Column("equipment_id", ForeignKey("equipment.id"), primary_key=True),
)

scene_crew = Table(
    "scene_crew",
    Base.metadata,
    Column("scene_id", ForeignKey("scenes.scene_id"), primary_key=True),
    Column("crew_id", ForeignKey("crew.id"), primary_key=True),
)


class Manager(Base):
    """A stakeholder contacted when a resource they represent is affected.

    Covers both talent managers (Actor.manager) and location owners/managers
    (Location.manager) — SPEC §4 does not distinguish a separate type.
    """

    __tablename__ = "managers"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)


class Actor(Base):
    __tablename__ = "actors"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    manager_id: Mapped[str | None] = mapped_column(ForeignKey("managers.id"), default=None)
    manager: Mapped[Manager | None] = relationship()
    availability: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String)


class Equipment(Base):
    __tablename__ = "equipment"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    vendor: Mapped[str] = mapped_column(String)
    availability: Mapped[list] = mapped_column(JSON, default=list)
    daily_cost: Mapped[float] = mapped_column(Float)


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    type: Mapped[str] = mapped_column(String)
    manager_id: Mapped[str | None] = mapped_column(ForeignKey("managers.id"), default=None)
    manager: Mapped[Manager | None] = relationship()
    availability: Mapped[list] = mapped_column(JSON, default=list)
    daily_cost: Mapped[float] = mapped_column(Float)
    weather_dependent: Mapped[bool] = mapped_column(Boolean, default=False)


class Crew(Base):
    __tablename__ = "crew"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String)
    availability: Mapped[list] = mapped_column(JSON, default=list)
    overtime_rate_per_hour: Mapped[float] = mapped_column(Float)


class Scene(Base):
    __tablename__ = "scenes"

    scene_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    type: Mapped[str] = mapped_column(String)
    duration_hours: Mapped[float] = mapped_column(Float)
    location_id: Mapped[str | None] = mapped_column(ForeignKey("locations.id"), default=None)
    location: Mapped[Location | None] = relationship()
    scheduled: Mapped[datetime] = mapped_column(DateTime)

    actors: Mapped[list[Actor]] = relationship(secondary=scene_actors)
    equipment: Mapped[list[Equipment]] = relationship(secondary=scene_equipment)
    crew: Mapped[list[Crew]] = relationship(secondary=scene_crew)
