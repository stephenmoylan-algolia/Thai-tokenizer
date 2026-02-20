"""Minimal tokenizer registry.

Tokenizers register themselves with an id, a callable, and metadata.
The app queries the registry at request time to find + invoke tokenizers.
"""


class TokenizerRegistry:
    def __init__(self):
        self._tokenizers: dict[str, dict] = {}

    def register(self, tokenizer_id: str, fn: callable, meta: dict):
        """Register a tokenizer.

        *fn* signature: fn(normalized_text: str) -> list[str]
        *meta* should include: tokenizer_id, pack, supports_scripts, description
        """
        self._tokenizers[tokenizer_id] = {
            "fn": fn,
            "meta": {**meta, "tokenizer_id": tokenizer_id},
        }

    def get(self, tokenizer_id: str):
        """Return (fn, meta) or (None, None) if not found."""
        entry = self._tokenizers.get(tokenizer_id)
        if entry is None:
            return None, None
        return entry["fn"], entry["meta"]

    def list_ids(self) -> list[str]:
        return list(self._tokenizers.keys())

    def list_meta(self) -> list[dict]:
        return [e["meta"] for e in self._tokenizers.values()]
