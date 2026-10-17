#!/usr/bin/env bash
# ============================================================
#  run-sarg-dashboard.sh
#  ------------------------------------------------------------
#  One command that:
#     1. Runs `sudo sarg` to (re)generate the Squid report
#        (skipped with --deploy-only).
#     2. Deploys the CISAI analytics dashboard (dashboard.html +
#        dashboard.css) into the freshly-created report folder so
#        THAT is the page you see, then regenerates EVERY data block
#        of it (subtitle, top consumers, sites, platform mix, denied
#        hotspots, alerts, insights, leaderboard, totals) from the
#        fresh report via refresh-dashboard.py (needs python3).
#     3. Themes every SARG page (Top users, Top sites, per-user
#        pages, graphs, ...) with sarg-dashboard.css, rewriting the
#        stylesheet link to a correct RELATIVE path pointing at the
#        SERVED copy at the output_dir root — stays inside the
#        web-visible tree on any vhost/alias (works over file:// too).
#     4. Refreshes the KPI strip in the deployed dashboard.html
#        from the freshly generated report (fallback if python3 is
#        unavailable; also re-checks badges/stat line).
#
#  FOLDER STRUCTURE (recommended):
#     /var/www/html/sarg/           <- SARG output_dir
#        DDMMMYYYY-DDMMMYYYY/       <- one folder per report period
#        sarg-dashboard.css         <- SERVED copy, written on every run;
#                                    every SARG page links here with a
#                                    relative ../ path, so the theme loads
#                                    even when sarg-assets/ is NOT visible
#                                    over HTTP (different vhost/alias root)
#        company-logo.jpg           <- served copy (sarg-dashboard.css
#                                    loads it with a relative url())
#     /var/www/html/sarg-assets/    <- this script + the master files
#        run-sarg-dashboard.sh
#        dashboard.html
#        dashboard.css
#        sarg-dashboard.css         <- master theme for the report pages
#        login-page.html            <- login-gate template (root index.html)
#        login-key                  <- optional: your access key (chmod 600)
#        company-logo.jpg           <- master logo
#
#  Only FILES (never folders) are baked into the output_dir root, so SARG
#  still sees nothing but report directories there.
#
#  Also, after every run it (re)writes a styled LOGIN page as the ROOT
#  index.html of the output_dir. Visitors to http://SERVER/ must sign in
#  first; a successful sign-in sets a 12h cookie and redirects to the
#  newest report's dashboard. (SARG itself regenerates that root
#  index.html on every run; this script always runs after sarg, so the
#  login gate always wins.) NOTE: the gate is client-side — for hard
#  protection, protect the whole output_dir with Apache Basic Auth.
#
#  Usage:
#     cd /var/www/html/sarg
#     sudo bash /var/www/html/sarg-assets/run-sarg-dashboard.sh
#     bash run-sarg-dashboard.sh --deploy-only   # skip running sarg
#     bash run-sarg-dashboard.sh --clean-dupes   # delete DDMMM-DDMMM.N
#                                                # duplicate folders of the
#                                                # newest report period
#  TIP: set "overwrite yes" in sarg.conf so re-running sarg for the same
#       period REPLACES the old folder instead of creating .1 .2 .3 ...
# ============================================================
set -euo pipefail

DEPLOY_ONLY=0
CLEAN_DUPES=0
for arg in "$@"; do
    case "$arg" in
        --deploy-only) DEPLOY_ONLY=1 ;;
        --clean-dupes) CLEAN_DUPES=1 ;;
        *) echo "Unknown argument: $arg" >&2; exit 2 ;;
    esac
done

# ------------------------------------------------------------
# Configure paths (override with environment variables if the
# defaults don't match your layout).
# ------------------------------------------------------------
# Directory that contains THIS script (where the masters live).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# SARG `output_dir` — the ROOT folder that holds one subfolder per
# report period (e.g. 03Sep2026-03Sep2026/). Default = current dir.
OUTPUT_DIR="${OUTPUT_DIR:-/var/www/html/sarg}"
[[ ! -d "$OUTPUT_DIR" ]] && OUTPUT_DIR="$(pwd)"

