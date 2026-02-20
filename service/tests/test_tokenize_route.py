"""Tests for tokenizer routing, endpoints, and registry-based pack loading."""

import os
import pytest

from service.core.registry import TokenizerRegistry
from service.core.tokenize import whitespace_tokenize, register_core, choose_tokenizer


# --------------- unit tests: registry + routing ---------------


class TestRegistry:
    def test_register_and_get(self):
        reg = TokenizerRegistry()
        reg.register("test", lambda t: t.split(), {"pack": "test", "supports_scripts": ["latin"], "description": "test"})
        fn, meta = reg.get("test")
        assert fn is not None
        assert meta["pack"] == "test"

    def test_get_missing(self):
        reg = TokenizerRegistry()
        fn, meta = reg.get("nope")
        assert fn is None
        assert meta is None

    def test_list_ids(self):
        reg = TokenizerRegistry()
        register_core(reg)
        assert "whitespace" in reg.list_ids()

    def test_list_meta(self):
        reg = TokenizerRegistry()
        register_core(reg)
        metas = reg.list_meta()
        assert any(m["tokenizer_id"] == "whitespace" for m in metas)


class TestWhitespaceTokenizer:
    def test_basic(self):
        assert whitespace_tokenize("hello world") == ["hello", "world"]

    def test_extra_spaces(self):
        assert whitespace_tokenize("  a   b  ") == ["a", "b"]

    def test_empty(self):
        assert whitespace_tokenize("") == []


class TestChooseTokenizer:
    def _make_registry_with_thai(self):
        reg = TokenizerRegistry()
        register_core(reg)
        # Simulate thai pack registration
        reg.register(
            "thai_pythainlp_newmm",
            lambda t: ["mock_thai"],
            {"pack": "thai", "supports_scripts": ["thai"], "description": "mock"},
        )
        return reg

    def test_explicit_tokenizer(self):
        reg = self._make_registry_with_thai()
        tid, fn, reason = choose_tokenizer(reg, "whitespace", "auto", "thai", reg.list_ids(), "whitespace", True)
        assert tid == "whitespace"
        assert reason == "explicit"

    def test_explicit_unknown_tokenizer(self):
        reg = self._make_registry_with_thai()
        tid, fn, reason = choose_tokenizer(reg, "nope", "auto", "latin", reg.list_ids(), "whitespace", True)
        assert fn is None

    def test_explicit_locale_thai(self):
        reg = self._make_registry_with_thai()
        tid, fn, reason = choose_tokenizer(reg, "auto", "th-TH", "latin", reg.list_ids(), "whitespace", True)
        assert tid == "thai_pythainlp_newmm"
        assert reason == "explicit_locale_thai"

    def test_auto_thai_script(self):
        reg = self._make_registry_with_thai()
        tid, fn, reason = choose_tokenizer(reg, "auto", "auto", "thai", reg.list_ids(), "whitespace", True)
        assert tid == "thai_pythainlp_newmm"
        assert reason == "thai_script"

    def test_auto_latin_fallback(self):
        reg = self._make_registry_with_thai()
        tid, fn, reason = choose_tokenizer(reg, "auto", "auto", "latin", reg.list_ids(), "whitespace", True)
        assert tid == "whitespace"
        assert reason == "fallback_default"

    def test_no_auto_routing(self):
        reg = self._make_registry_with_thai()
        tid, fn, reason = choose_tokenizer(reg, "auto", "auto", "thai", reg.list_ids(), "whitespace", False)
        assert tid == "whitespace"
        assert reason == "default_no_auto"

    def test_core_only_thai_text_falls_to_whitespace(self):
        """When Thai pack is NOT installed, Thai text routes to whitespace."""
        reg = TokenizerRegistry()
        register_core(reg)
        tid, fn, reason = choose_tokenizer(reg, "auto", "auto", "thai", reg.list_ids(), "whitespace", True)
        assert tid == "whitespace"
        assert reason == "fallback_default"
        assert fn is not None


# --------------- integration tests: Flask endpoints ---------------


@pytest.fixture
def client():
    """Client with Thai pack loaded (full integration)."""
    os.environ["INSTALLED_PACKS"] = "thai"
    # Re-import to trigger pack loading with env set
    import importlib
    import service.app
    importlib.reload(service.app)
    service.app.app.config["TESTING"] = True
    with service.app.app.test_client() as c:
        yield c


@pytest.fixture
def client_core_only():
    """Client with NO packs loaded (core only)."""
    os.environ["INSTALLED_PACKS"] = ""
    import importlib
    import service.app
    importlib.reload(service.app)
    service.app.app.config["TESTING"] = True
    with service.app.app.test_client() as c:
        yield c


