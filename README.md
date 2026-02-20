# Thai Tokenizer MVP

Pure Thai tokenizer service built on [PyThaiNLP](https://github.com/PyThaiNLP/pythainlp) (newmm engine). Exposes a REST API for tokenizing text with **automatic script detection and tokenizer routing**.

Phase 2 — auto language/script detection, tokenizer routing, metadata in responses. No auth, no rate limiting.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Demo UI (textarea + locale/tokenizer dropdowns) |
| `GET` | `/healthz` | Health check — `{"ok": true}` |
| `GET` | `/version` | Service version, available tokenizers, auto support |
| `GET` | `/detect?text=...` | Script detection without tokenizing |
| `POST` | `/tokenize` | Tokenize text with auto or explicit routing |

## Auto Routing

The service detects the script of the input text and routes to the appropriate tokenizer:

| Detected Script | Tokenizer | Reason |
|----------------|-----------|--------|
| Thai (U+0E00-0E7F) | `thai_pythainlp_newmm` | `thai_script` |
| CJK / Latin / Other | `whitespace` | `fallback_whitespace` |
| Any (locale=th-*) | `thai_pythainlp_newmm` | `explicit_locale_thai` |
| Any (explicit tokenizer_id) | as requested | `explicit` |

Mixed Thai+Latin text resolves to Thai. Detection is deterministic and O(n).

### POST /tokenize

**Request:**

```json
{
  "text": "รองเท้าnike วิ่ง ราคาไม่แพง",
  "locale": "auto",
  "tokenizer_id": "auto",
  "mode": "query"
}
```

- `locale` — default `auto`. Set `th-TH` to force Thai tokenizer.
- `tokenizer_id` — default `auto`. Set explicitly to bypass detection.
- `mode` — default `query`. Reserved for future use.

**Response:**

```json
{
  "tokens": ["รองเท้า", "nike", "วิ่ง", "ราคา", "ไม่", "แพง"],
  "joined": "รองเท้า nike วิ่ง ราคา ไม่ แพง",
  "normalized": "รองเท้าnike วิ่ง ราคาไม่แพง",
  "tokenizer_id": "thai_pythainlp_newmm",
  "version": "0.2.0",
  "locale": "auto",
  "mode": "query",
  "latency_ms": 12.34,
  "detected": {
    "script": "thai",
    "confidence": 1.0
  },
  "chosen": {
    "tokenizer_id": "thai_pythainlp_newmm",
    "reason": "thai_script"
  }
}
```

### GET /detect

Debug endpoint — returns detection result without tokenizing.

```
GET /detect?text=รองเท้า
```

```json
{
  "normalized": "รองเท้า",
  "detected": { "script": "thai", "confidence": 1.0 }
}
```

## Local Run

```bash
cd service
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export PORT=8080
gunicorn -b 0.0.0.0:$PORT app:app --workers 1 --threads 4 --timeout 30
```

## Curl Examples

**Auto (Thai):**

```bash
curl -s -X POST http://localhost:8080/tokenize \
  -H 'content-type: application/json' \
  -d '{"text":"รองเท้าnike วิ่ง ราคาไม่แพง","locale":"auto","tokenizer_id":"auto"}' | jq
```

**Auto (Latin fallback):**

```bash
curl -s -X POST http://localhost:8080/tokenize \
  -H 'content-type: application/json' \
  -d '{"text":"cheap running shoes","locale":"auto","tokenizer_id":"auto"}' | jq
```

**Explicit tokenizer:**

```bash
curl -s -X POST http://localhost:8080/tokenize \
  -H 'content-type: application/json' \
  -d '{"text":"รองเท้าวิ่ง","tokenizer_id":"thai_pythainlp_newmm"}' | jq
```

**Script detection only:**

```bash
curl -s 'http://localhost:8080/detect?text=รองเท้า+nike' | jq
```

## Tests

```bash
cd /path/to/thai-tokenizer-mvp
source .venv/bin/activate
pip install -r service/requirements.txt
python -m pytest service/tests/ -v
```

## Deploy to Railway

1. Push this repo to GitHub.
2. In Railway: **New Project -> Deploy from GitHub Repo -> select this repo**.
3. Railway auto-detects the `Procfile` start command. Confirm it shows:
   ```
   web: gunicorn -b 0.0.0.0:$PORT service.app:app --workers 1 --threads 4 --timeout 30
   ```
4. No environment variables required for MVP. Optionally set `APP_VERSION`, `TOKENIZER_ID`, or `THAI_ENGINE`.
5. Once deployed, open the Railway URL and test:
   - `GET /healthz`
   - `GET /version`
   - `POST /tokenize`
   - `GET /detect?text=...`

## Docker (for future infra deploys)

```bash
cd service
docker build -t thai-tokenizer-mvp .
docker run -e PORT=8080 -p 8080:8080 thai-tokenizer-mvp
```

The Dockerfile defaults `PORT` to 8080 but respects the env var, so any platform (Railway, GCP, etc.) can inject its own port. For Railway, the `Procfile` at the repo root is used instead.