# Master files. Defaults: next to this script (i.e. the assets dir),
# so the SARG output_dir stays clean.
MASTER_DASHBOARD="${MASTER_DASHBOARD:-$SCRIPT_DIR/dashboard.html}"
MASTER_CSS="${MASTER_CSS:-$SCRIPT_DIR/dashboard.css}"
MASTER_REPORT_CSS="${MASTER_REPORT_CSS:-$SCRIPT_DIR/sarg-dashboard.css}"
LOGO="${LOGO:-$SCRIPT_DIR/company-logo.jpg}"

# Login-page template (the access gate in front of the dashboard).
# Copied by the runner to $ASSETS_DIR/ so it can be edited on the server;
# a copy is baked into $OUTPUT_DIR/index.html on every run with the newest
# report target + the SHA-256 of the access key substituted in.
MASTER_LOGIN="${MASTER_LOGIN:-$SCRIPT_DIR/login-page.html}"

# ASSETS_DIR = where sarg-dashboard.css + company-logo.jpg are served
# from at link time. Defaults to the folder holding the master css.
ASSETS_DIR="${ASSETS_DIR:-$(dirname "$MASTER_REPORT_CSS")}"

# ------------------------------------------------------------
echo "==> SARG Dashboard runner"
echo "    Output dir (SARG output_dir): $OUTPUT_DIR"
echo "    Assets dir                  : $ASSETS_DIR"
echo "    Master dashboard            : $MASTER_DASHBOARD"
echo "    Master dashboard css        : $MASTER_CSS"
echo "    Master report css           : $MASTER_REPORT_CSS"
echo "    Company logo                : $LOGO"
echo "    Login template              : $MASTER_LOGIN"
echo

# Sanity: the master dashboard + dashboard stylesheet must exist.
if [[ ! -f "$MASTER_DASHBOARD" ]]; then
    echo "ERROR: master dashboard not found at:" >&2
    echo "       $MASTER_DASHBOARD" >&2
    echo "       Copy dashboard.html next to this script (or set MASTER_DASHBOARD)." >&2
    exit 1
fi
if [[ ! -f "$MASTER_CSS" ]]; then
    echo "ERROR: dashboard stylesheet not found at:" >&2
    echo "       $MASTER_CSS" >&2
    echo "       Copy dashboard.css next to this script (or set MASTER_CSS)." >&2
    exit 1
fi
if [[ ! -f "$MASTER_LOGIN" ]]; then
    echo "    NOTE: login-page.html template not found at:" >&2
    echo "          $MASTER_LOGIN" >&2
    echo "          The root page will be a plain auto-redirect (no login gate)." >&2
    echo "          Copy login-page.html next to this script to enable the gate." >&2
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
# mindepth 2 is REQUIRED: the landing page we write at the output_dir
# root (see step 5) is also called index.html and must never be taken
# for a report folder.
if [[ -n "${LATEST_REPORT:-}" && -d "$LATEST_REPORT" ]]; then
    newest="$LATEST_REPORT"
else
    newest="$(find "$OUTPUT_DIR" \
        -mindepth 2 \
        -maxdepth 2 \
        -type f \
        -name sarg-date \
        -printf '%T@ %h\n' 2>/dev/null |
        sort -rn |
        head -1 |
        cut -d' ' -f2-)"
fi

if [[ -z "$newest" || ! -d "$newest" ]]; then
    echo "ERROR: could not find the SARG report under:" >&2
    echo "       $OUTPUT_DIR" >&2
    echo "       Run 'sudo sarg' once manually, or check output_dir." >&2
    exit 1
fi

