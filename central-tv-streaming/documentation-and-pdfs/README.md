# Documentation & Production PDF Manuals

This directory contains the official architectural specifications, deployment runbooks, VAPT security audit reports, and executive PDF documentation for the CiSAI Central TV Streaming & Signage platform.

---

## 1. Executive PDF Documents

| Document | Format | Description |
|---|---|---|
| **CiSAI_Central_TV_Production_Implementation_Guide.pdf** | PDF | Step-by-step production runbook for Bare-Metal, Docker, and Raspberry Pi deployments, default credentials, and dashboard operations. |
| **CiSAI_Central_TV_Streaming_Production_Architecture.pdf** | PDF | Comprehensive technical architecture specification covering MediaMTX streaming core, network topology, and VAPT hardening. |
| **Raspberry_Pi_Production_Implementation_Guide.pdf** | PDF | Detailed hardware specifications, OS flashing, kiosk mode setup, cooling, and auto-boot guides for Raspberry Pi 4/5 endpoints. |

---

## 2. Technical Markdown Specifications

| File | Topic |
|---|---|
| **ARCHITECTURE.md** | Complete system architecture, multi-device support matrix, and zero-touch setup flow. |
| **VAPT_HARDENING_REPORT.md** | Vulnerability Assessment & Penetration Testing report detailing OWASP Top 10 remediation. |
| **RASPBERRY_PI_PRODUCTION_GUIDE.md** | Step-by-step Ubuntu and Raspberry Pi OS kiosk deployment runbook. |
| **README.md** | System overview, quick start, and general repository documentation. |

---

## 3. PDF Compilation Scripts (Python)

To regenerate any of the PDF documents using Google Chrome headless:
- `python3 build_implementation_guide_pdf.py` -> Generates `CiSAI_Central_TV_Production_Implementation_Guide.pdf`
- `python3 build_production_pdf.py` -> Generates `CiSAI_Central_TV_Streaming_Production_Architecture.pdf`
- `python3 build_pi_guide_pdf.py` -> Generates `Raspberry_Pi_Production_Implementation_Guide.pdf`
