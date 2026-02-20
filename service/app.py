"""Thai Tokenizer MVP — Flask app with registry-based tokenizer routing."""

import logging
import os
import time

from flask import Flask, request, jsonify

from service.core.normalize import normalize_text
from service.core.detect import detect_script
from service.core.registry import TokenizerRegistry
from service.core.tokenize import register_core, choose_tokenizer

log = logging.getLogger(__name__)

app = Flask(__name__)

# --------------- config ---------------

APP_VERSION = os.environ.get("APP_VERSION", "0.3.0")
INSTALLED_PACKS_ENV = os.environ.get("INSTALLED_PACKS", "")
ENABLED_TOKENIZERS_ENV = os.environ.get("ENABLED_TOKENIZERS", "")
DEFAULT_TOKENIZER = os.environ.get("DEFAULT_TOKENIZER", "whitespace")
AUTO_ROUTING = os.environ.get("AUTO_ROUTING", "true").lower() in ("true", "1", "yes")

# --------------- registry bootstrap ---------------

registry = TokenizerRegistry()
register_core(registry)

loaded_packs: list[str] = ["core"]

# Load optional packs based on INSTALLED_PACKS env
_requested_packs = [p.strip() for p in INSTALLED_PACKS_ENV.split(",") if p.strip()]

for pack_name in _requested_packs:
    try:
        mod = __import__(f"service.packs.{pack_name}", fromlist=["register"])
        mod.register(registry)
        loaded_packs.append(pack_name)
        log.info("Loaded pack: %s", pack_name)
    except Exception as exc:
        log.warning("Failed to load pack %s: %s", pack_name, exc)

# Compute enabled tokenizers
if ENABLED_TOKENIZERS_ENV:
    enabled_tokenizers = [
        t.strip() for t in ENABLED_TOKENIZERS_ENV.split(",") if t.strip()
    ]
else:
    enabled_tokenizers = registry.list_ids()


# --------------- endpoints ---------------


@app.route("/healthz")
def healthz():
    return jsonify(ok=True)


@app.route("/version")
def version():
    return jsonify(
        version=APP_VERSION,
        installed_packs=loaded_packs,
        available_tokenizers=registry.list_ids(),
        enabled_tokenizers=enabled_tokenizers,
        default_tokenizer=DEFAULT_TOKENIZER,
        auto_routing=AUTO_ROUTING,
    )


@app.route("/detect")
def detect():
    text = request.args.get("text", "")
    normalized = normalize_text(text)
    detected = detect_script(normalized)
    return jsonify(normalized=normalized, detected=detected)


@app.route("/tokenize", methods=["POST"])
def tokenize():
    body = request.get_json(force=True)
    raw_text = body.get("text", "")
    locale = body.get("locale", "auto")
    mode = body.get("mode", "query")
    tokenizer_id = body.get("tokenizer_id", "auto")

    normalized = normalize_text(raw_text)

    if not normalized:
        return jsonify(error="text is empty after normalisation"), 400

    detected = detect_script(normalized)

    t0 = time.perf_counter()
    chosen_id, fn, reason = choose_tokenizer(
        registry=registry,
        requested_tokenizer_id=tokenizer_id,
        requested_locale=locale,
        detected_script=detected["script"],
        enabled_tokenizers=enabled_tokenizers,
        default_tokenizer=DEFAULT_TOKENIZER,
        auto_routing=AUTO_ROUTING,
    )
    if fn is None:
        return jsonify(
            error=f"Tokenizer not installed or not enabled: {chosen_id}",
            available_tokenizers=registry.list_ids(),
            enabled_tokenizers=enabled_tokenizers,
        ), 400

    tokens = fn(normalized)
    latency_ms = round((time.perf_counter() - t0) * 1000, 2)

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
<h1>Thai Tokenizer MVP <small>v0.3</small></h1>
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