# ------------------------------------------------------------
# 2a) Optional: remove duplicate folders of the SAME report period
# ------------------------------------------------------------
# SARG's default "overwrite no" makes every re-run for the same period
# create DDMMMYYYY-DDMMMYYYY.1, .2, .3 … next to the original folder.
# With --clean-dupes we delete every sibling of the newest report that
# is the same period (base name + optional .N suffix).
# ------------------------------------------------------------
if [[ "$CLEAN_DUPES" -eq 1 ]]; then
    base="$(basename "$newest")"
    base="${base%.[0-9]*}"          # strip a trailing .N if present
    removed=0
    while IFS= read -r -d '' dup; do
        [[ "$dup" == "$newest" ]] && continue
        rm -rf -- "$dup" && { echo "    removed duplicate: $dup"; removed=$((removed+1)); }
    done < <(find "$OUTPUT_DIR" -mindepth 1 -maxdepth 1 -type d \
                 \( -name "$base" -o -name "${base}.[0-9]*" \) -print0 2>/dev/null)
    echo "==> Duplicate cleanup for period \"$base\": $removed folder(s) removed"
    echo "    (set 'overwrite yes' in sarg.conf to stop them being created)"
fi

# ------------------------------------------------------------
# 3) Deploy the dashboard into that report folder
#    (dashboard.html + dashboard.css go INSIDE the report folder,
#     exactly where SARG expects html pages to live.)
# ------------------------------------------------------------
echo "==> Deploying dashboard into: $newest"
cp -f "$MASTER_DASHBOARD" "$newest/dashboard.html"
cp -f "$MASTER_CSS" "$newest/dashboard.css"

