# Validation and reproduction

Run commands from the repository root. Close Desktop before `src/run.py` regenerates PBIP files.

```powershell
.\.venv\Scripts\python.exe src\run.py
.\.venv\Scripts\python.exe tests\reproducibility.py
.\.venv\Scripts\python.exe tests\test_validation_guards.py
.\.venv\Scripts\python.exe tests\cleanroom.py
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe src\validate_report_schema.py
```

The first run downloads the pinned original ZIP if source files are absent. All source file hashes and headers must match `config/source_manifest.json`. SQL integrity failures stop the transaction. Independent Python validation reads source CSVs using the standard library and uses Decimal for currency; it does not reuse DuckDB or the transformation SQL. It reconciles each order, all/core baselines and 565 month/state groups. The reproducibility test creates a new empty database and requires byte-identical ordered CSV exports.

## Desktop checks

Open the generated PBIP, choose Transform data > Close & Apply to synchronize generated queries, refresh, and wait until the loading dialog closes. These commands query the actual running Desktop engine through the installed Microsoft ADOMD client, then compare with independently checked data:

```powershell
.\tests\query_desktop_model.ps1 -QueryFile tests\model_baselines.dax -OutputFile reports\powerbi\model_baselines.json
.\tests\query_desktop_model.ps1 -QueryFile tests\model_month_state.dax -OutputFile reports\powerbi\model_month_state.json
.\tests\query_desktop_model.ps1 -QueryFile tests\model_diagnostics.dax -OutputFile reports\powerbi\model_diagnostics.json
.\tests\query_desktop_model.ps1 -QueryFile tests\model_tables.dax -OutputFile reports\powerbi\model_tables.json
.\tests\query_desktop_model.ps1 -QueryFile tests\model_review_context.dax -OutputFile reports\powerbi\model_review_context.json
.\tests\query_desktop_model.ps1 -QueryFile tests\model_relationships.dax -OutputFile reports\powerbi\model_relationships.json
.\.venv\Scripts\python.exe tests\validate_powerbi_results.py
.\.venv\Scripts\python.exe tests\validate_review_context.py
```

Use one relevant Desktop instance at a time: the script selects the newest local Analysis Services workspace. It checks that workspace has exactly one loaded catalog. UI slicer context is not inherited by an external DAX query; test queries specify their own context. Money tolerance is BRL 0.01; other numeric comparisons use relative 1e-10 / absolute 1e-9 tolerances.

The current build has 32 hard SQL checks. The guard suite rejects empty/duplicate baseline scopes, missing diagnostics, blank currency treated as zero, and Python `-O`; three mutations in an isolated copied database verify detection of null lateness, missing duration and inverted date logic. These synthetic test mutations never enter the analysis data or findings. The clean-room test copies only source/config/theme seed into a new ignored directory, starts with no raw data, runs the entire pipeline and requires nine matching mart hashes. It reuses the installed Python environment; it is not a dependency-installation or Desktop test. `--archive` can supply an authentic local ZIP for offline reproduction.

Schema validation checks Microsoft’s versioned JSON schemas and caches them locally. It does not prove that DAX, visuals or interaction behavior work. Actual Desktop refresh, live DAX and UI inspection supply those separate checks.

## Manual acceptance script

1. Open the saved PBIX. Both pages must render with no visual error banners. Default month and state are All within Jan 2017–Aug 2018.
2. Overview: 96,203 eligible; 93.2% on time; 10.2 median days; 4.09 average selected review.
3. Choose state RJ: 12,310 eligible; 87.9%; 12.0 days; 3.88. Switch pages: RJ remains selected; 1,495 late orders.
4. Clear state with the slicer eraser. Choose March 2018: 7,003 eligible; 81.0%; 13.4 days; 3.75.
5. Select RJ in the state chart: 864 eligible and 65.5% on time. Click the same bar again to clear selection.
6. Clear month, check the priorities page: 6,531 late; R$0.99M merchandise; 23.1 P90; 98.7% single-seller coverage. All eight default seller rows and all three stage rows with denominators must be visible. The overview review subtitle should show late coverage 29.2% versus on-time 99.3%.
7. Save, close and reopen. Recheck both pages and the baseline DAX. To save a new format use File > Save as > Browse this device. The quick-save WebView modal could not be controlled reliably in this VM.

Actual execution evidence: `reports/powerbi/ui_checks.json`, model result JSONs and validation summary; technical gates in `reports/validation/technical_gates.json`. Screenshots are evidence of rendering, not evidence of every calculation. No cloud refresh, Fabric workspace, cross-device portability or automatic Desktop deployment is claimed.