class TestHealthz:
    def test_healthz(self, client):
        r = client.get("/healthz")
        assert r.status_code == 200
        assert r.get_json()["ok"] is True


class TestVersion:
    def test_version_with_thai(self, client):
        data = client.get("/version").get_json()
        assert "version" in data
        assert "thai" in data["installed_packs"]
        assert "thai_pythainlp_newmm" in data["available_tokenizers"]
        assert "whitespace" in data["available_tokenizers"]
        assert data["auto_routing"] is True

    def test_version_core_only(self, client_core_only):
        data = client_core_only.get("/version").get_json()
        assert "thai" not in data["installed_packs"]
        assert "thai_pythainlp_newmm" not in data["available_tokenizers"]
        assert "whitespace" in data["available_tokenizers"]


class TestDetectEndpoint:
    def test_detect_thai(self, client):
        data = client.get("/detect?text=รองเท้า").get_json()
        assert data["detected"]["script"] == "thai"

    def test_detect_latin(self, client):
        data = client.get("/detect?text=hello+world").get_json()
        assert data["detected"]["script"] == "latin"


class TestTokenizeWithThai:
    def test_auto_thai_text(self, client):
        r = client.post("/tokenize", json={
            "text": "รองเท้าวิ่ง",
            "locale": "auto",
            "tokenizer_id": "auto",
        })
        data = r.get_json()
        assert r.status_code == 200
        assert data["chosen"]["tokenizer_id"] == "thai_pythainlp_newmm"
        assert data["chosen"]["reason"] == "thai_script"
        assert len(data["tokens"]) > 0

    def test_auto_latin_text(self, client):
        r = client.post("/tokenize", json={
            "text": "cheap running shoes",
            "locale": "auto",
            "tokenizer_id": "auto",
        })
        data = r.get_json()
        assert r.status_code == 200
        assert data["chosen"]["tokenizer_id"] == "whitespace"
        assert data["chosen"]["reason"] == "fallback_default"
        assert data["tokens"] == ["cheap", "running", "shoes"]

    def test_explicit_locale_thai(self, client):
        r = client.post("/tokenize", json={
            "text": "cheap running shoes",
            "locale": "th-TH",
            "tokenizer_id": "auto",
        })
        data = r.get_json()
        assert r.status_code == 200
        assert data["chosen"]["tokenizer_id"] == "thai_pythainlp_newmm"
        assert data["chosen"]["reason"] == "explicit_locale_thai"

    def test_explicit_tokenizer(self, client):
        r = client.post("/tokenize", json={
            "text": "hello world",
            "tokenizer_id": "thai_pythainlp_newmm",
        })
        data = r.get_json()
        assert r.status_code == 200
        assert data["chosen"]["reason"] == "explicit"

    def test_explicit_whitespace(self, client):
        r = client.post("/tokenize", json={
            "text": "รองเท้าวิ่ง",
            "tokenizer_id": "whitespace",
        })
        data = r.get_json()
        assert r.status_code == 200
        assert data["chosen"]["tokenizer_id"] == "whitespace"

    def test_unknown_tokenizer_400(self, client):
        r = client.post("/tokenize", json={
            "text": "hello",
            "tokenizer_id": "unknown_thing",
        })
        assert r.status_code == 400
        assert "error" in r.get_json()

    def test_empty_text_400(self, client):
        r = client.post("/tokenize", json={"text": "   "})
        assert r.status_code == 400

    def test_full_response_shape(self, client):
        r = client.post("/tokenize", json={
            "text": "รองเท้าnike วิ่ง",
            "locale": "auto",
            "tokenizer_id": "auto",
            "mode": "query",
        })
        data = r.get_json()
        for field in ["tokens", "joined", "normalized", "tokenizer_id",
                      "version", "locale", "mode", "latency_ms",
                      "detected", "chosen"]:
            assert field in data, f"Missing: {field}"
        assert "script" in data["detected"]
        assert "reason" in data["chosen"]


class TestTokenizeCoreOnly:
    def test_thai_text_routes_to_whitespace(self, client_core_only):
        """Without Thai pack, Thai text falls back to whitespace."""
        r = client_core_only.post("/tokenize", json={
            "text": "รองเท้าวิ่ง",
            "locale": "auto",
            "tokenizer_id": "auto",
        })
        data = r.get_json()
        assert r.status_code == 200
        assert data["chosen"]["tokenizer_id"] == "whitespace"
        assert data["chosen"]["reason"] == "fallback_default"

    def test_explicit_thai_tokenizer_400(self, client_core_only):
        """Explicitly requesting Thai tokenizer when not installed -> 400."""
        r = client_core_only.post("/tokenize", json={
            "text": "hello",
            "tokenizer_id": "thai_pythainlp_newmm",
        })
        assert r.status_code == 400
