import os

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Location, Problem, Report, User


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_core_crud_relationships_persist(db_session):
    user = User(email="citizen@example.test", password_hash="test-hash")
    location = Location(latitude=16.5062, longitude=80.6480, address="School road")
    problem = Problem(title="Flooded school road", summary="Children cannot enter safely", location=location)
    report = Report(problem=problem, reporter=user, description="Heavy rain floods the access road")
    db_session.add(report)
    db_session.commit()

    loaded = db_session.scalar(select(Problem).where(Problem.title == "Flooded school road"))
    assert loaded is not None
    assert loaded.location.latitude == pytest.approx(16.5062)
    assert loaded.reports[0].reporter.email == "citizen@example.test"