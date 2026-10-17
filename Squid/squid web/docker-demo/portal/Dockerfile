# syntax=docker/dockerfile:1
FROM python:3.11-slim

WORKDIR /app

RUN --network=host pip install --no-cache-dir flask>=2.3.0 ldap3>=2.9.1 gunicorn>=21.0.0

COPY app.py config.py ./
COPY templates/ ./templates/
COPY static/ ./static/

EXPOSE 5000

CMD ["gunicorn", "--workers", "2", "--bind", "0.0.0.0:5000", "app:app"]