# ------------------------------------------------------------
# 3a) Full dashboard regeneration from the fresh report
# ------------------------------------------------------------
# refresh-dashboard.py replaces every AUTO-marked block of the deployed
# dashboard.html (subtitle, JS data arrays -> top consumers/sites/mix/
# leaderboard, denied chips, alerts, insights, totals, KPIs, badges)
# with values parsed from index.html / topsites.html / denied.html /
# authfail.html of THIS report. If python3 or the script is missing we
# fall back to the KPI-only sed refresh in step 4 below.
# ------------------------------------------------------------
GEN_PY="${GEN_PY:-$SCRIPT_DIR/refresh-dashboard.py}"
GEN_OK=0
if command -v python3 >/dev/null 2>&1 && [[ -f "$GEN_PY" ]]; then
    if python3 "$GEN_PY" --report "$newest" --dashboard "$newest/dashboard.html"; then
        GEN_OK=1
        echo "==> Full dashboard data regenerated from the fresh report"
        # Keep the 5-day switcher dropdown and daily usage synchronized across all recent reports
        for sib in "$OUTPUT_DIR"/*; do
            if [[ -d "$sib" && "$sib" != "$newest" && -f "$sib/dashboard.html" && -f "$sib/sarg-date" ]]; then
                python3 "$GEN_PY" --report "$sib" --dashboard "$sib/dashboard.html" >/dev/null 2>&1 || true
            fi
        done
    else
        echo "==> NOTE: refresh-dashboard.py could not parse the report;" >&2
        echo "          falling back to KPI-only refresh." >&2
    fi
else
    echo "==> NOTE: python3 or refresh-dashboard.py not found — KPI-only refresh."
fi

# ------------------------------------------------------------
# 3a) Ensure the shared assets are in place:
#     - synced copies in ASSETS_DIR (the on-server masters, editable),
#     - SERVED copies at the ROOT of the output_dir. The SARG-generated
#       pages must load the theme over HTTP, but the assets folder is
#       often OUTSIDE the served tree (the vhost docroot/alias maps only
#       the output_dir) — links to it then 404 and the report pages
#       render completely unstyled. Served copies at the output_dir
#       root keep every relative ../ link inside the web-visible tree.
#       sarg-dashboard.css loads company-logo.jpg via a relative url(),
#       so both must sit side by side.
# ------------------------------------------------------------
if [[ -f "$MASTER_REPORT_CSS" ]]; then
    mkdir -p "$ASSETS_DIR"
    mkdir -p "$OUTPUT_DIR/images"

    if [[ "$(realpath -m "$MASTER_REPORT_CSS")" != "$(realpath -m "$ASSETS_DIR/sarg-dashboard.css")" ]]; then
        cp -f "$MASTER_REPORT_CSS" "$ASSETS_DIR/sarg-dashboard.css"
    fi
    cp -f "$MASTER_REPORT_CSS" "$OUTPUT_DIR/sarg-dashboard.css"
    cp -f "$MASTER_REPORT_CSS" "$OUTPUT_DIR/images/sarg-dashboard.css"

    if [[ -f "$LOGO" ]]; then
        if [[ "$(realpath -m "$LOGO")" != "$(realpath -m "$ASSETS_DIR/company-logo.jpg")" ]]; then
            cp -f "$LOGO" "$ASSETS_DIR/company-logo.jpg"
        fi
        cp -f "$LOGO" "$OUTPUT_DIR/company-logo.jpg"
        cp -f "$LOGO" "$OUTPUT_DIR/images/company-logo.jpg"
    fi
    if [[ -f "$MASTER_LOGIN" ]]; then
        if [[ "$(realpath -m "$MASTER_LOGIN")" != "$(realpath -m "$ASSETS_DIR/login-page.html")" ]]; then
            cp -f "$MASTER_LOGIN" "$ASSETS_DIR/login-page.html"
        fi
    fi
    echo "==> SARG report stylesheet (served): $OUTPUT_DIR/images/sarg-dashboard.css"
    echo "    SARG report stylesheet (assets): $ASSETS_DIR/sarg-dashboard.css"
fi

# ------------------------------------------------------------
# 3b) Theme the SARG-generated pages themselves
# ------------------------------------------------------------
# SARG pages live at several depths below $OUTPUT_DIR:
#   03Sep2026-03Sep2026/topsites.html           depth 1
#   03Sep2026-03Sep2026/user/daily.html         depth 2
#   03Sep2026-03Sep2026/user/10_31_4_66/g.html  depth 3
# sarg.conf usually sets external_css_file to a root-ABSOLUTE URL such
# as /assets/sarg-dashboard.css that 404s on the server. We rewrite
# every page's theme link to a RELATIVE ../ path pointing at the SERVED
# copy in $OUTPUT_DIR/images/ (step 3a), so the theme always loads.
# ------------------------------------------------------------
if [[ -f "$MASTER_REPORT_CSS" ]]; then
    SERVED_CSS="$OUTPUT_DIR/images/sarg-dashboard.css"
    STYLED=0
    while IFS= read -r -d '' page; do
        [[ ! -f "$page" ]] && continue
        # Skip the assets dir itself.
        case "$page" in "$ASSETS_DIR"/*) continue ;; esac
        # Never touch our own pages: dashboard.html carries its own
        # dashboard.css link, and the output_dir ROOT index.html is the
        # login gate / redirect page.
        case "$page" in */dashboard.html|"$OUTPUT_DIR"/index.html) continue ;; esac

        # Decide whether this SARG page needs theming. NOTE: do NOT
        # require the sarg.sourceforge.net marker before handling an
        # existing theme link — some SARG builds emit pages without the
        # marker, which would otherwise keep the broken absolute
        # /assets/… link and render completely unstyled.
        if grep -q 'sarg-dashboard\.css' "$page"; then
            :  # theme link already present (maybe broken) -> rewrite
        elif grep -q 'sarg.sourceforge.net' "$page" \
             || ! grep -q 'rel="stylesheet"' "$page"; then
            :  # genuine SARG page without any stylesheet -> inject
        else
            continue  # an unrelated styled document -> leave it alone
        fi

        pagedir="${page%/*}"

        # Relative path from the page's dir up to the SERVED copy.
        rel="$(realpath -m --relative-to="$pagedir" \
                   "$SERVED_CSS" 2>/dev/null || true)"
        if [[ -z "$rel" ]]; then
            # Fallback: ../ × the page's depth below OUTPUT_DIR.
            sub="${pagedir#"$OUTPUT_DIR"}"
            sub="${sub#/}"
            n=0
            [[ -n "$sub" ]] && n=$(awk -F/ '{print NF}' <<<"$sub")
            rel=$(printf '%.0s../' $(seq 1 "$n"))images/sarg-dashboard.css
        fi

        if grep -q 'sarg-dashboard\.css' "$page"; then
            # Rewrite any existing link (absolute /assets/... or relative).
            sed -E -i "s|(href=\")([^\"]*)sarg-dashboard\.css|\1$rel|g" "$page"
        else
            # No stylesheet link at all — inject one before </head>.
            sed -i "s|</head>|  <link rel=\"stylesheet\" href=\"$rel\" type=\"text/css\">\n</head>|" "$page"
        fi
        STYLED=$((STYLED+1))
    done < <(find "$OUTPUT_DIR" -name '*.html' -print0 2>/dev/null)
    echo "==> Themed $STYLED SARG report pages (link -> $SERVED_CSS)"
