"""Text normalisation utilities."""

import re
import unicodedata


def normalize_text(text: str) -> str:
    """Unicode NFC normalise, collapse whitespace, strip ends."""
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"\s+", " ", text)
    text = text.strip()
    return text
