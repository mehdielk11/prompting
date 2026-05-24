"""Tests for POST /api/generate and POST /api/optimize."""

from __future__ import annotations

from unittest.mock import patch

import pytest


GENERATE_PAYLOAD = {
    "description": "A warm female voice for a corporate e-learning introduction",
    "type": "tts",
    "tone": "professional",
    "duration": "short",
}

OPTIMIZE_PAYLOAD = {
    "raw_prompt": "A calm female voice reading a story.",
    "objective": "precision",
    "type": "tts",
}


class TestGenerate:
    def test_generate_happy_path(self, client, mock_hf_client):
        """A valid request should return 200 with prompt, variants, explanation, score."""
        with patch("backend.services.hf_client.get_hf_client", return_value=mock_hf_client):
            resp = client.post("/api/generate", json=GENERATE_PAYLOAD)
        assert resp.status_code == 200
        data = resp.json()
        assert "prompt" in data
        assert "variants" in data
        assert len(data["variants"]) == 2
        assert "explanation" in data
        assert 0 <= data["score"] <= 100

    def test_generate_missing_description(self, client):
        """Missing description should return 422."""
        payload = {**GENERATE_PAYLOAD, "description": ""}
        resp = client.post("/api/generate", json=payload)
        assert resp.status_code == 422

    def test_generate_invalid_type(self, client):
        """Invalid audio type should return 422."""
        payload = {**GENERATE_PAYLOAD, "type": "podcast"}
        resp = client.post("/api/generate", json=payload)
        assert resp.status_code == 422

    def test_generate_invalid_duration(self, client):
        """Invalid duration value should return 422."""
        payload = {**GENERATE_PAYLOAD, "duration": "very_long"}
        resp = client.post("/api/generate", json=payload)
        assert resp.status_code == 422

    def test_generate_invalid_tone(self, client):
        """Invalid tone value should return 422."""
        payload = {**GENERATE_PAYLOAD, "tone": "aggressive_robot"}
        resp = client.post("/api/generate", json=payload)
        assert resp.status_code == 422


class TestOptimize:
    def test_optimize_happy_path(self, client, mock_hf_client):
        """A valid optimise request should return 200 with before/after scores."""
        with patch("backend.services.hf_client.get_hf_client", return_value=mock_hf_client):
            resp = client.post("/api/optimize", json=OPTIMIZE_PAYLOAD)
        assert resp.status_code == 200
        data = resp.json()
        assert "optimized_prompt" in data
        assert "changes" in data
        assert "score_before" in data
        assert "score_after" in data

    def test_optimize_missing_prompt(self, client):
        """Empty raw_prompt should return 422."""
        resp = client.post("/api/optimize", json={"raw_prompt": "", "objective": "clarity"})
        assert resp.status_code == 422

    def test_optimize_invalid_objective(self, client):
        """Invalid objective should return 422."""
        resp = client.post("/api/optimize", json={"raw_prompt": "Some prompt", "objective": "speed"})
        assert resp.status_code == 422

    def test_optimize_with_audio_type(self, client, mock_hf_client):
        """Optimize should accept and use the audio type for scoring context."""
        with patch("backend.services.hf_client.get_hf_client", return_value=mock_hf_client):
            resp = client.post(
                "/api/optimize",
                json={"raw_prompt": "Cinematic orchestral music with strings.", "objective": "precision", "type": "music"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "optimized_prompt" in data
        assert "score_before" in data
        assert "score_after" in data
