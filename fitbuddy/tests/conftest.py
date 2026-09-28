import os

os.environ["DATABASE_URL"] = "sqlite:///./data/test_fitbuddy.db"
os.environ["GEMINI_API_KEY"] = ""
os.environ["ADMIN_KEY"] = "test-admin"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
