"""Baseline tokenizer(s) and routing logic."""

from __future__ import annotations

from service.core.registry import TokenizerRegistry


# --------------- baseline tokenizer ---------------


def whitespace_tokenize(text: str) -> list[str]:
    """Split on whitespace, filter empties."""
    return [t for t in text.split() if t]


def register_core(registry: TokenizerRegistry):
    """Register all core (baseline) tokenizers."""
    registry.register(
        tokenizer_id="whitespace",
        fn=whitespace_tokenize,
        meta={
            "pack": "core",
            "supports_scripts": ["latin", "cjk", "other", "thai"],
            "description": "Whitespace tokeniser fallback",
        },
    )


# --------------- routing ---------------


def choose_tokenizer(
    registry: TokenizerRegistry,
    requested_tokenizer_id: str,
    requested_locale: str,
    detected_script: str,
    enabled_tokenizers: list[str],
    default_tokenizer: str,
    auto_routing: bool,
) -> tuple[str, callable | None, str]:
    """Pick the right tokenizer.

    Returns (tokenizer_id, fn, reason).
    fn is None when the requested tokenizer is not installed/enabled.
    """

    # 1) Explicit tokenizer requested
    if requested_tokenizer_id and requested_tokenizer_id != "auto":
        fn, _meta = registry.get(requested_tokenizer_id)
        if fn is None or requested_tokenizer_id not in enabled_tokenizers:
            return requested_tokenizer_id, None, "explicit"
        return requested_tokenizer_id, fn, "explicit"

    # 2) Explicit Thai locale override
    if requested_locale.startswith("th"):
        thai_id = "thai_pythainlp_newmm"
        fn, _meta = registry.get(thai_id)
        if fn is not None and thai_id in enabled_tokenizers:
            return thai_id, fn, "explicit_locale_thai"
        # Thai pack not installed; fall through to default
        fn_def, _ = registry.get(default_tokenizer)
        return default_tokenizer, fn_def, "fallback_default"

    # 3) Auto routing
    if auto_routing:
        if detected_script == "thai":
            thai_id = "thai_pythainlp_newmm"
            fn, _meta = registry.get(thai_id)
            if fn is not None and thai_id in enabled_tokenizers:
                return thai_id, fn, "thai_script"
        # fallback
        fn_def, _ = registry.get(default_tokenizer)
        return default_tokenizer, fn_def, "fallback_default"

    # 4) No auto routing
    fn_def, _ = registry.get(default_tokenizer)
    return default_tokenizer, fn_def, "default_no_auto"
