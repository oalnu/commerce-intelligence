# Source-release maintenance

The public release is an unpaid educational portfolio. Its scope and known limitations are recorded in [RELEASE_NOTES.md](../RELEASE_NOTES.md). Source-derived previews, aggregates and the brief retain the [Olist attribution and CC BY-NC-SA 4.0 terms](../DATA_LICENSE.md). No commercial-use permission is granted. The licence's treatment of a particular later use depends on that use; this project supplies no blanket legal clearance.

## Public versus local files

The release includes Python, SQL, tests, aggregated validation evidence, Power BI source, genuine report-canvas previews, diagrams and documentation. It excludes raw/processed data, populated PBIX, databases, row-level exception extracts, caches and private feasibility history. The published M DataRoot is a setup placeholder; running `src/run.py` regenerates it for the user's checkout.

The previews are owner-authorized, pixel-exact crops. Full original screenshots remain local. Crop coordinates and source/output hashes are preserved in the screenshot manifest. No application account name is visible in the released previews.

## Prepare a later release from the original working folder

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip install Pillow==12.3.0
.\.venv\Scripts\python.exe src\prepare_publication.py --crop-screenshots
```

The script creates an isolated timestamped folder under ignored `dist/`; it never uploads. Its fixed crop is specific to the original verified 1710 x 1021 screenshots. Reinspect any replacement captures before changing the crop. Run it from the private original working folder when generating that same release; it deliberately rejects already-cropped images.

Before a future push, review the complete file list and Git diff, scan text for secrets and personal paths, verify local documentation links and licence notices, and revalidate changed code/report behavior. Do not upload the original working directory wholesale. The source package's placeholder is schema-checked; it is not claimed to refresh before setup. See [validation.md](validation.md) for independent pipeline and actual Desktop checks.

## Repository presentation

Suggested description: **Delivery reliability and review-selection analysis with Python, DuckDB SQL and a validated two-page Power BI report.**

Topics: `power-bi`, `sql`, `duckdb`, `python`, `data-analysis`, `analytics-engineering`, `olist`, `portfolio`.

After publication, pin the repository on the GitHub profile. Put its direct URL beside the CV project title. Personally rehearse the [five-minute walkthrough](interview_guide.md) and demonstrate the five concepts before claiming proficiency. No Fabric trial, paid cloud resource or automated cloud deployment is required.

