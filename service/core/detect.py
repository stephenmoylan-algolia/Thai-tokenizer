"""Deterministic O(n) script detection via Unicode ranges.

Priority: thai > cjk > latin > other.
Mixed Thai+Latin resolves to 'thai'.
"""


def detect_script(text: str) -> dict:
    """Return {"script": str, "confidence": 1.0} for *text*."""
    has_thai = False
    has_cjk = False
    has_latin = False

    for ch in text:
        cp = ord(ch)
        # Thai: U+0E00-U+0E7F
        if 0x0E00 <= cp <= 0x0E7F:
            has_thai = True
            break  # Thai wins immediately
        # CJK Unified Ideographs / Hiragana / Katakana / Hangul
        elif (0x4E00 <= cp <= 0x9FFF
              or 0x3040 <= cp <= 0x309F
              or 0x30A0 <= cp <= 0x30FF
              or 0xAC00 <= cp <= 0xD7AF):
            has_cjk = True
        elif (0x0041 <= cp <= 0x005A) or (0x0061 <= cp <= 0x007A):
            has_latin = True

    if has_thai:
        script = "thai"
    elif has_cjk:
        script = "cjk"
    elif has_latin:
        script = "latin"
    else:
        script = "other"

    return {"script": script, "confidence": 1.0}
