# Build context: repo root.
#   docker build -t tokenizer:thai .                      # with Thai pack (default)
#   docker build --build-arg PACKS="" -t tokenizer:core .  # core only
# Also used by Cloudflare Containers (see wrangler.jsonc).
FROM python:3.11-slim

WORKDIR /app

ARG PACKS="thai"
ENV INSTALLED_PACKS=${PACKS}

COPY service/requirements-core.txt service/requirements-thai.txt ./
RUN pip install --no-cache-dir -r requirements-core.txt && \
    if echo "$PACKS" | grep -q "thai"; then pip install --no-cache-dir -r requirements-thai.txt; fi

# app.py imports `service.core...`, so the package must live at /app/service
COPY service ./service

ENV APP_VERSION=0.3.0 \
    DEFAULT_TOKENIZER=whitespace \
    AUTO_ROUTING=true \
    PORT=8080

EXPOSE 8080

CMD ["sh", "-c", "exec gunicorn -b 0.0.0.0:${PORT} service.app:app --preload --workers 1 --threads 4 --timeout 30"]
