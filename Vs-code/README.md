# SARG Creative Dashboard (CiSOI)

A polished, executive **analytics dashboard** that replaces the plain
SARG (Squid Analysis Report Generator) index page whenever you run
`sudo sarg`.

## What's in this folder

| File | Purpose |
|------|---------|
| `run-sarg-dashboard.sh` | **Run this.** Runs `sudo sarg`, then drops `dashboard.html` into the freshly-generated report so the creative dashboard is what you see. |
| `dashboard.html` | The analytics dashboard (master copy). It is copied into each new report folder by the runner. |
| `company-logo.jpg` | Company logo shown in the dashboard header (`dashboard.html` links to it via `../company-logo.jpg`). |
| `29Aug2026-29Aug2026/` | Sample SARG report output, including the deployed `dashboard.html`. |
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
3. Copies the master `dashboard.html` into that folder.
4. Ensures `company-logo.jpg` is present in the output root (the logo is
   referenced as `../company-logo.jpg` from inside a report folder).
5. Tells you the exact URL/path to open.

## Usage

```bash
# From the folder that contains dashboard.html + company-logo.jpg
# (this is your SARG output_dir; adjust OUTPUT_DIR if it differs):
sudo bash run-sarg-dashboard.sh
```

Or explicitly point at your SARG `output_dir`:

```bash
sudo OUTPUT_DIR=/var/www/sarg bash run-sarg-dashboard.sh
```

Then open the printed path in a browser, for example:

```
http://SERVER/sarg/29Aug2026-29Aug2026/dashboard.html
```

## Config

The runner reads three optional environment variables:

| Variable | Default | Meaning |
|----------|---------|---------|
| `OUTPUT_DIR` | current directory | Root folder that holds one subfolder per SARG report period. |
| `MASTER_DASHBOARD` | `$OUTPUT_DIR/dashboard.html` | Master dashboard file to copy into each report. |
| `LOGO` | `$OUTPUT_DIR/company-logo.jpg` | Company logo. |

## Notes

- `dashboard.html` is a **static, self-contained** page (no external
  libraries; charts are hand-drawn SVG/CSS). It works fully offline.
- Its numbers are a snapshot of the report it was built from. To refresh
  the figures you should regenerate the dashboard's data arrays from the
  latest SARG output (or update them after each `sudo sarg` run).
