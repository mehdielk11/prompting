"""Tests for POST /api/score."""

from __future__ import annotations

from unittest.mock import patch

SCORE_PAYLOAD = {
    "prompt": "Female voice, mid-30s, neutral French accent. Warm and confident tone. 130 wpm.",
    "type": "tts",
}

SCORE_JSON_RESPONSE = (
    '{"clarity": 80, "specificity": 75, "structure": 70, '
    '"relevance": 85, "creativity": 60, '
    '"recommendations": ["Add delivery style", "Specify context"]}'
)


class TestScore:
    def test_score_happy_path(self, client, mock_hf_client):
        """Valid prompt should return 200 with global score and dimension scores."""
        mock_hf_client.generate_text.return_value = SCORE_JSON_RESPONSE
        with patch("backend.services.hf_client.get_hf_client", return_value=mock_hf_client):
            resp = client.post("/api/score", json=SCORE_PAYLOAD)
        assert resp.status_code == 200
        data = resp.json()
        assert 0 <= data["global_score"] <= 100
        dims = data["dimension_scores"]
        for dim in ("clarity", "specificity", "structure", "relevance", "creativity"):
            assert dim in dims
            assert 0 <= dims[dim] <= 100
        assert isinstance(data["recommendations"], list)

    def test_score_weighted_calculation(self, client, mock_hf_client):
        """Global score should match the weighted formula."""
        mock_hf_client.generate_text.return_value = SCORE_JSON_RESPONSE
        with patch("backend.services.hf_client.get_hf_client", return_value=mock_hf_client):
            resp = client.post("/api/score", json=SCORE_PAYLOAD)
        data = resp.json()
        dims = data["dimension_scores"]
        expected = round(
            dims["clarity"] * 0.25
            + dims["specificity"] * 0.25
            + dims["structure"] * 0.20
            + dims["relevance"] * 0.20
            + dims["creativity"] * 0.10,
            1,
        )
        assert abs(data["global_score"] - expected) < 0.5

    def test_score_missing_prompt(self, client):
        """Empty prompt should return 422."""
        resp = client.post("/api/score", json={"prompt": "", "type": "tts"})
        assert resp.status_code == 422

    def test_score_invalid_type(self, client):
        """Invalid audio type should return 422."""
        resp = client.post("/api/score", json={"prompt": "Some prompt", "type": "podcast"})
        assert resp.status_code == 422
