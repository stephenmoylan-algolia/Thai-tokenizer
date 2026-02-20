# Thai Tokenizer MVP

Language-agnostic tokenizer service with **build-time selectable language packs**. Built on Flask with a registry-based architecture. Thai (PyThaiNLP newmm) is the first optional pack; baseline includes whitespace tokenizer + auto script detection + routing.

## Architecture

```
service/
  app.py              # Flask entry point, wires registry + packs
  core/
    normalize.py      # Unicode NFC + whitespace collapse
    detect.py         # O(n) script detection (thai > cjk > latin > other)
    registry.py       # TokenizerRegistry — register/get/list
    tokenize.py       # Whitespace tokenizer + choose_tokenizer routing
  packs/
    thai/
      tokenizer.py    # PyThaiNLP newmm tokenizer + register()
  tests/
```

**Baseline image** (core only): whitespace tokenizer, detection, routing.
**Baseline + Thai**: adds PyThaiNLP tokenizer, auto-routes Thai script.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Demo UI |
| `GET` | `/healthz` | `{"ok": true}` |
| `GET` | `/version` | Installed packs, available/enabled tokenizers, config |
| `GET` | `/detect?text=...` | Script detection without tokenizing |
| `POST` | `/tokenize` | Tokenize with auto or explicit routing |

## Auto Routing

| Condition | Tokenizer | Reason |
|-----------|-----------|--------|
| Thai script detected | `thai_pythainlp_newmm` | `thai_script` |
| `locale=th-*` | `thai_pythainlp_newmm` | `explicit_locale_thai` |
| Explicit `tokenizer_id` | as requested | `explicit` |
| Non-Thai, auto | `whitespace` | `fallback_default` |
| Auto routing disabled | `whitespace` | `default_no_auto` |

If Thai pack is not installed, Thai text falls back to whitespace.

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

**Response:**

```json
{
  "tokens": ["รองเท้า", "nike", "วิ่ง", "ราคา", "ไม่", "แพง"],
  "joined": "รองเท้า nike วิ่ง ราคา ไม่ แพง",
  "normalized": "รองเท้าnike วิ่ง ราคาไม่แพง",
  "tokenizer_id": "thai_pythainlp_newmm",
  "version": "0.3.0",
  "locale": "auto",
  "mode": "query",
  "latency_ms": 12.34,
  "detected": { "script": "thai", "confidence": 1.0 },
  "chosen": { "tokenizer_id": "thai_pythainlp_newmm", "reason": "thai_script" }
}
```

## Docker Builds

**Baseline (core only):**

```bash
docker build -f service/Dockerfile -t tokenizer:core service/
docker run -e PORT=8080 -p 8080:8080 tokenizer:core
```

**Baseline + Thai pack:**

```bash
docker build -f service/Dockerfile --build-arg PACKS="thai" -t tokenizer:thai service/
docker run -e PORT=8080 -p 8080:8080 tokenizer:thai
```

The `PACKS` build arg controls which language packs are installed at build time. The `INSTALLED_PACKS` env var tells the app which packs to load at startup.

## Local Run (development)

```bash
cd service
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export PORT=8080
export INSTALLED_PACKS=thai
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

**Explicit Thai tokenizer** (requires Thai pack):

```bash
curl -s -X POST http://localhost:8080/tokenize \
  -H 'content-type: application/json' \
  -d '{"text":"รองเท้าวิ่ง","tokenizer_id":"thai_pythainlp_newmm"}' | jq
```

**Script detection:**

```bash
curl -s 'http://localhost:8080/detect?text=รองเท้า+nike' | jq
```

## Runtime Configuration

| Env var | Default | Description |
|---------|---------|-------------|
| `INSTALLED_PACKS` | `""` | Comma-separated pack names to load (e.g. `thai`) |
| `ENABLED_TOKENIZERS` | all installed | Comma-separated allowlist (e.g. `whitespace,thai_pythainlp_newmm`) |
| `DEFAULT_TOKENIZER` | `whitespace` | Fallback when no pack matches |
| `AUTO_ROUTING` | `true` | Enable auto script detection routing |
| `APP_VERSION` | `0.3.0` | Reported in `/version` |
| `THAI_ENGINE` | `newmm` | PyThaiNLP engine (only if Thai pack loaded) |

## Tests

```bash
pip install -r service/requirements-dev.txt
INSTALLED_PACKS=thai python -m pytest service/tests/ -v
```

41 tests covering: detection, normalisation, registry, routing logic, endpoint integration (with and without Thai pack).

## Deploy to Railway

Railway deploys from GitHub using nixpacks (not Docker). The `railway.toml` sets `INSTALLED_PACKS=thai` in the start command.

1. Push repo to GitHub.
2. Railway: **New Project -> Deploy from GitHub Repo -> select this repo**.
3. Railway auto-detects `railway.toml` config.
4. Optionally set env vars in Railway dashboard (`INSTALLED_PACKS`, `ENABLED_TOKENIZERS`, etc.).
5. Test: `/healthz`, `/version`, `/tokenize`.

For build-time packs via Docker, deploy via a Docker-compatible platform or Railway Dockerfile deployment with build args.
