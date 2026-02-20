import os
import time
import unicodedata
import re

from flask import Flask, request, jsonify

app = Flask(__name__)

APP_VERSION = os.environ.get("APP_VERSION", "0.1.0")
TOKENIZER_ID = os.environ.get("TOKENIZER_ID", "thai_pythainlp_newmm")
THAI_ENGINE = os.environ.get("THAI_ENGINE", "newmm")


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"\s+", " ", text)
    text = text.strip()
    return text


def tokenize_thai(text: str) -> list[str]:
    from pythainlp.tokenize import word_tokenize

    tokens = word_tokenize(text, engine=THAI_ENGINE, keep_whitespace=False)
    return [t for t in tokens if t]


def tokenize_fallback(text: str) -> list[str]:
    return [t for t in text.split() if t]


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
    )


@app.route("/tokenize", methods=["POST"])
def tokenize():
    body = request.get_json(force=True)
    raw_text = body.get("text", "")
    locale = body.get("locale", "th-TH")
    mode = body.get("mode", "query")

    normalized = normalize(raw_text)

    t0 = time.perf_counter()
    if locale.startswith("th"):
        tokens = tokenize_thai(normalized)
    else:
        tokens = tokenize_fallback(normalized)
    latency_ms = round((time.perf_counter() - t0) * 1000, 2)

    return jsonify(
        tokens=tokens,
        joined=" ".join(tokens),
        normalized=normalized,
        tokenizer_id=TOKENIZER_ID,
        version=APP_VERSION,
        locale=locale,
        mode=mode,
        latency_ms=latency_ms,
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
</style>
</head>
<body>
<h1>Thai Tokenizer MVP</h1>
<textarea id="txt" placeholder="Type Thai text here...">รองเท้าnike วิ่ง ราคาไม่แพง</textarea>
<br>
<label>Locale
  <select id="locale">
    <option value="th-TH" selected>th-TH</option>
    <option value="en-US">en-US</option>
  </select>
</label>
<button onclick="run()">Tokenize</button>
<pre id="out"></pre>
<script>
async function run(){
  const res=await fetch("/tokenize",{
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({text:document.getElementById("txt").value,
                         locale:document.getElementById("locale").value,
                         mode:"query"})
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