else
    echo "==> NOTE: sarg-dashboard.css not found at $MASTER_REPORT_CSS"
    echo "          SARG report pages will keep their default styling."
fi

# ------------------------------------------------------------
# 3c) FALLBACK: refresh the dashboard KPI snapshot from the report
# ------------------------------------------------------------
# Runs only when refresh-dashboard.py did NOT run (GEN_OK=0) — the
# generator already patches these (and everything else) richer itself.
# ------------------------------------------------------------
DASH_OUT="$newest/dashboard.html"
idx="$newest/index.html"

if [[ "${GEN_OK:-0}" -eq 0 && -f "$DASH_OUT" && -f "$idx" ]]; then

    users_n=$(find "$newest" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l)

    # BYTES cells: a size cell immediately followed by a %BYTES cell.
    bytes_list=$(grep -oP '<td class="data">\K[0-9.]+[KMGT](?=</td><td class="data">[0-9.]+%)' "$idx" 2>/dev/null || true)
    tot_gb=$(awk '{u=substr($0,length($0));v=substr($0,1,length($0)-1);
        m=(u=="K"?1/1048576:(u=="M"?1/1024:(u=="G"?1:(u=="T"?1024:0))));
        s+=v*m} END{if(NR>0)printf "%.2f",s; else print ""}' <<<"$bytes_list")

    # CONNECT cells: a count cell immediately followed by BYTES + %BYTES.
    conn_list=$(grep -oP '<td class="data">\K[0-9.]+[KMGT]?(?=</td><td class="data">[0-9.]+[KMGT]</td><td class="data">[0-9.]+%)' "$idx" 2>/dev/null || true)
    tot_conn=$(awk '{u=substr($0,length($0));
        if(u~/[KMGT]/){v=substr($0,1,length($0)-1)}else{u="";v=$0}
        m=(u=="K"?1024:(u=="M"?1048576:(u=="G"?1073741824:(u=="T"?1099511627776:1))));
        s+=v*m} END{if(NR>0)printf "%.0f",s; else print ""}' <<<"$conn_list")

    # Weighted in-cache % (per-row IN% matches alternate with %BYTES matches).
    in_pct=$(paste -d' ' <(printf '%s\n' "$bytes_list") \
        <(grep -oP '<td class="data">\K[0-9.]+(?=%</td><td class="data">[0-9.]+%</td>)' "$idx" 2>/dev/null | awk 'NR%2==0') \
        2>/dev/null | awk '{u=substr($1,length($1));v=substr($1,1,length($1)-1);
            m=(u=="K"?1/1048576:(u=="M"?1/1024:(u=="G"?1:(u=="T"?1024:0))));
            gb=v*m; s+=gb; w+=gb*$2}
        END{if(s>0)printf "%.2f",w/s; else print ""}')

    # Denied / authfail totals = visible rows + summed "N more ..." notes.
    count_events(){
        local vis more
        vis=$(grep -oP '\d{2}/\d{2}/\d{4}-\d{2}:\d{2}:\d{2}' "$1" 2>/dev/null | wc -l)
        more=$(grep -oP "[0-9]+(?= more $2)" "$1" 2>/dev/null | awk '{s+=$1}END{print s+0}')
        echo $(( vis + more ))
    }
    denied_n=0; auth_n=0
    [[ -f "$newest/denied.html" ]]   && denied_n=$(count_events "$newest/denied.html"  "denied")
    [[ -f "$newest/authfail.html" ]] && auth_n=$(count_events "$newest/authfail.html" "authentication")

    # Period label + generation timestamp from the report itself.
    # NOTE: sarg mixes plain spaces and &nbsp;/U+00A0, so strip all leading
    # non-alphanumerics after "Period:"; trailing '|| true' keeps set -e +
    # pipefail happy when a pattern is absent.
    period=$(grep -oP 'Period:[^<]*' "$idx" 2>/dev/null | head -1 \
             | sed -E 's/^Period:[^0-9A-Za-z]+//' || true)
    [[ -z "$period" ]] && \
        period=$(grep -oP '(?<=report for )[^<]+' "$idx" 2>/dev/null | head -1 || true)
    gent=$(grep -oP 'on \K[0-9]{2}/[A-Za-z]{3}/[0-9]{4}-[0-9:]+' "$idx" 2>/dev/null | head -1 || true)
    gent_disp="${gent/-/ · }"

    # Pretty unit formatting for the KPI cards.
    if [[ -n "$tot_gb" && -n "$tot_conn" && "$users_n" -gt 0 ]]; then

        read bw_v bw_d bw_u <<<"$(awk -v g="$tot_gb" 'BEGIN{
            if(g>=1024){printf "%.2f 2 T", g/1024}
            else if(g>=1){printf "%.2f 2 G", g}
            else       {printf "%.0f 0 MB", g*1024}}')"
        read cn_v cn_d cn_u <<<"$(awk -v c="$tot_conn" 'BEGIN{
            if(c>=1000000){printf "%.2f 2 M", c/1000000}
            else if(c>=1000){printf "%.2f 2 K", c/1000}
            else          {printf "%d 0 X", c}}')" ; [[ "$cn_u" == "X" ]] && cn_u=""
        tot_fmt=$(awk -v g="$tot_gb" 'BEGIN{if(g>=1024)printf "%.2f TB",g/1024; else printf "%.1f GB",g}')
        gb_fmt="${tot_gb} GB"; in_fmt=""; out_fmt=""
        if [[ -n "$in_pct" ]]; then
            in_fmt=$(awk -v g="$tot_gb" -v p="$in_pct" 'BEGIN{printf "%.1f GB",  g*p/100}')
            out_fmt=$(awk -v g="$tot_gb" -v p="$in_pct" 'BEGIN{printf "%.2f GB", g*(100-p)/100}')
        fi

        sed -E -i \
            -e "s/(id=\"kpi-bw\" data-count=\")[^\"]*(\" data-dec=\")[^\"]*(\" data-suffix=\")[^\"]*/\1${bw_v}\2${bw_d}\3${bw_u}/" \
            -e "s/(id=\"kpi-conn\" data-count=\")[^\"]*(\" data-dec=\")[^\"]*(\" data-suffix=\")[^\"]*/\1${cn_v}\2${cn_d}\3${cn_u}/" \
            -e "s/(id=\"kpi-users\" data-count=\")[^\"]*/\1${users_n}/" \
            -e "s/(id=\"kpi-cache\" data-count=\")[^\"]*/\1${in_pct:-0}/" \
            -e "s/(id=\"kpi-denied\" data-count=\")[^\"]*/\1${denied_n}/" \
            -e "s/(id=\"kpi-auth\" data-count=\")[^\"]*/\1${auth_n}/" \
            -e "s|(id=\"foot-bw\">)[^<]*|\1≈${gb_fmt} transferred in the period|" \
            -e "s|(id=\"foot-conn\">)[^<]*|\1requests through the proxy|" \
            -e "s|(id=\"foot-users\">)[^<]*|\1distinct client IPs in the logs|" \
            -e "s|(id=\"foot-cache\">)[^<]*|\1only ≈${out_fmt} left to the internet|" \
            -e "s|(id=\"foot-denied\">)[^<]*|\1blocked by Squid policy|" \
            -e "s|(id=\"foot-auth\">)[^<]*|\1failed logins recorded|" \
            -e "s|(id=\"badge-period\">)[^<]*|\1${period:-…}|" \
            -e "s|(id=\"badge-time\">)[^<]*|\1${gent_disp:-…}|" \
            -e "s|(id=\"stat-incache\">)[^<]*|\1≈${in_fmt:-—}|" \
            -e "s|(id=\"stat-outcache\">)[^<]*|\1≈${out_fmt:-—}|" \
            -e "s|(id=\"stat-total\">)[^<]*|\1${tot_fmt}|" \
            "$DASH_OUT"
        echo "==> Dashboard KPIs refreshed: ${tot_fmt}, ${tot_conn} connections," \
             "${users_n} users, ${in_pct:-?}% cache, ${denied_n} denied, ${auth_n} auth failures"
    else
        echo "==> NOTE: could not extract totals from $idx — leaving dashboard values as-is."
    fi
