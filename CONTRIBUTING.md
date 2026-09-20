# Contributing to Lucknow Cafe Finder

## Project Overview

Lucknow Cafe Finder is a Python toolkit for ingesting, analyzing, and visualizing cafe data from OpenStreetMap using the Overpass API. The project processes OSM `amenity=cafe` elements for Lucknow, Uttar Pradesh, India.

**Data source**: OpenStreetMap (ODbL 1.0)
**Code license**: MIT

## Project Structure

```
cafe-finder/
├── src/cafe_finder/     # Package source code
├── tests/               # Test suite
├── data/                # Data files (raw, processed, snapshots)
├── .github/workflows/   # CI configuration
├── pyproject.toml       # Package metadata and dependencies
├── requirements.txt     # Runtime and test dependencies
├── README.md            # Project documentation
├── LICENSE              # MIT license for code
├── DATA_LICENSE.md      # ODbL attribution for data
└── CHANGELOG.md         # Phase history
```

## Installation

The project uses a `src/` package layout. Install with:

```bash
python -m pip install -e ".[test]"
```

This installs the package and all runtime dependencies (`requests`, `pandas`, `matplotlib`) plus `pytest` for testing. After installation, `import cafe_finder` works from anywhere — no `PYTHONPATH=src` is needed.

## Running Tests

The current regression baseline is **482 tests**.

Collect tests:
```bash
python -m pytest --collect-only -q
```

Run all tests:
```bash
python -m pytest -q
```

The full suite must pass before any change is considered complete.

## Development Workflow

```
install → run tests → run relevant CLI/tests → run full regression suite
```

1. Install the package: `python -m pip install -e ".[test]"`
2. Run the full test suite: `python -m pytest -q`
3. Test any new or modified CLI: `cafe-finder-<command> --help`
4. Verify the regression gate: **482/482 tests pass**

## CLI Development Expectations

All CLI commands are defined in `pyproject.toml` under `[project.scripts]`. Each command has a `main()` function in its module.

Console commands:
- `cafe-finder-pipeline` — Data ingestion
- `cafe-finder-search` — Search and filter
- `cafe-finder-quality` — Data quality report
- `cafe-finder-history` — Historical analysis
- `cafe-finder-integrity` — Integrity verification
- `cafe-finder-analyze` — EDA
- `cafe-finder-visualize` — Visualization
- `cafe-finder-snapshot` — Snapshot management
- `cafe-finder-lineage` — Lineage report
- `cafe-finder-compare` — Dataset comparison

All commands support `--help`. When adding new CLI commands, define the entry point in `pyproject.toml` and implement `main()` in the corresponding module.

## Data-Source and Provenance Rules

- **OSM-derived data is attributed.** All datasets inherit the ODbL 1.0 license.
- **Missing fields remain missing.** The project does not fabricate ratings, hours, phones, or other missing facts.
- **No unsupported claims.** Missing data is described as "unavailable in dataset", never as "cafe has no X".
- **Historical snapshots preserve provenance.** Timestamps are generated at execution time, never hardcoded.
- **Integrity manifests/checksums protect snapshot artifacts.**
- **Data quality is reported rather than hidden.**

See `DATA_LICENSE.md` for full ODbL attribution details.

## OSM-Derived Data Handling

- Data comes from OpenStreetMap via the Overpass API
- The geographic scope is Lucknow, Uttar Pradesh, India
- OSM data may be incomplete — some fields may be missing
- The project does not enrich or fabricate missing data
- All data-quality checks use `quality.is_missing()` for consistent missing value detection

## Code and Test Expectations

- Follow the existing code style and conventions
- Write tests for new functionality
- Do not modify existing test behavior unless a genuine regression is found
- The `src/` package layout must be preserved
- All paths must be resolved through `src/cafe_finder/config.py`
- Do not hardcode `Path("data/...")` in modules

## Documentation Expectations

- Keep documentation accurate and factual
- Do not invent capabilities not supported by the code
- Update README and CHANGELOG when adding features
- Keep ODbL attribution clear and prominent
- Verify all CLI commands against `pyproject.toml`

## CI Expectations

The project uses GitHub Actions CI (`.github/workflows/ci.yml`):
- Python matrix: 3.10–3.14
- Installation via `pip install -e ".[test]"`
- Test collection gate: 482 tests
- Full pytest execution
- All 10 CLI `--help` verification

**Note**: The CI workflow has not yet been verified to execute on GitHub. The configuration is based on the local implementation.

## Configuration

The project uses `src/cafe_finder/config.py` for centralized path configuration. Override the data root with:

```bash
CAFE_FINDER_DATA_DIR=/path/to/data python -m cafe_finder.pipeline
```

Relative paths are resolved relative to the current working directory.

## No New Dependencies

Do not add new dependencies. The project uses:
- `requests` — Overpass API
- `pandas` — Data manipulation
- `matplotlib` — Visualization
- `pytest` — Testing

No documentation-generation frameworks (MkDocs, Sphinx, etc.) are used.

## No Git Operations

This repository intentionally has no `.git` directory. Do not initialize Git, commit, or push.

## Scope Compliance

- Do not add application features outside the project phases
- Do not modify algorithms or data behavior
- Do not add new dependencies
- Do not implement Docker, deployment, or package publishing
- Do not initialize Git or perform any Git operations
