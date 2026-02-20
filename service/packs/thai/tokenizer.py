"""Thai tokenizer — PyThaiNLP (newmm engine)."""

import os

from service.core.registry import TokenizerRegistry

THAI_ENGINE = os.environ.get("THAI_ENGINE", "newmm")


def tokenize_thai(text: str) -> list[str]:
    """Word-tokenize Thai text using PyThaiNLP."""
    from pythainlp.tokenize import word_tokenize

    tokens = word_tokenize(text, engine=THAI_ENGINE, keep_whitespace=False)
    return [t for t in tokens if t]


def register(registry: TokenizerRegistry):
    """Register the Thai tokenizer in the given registry."""
    registry.register(
        tokenizer_id="thai_pythainlp_newmm",
        fn=tokenize_thai,
        meta={
            "pack": "thai",
            "supports_scripts": ["thai"],
            "description": "PyThaiNLP tokenizer (newmm)",
        },
    )