fi

# ------------------------------------------------------------
# 5) Root page: a styled LOGIN GATE in front of the dashboard
# ------------------------------------------------------------
# The web server serves $OUTPUT_DIR as its document root, and SARG's own
# root index.html there just lists the report folders. We replace it with
# the login gate (login-page.html template with the newest report target
# + the SHA-256 digest of the access key baked in). Visitors to
# http://SERVER/ must sign in first; a successful sign-in sets a 12h
# cookie and redirects to the newest dashboard. A wrong key just shows
# an error. SARG re-creates its listing on every run, and this script
# re-creates the gate right after, so the login ALWAYS comes first.
# The page is fully self-contained (no external css/js) and carries no
# sarg.sourceforge.net marker, so the theming loop above never touches it.
#
# Access key resolution order:  $LOGIN_PASS env var  ->  the file
# $ASSETS_DIR/login-key (one line, chmod 600)  ->  built-in default
# (with a warning). The plain key never appears in the served page —
# only its sha256sum digest does (unless sha256sum is missing, in which
# case a plaintext fallback keeps the gate working).
# ------------------------------------------------------------
LANDING="$OUTPUT_DIR/index.html"
dash_rel="$(basename "$newest")/dashboard.html"
land_period="$(grep -oP 'Period:[^<]*' "$newest/index.html" 2>/dev/null | head -1 \
               | sed -E 's/^Period:[^0-9A-Za-z]+//' || true)"
