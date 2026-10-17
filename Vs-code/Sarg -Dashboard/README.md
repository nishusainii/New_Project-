# Proxy Network Intelligence Dashboard (CISAI)

A polished, executive **proxy network analytics dashboard** that replaces the plain
SARG (Squid Analysis Report Generator) index page whenever you run
`sudo sarg`.

## What's in this folder

| File | Purpose |
|------|---------|
| `run-sarg-dashboard.sh` | **Run this.** Runs `sudo sarg`, then drops `dashboard.html` + `dashboard.css` into the freshly-generated report and themes every SARG page via `sarg-dashboard.css` (served from a copy at the output_dir root) so the creative dashboard is what you see. |
| `dashboard.html` | The analytics dashboard markup + logic (master copy). It is copied into each new report folder by the runner. |
| `dashboard.css` | The dashboard's **creative stylesheet** — "NOC Command Center" theme (blue & purple enterprise accents). All visuals live here; `dashboard.html` loads it with a plain `<link>`. |
| `refresh-dashboard.py` | **Data engine.** Rebuilds every `AUTO` block of the deployed dashboard from the SARG report itself (`index.html` / `topsites.html` / `denied.html` / `authfail.html`): subtitle, KPI cards, top-consumers, top-sites, platform-mix donut, denied hotspots, analyst alerts, key insights and the full leaderboard — so the dashboard always matches the current report period. Python 3, stdlib only. Invoked automatically by the runner; can also be run standalone: `python3 refresh-dashboard.py --report <report-dir> --dashboard <dashboard.html>`. |
| `sarg-dashboard.css` | The theme for the **SARG-generated report pages** (Top users, Top sites, Sites & Users, Downloads, Denied, Auth failures, per-user pages, graphs). The master lives in the assets folder; the runner also bakes a **served copy into the output_dir root** and rewrites every SARG page's stylesheet link to a relative `../` path pointing at it — so the theme loads even when the assets folder is not reachable over HTTP. |
| `login-page.html` | **Login gate.** Styled sign-in page shown at `http://SERVER/` before the report. The runner bakes the newest report target + a SHA-256 digest of your access key into it, so the plain key never appears in the served file. |
| `company-logo.jpg` | Company logo. **Embedded as base64 inside `dashboard.html`** (works wherever the file is opened). The report pages' top bar loads it via `sarg-dashboard.css` (relative `url()`), so the runner keeps a copy next to that CSS — in the assets folder and at the output_dir root. |
| `29Aug2026-29Aug2026/` | Sample SARG report output, including the deployed `dashboard.html` + `dashboard.css`. |
| `README.md` | This file. |

## How it works

Every SARG run writes its report into a per-period folder such as
`29Aug2026-29Aug2026/` containing `index.html`, `topsites.html`,
`denied.html`, etc. This project adds a hand-built `dashboard.html`
(rich KPI cards, animated charts, a full user leaderboard, and analyst
insights) next to those files.

`run-sarg-dashboard.sh`:

1. Runs `sudo sarg` to (re)generate the report for the current period.
2. Finds the newest report folder.
3. Copies the master `dashboard.html` **and** `dashboard.css` into that
   folder.
4. Keeps the **masters** of `sarg-dashboard.css` + `company-logo.jpg` in
   the **assets folder** (outside SARG's `output_dir`, so SARG never
   mistakes them for report directories), bakes **served copies** of both
   into the **output_dir root**, and **rewrites the stylesheet link in
   every SARG-generated page** (`index.html`, `topsites.html`, per-user
   pages, graphs, ...) from the broken root-absolute
   `/assets/sarg-dashboard.css` (or any previous relative path) to a
   correct *relative* `../` path pointing at that served copy. Pages with
   no stylesheet link get one injected before `</head>`. Because the theme
   file is served from inside the same tree as the reports, it loads no
   matter how the vhost/alias is mapped — and over `file://` too.
5. **Regenerates the whole dashboard's data** from the fresh report via
   `refresh-dashboard.py`: the header subtitle and badges, the KPI strip,
   Top Bandwidth Consumers, Top Destinations, the Traffic-Mix donut
   (sites auto-classified into Twitter/X, Meta, Google, Dev/tools,
   Everything else), Cache Efficiency, Denied Access Hotspots, Analyst
   Alerts, Key Insights, and the full per-user leaderboard + totals row —
   all extracted from `index.html` / `topsites.html` / `denied.html` /
   `authfail.html`. The dashboard's `<!-- AUTO:… -->` blocks keep the
   regeneration idempotent. If `python3` is unavailable the runner falls
   back to the KPI-strip-only refresh.
