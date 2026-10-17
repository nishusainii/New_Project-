FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8088
ENV PYTHONUNBUFFERED=1

EXPOSE 8088

CMD ["gunicorn", "--bind", "0.0.0.0:8088", "--workers", "2", "app:app"]
