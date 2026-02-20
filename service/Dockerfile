FROM python:3.11-slim

WORKDIR /app

ARG PACKS=""
ENV PACKS=${PACKS}
ENV INSTALLED_PACKS=${PACKS}

COPY requirements-core.txt requirements-thai.txt ./
RUN pip install --no-cache-dir -r requirements-core.txt && \
    if echo "$PACKS" | grep -q "thai"; then pip install --no-cache-dir -r requirements-thai.txt; fi

COPY . .

ENV APP_VERSION=0.3.0
ENV DEFAULT_TOKENIZER=whitespace
ENV AUTO_ROUTING=true
ENV PORT=8080

EXPOSE ${PORT}

CMD sh -c "gunicorn -b 0.0.0.0:${PORT} app:app --workers 1 --threads 4 --timeout 30"
