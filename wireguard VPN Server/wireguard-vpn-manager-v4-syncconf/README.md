# WireGuard VPN Manager V4 syncconf edition

Matches the observed production flow: `/etc/wireguard/wg0.conf` -> `wg-quick strip` -> `/usr/local/bin/wgreload` -> `wg syncconf wg0` -> existing `wg0` remains active.

## Safe first start

```bash
cp .env.example .env
chmod 600 .env
# Set APP_SECRET and ADMIN_PASSWORD. Keep WG_EXECUTION_MODE=dry-run.
docker compose config
docker compose up --build -d
curl http://127.0.0.1:8080/health
```

The default dry-run mode only previews rendered configuration. `/etc/wireguard` remains read-only and the host agent is not needed.

## Production apply architecture

The Admin-only Apply route validates the CSRF token, renders a candidate, and sends an HMAC-authenticated request to a host agent bound to `127.0.0.1:9081`. The agent validates with `wg-quick strip`, backs up `wg0.conf`, atomically replaces it, runs the existing `/usr/local/bin/wgreload`, checks peer count, and attempts rollback if reload fails.

## Do not enable Apply yet

Before enabling Apply, perform code review, staging tests, exact round-trip comparison with the production file, backup and rollback validation, and verify that all existing Interface directives are preserved. Keep production `wg0` unchanged during evaluation.

## Host agent installation after approval only

```bash
sudo install -d -o root -g root -m 0700 /etc/wireguard-manager
sudo sh -c 'openssl rand -hex 32 > /etc/wireguard-manager/agent.token'
sudo chmod 600 /etc/wireguard-manager/agent.token
sudo install -o root -g root -m 0750 host-agent/wg-manager-agent /usr/local/sbin/wg-manager-agent
sudo install -o root -g root -m 0644 host-agent/wg-manager-agent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now wg-manager-agent
curl http://127.0.0.1:9081/health
```

Copy the same token to `.env` as `WG_AGENT_TOKEN`, set `WG_EXECUTION_MODE=apply`, and recreate the Web UI only during an approved change window. Never publish TCP 9081.
