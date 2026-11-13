import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.config import settings
from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture()
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def admin_headers(client, db_session):
    client.post("/auth/signup", json={"username": "admin", "password": "password123"})
    user = db_session.query(models.User).filter_by(username="admin").one()
    user.is_admin = True
    db_session.commit()
    token = client.post(
        "/auth/login", data={"username": "admin", "password": "password123"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def local_sandbox_by_default(monkeypatch):
    """Normal tests use the fast local runner so they don't need Docker.
    The Docker tests in test_sandbox.py switch it back on themselves."""
    monkeypatch.setattr(settings, "sandbox_backend", "local")
