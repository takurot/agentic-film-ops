from sqlalchemy import inspect

from app.db import create_db_engine, get_session, init_db


def test_init_db_creates_the_production_resource_graph_tables(tmp_path):
    test_engine = create_db_engine(tmp_path / "test.db")

    init_db(bind=test_engine)

    tables = set(inspect(test_engine).get_table_names())
    assert {"scenes", "actors", "equipment", "locations", "crew", "managers"} <= tables


def test_get_session_returns_a_session_bound_to_the_given_engine(tmp_path):
    test_engine = create_db_engine(tmp_path / "test.db")
    init_db(bind=test_engine)

    with get_session(bind=test_engine) as session:
        assert session.get_bind() is test_engine
