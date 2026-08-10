from app.models import Scene
from app.seed import seed_scene_42


def test_seed_scene_42_populates_the_full_graph(session):
    seed_scene_42(session)

    scene = session.get(Scene, "SC-042")
    assert scene is not None
    assert scene.name == "Rooftop confrontation"
    assert {a.id for a in scene.actors} == {"ACT-001", "ACT-002"}
    assert {e.id for e in scene.equipment} == {"EQ-001", "EQ-004"}
    assert scene.location.id == "LOC-003"
    assert {c.id for c in scene.crew} == {"CREW-001"}

    # Graph relationships are queryable: Scene -> Actor -> Manager,
    # Scene -> Equipment -> vendor, Scene -> Location -> Manager.
    emma = next(a for a in scene.actors if a.id == "ACT-001")
    assert emma.manager.name
    alexa = next(e for e in scene.equipment if e.id == "EQ-001")
    assert alexa.vendor == "Cinema Rental Tokyo"
    assert scene.location.manager.name


def test_seed_scene_42_is_idempotent(session):
    seed_scene_42(session)
    seed_scene_42(session)

    scenes = session.query(Scene).filter_by(scene_id="SC-042").all()
    assert len(scenes) == 1
