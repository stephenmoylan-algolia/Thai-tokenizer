FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

ENV APP_VERSION=0.1.0
ENV TOKENIZER_ID=thai_pythainlp_newmm
ENV THAI_ENGINE=newmm
ENV PORT=8080

EXPOSE ${PORT}

CMD gunicorn -b 0.0.0.0:$PORT app:app --workers 1 --threads 4 --timeout 30
