import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
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