landing_note="Updated $(date '+%d %b %Y · %H:%M') — period ${land_period:-$(basename "$newest")}"

LOGIN_PASS="${LOGIN_PASS:-}"
if [[ -z "$LOGIN_PASS" && -f "$ASSETS_DIR/login-key" ]]; then
    LOGIN_PASS="$(< "$ASSETS_DIR/login-key")"
fi
LOGIN_MODE="hash"; LOGIN_HASH=""; LOGIN_PLAIN=""
if [[ -z "$LOGIN_PASS" ]]; then
    LOGIN_PASS="cisoi-dashboard"
    echo "==> WARNING: no access key configured — using the default key." >&2
    echo "          Choose your own with LOGIN_PASS=... or by creating $ASSETS_DIR/login-key" >&2
    echo "          (one line, then chmod 600 it)." >&2
fi
if command -v sha256sum >/dev/null 2>&1; then
    LOGIN_HASH="$(printf '%s' "$LOGIN_PASS" | sha256sum 2>/dev/null | awk '{print $1}' || true)"
fi
if [[ "$LOGIN_HASH" =~ ^[0-9a-f]{64}$ ]]; then
    LOGIN_MODE="hash"; LOGIN_PLAIN=""
else
    LOGIN_MODE="plain"; LOGIN_PLAIN="$LOGIN_PASS"
    echo "==> NOTE: sha256sum unavailable — the key is embedded in plain text." >&2
