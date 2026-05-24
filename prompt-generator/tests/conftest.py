"""Shared pytest fixtures."""

from __future__ import annotations

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Point the DB to a temp file before importing anything that touches the DB
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["SQLITE_DB_PATH"] = _tmp.name
os.environ["HF_API_TOKEN"] = "test_token"


@pytest.fixture(scope="session", autouse=True)
def _init_test_db():
    """Initialise the test database once per session."""
    from backend.database.db import init_db
    init_db()


@pytest.fixture(scope="session")
def mock_hf_client():
    """Return a MagicMock that replaces the real HFClient."""
    mock = MagicMock()
    mock.generate_text.return_value = (
        '{"prompt": "Test prompt", "variants": ["Variant A", "Variant B"], '
        '"explanation": "Test explanation", '
        '"clarity": 80, "specificity": 75, "structure": 70, '
        '"relevance": 85, "creativity": 60, '
        '"recommendations": ["Add more detail"], '
        '"optimized_prompt": "Optimised test prompt", '
        '"changes": ["Added detail", "Improved structure"]}'
    )
    return mock


@pytest.fixture(scope="session")
def client(mock_hf_client):
    """FastAPI TestClient with HF calls mocked out."""
    with patch("backend.services.hf_client.get_hf_client", return_value=mock_hf_client):
        from backend.main import app
        with TestClient(app) as c:
            yield c
