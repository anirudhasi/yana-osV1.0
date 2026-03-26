FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# Django on 8003, FastAPI telemetry on 8013
EXPOSE 8003 8013

# Default: Django. Override in docker-compose for FastAPI sidecar.
CMD ["gunicorn", "fleet_service.wsgi:application", \
     "--bind", "0.0.0.0:8003", \
     "--workers", "2", "--timeout", "60"]
