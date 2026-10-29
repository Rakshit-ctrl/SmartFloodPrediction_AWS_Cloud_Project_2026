import os
import tempfile
from pathlib import Path

# Must be set before the app is imported so tests never touch the real database.
_TMP = tempfile.mkdtemp(prefix="flood_tests_")
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_TMP, 'test.db').as_posix()}"
Path(_TMP, "empty_models").mkdir()
os.environ["MODEL_DIR"] = str(Path(_TMP, "empty_models"))  # no model installed by default

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_registry(monkeypatch):
    from app.ml import registry
    monkeypatch.setenv("MODEL_DIR", os.environ["MODEL_DIR"])
    registry.reset()
    yield
    registry.reset()


@pytest.fixture(autouse=True)
def _clear_geocode_cache():
    from app.services.weather import geocode
    geocode.cache_clear()
    yield
    geocode.cache_clear()


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
