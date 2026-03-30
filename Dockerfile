# syntax=docker/dockerfile:1
# Multi-stage: install deps as root, run app as non-root user.

FROM python:3.12-slim AS deps
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
WORKDIR /app

RUN adduser --disabled-password --gecos "" appuser

COPY --from=deps /install /usr/local

COPY app/ ./app/

USER appuser

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
