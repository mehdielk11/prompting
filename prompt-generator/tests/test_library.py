"""Tests for /api/library CRUD, search, duplicate, and /api/export."""

from __future__ import annotations

import pytest

CREATE_PAYLOAD = {
    "title": "Test TTS Prompt",
    "content": "Female voice, mid-30s, neutral accent. Professional tone.",
    "type": "tts",
    "tags": ["corporate", "elearning"],
    "score": 82.5,
}


class TestLibraryCRUD:
    def test_create_prompt(self, client):
        """POST /api/library should return 201 with the created prompt."""
        resp = client.post("/api/library", json=CREATE_PAYLOAD)
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == CREATE_PAYLOAD["title"]
        assert data["type"] == "tts"
        assert data["score"] == 82.5
        assert "id" in data

    def test_get_prompt(self, client):
        """GET /api/library/{id} should return the prompt."""
        created = client.post("/api/library", json=CREATE_PAYLOAD).json()
        resp = client.get(f"/api/library/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == created["id"]

    def test_get_prompt_not_found(self, client):
        """GET with a non-existent ID should return 404."""
        resp = client.get("/api/library/999999")
        assert resp.status_code == 404

    def test_list_prompts(self, client):
        """GET /api/library should return a paginated list."""
        resp = client.get("/api/library")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    def test_list_prompts_type_filter(self, client):
        """Type filter should only return prompts of that type."""
        resp = client.get("/api/library", params={"type": "tts"})
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["type"] == "tts"

    def test_update_prompt(self, client):
        """PUT /api/library/{id} should update the specified fields."""
        created = client.post("/api/library", json=CREATE_PAYLOAD).json()
        resp = client.put(
            f"/api/library/{created['id']}",
            json={"title": "Updated Title", "score": 90.0},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Updated Title"
        assert data["score"] == 90.0

    def test_delete_prompt(self, client):
        """DELETE /api/library/{id} should return 204 and remove the prompt."""
        created = client.post("/api/library", json=CREATE_PAYLOAD).json()
        resp = client.delete(f"/api/library/{created['id']}")
        assert resp.status_code == 204
        # Confirm it's gone
        assert client.get(f"/api/library/{created['id']}").status_code == 404

    def test_delete_not_found(self, client):
        """DELETE with a non-existent ID should return 404."""
        resp = client.delete("/api/library/999999")
        assert resp.status_code == 404


class TestLibrarySearch:
    def test_search_returns_results(self, client):
        """Search should return prompts matching the query."""
        client.post("/api/library", json={**CREATE_PAYLOAD, "title": "Searchable Prompt XYZ"})
        resp = client.get("/api/library/search", params={"q": "Searchable"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert any("Searchable" in item["title"] for item in data["items"])

    def test_search_no_results(self, client):
        """Search with no match should return empty list."""
        resp = client.get("/api/library/search", params={"q": "ZZZNOMATCH999"})
        assert resp.status_code == 200
        assert resp.json()["total"] == 0


class TestLibraryDuplicate:
    def test_duplicate_prompt(self, client):
        """Duplicate should create a copy with '(copy)' in the title."""
        created = client.post("/api/library", json=CREATE_PAYLOAD).json()
        resp = client.post(f"/api/library/{created['id']}/duplicate")
        assert resp.status_code == 201
        data = resp.json()
        assert "(copy)" in data["title"]
        assert data["content"] == created["content"]
        assert data["id"] != created["id"]


class TestVersions:
    def test_versions_created_on_update(self, client):
        """Updating a prompt should create a version snapshot."""
        created = client.post("/api/library", json=CREATE_PAYLOAD).json()
        client.put(f"/api/library/{created['id']}", json={"title": "New Title"})
        resp = client.get(f"/api/library/{created['id']}/versions")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1


class TestExport:
    def test_export_json(self, client):
        """Export as JSON should return a valid JSON file."""
        created = client.post("/api/library", json=CREATE_PAYLOAD).json()
        resp = client.post("/api/export", json={"ids": [created["id"]], "format": "json"})
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/json")
        import json
        payload = json.loads(resp.content)
        assert "prompts" in payload
        assert len(payload["prompts"]) == 1

    def test_export_markdown(self, client):
        """Export as Markdown should return text content."""
        created = client.post("/api/library", json=CREATE_PAYLOAD).json()
        resp = client.post("/api/export", json={"ids": [created["id"]], "format": "markdown"})
        assert resp.status_code == 200
        assert "text/markdown" in resp.headers["content-type"]
        content = resp.content.decode("utf-8")
        assert "# Bibliothèque de Prompts Audio" in content

    def test_export_missing_ids(self, client):
        """Export with non-existent IDs should return 404."""
        resp = client.post("/api/export", json={"ids": [999999], "format": "json"})
        assert resp.status_code == 404