fi

# Escape backslashes + ampersands so the values survive a sed replacement.
esc(){ printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/&/\\&/g'; }

if [[ -f "$MASTER_LOGIN" ]]; then
    tgt="$(esc "$dash_rel")"
    per="$(esc "${land_period:-$(basename "$newest")}")"
    note="$(esc "$landing_note")"
    plain="$(esc "$LOGIN_PLAIN")"
    sed -e "s|@@TARGET@@|$tgt|g" \
        -e "s|@@MODE@@|$LOGIN_MODE|g" \
        -e "s|@@HASH@@|$LOGIN_HASH|g" \
        -e "s|@@PASSWORD@@|$plain|g" \
        -e "s|@@PERIOD@@|$per|g" \
        -e "s|@@NOTE@@|$note|g" \
        "$MASTER_LOGIN" > "$LANDING"
    echo "==> Login gate written: $LANDING"
    echo "    Access key: [hidden — set via LOGIN_PASS or $ASSETS_DIR/login-key] (mode=$LOGIN_MODE)"
    echo "    After a successful sign-in it redirects to: $dash_rel"
else
    # Fallback: instant-redirect landing page (keeps http://SERVER/ working
    # even when login-page.html has not been copied to the server yet).
    echo "==> NOTE: login template not found — writing a plain auto-redirect page." >&2
    cat > "$LANDING" <<EOF
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <!-- Never cache this redirect: if the browser keeps a stale copy it
       will keep sending visitors to an old period's dashboard. -->
  <meta http-equiv="cache-control" content="no-cache, no-store, must-revalidate">
  <meta http-equiv="pragma" content="no-cache">
  <meta http-equiv="expires" content="0">
  <meta http-equiv="refresh" content="0; url=$dash_rel">
  <link rel="canonical" href="$dash_rel">
  <title>CISAI · Proxy Network Intelligence Dashboard</title>
  <style>
    body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
         background:radial-gradient(1200px 800px at 20% 10%,#16213e 0%,#0a0f1e 55%,#060913 100%);
         color:#e2e8f0;font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;text-align:center}
    .card{padding:2.5rem 3rem;border:1px solid rgba(56,189,248,.25);border-radius:1rem;
          background:rgba(13,20,38,.75);box-shadow:0 0 40px rgba(56,189,248,.12)}
    h1{margin:.8rem 0 .4rem;font-size:1.35rem;
       background:linear-gradient(90deg,#38bdf8,#a78bfa);-webkit-background-clip:text;background-clip:text;color:transparent}
    p{margin:.3rem 0;color:#94a3b8;font-size:.92rem}
    a{color:#38bdf8;font-weight:600}
    .dot{width:14px;height:14px;margin:0 auto;border-radius:50%;background:#38bdf8;
         box-shadow:0 0 18px #38bdf8;animation:p 1.1s ease-in-out infinite}
    @keyframes p{50%{transform:scale(.55);opacity:.5}}
  </style>
</head>
<body>
  <div class="card">
    <div class="dot"></div>
    <h1>Proxy Network Intelligence Dashboard</h1>
    <p>Opening the latest report &hellip;</p>
    <p><a href="$dash_rel">Continue to the dashboard</a></p>
    <p style="opacity:.55;font-size:.78rem">$landing_note</p>
  </div>
  <script>location.replace("$dash_rel");</script>
</body>
</html>
EOF
    echo "==> Landing page written: $LANDING (redirects -> $dash_rel)"
fi

# ------------------------------------------------------------
# 6) Report where to open it
# ------------------------------------------------------------
echo
echo "==> Done."
echo "    Open this path in your browser (you will be asked to sign in):"
echo "        $LANDING"
echo
echo "    After signing in it opens the newest dashboard:"
echo "        $newest/dashboard.html"
echo
echo "    (If the output_dir maps to http://SERVER/, simply open:)"
echo "        http://SERVER/"