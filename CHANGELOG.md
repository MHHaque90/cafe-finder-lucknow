# Change Log

## Phase 12 — Documentation & Provenance Polish

- Verified README against actual implementation
- Added configuration section documenting `CAFE_FINDER_DATA_DIR`
- Added portability section documenting `src/` layout and packaging-based import
- Updated project structure to include all 18 modules
- Fixed test command references (`python -m pytest` instead of `python -m pytest tests/ -v`)
- Updated license section to clearly separate MIT code and ODbL data licensing
- Created `CHANGELOG.md`
- Created `CONTRIBUTING.md`
- Updated `src/cafe_finder/__init__.py` docstring to remove outdated "Phase 1" reference

## Phase 11 — Configuration Hardening & Portability

- Created `src/cafe_finder/config.py` with `CAFE_FINDER_DATA_DIR` environment variable support
- Added `DATA_DIR`, `RAW_DIR`, `PROCESSED_DIR`, `SNAPSHOTS_RAW_DIR`, `SNAPSHOTS_PROCESSED_DIR`, `DEFAULT_CSV_PATH`, `DEFAULT_OUTPUT_DIR` constants
- Updated `pipeline.py`, `integrity.py`, `analyze.py`, `search.py`, `quality.py`, `clean.py`, `fetch.py`, `validate.py`, `visualize.py` to import paths from `config` instead of hardcoding
- All modules now resolve paths centrally; no hardcoded `Path("data/...")` remains
- Relative environment paths are resolved relative to the current working directory

## Phase 10 — Data Contracts, Reproducibility & Pipeline Integrity

- Added `src/cafe_finder/schema.py` — Schema definition and validation
- Added `src/cafe_finder/manifest.py` — Draft/final manifest with validation
- Added `src/cafe_finder/integrity.py` — SHA-256 checksums, snapshot verification, CLI
- Added schema contract (13 canonical columns, version 1)
- Added manifest contract (draft and final, with checksums and atomic writes)
- Added quarantine mechanism for failed snapshots
- Added 9-status authoritative status model
- Added safe transactional promotion with backup and rollback
- Updated `src/cafe_finder/snapshot.py` — Added manifest and quarantine paths
- Updated `src/cafe_finder/pipeline.py` — Integrated schema validation, checksums, manifests
- Added tests: `tests/test_schema.py`, `tests/test_manifest.py`, `tests/test_integrity.py`, `tests/test_pipeline.py`

## Phase 9 — Historical Change Analysis & Data Lineage

- Added `src/cafe_finder/history.py` — Historical change analysis across snapshots
- Added `src/cafe_finder/lineage.py` — Data lineage report
- Added first/last observation tracking for each `osm_id`
- Added field-level change history with structured records
- Added snapshot reconstruction CLI
- Added historical quality evolution tracking

## Phase 8 — Data Freshness, Snapshots & Change Detection

- Added `src/cafe_finder/snapshot.py` — Snapshot management, comparison
- Added `src/cafe_finder/compare.py` — Dataset comparison between CSV snapshots
- Added snapshot workflow with `--snapshot` flag on pipeline
- Added atomic promotion with backup and rollback
- Added safe refresh guarantee
- Added dataset comparison with added/removed/modified/unchanged categories

## Phase 7 — Data Quality & Provenance

- Added `src/cafe_finder/quality.py` — Data quality and provenance module
- Added `is_missing()` function for consistent missing value detection
- Added `calculate_completeness()` for field-level completeness metrics
- Added `validate_coordinates()` for coordinate validation
- Added `detect_duplicates()` for duplicate detection
- Added `generate_record_quality_flags()` for record-level quality flags
- Added `generate_provenance()` for data lineage tracking
- Added `generate_quality_report()` for structured quality reporting
- Added `_normalize_name()` and `_normalize_coord()` helpers

## Phase 6 — Deterministic Cafe Ranking & Explainable Recommendations

- Added `src/cafe_finder/ranking.py` — Deterministic scoring and ranking
- Added 100-point scoring model (distance, cuisine, hours, website, phone)
- Added `--sort-by score` option to search CLI
- Added explainable score breakdown
- Added deterministic tie-breaking

## Phase 5 — Location & Distance

- Added `src/cafe_finder/distance.py` — Haversine distance calculation
- Added `--lat`, `--lon`, `--radius` options to search CLI
- Added `--sort-by distance` option
- Added coordinate and radius validation
- Added distance sorting

## Phase 4 — Search & Filtering

- Added `src/cafe_finder/search.py` — Search and filter CLI
- Added `--name`, `--cuisine`, `--has-website`, `--has-phone`, `--has-opening-hours` filters
- Added `--sort-by` option (name, latitude, longitude, distance, score)
- Added cuisine tag splitting support
- Added `--lat`/`--lon`/`--radius` integration

## Phase 3 — Data Visualization

- Added `src/cafe_finder/visualize.py` — Data visualization CLI
- Added cuisine distribution chart
- Added data completeness chart
- Added cafe locations scatter plot
- Added `--output-dir` option
- Added `--csv-path` option

## Phase 2 — Exploratory Data Analysis (EDA)

- Added `src/cafe_finder/analyze.py` — Exploratory data analysis CLI
- Added dataset structure, completeness, cuisine, contact info analysis
- Added geographic coverage analysis
- Added address completeness analysis
- Added `--csv-path` option

## Phase 1 — Data Ingestion Pipeline

- Added `src/cafe_finder/fetch.py` — Overpass API data retrieval
- Added `src/cafe_finder/clean.py` — Cleaning, normalization, deduplication
- Added `src/cafe_finder/validate.py` — Validation checks
- Added `src/cafe_finder/pipeline.py` — Main orchestration
- Added `src/cafe_finder/__init__.py` — Package initialization
- Added `data/raw/lucknow_cafes_raw.json` — Raw OSM response
- Added `data/raw/lucknow_cafes_cleaned.json` — Cleaned records
- Added `data/processed/lucknow_cafes.csv` — Final validated CSV
- Initial tests: `tests/test_pipeline.py`

## Packaging & CI

- Updated `pyproject.toml` — src layout, test extras, 10 console scripts
- Updated `requirements.txt` — Runtime and test dependencies
- Added `.github/workflows/ci.yml` — GitHub Actions CI with Python 3.10–3.14 matrix
- Added README CI section
- 482-test regression gate

## Cleanup & Configuration

- Removed artifacts, created LICENSE and DATA_LICENSE.md
- Updated `.gitignore` with visualization output patterns
- Created `src/cafe_finder/config.py` — Centralized path configuration
- Updated all modules to use config imports
- 482/482 tests passing
