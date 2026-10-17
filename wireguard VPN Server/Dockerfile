FROM python:3.12-slim

# Fix debian repositories to use https for reliable fetching
RUN sed -i 's|http://|https://|g' /etc/apt/sources.list.d/*.sources 2>/dev/null || true && \
    apt-get update && apt-get install -y --no-install-recommends \
    wireguard-tools \
    iproute2 \
    iptables \
    nftables \
    curl \
    procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

ENV DATA_DIR=/data \
    PYTHONUNBUFFERED=1 \
    WG_EXECUTION_MODE=direct \
    WG_INTERFACE=wg0

EXPOSE 8000 51820/udp

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
