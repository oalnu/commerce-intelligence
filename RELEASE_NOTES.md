# Commerce Intelligence — source release 1.0.0

## Included

- Reproducible ingestion of the authentic, hash-pinned Olist dataset.
- DuckDB staging, order/item marts, seven analytical queries and 32 integrity checks.
- Independent raw-CSV reconciliation and failure-detection regression tests.
- Editable two-page Power BI report, semantic model, 36 measures and seven active relationships.
- Genuine dashboard previews, architecture diagram, management brief and interview guide.
- Recorded local Desktop validation: full import/refresh, saved-file reopen, live DAX comparisons and visual interaction checks.

## Release boundaries

The public package excludes the imported PBIX, raw/processed data, DuckDB databases, row-level exception extracts, local caches and private investigation history. Downloaded data remains local when reproducing the pipeline.

The published DataRoot is a setup placeholder. Run `src/run.py` before opening the PBIP; it generates the local data and sets the local path. The validated local Desktop report is the source of the previews and saved DAX evidence. Schema validation of the sanitized source is recorded separately; an untouched placeholder package is not claimed to refresh immediately.

Public previews remove application chrome using a pixel-exact rectangular crop. Source screenshot hashes, crop coordinates and output hashes are recorded in [the screenshot manifest](reports/powerbi/screenshot_manifest.json). No charts, values or report pixels were added, retouched or regenerated.

## Known limitations

The source is historical, survey timing is selective and operational causes are unobserved. No causal effects, financial losses or realized savings are claimed. Power BI Desktop is needed for interaction; the GitHub previews are static. Desktop publishing and refresh are local/manual, with no cloud or CI deployment claim.

Source attribution and CC BY-NC-SA 4.0 terms are in [DATA_LICENSE.md](DATA_LICENSE.md). This source release is an educational portfolio, with no commercial licence granted.
