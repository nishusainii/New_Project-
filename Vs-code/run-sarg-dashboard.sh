#!/usr/bin/env bash
# ============================================================
#  run-sarg-dashboard.sh
#  ------------------------------------------------------------
#  One command that:
#     1. Runs  `sudo sarg`  to (re)generate the Squid report
#        for the current period.
#     2. Deploys the CiSOI analytics dashboard (dashboard.html)
#        into the freshly-created report folder so THAT is the
#        page you see, instead of SARG's plain index.html.
#     3. Keeps company-logo.jpg in reach (dashboard.html links
#        to it via ../company-logo.jpg).
#
#  Usage:   bash run-sarg-dashboard.sh
#           sudo bash run-sarg-dashboard.sh
#           bash run-sarg-dashboard.sh --deploy-only
#                  (skip running sarg; only deploy dashboard.html
#                   into the newest report folder. Used by the
#                   /usr/local/bin/sarg wrapper.)
# ============================================================
set -euo pipefail

DEPLOY_ONLY=0
for arg in "$@"; do
    case "$arg" in
        --deploy-only) DEPLOY_ONLY=1 ;;
        *) echo "Unknown argument: $arg" >&2; exit 2 ;;
    esac
done

# ------------------------------------------------------------
# Configure paths (override with environment variables if the
# defaults don't match your server layout).
# ------------------------------------------------------------
# SARG `output_dir` — the ROOT folder that holds one subfolder per
# report period (e.g. 29Aug2026-29Aug2026/). Default = current dir.
OUTPUT_DIR="${OUTPUT_DIR:-$(pwd)}"

# Where the dashboard + logo live in the output root.
# dashboard.html in each period folder links to ../company-logo.jpg,
# i.e. $OUTPUT_DIR/company-logo.jpg
MASTER_DASHBOARD="${MASTER_DASHBOARD:-$OUTPUT_DIR/dashboard.html}"
LOGO="${LOGO:-$OUTPUT_DIR/company-logo.jpg}"

# ------------------------------------------------------------
echo "==> SARG Dashboard runner"
echo "    Output dir (SARG output_dir): $OUTPUT_DIR"
echo "    Master dashboard           : $MASTER_DASHBOARD"
echo "    Company logo               : $LOGO"
echo

# Sanity: the master dashboard must exist.
if [[ ! -f "$MASTER_DASHBOARD" ]]; then
    echo "ERROR: master dashboard not found at:" >&2
    echo "       $MASTER_DASHBOARD" >&2
    echo "       Copy dashboard.html into $OUTPUT_DIR first." >&2
    exit 1
fi

# ------------------------------------------------------------
# 1) Generate the report (skipped in --deploy-only mode)
# ------------------------------------------------------------
if [[ "$DEPLOY_ONLY" -eq 0 ]]; then
    echo "==> Running: sudo sarg"
    sudo sarg
else
    echo "==> --deploy-only: skipping 'sarg' run"
fi

# ------------------------------------------------------------
# 2) Locate the newest report folder (one subdir under OUTPUT_DIR)
# ------------------------------------------------------------
# Keep the folder containing the most recently modified index.html.
newest="$(find "$OUTPUT_DIR" -maxdepth 2 -name index.html -printf '%T@ %h\n' \
          2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)"

if [[ -z "$newest" || ! -d "$newest" ]]; then
    echo "ERROR: could not find the SARG report under:" >&2
    echo "       $OUTPUT_DIR" >&2
    echo "       Run 'sudo sarg' once manually, or check output_dir." >&2
    exit 1
fi

# ------------------------------------------------------------
# 3) Deploy the dashboard + logo into that report folder
# ------------------------------------------------------------
echo "==> Deploying dashboard into: $newest"
cp -f "$MASTER_DASHBOARD" "$newest/dashboard.html"
if [[ -f "$LOGO" ]]; then
    cp -f "$LOGO" "$OUTPUT_DIR/company-logo.jpg"
fi

# ------------------------------------------------------------
# 4) Report where to open it
# ------------------------------------------------------------
echo
echo "==> Done."
echo "    Open this path in your browser:"
echo "        $newest/dashboard.html"
echo
echo "    (It is served from your web server's SARG output_dir."
echo "     If that maps to e.g. http://SERVER/sarg/, then open:)"
echo "        http://SERVER/sarg/$(basename "$newest")/dashboard.html"
