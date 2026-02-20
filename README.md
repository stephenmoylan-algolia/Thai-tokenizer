# Thai Tokenizer MVP

Pure Thai tokenizer service built on [PyThaiNLP](https://github.com/PyThaiNLP/pythainlp) (newmm engine). Exposes a simple REST API for tokenizing Thai text, with a tiny demo UI.

Phase 1 — no auth, no rate limiting, Thai-only tokenization (non-Thai locales fall back to whitespace split).

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Demo UI (textarea + tokenize button) |
| `GET` | `/healthz` | Health check — `{"ok": true}` |
| `GET` | `/version` | Service + tokenizer version info |
| `POST` | `/tokenize` | Tokenize text (see below) |

### POST /tokenize

**Request:**

```json
{
  "text": "รองเท้าnike วิ่ง ราคาไม่แพง",
  "locale": "th-TH",
  "mode": "query"
}
```

- `locale` — default `th-TH`. Non-Thai locales fall back to whitespace split.
- `mode` — default `query`. Reserved for future use.

**Response:**

```json
{
  "tokens": ["รองเท้า", "nike", "วิ่ง", "ราคา", "ไม่", "แพง"],
  "joined": "รองเท้า nike วิ่ง ราคา ไม่ แพง",
  "normalized": "รองเท้าnike วิ่ง ราคาไม่แพง",
  "tokenizer_id": "thai_pythainlp_newmm",
  "version": "0.1.0",
  "locale": "th-TH",
  "mode": "query",
  "latency_ms": 12.34
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

### Curl Example

```bash
curl -s -X POST http://localhost:8080/tokenize \
  -H 'content-type: application/json' \
  -d '{"text":"รองเท้าnike วิ่ง ราคาไม่แพง","locale":"th-TH","mode":"query"}' | jq
```

## Deploy to Railway

1. Push this repo to GitHub.
2. In Railway: **New Project → Deploy from GitHub Repo → select this repo**.
3. Railway auto-detects the `Procfile` start command. Confirm it shows:
   ```
   web: gunicorn -b 0.0.0.0:$PORT service.app:app --workers 1 --threads 4 --timeout 30
   ```
4. No environment variables required for MVP. Optionally set `APP_VERSION`, `TOKENIZER_ID`, or `THAI_ENGINE`.
5. Once deployed, open the Railway URL and test:
   - `GET /healthz`
   - `GET /version`
   - `POST /tokenize`

## Docker (for future infra deploys)

```bash
cd service
docker build -t thai-tokenizer-mvp .
docker run -e PORT=8080 -p 8080:8080 thai-tokenizer-mvp
```

The Dockerfile defaults `PORT` to 8080 but respects the env var, so any platform (Railway, GCP, etc.) can inject its own port. For Railway, the `Procfile` at the repo root is used instead.
