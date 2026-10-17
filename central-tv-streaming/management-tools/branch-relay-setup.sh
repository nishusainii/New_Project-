#!/usr/bin/env bash
# ==============================================================================
# Branch Office Edge Relay Setup (Remote Site)
# Saves WAN/VPN bandwidth by pulling 1 stream from HQ and serving local TVs
# ==============================================================================

HQ_VPN_IP="${1:-10.10.1.10}"

echo "Configuring Branch Edge Relay pointing to HQ Server: ${HQ_VPN_IP}"

cat <<EOF > branch-relay-mediamtx.yml
logLevel: info
rtsp: no
rtmp: no

# Enable local HLS & WebRTC for branch office TVs
hls: yes
hlsAddress: :8888

webrtc: yes
webrtcAddress: :8889
webrtcAllowOrigins: ["*"]

paths:
  # Pull HQ live stream over Site-to-Site VPN on-demand
  live:
    source: rtsp://${HQ_VPN_IP}:8554/live
    sourceOnDemand: yes
EOF

echo "To run the branch relay on a local Raspberry Pi at the branch office:"
echo "  docker run -d --name branch-relay --restart unless-stopped \\"
echo "    -p 8889:8889 -p 8888:8888 \\"
echo "    -v \$(pwd)/branch-relay-mediamtx.yml:/mediamtx.yml:ro \\"
echo "    bluenviron/mediamtx:latest"
