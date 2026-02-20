import os
import time
import unicodedata
import re

from flask import Flask, request, jsonify

app = Flask(__name__)

APP_VERSION = os.environ.get("APP_VERSION", "0.2.0")
TOKENIZER_ID = os.environ.get("TOKENIZER_ID", "thai_pythainlp_newmm")
THAI_ENGINE = os.environ.get("THAI_ENGINE", "newmm")

AVAILABLE_TOKENIZERS = ["thai_pythainlp_newmm", "whitespace"]


# --------------- helpers ---------------


def normalize(text: str) -> str:
    """Unicode NFC, collapse whitespace, strip ends."""
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"\s+", " ", text)
    text = text.strip()
    return text


def detect_script(text: str) -> dict:
    """Deterministic O(n) script detection via Unicode ranges.

    Priority: thai > cjk > latin > other.
    Mixed Thai+Latin resolves to 'thai'.
    """
    has_thai = False
    has_cjk = False
    has_latin = False

    for ch in text:
        cp = ord(ch)
        # Thai: U+0E00–U+0E7F
        if 0x0E00 <= cp <= 0x0E7F:
            has_thai = True
            break  # Thai wins immediately
        # CJK Unified Ideographs: U+4E00–U+9FFF
        # Hiragana: U+3040–U+309F
        # Katakana: U+30A0–U+30FF
        # Hangul syllables: U+AC00–U+D7AF
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


def tokenize_thai(text: str) -> list[str]:
    from pythainlp.tokenize import word_tokenize

    tokens = word_tokenize(text, engine=THAI_ENGINE, keep_whitespace=False)
    return [t for t in tokens if t]


def tokenize_whitespace(text: str) -> list[str]:
    return [t for t in text.split() if t]


def route_tokenizer(normalized: str, locale: str, tokenizer_id: str):
    """Choose tokenizer based on locale, tokenizer_id, and detected script.

    Returns (tokens, chosen_tokenizer_id, reason, detected).
    """
    detected = detect_script(normalized)

    # Explicit tokenizer requested
    if tokenizer_id != "auto":
        if tokenizer_id == "thai_pythainlp_newmm":
            tokens = tokenize_thai(normalized)
            return tokens, "thai_pythainlp_newmm", "explicit", detected
        elif tokenizer_id == "whitespace":
            tokens = tokenize_whitespace(normalized)
            return tokens, "whitespace", "explicit", detected
        else:
            return None, tokenizer_id, "unknown", detected

    # Auto mode: explicit locale override
    if locale.startswith("th"):
        tokens = tokenize_thai(normalized)
        return tokens, "thai_pythainlp_newmm", "explicit_locale_thai", detected

    # Auto mode: detection-based routing
    if detected["script"] == "thai":
        tokens = tokenize_thai(normalized)
        return tokens, "thai_pythainlp_newmm", "thai_script", detected
    else:
        tokens = tokenize_whitespace(normalized)
        return tokens, "whitespace", "fallback_whitespace", detected


# --------------- endpoints ---------------


@app.route("/healthz")
def healthz():
    return jsonify(ok=True)


@app.route("/version")
def version():
    return jsonify(
        version=APP_VERSION,
        tokenizer_id=TOKENIZER_ID,
        engine=THAI_ENGINE,
        available_tokenizers=AVAILABLE_TOKENIZERS,
        supports_auto=True,
    )


@app.route("/detect")
def detect():
    text = request.args.get("text", "")
    normalized = normalize(text)
    detected = detect_script(normalized)
    return jsonify(normalized=normalized, detected=detected)


@app.route("/tokenize", methods=["POST"])
def tokenize():
    body = request.get_json(force=True)
    raw_text = body.get("text", "")
    locale = body.get("locale", "auto")
    mode = body.get("mode", "query")
    tokenizer_id = body.get("tokenizer_id", "auto")

    normalized = normalize(raw_text)

    t0 = time.perf_counter()
    tokens, chosen_id, reason, detected = route_tokenizer(
        normalized, locale, tokenizer_id
    )
    latency_ms = round((time.perf_counter() - t0) * 1000, 2)

    # Unknown tokenizer -> 400
    if reason == "unknown":
        return jsonify(
            error=f"Unknown tokenizer_id: {tokenizer_id}",
            available_tokenizers=AVAILABLE_TOKENIZERS,
        ), 400

    return jsonify(
        tokens=tokens,
        joined=" ".join(tokens),
        normalized=normalized,
        tokenizer_id=chosen_id,
        version=APP_VERSION,
        locale=locale,
        mode=mode,
        latency_ms=latency_ms,
        detected=detected,
        chosen={"tokenizer_id": chosen_id, "reason": reason},
    )


# --------------- tiny demo UI ---------------

UI_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Thai Tokenizer MVP</title>
<style>
  body{font-family:system-ui,sans-serif;max-width:640px;margin:2rem auto;padding:0 1rem}
  textarea{width:100%;height:80px;font-size:1rem}
  select,button{font-size:1rem;margin:.5rem .5rem 0 0;padding:.4rem .8rem}
  pre{background:#f4f4f4;padding:1rem;overflow-x:auto;border-radius:4px}
  .row{display:flex;gap:.5rem;flex-wrap:wrap;align-items:end}
</style>
</head>
<body>
<h1>Thai Tokenizer MVP <small>v0.2</small></h1>
<textarea id="txt" placeholder="Type text here...">รองเท้าnike วิ่ง ราคาไม่แพง</textarea>
<div class="row">
<label>Locale
  <select id="locale">
    <option value="auto" selected>auto</option>
    <option value="th-TH">th-TH</option>
    <option value="en-US">en-US</option>
  </select>
</label>
<label>Tokenizer
  <select id="tid">
    <option value="auto" selected>auto</option>
    <option value="thai_pythainlp_newmm">thai_pythainlp_newmm</option>
    <option value="whitespace">whitespace</option>
  </select>
</label>
<button onclick="run()">Tokenize</button>
</div>
<pre id="out"></pre>
<script>
async function run(){
  const res=await fetch("/tokenize",{
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({
      text:document.getElementById("txt").value,
      locale:document.getElementById("locale").value,
      tokenizer_id:document.getElementById("tid").value,
      mode:"query"
    })
  });
  document.getElementById("out").textContent=JSON.stringify(await res.json(),null,2);
}
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return UI_HTML, 200, {"Content-Type": "text/html"}
