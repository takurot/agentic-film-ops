from pathlib import Path

from fastapi.testclient import TestClient


from app.api import router
from app.db import create_db_engine, get_session
from app.models import Actor, Base, Crew, Equipment, Location, Scene
from app.scenario_loader import (
    DemoScenario,
    compute_scenario_hash,
    get_scenario_hash,
    get_scenario_raw_data,
    load_demo_scenario,
)
from app.seed import seed_demo_incident, seed_scene_42
from app.workflow import Incident


def test_scenario_json_and_schema_validation():
    """Verify demo_scenario.json conforms to Pydantic schema and raw structure."""
    scenario = load_demo_scenario()
    assert isinstance(scenario, DemoScenario)
    assert scenario.meta.scenario_id == "SCENARIO-SC042-RAIN-V1"
    assert scenario.meta.version == "1.0.0"

    raw = get_scenario_raw_data()
    assert "production" in raw
    assert "resources" in raw
    assert "incident" in raw
    assert "options" in raw
    assert "cost_benefit_model" in raw


def test_scenario_financial_formula_recalculation():
    """Verify avoided cost formula: standby_day_penalty ($84k) - option_a_variance ($4.2k) = $79,800."""
    scenario = load_demo_scenario()
    model = scenario.cost_benefit_model

    standby = model.standby_day_penalty_usd
    variance = model.option_a_variance_usd
    net_avoided = model.net_cost_avoided_usd

    assert standby == 84000
    assert variance == 4200
    assert net_avoided == 79800
    assert standby - variance == net_avoided

    # Verify Option A in options matches model variance
    opt_a = next(opt for opt in scenario.options if opt["option_id"] == "OPT-A")
    assert opt_a["cost_impact"] == variance
    assert opt_a["recommended"] is True


def test_seed_matches_canonical_scenario(tmp_path: Path):
    """Verify database seed produces entities that match canonical scenario definition."""
    engine = create_db_engine(tmp_path / "contract.db")
    Base.metadata.create_all(engine)

    with get_session(engine) as session:
        seed_scene_42(session)
        seed_demo_incident(session)

        # Check Scene 42
        scene = session.get(Scene, "SC-042")
        assert scene is not None
        assert scene.name == "Rooftop confrontation"
        assert scene.location.id == "LOC-003"
        assert {a.id for a in scene.actors} == {"ACT-001", "ACT-002"}
        assert {e.id for e in scene.equipment} == {"EQ-001", "EQ-004"}
        assert {c.id for c in scene.crew} == {"CREW-001"}

        # Check Actors
        emma = session.get(Actor, "ACT-001")
        assert emma.name == "Emma Carter"
        daniel = session.get(Actor, "ACT-002")
        assert daniel.name == "Daniel"

        # Check Equipment
        alexa = session.get(Equipment, "EQ-001")
        assert alexa.name == "ARRI Alexa 35"
        lighting = session.get(Equipment, "EQ-004")
        assert lighting.name == "Lighting Kit"

        # Check Locations
        rooftop = session.get(Location, "LOC-003")
        assert rooftop.name == "Rooftop, Shibuya Tower"
        assert rooftop.type == "outdoor"
        studio_b = session.get(Location, "LOC-STUDIO-B")
        assert studio_b.name == "Studio B"
        assert studio_b.type == "indoor"

        # Check Crew
        kenji = session.get(Crew, "CREW-001")
        assert kenji.name == "Kenji Sato"

        # Check Incident
        scenario = load_demo_scenario()
        incident = session.get(Incident, scenario.incident["incident_id"])
        assert incident is not None
        assert incident.scene_id == "SC-042"
        assert incident.type == "WEATHER"
        assert incident.resolved is False


def test_production_health_endpoint_matches_scenario(tmp_path: Path):
    """Verify GET /api/production/health delivers exact canonical scenario production metrics."""
    from fastapi import FastAPI

    from app.db import get_db_session

    engine = create_db_engine(tmp_path / "health.db")
    Base.metadata.create_all(engine)
    with get_session(engine) as session:
        seed_scene_42(session)
        seed_demo_incident(session)

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db_session] = lambda: get_session(engine)


    client = TestClient(app)
    res = client.get("/api/production/health")
    assert res.status_code == 200
    data = res.json()

    scenario = load_demo_scenario()
    prod = scenario.production
    assert data["production_day_current"] == prod.production_day_current
    assert data["production_day_total"] == prod.production_day_total
    assert data["schedule_adherence_percent"] == prod.schedule_adherence_percent
    assert data["budget_spent_usd"] == prod.budget_spent_usd
    assert data["budget_total_usd"] == prod.budget_total_usd
    assert data["scenes_completed"] == prod.scenes_completed
    assert data["scenes_total"] == prod.scenes_total
    assert data["overall_risk"] == prod.overall_risk
    assert len(data["today_scenes"]) == len(scenario.today_scenes)


def test_scenario_hash_determinism():
    """Verify scenario hash is deterministic."""
    raw = get_scenario_raw_data()
    hash_1 = compute_scenario_hash(raw)
    hash_2 = get_scenario_hash()
    assert hash_1 == hash_2
    assert len(hash_1) == 16
