from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from mde.settings import Settings


@pytest.fixture
def client(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "data")
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client


def assert_error_shape(response, expected_status: int | None = None):
    if expected_status is not None:
        assert response.status_code == expected_status
    body = response.json()
    assert set(body) == {"code", "message", "details"}
    assert isinstance(body["code"], str)
    assert isinstance(body["message"], str)
    assert isinstance(body["details"], dict)
    return body
