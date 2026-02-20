"""Tests for /tokenize endpoint routing and /detect endpoint."""

import pytest

from service.app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestHealthz:
    def test_healthz(self, client):
        r = client.get("/healthz")
        assert r.status_code == 200
        assert r.get_json()["ok"] is True


class TestVersion:
    def test_version_fields(self, client):
        r = client.get("/version")
        data = r.get_json()
        assert "version" in data
        assert "available_tokenizers" in data
        assert "thai_pythainlp_newmm" in data["available_tokenizers"]
        assert "whitespace" in data["available_tokenizers"]
        assert data["supports_auto"] is True


class TestDetectEndpoint:
    def test_detect_thai(self, client):
        r = client.get("/detect?text=รองเท้า")
        data = r.get_json()
        assert data["detected"]["script"] == "thai"
        assert "normalized" in data

    def test_detect_latin(self, client):
        r = client.get("/detect?text=hello+world")
        data = r.get_json()
        assert data["detected"]["script"] == "latin"

    def test_detect_empty(self, client):
        r = client.get("/detect?text=")
        data = r.get_json()
        assert data["detected"]["script"] == "other"


class TestTokenizeAutoRouting:
    def test_auto_thai_text(self, client):
        """Auto locale + auto tokenizer_id with Thai text -> thai tokenizer."""
        r = client.post("/tokenize", json={
            "text": "รองเท้าวิ่ง",
            "locale": "auto",
            "tokenizer_id": "auto",
        })
        data = r.get_json()
        assert r.status_code == 200
        assert data["chosen"]["tokenizer_id"] == "thai_pythainlp_newmm"
        assert data["chosen"]["reason"] == "thai_script"
        assert data["detected"]["script"] == "thai"
        assert len(data["tokens"]) > 0

    def test_auto_latin_text(self, client):
        """Auto with Latin text -> whitespace fallback."""
        r = client.post("/tokenize", json={
            "text": "cheap running shoes",
            "locale": "auto",
            "tokenizer_id": "auto",
        })
        data = r.get_json()
        assert r.status_code == 200
        assert data["chosen"]["tokenizer_id"] == "whitespace"
        assert data["chosen"]["reason"] == "fallback_whitespace"
        assert data["tokens"] == ["cheap", "running", "shoes"]

    def test_explicit_locale_thai(self, client):
        """locale=th-TH + auto tokenizer_id -> forces Thai tokenizer."""
        r = client.post("/tokenize", json={
            "text": "cheap running shoes",
            "locale": "th-TH",
            "tokenizer_id": "auto",
        })
        data = r.get_json()
        assert r.status_code == 200
        assert data["chosen"]["tokenizer_id"] == "thai_pythainlp_newmm"
        assert data["chosen"]["reason"] == "explicit_locale_thai"

    def test_explicit_tokenizer_thai(self, client):
        """Explicit tokenizer_id=thai_pythainlp_newmm -> uses Thai regardless."""
        r = client.post("/tokenize", json={
            "text": "hello world",
            "tokenizer_id": "thai_pythainlp_newmm",
        })
        data = r.get_json()
        assert r.status_code == 200
        assert data["chosen"]["tokenizer_id"] == "thai_pythainlp_newmm"
        assert data["chosen"]["reason"] == "explicit"

    def test_explicit_tokenizer_whitespace(self, client):
        """Explicit tokenizer_id=whitespace -> uses whitespace."""
        r = client.post("/tokenize", json={
            "text": "รองเท้าวิ่ง",
            "tokenizer_id": "whitespace",
        })
        data = r.get_json()
        assert r.status_code == 200
        assert data["chosen"]["tokenizer_id"] == "whitespace"
        assert data["chosen"]["reason"] == "explicit"

    def test_unknown_tokenizer_400(self, client):
        """Unknown tokenizer_id -> 400 error."""
        r = client.post("/tokenize", json={
            "text": "hello",
            "tokenizer_id": "unknown_thing",
        })
        assert r.status_code == 400
        data = r.get_json()
        assert "error" in data
        assert "available_tokenizers" in data


class TestTokenizeResponseShape:
    def test_full_response_fields(self, client):
        """Verify all required fields are present."""
        r = client.post("/tokenize", json={
            "text": "รองเท้าnike วิ่ง ราคาไม่แพง",
            "locale": "auto",
            "tokenizer_id": "auto",
            "mode": "query",
        })
        data = r.get_json()
        assert r.status_code == 200

        required_fields = [
            "tokens", "joined", "normalized", "tokenizer_id",
            "version", "locale", "mode", "latency_ms",
            "detected", "chosen",
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

        assert "script" in data["detected"]
        assert "confidence" in data["detected"]
        assert "tokenizer_id" in data["chosen"]
        assert "reason" in data["chosen"]

    def test_defaults_when_omitted(self, client):
        """locale and tokenizer_id should default to 'auto'."""
        r = client.post("/tokenize", json={"text": "hello"})
        data = r.get_json()
        assert data["locale"] == "auto"
        assert data["mode"] == "query"