6. Ensures `company-logo.jpg` sits next to `sarg-dashboard.css` in both
   places — assets folder (master) and output_dir root (served copy the
   report pages actually load; the CSS pulls it in with a relative
   `url()` for the report pages' top bar).
7. Writes a styled **login gate** as the root `index.html` in the
   output_dir. Visitors to `http://SERVER/` must enter the access key
   first; a successful sign-in sets a 12-hour cookie and redirects to
   the newest report's `dashboard.html`. SARG re-creates its own listing
   `index.html` on every run; the runner always overwrites it with the
   login gate again right after.
8. With `--clean-dupes`, also deletes the `DDMMMYYYY-DDMMMYYYY.1/.2/…`
   duplicate folders that SARG creates for a period when `overwrite no`
   (the default) is set in `sarg.conf` — keep one folder per period.
9. Tells you the exact URL/path to open.

## Usage

Recommended server layout — keep SARG's `output_dir` clean (it must
contain **only** report folders, or SARG warns about stray files):

```
/var/www/html/sarg/           <- SARG output_dir
   DDMMMYYYY-DDMMMYYYY/       <- one folder per report period
   sarg-dashboard.css         <- served copy (written by the runner;
                                every SARG page links here relatively)
   company-logo.jpg           <- served copy (loaded by sarg-dashboard.css)
/var/www/html/sarg-assets/    <- this script + the master files
   run-sarg-dashboard.sh
   dashboard.html
   dashboard.css
   sarg-dashboard.css
   login-page.html
   login-key                  <- optional: your access key (chmod 600)
   company-logo.jpg
```

Run it from the output dir:

```bash
cd /var/www/html/sarg
sudo bash /var/www/html/sarg-assets/run-sarg-dashboard.sh
```

Or explicitly point at your SARG `output_dir` from anywhere:

```bash
sudo OUTPUT_DIR=/var/www/sarg bash /opt/sarg-dashboard/run-sarg-dashboard.sh
```

The script finds the master files next to itself by default; `OUTPUT_DIR`
is the only variable you normally need to set.

Then open the printed path in a browser, for example:

```
http://SERVER/sarg/29Aug2026-29Aug2026/dashboard.html
```

If the web server's document root **is** the SARG `output_dir` (as on the
CISAI server), you can simply open:

```
http://SERVER/          → login page → <newest-period>/dashboard.html
```

### Set the access key

The login gate asks for a single access key. The runner resolves it in
this order:

1. the `LOGIN_PASS` environment variable, then
2. the file `$ASSETS_DIR/login-key` (one line — convenient for a
   permanent key on the server), then
3. a built-in default key (with a printed warning).

Example (permanent key on the server):

```bash
sudo bash -c 'umask 077; echo "Choose-Your-Own-Key-2026" > /var/www/html/sarg-assets/login-key'
```

Only the **SHA-256 digest** of the key ends up in the served page, never
the key itself. If you want a different key later, just change the file
(or the variable) and re-run the runner.

### Flags

| Flag | Effect |
|------|--------|
| `--deploy-only` | Skip running `sudo sarg`; just (re)deploy the dashboard, theme, KPI refresh and the login gate into the newest report. |
| `--clean-dupes` | Delete `DDMMMYYYY-DDMMMYYYY.1`, `.2`, `.3` … duplicate folders of the newest report period. |

### Stop duplicate period folders (one-time, on the server)

SARG's default `overwrite no` creates a new `.1/.2/.3…` folder every time
it runs for a period you already reported on. To make re-runs **replace**
the old folder instead, set in `/etc/sarg/sarg.conf` (path may be
`/usr/local/etc/sarg/sarg.conf` depending on the install):

```
overwrite yes
```

Then clean the existing duplicates once, either manually
(`rm -rf /path/to/output_dir/PERIOD.[0-9]*`) or with
`bash run-sarg-dashboard.sh --deploy-only --clean-dupes`.

## Config

The runner reads optional environment variables:

