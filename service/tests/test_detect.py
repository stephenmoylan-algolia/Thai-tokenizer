"""Tests for script detection and normalisation (core modules)."""

from service.core.detect import detect_script
from service.core.normalize import normalize_text


class TestDetectScript:
    def test_thai_only(self):
        assert detect_script("รองเท้าวิ่ง")["script"] == "thai"

    def test_mixed_thai_latin(self):
        assert detect_script("รองเท้า nike")["script"] == "thai"

    def test_japanese_katakana(self):
        assert detect_script("ノートPC")["script"] == "cjk"

    def test_chinese(self):
        assert detect_script("电脑")["script"] == "cjk"

    def test_korean(self):
        assert detect_script("노트북")["script"] == "cjk"

    def test_latin(self):
        assert detect_script("running shoes")["script"] == "latin"

    def test_digits_punct(self):
        assert detect_script("12345 !!!")["script"] == "other"

    def test_empty_string(self):
        assert detect_script("")["script"] == "other"

    def test_confidence_always_one(self):
        for text in ["รองเท้า", "hello", "电脑", "12345"]:
            assert detect_script(text)["confidence"] == 1.0


class TestNormalize:
    def test_collapse_whitespace(self):
        assert normalize_text("hello   world") == "hello world"

    def test_strip_ends(self):
        assert normalize_text("  hello  ") == "hello"

    def test_nfc(self):
        result = normalize_text("สำหรับ")
        assert isinstance(result, str)
        assert len(result) > 0
