#!/usr/bin/env bash
set -euo pipefail

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo -e "${BLUE}=== Exporting WireGuard Enterprise Offline Production Bundle ===${NC}"
echo -e "Working directory: ${ROOT_DIR}"

# 1. Build local docker image
echo -e "${YELLOW}[1/3] Building self-contained Docker image (wireguard-enterprise:latest)...${NC}"
docker build -t wireguard-enterprise:latest -f "${ROOT_DIR}/Dockerfile" "${ROOT_DIR}"

# 2. Export image to tar.gz
OUTPUT_TAR="${ROOT_DIR}/wireguard-enterprise-image.tar.gz"
echo -e "${YELLOW}[2/3] Saving and compressing Docker image to ${OUTPUT_TAR}...${NC}"
docker save wireguard-enterprise:latest | gzip > "${OUTPUT_TAR}"

FILE_SIZE=$(du -h "${OUTPUT_TAR}" | cut -f1)
echo -e "${GREEN}[OK] Successfully exported offline image (${FILE_SIZE}).${NC}"

# 3. Optional: Export pip wheels for standalone python usage
WHEELS_DIR="${ROOT_DIR}/offline-wheels"
mkdir -p "${WHEELS_DIR}"
echo -e "${YELLOW}[3/3] Downloading offline Python pip wheels into ${WHEELS_DIR}...${NC}"
pip download -r "${ROOT_DIR}/requirements.txt" -d "${WHEELS_DIR}" || true

echo -e "${GREEN}=== Export Complete! Transfer this folder to your offline server. ===${NC}"
