"""Tests for script detection."""

from service.app import detect_script, normalize


class TestDetectScript:
    def test_thai_only(self):
        result = detect_script("รองเท้าวิ่ง")
        assert result["script"] == "thai"
        assert result["confidence"] == 1.0

    def test_mixed_thai_latin(self):
        """Thai + Latin must resolve to 'thai'."""
        result = detect_script("รองเท้า nike")
        assert result["script"] == "thai"

    def test_japanese_katakana(self):
        result = detect_script("ノートPC")
        # Contains katakana -> cjk, even with Latin "PC"
        # But CJK chars come first, so cjk wins over latin
        assert result["script"] == "cjk"

    def test_chinese(self):
        result = detect_script("电脑")
        assert result["script"] == "cjk"

    def test_korean(self):
        result = detect_script("노트북")
        assert result["script"] == "cjk"

    def test_latin(self):
        result = detect_script("running shoes")
        assert result["script"] == "latin"

    def test_digits_punct(self):
        result = detect_script("12345 !!!")
        assert result["script"] == "other"

    def test_empty_string(self):
        result = detect_script("")
        assert result["script"] == "other"

    def test_confidence_always_one(self):
        """All detections return confidence 1.0 (deterministic)."""
        for text in ["รองเท้า", "hello", "电脑", "12345"]:
            assert detect_script(text)["confidence"] == 1.0


class TestNormalize:
    def test_collapse_whitespace(self):
        assert normalize("hello   world") == "hello world"

    def test_strip_ends(self):
        assert normalize("  hello  ") == "hello"

    def test_nfc(self):
        # NFD form of Thai sara am (U+0E33) can be composed differently
        # Just verify it doesn't crash and returns a string
        result = normalize("สำหรับ")
        assert isinstance(result, str)
        assert len(result) > 0