| Variable | Default | Meaning |
|----------|---------|---------|
| `OUTPUT_DIR` | current directory | Root folder that holds one subfolder per SARG report period (reports only). |
| `ASSETS_DIR` | dirname of `MASTER_REPORT_CSS` | Folder holding the on-server master copies of `sarg-dashboard.css` + `company-logo.jpg` (the pages themselves load the served copies baked into `OUTPUT_DIR`). |
| `MASTER_DASHBOARD` | `$SCRIPT_DIR/dashboard.html` | Master dashboard file to copy into each report (`SCRIPT_DIR` = the script's own folder). |
| `MASTER_CSS` | `$SCRIPT_DIR/dashboard.css` | Master stylesheet to copy next to each `dashboard.html`. |
| `MASTER_REPORT_CSS` | `$SCRIPT_DIR/sarg-dashboard.css` | Master stylesheet for the SARG-generated report pages. |
| `MASTER_LOGIN` | `$SCRIPT_DIR/login-page.html` | Master login-gate template baked into the root `index.html`. |
| `LOGIN_PASS` | *(see "Set the access key")* | Access key for the login gate. |
| `LOGO` | `$SCRIPT_DIR/company-logo.jpg` | Company logo. |

## Styling

All of the dashboard's look & feel lives in **`dashboard.css`** — a
pure-CSS, zero-dependency theme ("NOC Command Center", blue & purple
enterprise accents). To restyle the
dashboard, edit only that one file; the markup and animations in
`dashboard.html` stay untouched.

Highlights:

- Midnight glassmorphism panels with blue/purple orbs, grid + starfield backdrop.
- Animated blue→purple gradient titles, glowing KPI numbers and pulsing status dot.
- Gold / silver / bronze medal ranks, shimmering progress bars.
- Rotating conic glow behind the donut charts, hover glows on rows/cards.
- Custom scrollbar, smooth reveal-on-scroll, `prefers-reduced-motion` support.

## Notes

- The dashboard is **static and offline** (no external libraries, no CDNs):
  `dashboard.html` + `dashboard.css` are the only two files it needs — the
  logo is embedded as a base64 data-URI inside `dashboard.html`, so it can
  never render as a broken image, no matter where the file is opened.
  The themed SARG report pages load the logo via `sarg-dashboard.css`
  (relative `url()`), which is why the runner keeps `company-logo.jpg`
  next to that CSS file in both the assets folder and the output_dir root.
- SARG's `output_dir` still contains only report **folders**; the two
  served files the runner drops at its root are plain files, so SARG does
  not print "doesn't contain a sarg-date file" warnings for them.
- **Every** section of the dashboard — KPI cards, header subtitle and
  badges, top-consumers bars, sites list, traffic-mix donut and legend,
  cache stats, denied hotspots, analyst alerts, key insights and the
  full leaderboard — is **auto-regenerated from the report data** on
  every `run-sarg-dashboard.sh` run (by `refresh-dashboard.py`), so the
  page always reflects the current period. Two folders of the *same* day
  can still look similar because they analyse the same day's Squid log —
  but nothing is a frozen hand-tuned snapshot any more.
- The root **login gate** `index.html` at the output_dir is fully
  self-contained (inline CSS/JS, no external assets) and intentionally
  carries no SARG markers, so the report-theming pass never touches it.
  It always points at the newest report folder, and SARG's own root
  listing is restored each run and immediately replaced again —
  refreshing is automatic.
- The dashboard's **"Sign out"** link (top-right of the header) clears
  the session cookie and returns you to the login page.
- **Access-gate security note.** The login gate is a *client-side
  barrier*, not server-side security: the access key is embedded only as
  a SHA-256 digest (or, if `sha256sum` is missing on the server, in
  plain text), the session is a cookie, and the report folders themselves
  stay reachable if someone knows their direct URLs. It keeps casual
  visitors out and looks the part, but for **real** protection, guard the
  whole output_dir with Apache Basic Auth instead:

  ```bash
  sudo apt install apache2-utils
  sudo htpasswd -c /etc/apache2/sarg-htpasswd youruser
  ```

  then add to the Apache configuration for the output_dir:

  ```
  <Directory /var/www/html/sarg>
      AuthType Basic
      AuthName "CISAI Restricted"
      AuthUserFile /etc/apache2/sarg-htpasswd
      Require valid-user
  </Directory>
  ```

  and reload Apache. With Basic Auth the browser shows its own native
  login prompt and **every** file is protected; the styled gate above
  becomes the front page you land on after that first login.
