# Cafe Finder — Lucknow

A Python data engineering project demonstrating cafe discovery, analysis, and historical tracking in Lucknow, India using OpenStreetMap/Overpass data.

**Scope**: Lucknow, Uttar Pradesh, India only.
**Data source**: OpenStreetMap `amenity=cafe` elements.
**License**: MIT (code) / ODbL 1.0 (data).

Current baseline: **482 tests**.

## What This Project Is

Cafe Finder is a portfolio-grade Python project demonstrating a complete data engineering workflow: from raw OpenStreetMap ingestion through cleaning, validation, analysis, visualization, search, ranking, historical tracking, and integrity verification. It is not a commercial product — it is an engineering exercise showing how a real-world dataset is transformed, analyzed, and maintained over time.

The project processes OSM data for Lucknow cafes and demonstrates:

1. **Ingestion** — Fetch cafe data from Overpass API, preserve raw artifacts
2. **Cleaning** — Normalize values, handle missing data, strip whitespace
3. **Validation** — Schema enforcement, coordinate ranges, duplicate detection
4. **Quality assessment** — Completeness metrics, data-quality flags, provenance
5. **Exploratory analysis** — Dataset structure, cuisine distribution, geographic coverage
6. **Visualization** — Charts for cuisine, completeness, and locations
7. **Search and filtering** — Name, cuisine, metadata, location, distance
8. **Deterministic ranking** — Weighted, explainable scoring
9. **Historical tracking** — Snapshots, change detection, observation history, lineage
10. **Integrity verification** — Schema validation, checksums, manifests, quarantine

### Why This Project

The engineering progression matters more than the final dataset:

```text
Raw data
  → Clean data
    → Validated data
      → Analyzed data
        → Searchable data
          → Ranked results
            → Historical snapshots
              → Provenance
                → Integrity verification
                  → Reproducible package
```

Each stage addresses a real data engineering challenge: incomplete source data, evolving snapshots, data contracts, and reproducibility.

### Portfolio Highlights

| Category | What it demonstrates |
|----------|---------------------|
| **Data ingestion** | Overpass API, raw preservation, cleaning, validation |
| **Data analysis** | pandas, completeness analysis, EDA |
| **Visualization** | matplotlib charts (cuisine, completeness, locations) |
| **Search** | Cuisine filtering, combined filters, exact tag semantics |
| **Geospatial** | Haversine distance, radius filtering |
| **Ranking** | Deterministic weighted scoring, explainable breakdown |
| **Data quality** | Completeness, coordinate validation, duplicate detection |
| **Historical** | Snapshots, change detection, observation history, lineage |
| **Integrity** | Schema validation, SHA-256 checksums, manifests, quarantine |
| **Engineering** | `src/` layout, 10 CLI entry points, pytest, CI matrix |
| **Testing** | 482 tests across 14 modules, Python 3.10–3.14 |

## Installation

```bash
pip install -e ".[test]"
```

This installs the package and all runtime dependencies (`requests`, `pandas`, `matplotlib`) plus `pytest` for testing.

The `src/` package layout is used — after installation, `import cafe_finder` works from anywhere without `PYTHONPATH=src`.

## Configuration

The project uses a central configuration module (`src/cafe_finder/config.py`). The user-facing setting is `CAFE_FINDER_DATA_DIR`:

* **`CAFE_FINDER_DATA_DIR`** — Environment variable to override the data root directory. Defaults to `Path("data")`, i.e. a `data` directory relative to the current working directory. All data and output paths are derived from this:
  * `data/raw/` — Raw and cleaned JSON
  * `data/raw/snapshots/` — Snapshot raw artifacts
  * `data/processed/` — Final CSV output and visualizations
  * `data/processed/snapshots/` — Snapshot processed artifacts
  * `data/processed/visualizations/` — Chart outputs

To override the data root:
```bash
CAFE_FINDER_DATA_DIR=/path/to/data python -m cafe_finder.pipeline
```

Relative environment paths are resolved relative to the current working directory.

## CLI

After `pip install -e ".[test]"`, the following console commands are available:

| Command | Module | Description |
|---------|--------|-------------|
| `cafe-finder-pipeline` | `cafe_finder.pipeline` | Data ingestion pipeline |
| `cafe-finder-search` | `cafe_finder.search` | Search and filter cafes |
| `cafe-finder-quality` | `cafe_finder.quality` | Data quality report |
| `cafe-finder-history` | `cafe_finder.history` | Historical change analysis |
| `cafe-finder-integrity` | `cafe_finder.integrity` | Integrity verification |
| `cafe-finder-analyze` | `cafe_finder.analyze` | Exploratory data analysis |
| `cafe-finder-visualize` | `cafe_finder.visualize` | Data visualization |
| `cafe-finder-snapshot` | `cafe_finder.snapshot` | Snapshot management |
| `cafe-finder-lineage` | `cafe_finder.lineage` | Data lineage report |
| `cafe-finder-compare` | `cafe_finder.compare` | Dataset comparison |

All commands support `--help` for usage information.

## Data Fields

The CSV contains these columns (empty if not available in OSM):

| Field | Description |
|-------|-------------|
| `osm_id` | OSM element ID with type prefix (e.g., `node12345`) |
| `name` | Cafe name (original casing preserved) |
| `latitude` | Latitude in decimal degrees |
| `longitude` | Longitude in decimal degrees |
| `street` | Street address (`addr:street`) |
| `housenumber` | House number (`addr:housenumber`) |
| `city` | City (`addr:city`) |
| `postcode` | Postal code (`addr:postcode`) |
| `cuisine` | Cuisine type (`cuisine`) |
| `opening_hours` | Opening hours (`opening_hours`) |
| `website` | Website URL (`website`) |
| `phone` | Phone number (`phone`) |
| `source` | OSM source tag (`source`) |

## Data Provenance

The project uses **OpenStreetMap-derived data through the Overpass API**.

* **Source**: OpenStreetMap `amenity=cafe` elements
* **Retrieval method**: Overpass API (`https://overpass-api.de/api/interpreter`)
* **Geographic scope**: Lucknow, Uttar Pradesh, India
* **Completeness**: OSM data may be incomplete — fields such as cuisine, hours, website, and phone may be missing
* **No fabrication**: The project does not fabricate missing cafe information

## OSM / ODbL Attribution

**This product includes data from OpenStreetMap contributors.**

Data licensed under **Open Database License (ODbL) 1.0**
https://www.openstreetmap.org/copyright

Map tiles and imagery © OpenStreetMap contributors.

When using this dataset, please attribute:
> "Contains data from OpenStreetMap contributors, licensed under ODbL 1.0"

See `DATA_LICENSE.md` for full attribution details and licensing boundaries.

---

## Portfolio Summary

Cafe Finder demonstrates a complete data engineering lifecycle: from OpenStreetMap ingestion through cleaning, validation, quality assessment, analysis, visualization, search, ranking, historical tracking, and integrity verification. It is packaged as a Python project with 18 source modules, 14 test modules, 482 tests, and 10 CLI commands. The project is CI-configured for Python 3.10–3.14 and uses a `src/` layout with centralized configuration via `CAFE_FINDER_DATA_DIR`.

### Problem

Discover and analyze cafes in Lucknow using OpenStreetMap data, while maintaining data quality, historical tracking, and integrity verification.

### Data

OpenStreetMap `amenity=cafe` elements retrieved via the Overpass API. The current dataset contains 33 records with 13 canonical columns. Many fields are incomplete (e.g., 29 of 33 records lack phone numbers), which the project reports honestly rather than fabricating.

### Engineering

The project implements: data ingestion, cleaning, schema validation, quality assessment, EDA, visualization, search/filtering, Haversine distance calculation, deterministic ranking, snapshot management, change detection, historical analysis, lineage tracking, and integrity verification. All of this is packaged as a Python project with 10 CLI entry points, 482 tests, and a Python 3.10–3.14 CI matrix.

### Reliability

Missing data is reported as missing — never fabricated. Historical snapshots preserve provenance with actual timestamps. Integrity manifests and SHA-256 checksums protect snapshot artifacts. Failed operations trigger safe rollback or quarantine behavior.

### Reproducibility

Install with `pip install -e ".[test]"`, run `python -m pytest -q` to verify 482 tests. Data paths are centrally configured via `CAFE_FINDER_DATA_DIR`. The CI workflow documents the exact installation and test steps.

## Skills Demonstrated

* Python 3.10+
* pandas for data manipulation
* matplotlib for visualization
* CLI development with argparse
* Package engineering (`src/` layout, `pyproject.toml`)
* pytest and test-driven development
* CI/CD pipeline configuration
* Data cleaning and validation
* Geospatial calculations (Haversine)
* Deterministic ranking systems
* Data quality assessment
* Historical data analysis
* Data lineage and provenance
* Integrity verification (checksums, manifests)
* Configuration management
* Reproducible workflows

## Running Tests

```bash
python -m pytest --collect-only -q
python -m pytest -q
```

Tests cover all project phases. The current regression baseline is **482 tests**.

## Portability

The project uses a `src/` package layout. After installation via `pip install -e ".[test]"`, the package is importable from anywhere without setting `PYTHONPATH=src`. All data paths are centrally resolved through `src/cafe_finder/config.py`, and `CAFE_FINDER_DATA_DIR` can override the data root. Explicit CLI paths (`--csv-path`, `--output-dir`) retain their intended semantics regardless of configuration.

Relative environment variable paths are resolved relative to the current working directory when the variable is not set.

## Continuous Integration

This project uses GitHub Actions CI. The workflow runs on every push and pull request across all supported Python versions.

CI verifies:
- Installation via `pip install -e ".[test]"`
- Package imports correctly from installed location
- All 10 CLI entry points respond to `--help`
- Test collection equals exactly **482 tests**
- Full test suite passes (**482/482**)
- All supported Python versions pass (Python 3.10–3.14)

See `.github/workflows/ci.yml` for details.

**Note**: The CI workflow has not yet been verified to execute successfully on GitHub. The instructions and configuration are based on the local implementation only.

## Project Structure

```
cafe-finder/
├── data/
│   ├── raw/                    # Raw & cleaned JSON
│   │   └── snapshots/          # Snapshot raw artifacts
│   └── processed/              # Final CSV output and visualizations
│       ├── lucknow_cafes.csv
│       └── snapshots/          # Snapshot processed artifacts
├── src/cafe_finder/
│   ├── __init__.py
│   ├── config.py               # Centralized path configuration
│   ├── fetch.py                # Overpass API data retrieval
│   ├── clean.py                # Cleaning, normalization, deduplication
│   ├── validate.py             # Validation checks
│   ├── pipeline.py             # Main orchestration
│   ├── quality.py              # Data quality & provenance
│   ├── schema.py               # Schema definition & validation
│   ├── manifest.py             # Draft/final manifest + validation
│   ├── integrity.py            # SHA-256, verification, CLI
│   ├── analyze.py              # Exploratory data analysis
│   ├── search.py               # Search & filtering
│   ├── distance.py             # Haversine distance calculation
│   ├── ranking.py              # Deterministic cafe ranking
│   ├── visualize.py            # Data visualization
│   ├── snapshot.py             # Snapshot management
│   ├── compare.py              # Dataset comparison
│   ├── history.py              # Historical change analysis
│   └── lineage.py              # Data lineage report
├── tests/
│   ├── test_pipeline.py
│   ├── test_search.py
│   ├── test_quality.py
│   ├── test_analyze.py
│   ├── test_visualize.py
│   ├── test_distance.py
│   ├── test_ranking.py
│   ├── test_history.py
│   ├── test_integrity.py
│   ├── test_schema.py
│   ├── test_manifest.py
│   ├── test_snapshot.py
│   ├── test_lineage.py
│   └── test_compare.py
├── docs/
│   └── architecture/
│       ├── cafe-finder-architecture.json
│       └── cafe-finder-architecture.html
├── .github/workflows/
│   └── ci.yml
├── README.md
├── LICENSE
├── DATA_LICENSE.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── pyproject.toml
├── requirements.txt
└── .gitignore
```

## Demo / Quick Start

```bash
# Verify installation
cafe-finder-pipeline --help
cafe-finder-search --help
cafe-finder-quality --help
cafe-finder-history --help

# Run quality report
python -m cafe_finder.quality

# Search cafes
python -m cafe_finder.search --name cafe
python -m cafe_finder.search --cuisine coffee_shop --has-website

# Location-based search with distance and ranking
python -m cafe_finder.search --lat 26.8467 --lon 80.9462 --radius 3 --sort-by score

# View historical snapshots
python -m cafe_finder.snapshot --verbose

# Verify integrity of latest snapshot
python -m cafe_finder.integrity --verbose
```

## Example Commands

### Search

```bash
python -m cafe_finder.search --name cafe
python -m cafe_finder.search --cuisine coffee_shop --has-website
python -m cafe_finder.search --lat 26.8467 --lon 80.9462 --radius 3 --sort-by score
```

### Quality

```bash
python -m cafe_finder.quality
python -m cafe_finder.quality --verbose
python -m cafe_finder.quality path/to/cafes.csv
```

### History

```bash
python -m cafe_finder.history
python -m cafe_finder.history --osm-id node12345
python -m cafe_finder.history --quality --json
```

### Integrity

```bash
python -m cafe_finder.integrity
python -m cafe_finder.integrity --snapshot 2026-09-08T120000Z
python -m cafe_finder.integrity --json --output report.json
```

## Architecture

```text
OpenStreetMap / Overpass
          │
          ▼
      fetch.py
          │
          ▼
      clean.py ──→ validate.py
          │              │
          ▼              ▼
    pipeline.py ──→ quality.py ──→ analyze.py
          │              │              │
          ▼              ▼              ▼
    schema.py      manifest.py    visualize.py
          │              │              │
          ▼              ▼              ▼
    integrity.py   ranking.py   distance.py
          │              │              │
          ▼              ▼              ▼
    snapshot.py    search.py    compare.py
          │              │
          ▼              ▼
    history.py     lineage.py
```

All modules import paths from `src/cafe_finder/config.py`. No hardcoded `Path("data/...")` remains.

[Interactive system architecture](docs/architecture/cafe-finder-architecture.html)

## Data Flow

```text
1. Retrieve from Overpass API
2. Preserve raw JSON artifact
3. Clean and normalize
4. Validate (schema, coordinates, duplicates)
5. Generate processed CSV
6. Assess quality and completeness
7. Search, filter, rank, and analyze
8. Store in snapshots (if --snapshot)
9. Compare across snapshots (historical)
10. Verify integrity (checksums, manifests)
```

Key distinctions:
* **Source data** — OpenStreetMap `amenity=cafe` elements
* **Raw artifacts** — Direct OSM response + cleaned JSON
* **Processed data** — Validated CSV dataset
* **Historical snapshots** — Timestamped dataset versions
* **Metadata/manifests** — SHA-256 checksums, schema validation

## Limitations

* **OSM data completeness** — Many cafe fields are missing (e.g., 29 of 33 records lack phone, 31 of 33 lack website). The project reports these as missing; it does not fabricate them.
* **No commercial data** — No ratings, reviews, pricing, or business information is included.
* **Overpass dependency** — Data retrieval depends on the Overpass API availability.
* **Dataset scope** — Limited to Lucknow, Uttar Pradesh, India.
* **Ranking is deterministic, not learned** — The ranking system uses explicit rules, not machine learning. It scores available evidence, not real-world quality.
* **No real-time updates** — Data reflects the OSM state at fetch time.
* **Snapshot ID granularity** — 1-second resolution; two refreshes started in the same second share an identifier.

## Data Quality Philosophy

* Missing source fields remain missing.
* Data is not fabricated to improve completeness.
* Quality is measured and reported — not hidden.
* Historical snapshots preserve provenance (actual timestamps, never hardcoded).
* Integrity manifests and checksums protect snapshot artifacts.
* OSM-derived data retains appropriate ODbL attribution.

This project does not claim to represent all Lucknow cafes. It reports what OSM contains and how complete that data is.

## Project Metrics

* **18 source modules** under `src/cafe_finder/`
* **14 test modules** under `tests/`
* **482 tests** (current baseline)
* **10 CLI commands**
* **Python 3.10–3.14** CI matrix
* **13 canonical data columns** in the processed CSV
* **33 records** in the current dataset
* **5 runtime dependencies** (`requests`, `pandas`, `matplotlib`, `pytest`)
* **0 application behavior changes** in documentation-only phases

## License

**Project code**: MIT License (see `LICENSE`)

**Data (OSM-derived)**: Open Database License (ODbL) 1.0 — see `DATA_LICENSE.md`

The MIT license applies to the original Python source code, tests, and documentation. The ODbL 1.0 license applies to the OSM-derived datasets and any output derived from them. The two licensing boundaries are kept clearly separate.

## Phase 2: Exploratory Data Analysis (EDA)

### What is EDA?

Exploratory Data Analysis (EDA) is the process of examining and summarizing a dataset to understand its structure, content, quality, and patterns. In this project, Phase 2 performs a terminal-based EDA on the validated cafe dataset produced by Phase 1.

The EDA report provides insights into:
- **Dataset structure**: Rows, columns, data types, memory usage
- **Data completeness**: Which fields are populated vs missing
- **Cafe names**: How many have names, duplicates, most common names
- **Cuisine types**: What cuisines are represented (split from semicolon-separated values)
- **Contact info**: Website and phone number availability
- **Opening hours**: How many cafes provide hours
- **Geographic coverage**: Latitude/longitude range of the dataset
- **Address completeness**: Street, house number, city, postcode availability

### How to Run the Analysis

```bash
# Run with default CSV (data/processed/lucknow_cafes.csv)
python -m cafe_finder.analyze

# Run with custom CSV path
python -m cafe_finder.analyze path/to/cafes.csv
```

### What the Report Tells You

The report answers questions like:
- How many cafes were found in total?
- How many have names, cuisine info, websites, phone numbers, opening hours?
- What are the most common cuisine types in Lucknow?
- What is the geographic spread of the dataset?
- How complete are the address fields?

### Data Source

The analysis is based on the current OpenStreetMap dataset snapshot retrieved in Phase 1. The data reflects OSM community contributions and may contain gaps, outdated information, or inconsistencies. No data enrichment or inference is performed—only what OSM provides is analyzed.

## Phase 3: Data Visualization

### Why Data Visualization?

Data visualization transforms numerical findings from EDA into intuitive charts that reveal patterns at a glance. While the terminal report shows exact numbers, charts make it easier to compare relative magnitudes, spot outliers, and communicate findings to others.

### What is Matplotlib?

[Matplotlib](https://matplotlib.org/) is Python's foundational plotting library. It provides a MATLAB-style interface for creating static, publication-quality charts. We use it directly (no Seaborn or higher-level wrappers) to learn the core concepts.

### The Three Charts

| Chart | File | What It Shows |
|-------|------|---------------|
| **Cuisine Distribution** | `cuisine_distribution.png` | Bar chart of individual cuisine tags (split from semicolon-separated values). Shows the most common cuisine types in Lucknow cafes. |
| **Data Completeness** | `data_completeness.png` | Horizontal bar chart showing the percentage of records with usable data for each field (name, address parts, cuisine, hours, contact info). Quickly reveals which fields are well-populated vs sparse. |
| **Cafe Locations** | `cafe_locations.png` | Scatter plot of longitude vs latitude for all cafes with valid coordinates. Shows the geographic spread of the dataset. Note: reflects OSM data coverage, not official city boundaries. |

### Where Charts Are Saved

All charts are saved to:

```text
data/processed/visualizations/
```

### How to Run the Visualization

```bash
# Run with default CSV (data/processed/lucknow_cafes.csv)
python -m cafe_finder.visualize

# Run with custom CSV path and/or output directory
python -m cafe_finder.visualize path/to/cafes.csv --output-dir path/to/output
```

### What Each Chart Helps Us Understand

- **Cuisine Distribution**: Identifies the dominant food/beverage categories in Lucknow's cafe scene (e.g., coffee shops vs tea shops vs multi-cuisine).
- **Data Completeness**: Highlights data quality gaps — fields like `website` and `phone` are often missing in OSM, while `latitude`/`longitude` are nearly always present.
- **Cafe Locations**: Visualizes the spatial distribution of mapped cafes, showing where OSM contributors have mapped cafes within the Lucknow bounding box.

## Phase 4: Search & Filtering

### Why Search & Filtering?

Phase 4 adds a command-line interface to search and filter the cafe dataset. Users can find cafes by name, cuisine type, or the presence of specific fields (website, phone, opening hours). Results can be sorted by name, latitude, or longitude.

### How to Run Search

```bash
# Show all cafes
python -m cafe_finder.search

# Search by name (case-insensitive partial match)
python -m cafe_finder.search --name coffee

# Filter by cuisine tag (exact tag match, case-insensitive)
python -m cafe_finder.search --cuisine coffee_shop

# Only show cafes with a website
python -m cafe_finder.search --has-website

# Only show cafes with a phone number
python -m cafe_finder.search --has-phone

# Only show cafes with opening hours
python -m cafe_finder.search --has-opening-hours

# Combine filters (AND logic)
python -m cafe_finder.search --cuisine coffee_shop --has-website

# Sort results
python -m cafe_finder.search --sort-by name
python -m cafe_finder.search --sort-by latitude
python -m cafe_finder.search --sort-by longitude

# Use custom CSV
python -m cafe_finder.search path/to/cafes.csv --name cafe
```

### Filter Logic

All filters use **AND logic**: a cafe must match all specified criteria to appear in results. For example, `--cuisine coffee_shop --has-website` returns only coffee shops that also have a website.

The `--cuisine` filter matches individual tags after splitting the semicolon-separated `cuisine` field. For example, a cafe with `cuisine="coffee_shop;pasta"` matches `--cuisine coffee_shop` and `--cuisine pasta`.

## Phase 5: Location & Distance

### Why Latitude/Longitude Are Useful

The cafe dataset includes latitude and longitude coordinates from OpenStreetMap. These coordinates enable **geospatial queries** — finding cafes near a specific location, calculating distances, and sorting by proximity. This is the foundation of any "near me" search functionality.

### What the Haversine Formula Does

The **Haversine formula** calculates the great-circle distance between two points on a sphere (Earth) given their latitudes and longitudes. It accounts for Earth's curvature, providing accurate distances in kilometers for any two coordinate pairs.

```
a = sin²(Δlat/2) + cos(lat1) · cos(lat2) · sin²(Δlon/2)
c = 2 · atan2(√a, √(1−a))
d = R · c
```

Where:
- `lat1, lon1` = user's coordinates
- `lat2, lon2` = cafe's coordinates
- `R` = Earth's radius (6371 km)
- `d` = distance in kilometers

### What "Radius Search" Means

**Radius search** returns all cafes within a specified distance (in kilometers) from a given location. For example, `--radius 3` with `--lat 26.8467 --lon 80.9462` returns only cafes whose calculated Haversine distance is ≤ 3 km from that point. Results are sorted nearest-first by default.

### How Distance Sorting Works

When a location (`--lat` and `--lon`) is provided:
- All results are automatically sorted by distance ascending (nearest first)
- The `--sort-by distance` option is enabled and works explicitly
- Distance is calculated using the Haversine formula from the user's coordinates to each cafe's coordinates
- If `--sort-by distance` is requested without `--lat` and `--lon`, an error is shown

### CLI Examples

```bash
# Find cafes near a location, sorted by distance (default when location given)
python -m cafe_finder.search --lat 26.8467 --lon 80.9462

# Find cafes within 3 km of a location
python -m cafe_finder.search --lat 26.8467 --lon 80.9462 --radius 3

# Combine cuisine filter with location and radius
python -m cafe_finder.search --cuisine coffee_shop --lat 26.8467 --lon 80.9462 --radius 5

# Explicit distance sorting
python -m cafe_finder.search --lat 26.8467 --lon 80.9462 --sort-by distance
```

### Validation Behavior

The CLI validates coordinate and radius arguments:

| Invalid Combination | Error Message |
|---------------------|---------------|
| `--lat` without `--lon` | `Error: --lat requires --lon` |
| `--lon` without `--lat` | `Error: --lon requires --lat` |
| `--radius` without location | `Error: --radius requires --lat and --lon` |
| `--radius -1` (negative) | `Error: --radius must be non-negative` |
| `--lat 200` (invalid) | `Error: Invalid latitude 200.0: must be in range [-90, 90]` |
| `--lon 200` (invalid) | `Error: Invalid longitude 200.0: must be in range [-180, 180]` |
| `--sort-by distance` without location | `Error: --sort-by distance requires --lat and --lon` |

### Limitations

- **No geocoding**: You must provide latitude/longitude directly. The tool does not convert addresses or place names to coordinates.
- **No map API**: No Google Maps, Mapbox, or other external mapping services are used. Distances are calculated purely from the OSM dataset coordinates using the Haversine formula.
- **Straight-line distance**: Distances are "as the crow flies" (great-circle), not walking/driving distances.
- **Data-dependent**: Accuracy depends on the quality of OSM coordinates. Some cafes may have approximate or missing coordinates.

## Phase 6: Deterministic Cafe Ranking & Explainable Recommendations

### Why Deterministic Ranking?

Phase 6 adds a **deterministic, rule-based scoring system** to rank cafes by relevance. Unlike ML/AI approaches, this system uses explicit, transparent rules with no randomness, no external APIs, and no training data. The score is a **match score based on available dataset evidence** — it is not an objective measure of cafe quality.

### The 100-Point Scoring Model

Each cafe receives a score from 0 to 100, composed of five weighted components:

| Component | Weight | Description |
|-----------|--------|-------------|
| **Distance** | 40 pts | Proximity to user location (when provided) |
| **Cuisine Match** | 30 pts | Exact tag match with requested cuisine |
| **Opening Hours** | 15 pts | Available in dataset |
| **Website** | 10 pts | Available in dataset |
| **Phone** | 5 pts | Available in dataset |

**Total: 100 points maximum**

### Distance Bands

When a location (`--lat`/`--lon`) is provided, distance is scored in bands:

| Distance | Points |
|----------|--------|
| ≤ 1 km | 40 |
| > 1 km and ≤ 2 km | 30 |
| > 2 km and ≤ 3 km | 20 |
| > 3 km and ≤ 5 km | 10 |
| > 5 km | 0 |
| Missing/invalid | 0 |

**Without a location**, `score_distance` is always 0 — no distance is fabricated.

### Cuisine Matching Semantics

Cuisine matching follows the **exact Phase 4 semantics**:

- Case-insensitive exact tag matching
- Semicolon-separated tags (e.g., `coffee_shop;pasta;breakfast`)
- `coffee_shop` matches `coffee_shop;pasta` → **30 points**
- `coffee` does **NOT** match `coffee_shop` → **0 points** (no substring matching)
- Missing cuisine or no requested cuisine → **0 points**

### Metadata Signals

- **Opening hours**: 15 pts if present in dataset, 0 if missing
- **Website**: 10 pts if present in dataset, 0 if missing
- **Phone**: 5 pts if present in dataset, 0 if missing

### Explainable Score Breakdown

Every scored cafe includes a human-readable breakdown showing **why** it received each score component:

```
1. Cafe Coffee Day
   Score: 85/100
   Distance: 0.80 km
   Why:
   - Distance: 40 points
   - Cuisine match: coffee_shop → 30 points
   - Opening hours available in dataset → 15 points
   - Website unavailable in dataset → 0 points
   - Phone unavailable in dataset → 0 points
```

**Dataset language, not real-world claims**: Missing data is described as "unavailable in dataset" — never as "cafe has no website" — because missing OSM data does not prove the real-world cafe lacks that attribute.

### Using `--sort-by score`

Enable ranking with the new sort option:

```bash
# Rank all cafes by score (no location needed)
python -m cafe_finder.search --sort-by score

# Rank cafes near a location
python -m cafe_finder.search --lat 26.8467 --lon 80.9462 --sort-by score

# Combine with cuisine filter and radius
python -m cafe_finder.search --cuisine coffee_shop --lat 26.8467 --lon 80.9462 --radius 5 --sort-by score
```

### Score Without Location

Score sorting works **without** latitude/longitude:

```bash
python -m cafe_finder.search --sort-by score
```

In this case:
- `score_distance = 0` (no distance evidence exists)
- Other components (cuisine, hours, website, phone) still contribute
- No distance is fabricated

### Deterministic Tie-Breaking

When multiple cafes have the same `score_total`, ordering is deterministic:

1. `score_total` descending
2. Normalized cafe `name` ascending (trimmed, case-insensitive)
3. `osm_id` ascending

The final `osm_id` tie-breaker ensures deterministic ordering even when names are missing or identical.

### Missing-Data Semantics

- Missing distance → "Distance could not be determined from dataset → 0 points"
- Missing cuisine match → "Cuisine unavailable in dataset or no match → 0 points"
- Missing opening hours → "Opening hours unavailable in dataset → 0 points"
- Missing website → "Website unavailable in dataset → 0 points"
- Missing phone → "Phone unavailable in dataset → 0 points"

No unsupported real-world claims are made.

### Rule-Based vs AI/ML

This is a **purely rule-based** system:
- No machine learning
- No AI/LLM
- No external APIs
- No personalization
- No user profiles
- No database
- Deterministic, repeatable results

### Preserved Behavior

All Phase 1–5 functionality remains intact:
- `--sort-by distance` still requires `--lat` and `--lon`
- Phase 4 filters (`--name`, `--cuisine`, `--has-website`, etc.) work identically
- Phase 5 radius filtering works identically
- Normal output (without `--sort-by score`) is unchanged

## Phase 7: Data Quality & Provenance

### Why Data Quality & Provenance?

Phase 7 adds a standalone, deterministic data-quality and provenance layer that answers:

> **"How complete, valid, unique, and traceable is the cafe dataset?"**

Phase 7 evaluates **dataset quality**, not the quality of the businesses. It does not judge whether a cafe is "good" — it measures how well the dataset represents what it claims to represent.

The architecture remains:

```text
OSM / Overpass
      ↓
Raw JSON
      ↓
Clean + Validate
      ↓
Processed CSV
      ↓
Data Quality / Provenance     ← Phase 7
      ↓
Search / Distance / Ranking
```

No AI, ML, databases, maps, geocoding, user accounts, personalization, or paid APIs are introduced.

---

### Data Quality

The quality module (`src/cafe_finder/quality.py`) provides deterministic, rule-based checks across four dimensions:

#### Completeness
For each important field, the report shows:
- **Present count** — records with usable values
- **Missing count** — records where the field is missing
- **Completeness percentage** — present / total × 100

Fields analyzed: `name`, `latitude`, `longitude`, `street`, `housenumber`, `city`, `postcode`, `cuisine`, `opening_hours`, `website`, `phone`.

A field is **missing** when it is:
- `None`
- `NaN` / `pd.NA`
- Empty string (`""`)
- Whitespace-only string (`"   "`)

**Missing ≠ negative fact**. "Website missing" means *website information is unavailable in the dataset* — not *the cafe has no website*.

#### Validity (Coordinate Validation)
Coordinates are validated against their defined ranges:
- Latitude ∈ `[-90, 90]`
- Longitude ∈ `[-180, 180]`

Each record is checked for:
- Missing latitude / longitude
- Non-numeric latitude / longitude
- Latitude outside valid range
- Longitude outside valid range

**No silent conversion** — invalid coordinates are flagged, not coerced into validity.

#### Uniqueness (Duplicate Detection)
Two deterministic duplicate checks:

1. **Duplicate OSM IDs** — Records sharing the same `osm_id`
2. **Coordinate + Name duplicates** — Records with the same normalized `(name, latitude, longitude)` combination

Normalization for coordinate+name:
- Name: trimmed, internal whitespace collapsed, casefolded (case-insensitive)
- Coordinates: rounded to 6 decimal places (~0.1 m precision)
- Missing names → empty string (so two unnamed cafes at identical coordinates are flagged)

**Important**: Identical cafe names at *different* coordinates are **not** duplicates. Multiple "Cafe Coffee Day" records at distinct locations remain separate.

#### Record-Level Quality Flags
`generate_record_quality_flags(df)` returns a new DataFrame (original unmodified) with a `quality_flags` column — a list of issue strings per record. Possible flags:
- `missing_name`, `missing_cuisine`, `missing_opening_hours`, `missing_website`, `missing_phone`
- `invalid_latitude`, `invalid_longitude`
- `duplicate_osm_id`, `duplicate_location_name`

A clean record has an empty flag list.

---

### Provenance

Provenance captures data lineage without altering cafe attributes:

| Field | Value |
|-------|-------|
| **Source** | OpenStreetMap |
| **Retrieval method** | Overpass API |
| **Retrieved at** | Actual execution timestamp (ISO 8601, UTC) — never hardcoded |
| **Record count** | Number of rows in the supplied DataFrame |
| **Source file** | Path to the CSV used (when available) |

Provenance is:
- **Explicit** — separate from cafe data
- **Truthful** — timestamp generated at report time
- **Deterministic in structure** — same keys every run

---

### CLI

Run the quality report:

```powershell
python -m cafe_finder.quality
```

Loads `data/processed/lucknow_cafes.csv` by default (project-relative path consistent with other modules). Accepts an optional positional path:

```powershell
python -m cafe_finder.quality path/to/cafes.csv
```

**Verbose mode** — record-level issues:

```powershell
python -m cafe_finder.quality --verbose
```

Example output:
```text
Record: node123
Issues:
  - missing_name
  - missing_website
```

**Validation behavior** (same principle as Phase 5):
- Missing file → actionable error on stderr, exit code 1, **no misleading report**
- Empty CSV (0 records) → handled safely, reports `Records: 0`, **not treated as missing file**

---

### Important Limitation

> **Data-quality checks measure the quality and completeness of the dataset. They do not prove that every cafe attribute is currently true in the real world.**

A cafe marked with `missing_website` may well have a website in reality — it simply isn't recorded in this OSM snapshot. All language uses "unavailable in dataset", never "cafe has no X".

---

## Phase 8: Data Freshness, Snapshots & Change Detection

### Why Snapshots?

OpenStreetMap data changes over time — cafes open, close, get renamed, or gain new attributes. Phase 8 answers:

> **"What changed since the last refresh, and can we refresh safely without losing the current dataset?"**

Phase 8 adds a snapshot-based refresh workflow:

```text
Fetch (Overpass)
      ↓
Raw snapshot + metadata          ← timestamped, status = "success"
      ↓
Clean + Validate (existing rules)
      ↓
Processed snapshot + metadata    ← timestamped, actual UTC retrieval time
      ↓
Atomic promotion                 ← current CSV replaced only on success
      ↓
Compare with previous snapshot   ← added / removed / modified / unchanged
```

No AI, ML, databases, maps, schedulers, or new dependencies are introduced.

---

### Snapshot Concepts

Two distinct timestamps are used:

| Concept | Meaning | When recorded |
|---------|---------|---------------|
| **`snapshot_id`** | Filesystem-safe identifier (`YYYY-MM-DDTHHMMSSZ`) | At refresh start, so the snapshot has a stable directory name |
| **`retrieved_at_utc`** | Actual UTC time the Overpass request successfully returned | Immediately after the fetch succeeds — never inferred, never hardcoded |

A snapshot is only considered **valid** (usable as a comparison baseline) if:

1. `status == "success"` in its metadata
2. All required metadata keys exist
3. Both the raw (`raw.json`) and processed (`cafes.csv`) artifacts exist and are readable

Failed or incomplete snapshots are ignored by listing and comparison — the existence of a snapshot directory alone never implies success.

### Snapshot Directory Structure

```text
data/
├── raw/
│   └── snapshots/
│       └── 2026-09-08T120000Z/
│           ├── raw.json
│           └── metadata.json
└── processed/
    └── snapshots/
        └── 2026-09-08T120000Z/
            ├── cafes.csv
            └── metadata.json
```

### Snapshot Metadata

Each snapshot carries a `metadata.json` with:

| Field | Description |
|-------|-------------|
| `snapshot_id` | Snapshot identifier |
| `retrieved_at_utc` | Actual retrieval timestamp (ISO 8601, UTC) |
| `source` | `OpenStreetMap` |
| `retrieval_method` | `Overpass API` |
| `endpoint` | Overpass API URL used |
| `query` | Overpass QL query used |
| `record_count` | Records in the finalized dataset |
| `raw_file` | Raw artifact filename |
| `processed_file` | Processed artifact filename |
| `status` | `success` (only successful snapshots are listed/compared) |

---

### Refresh Workflow

Standard pipeline behavior is unchanged:

```powershell
python -m cafe_finder.pipeline
```

The snapshot workflow is opt-in:

```powershell
python -m cafe_finder.pipeline --snapshot
```

What `--snapshot` does:

1. Generates a `snapshot_id` at refresh start
2. Records the previous successful snapshot (before the new one exists)
3. Fetches from Overpass; on success records the real `retrieved_at_utc` and saves the raw snapshot
4. Runs the existing clean → validate steps (no new quality thresholds — existing Phase 1/7 semantics apply)
5. Saves the processed snapshot (`cafes.csv` + metadata)
6. **Atomically promotes** the new dataset: writes a temp file, then replaces `data/processed/lucknow_cafes.csv` in one step
7. Compares the new dataset against the previous successful snapshot and prints the summary
8. Reports `Snapshot ID`, `Retrieved at (UTC)`, and `Compared with` in the pipeline summary

### Safe Refresh Guarantee

The current dataset `data/processed/lucknow_cafes.csv` is **never replaced until the new dataset has completed fetch, cleaning, validation, and snapshot saving**. If any step fails (network error, malformed response, cleaning failure), the pipeline exits and the current dataset remains untouched. Atomic promotion also protects against partial writes.

No new pass/fail quality thresholds were invented: the refresh follows the existing fetch/clean/validate rules and fails safely on the same conditions the existing pipeline treats as failures.

---

### Dataset Comparison

`compare.py` detects changes between two CSV datasets using `osm_id` as the stable record identity:

| Category | Meaning |
|----------|---------|
| **Added** | `osm_id` present in new dataset only |
| **Removed** | `osm_id` present in old dataset only |
| **Modified** | `osm_id` in both, with at least one tracked-field change |
| **Unchanged** | `osm_id` in both, all tracked fields equal |

Tracked fields: all 13 schema columns (`osm_id`, `name`, `latitude`, `longitude`, `street`, `housenumber`, `city`, `postcode`, `cuisine`, `opening_hours`, `website`, `phone`, `source`).

Missing-value comparison reuses the Phase 7 semantics (`quality.is_missing`): `None`, `NaN`, `""`, and whitespace-only values are equivalent to each other, while `0` / `0.0` / `False` are real values. Output is deterministic (sorted by `osm_id`, fields in schema order).

CLI:

```powershell
# Summary counts
python -m cafe_finder.compare old.csv new.csv

# Summary plus per-record field changes
python -m cafe_finder.compare old.csv new.csv --verbose
```

Example output:

```text
Dataset Comparison
------------------
Previous records: 33
Current records:  35

Added:      2
Removed:    0
Modified:   1
Unchanged:  32
```

Verbose mode additionally lists added/removed records and per-record `field: old -> new` changes (missing values shown as `(missing)`).

---

### Snapshot CLI

List successful snapshots (newest first):

```powershell
python -m cafe_finder.snapshot
```

Detailed metadata:

```powershell
python -m cafe_finder.snapshot --verbose
```

With no snapshots yet, the CLI reports `(no successful snapshots found)` rather than an empty or misleading listing.

---

### Important Limitations

- **Snapshot IDs have 1-second granularity** (`YYYY-MM-DDTHHMMSSZ`). A full refresh takes seconds, so collisions are not expected in practice, but two refreshes started within the same UTC second would share an identifier.
- **Comparison is CSV-based**: it operates on processed CSV datasets, not live OSM state. It reports dataset differences, not verified real-world openings/closings.
- **Live refresh requires network access** to the Overpass API. If the API is unreachable or returns an error, the refresh fails safely and the current dataset is preserved.
- **Phase 8 is not a scheduler**: refreshes are manual (`--snapshot`). No background workers, cron jobs, or cloud services are involved.

---

## Phase 9: Historical Change Analysis & Data Lineage

### Purpose

Phase 8 answers *"What changed between two snapshots?"* Phase 9 answers:

> **What changed over time, when did it change, and where did the information come from?**

Phase 9 is a lightweight, file-based, **read-only analysis layer** on top of the successful snapshots created by Phase 8. The source of truth remains the existing snapshot files. No database is used, no network calls are made, and snapshots are never modified.

```text
OpenStreetMap
    ↓
Overpass API
    ↓
Snapshot (Phase 8)
    ↓
Processed dataset
    ↓
Adjacent comparisons (Phase 8 semantics)
    ↓
Historical analysis (Phase 9)
```

### Historical Snapshot Chain

Analysis operates on **valid successful snapshots only** (Phase 8 validity: `status == "success"`, complete metadata, readable raw + processed artifacts). Failed, incomplete, or unreadable snapshots are ignored — never treated as historical inputs.

Snapshots are processed **chronologically, oldest → newest**. For snapshots `A → B → C → D`, every adjacent pair is compared (`A→B`, `B→C`, `C→D`) — never only `A→D` — so intermediate changes are preserved.

### First and Last Observation

For every `osm_id` observed, history records:

| Field | Meaning |
|-------|---------|
| `first_observed_snapshot` / `first_observed_at` | Earliest successful snapshot containing the ID (timestamp from that snapshot's metadata) |
| `last_observed_snapshot` / `last_observed_at` | Latest successful snapshot containing the ID |
| `snapshot_count` | Number of successful snapshots containing the ID |

Identity is `osm_id` only: same name with different IDs means different entities; different names with the same ID means one entity with a name change. Display uses the latest-known non-missing name, documented as display-only.

### No-Longer-Observed Semantics

A cafe present in an earlier snapshot but absent from a newer one is described as **no longer observed** (or **absent from snapshot**).

> Absence from an OSM snapshot does not prove that a cafe closed.

Disappearance from the dataset cannot establish real-world closure, and coordinate changes are never interpreted as physical relocation. A cafe that disappears and later reappears keeps a single continuous history entry.

> Historical analysis describes changes in the dataset, not guaranteed real-world changes.

### Field-Level Change History

Every modification between adjacent snapshots produces one structured record per changed field (`osm_id`, `snapshot_before`, `snapshot_after`, `changed_at`, `field`, `old_value`, `new_value`), where `changed_at` is the retrieval timestamp of `snapshot_after`. Missing-value handling reuses `quality.is_missing()`; missing→populated and populated→missing count as changes, while equivalent missing representations do not.

### Summary Counting Semantics

Summary counts are kept conceptually separate and documented as such:

- **Unique entities** — distinct `osm_id` values (`unique_cafes`)
- **Observation counts** — unique entities by presence: `added` (first seen after the earliest snapshot), `no_longer_observed` (last seen before the latest snapshot), `unchanged` (present in every snapshot, no changes)
- **Change counts** — `modified` entities (at least one field change)
- **Field-change events** — snapshot-to-snapshot field changes (`field_summary`, ordered by count descending then field ascending)

These categories may overlap (e.g. a cafe that appeared mid-history and later changed counts as both added and modified) and are never forced to sum to a single total.

### Lineage

`lineage.py` traces the analysis back to its origins from Phase 8 metadata: analysis type (`historical_change_analysis`), source (`OpenStreetMap`), retrieval method (`Overpass API`), every analyzed snapshot ID with retrieval timestamps, record counts, and raw/processed artifact references, plus `generated_at_utc` — the actual report-generation time, distinct from retrieval timestamps. Nothing is fabricated; missing lineage fails explicitly.

### CLI Commands

```powershell
# Historical summary (works with zero snapshots: zero-count summary, exit 0)
python -m cafe_finder.history

# Aggregate field-level changes
python -m cafe_finder.history --fields

# Single-cafe history (unknown ID: stderr error, exit 1)
python -m cafe_finder.history --osm-id <OSM_ID>

# Exports (parent directories created; missing values as literal "missing")
python -m cafe_finder.history --output <PATH>
python -m cafe_finder.history --changes-output <PATH>

# Snapshot reconstruction (invalid snapshot: stderr error, exit 1)
python -m cafe_finder.history --reconstruct --snapshot-id <SNAPSHOT_ID>
python -m cafe_finder.history --reconstruct --snapshot-id <SNAPSHOT_ID> --json
python -m cafe_finder.history --reconstruct --snapshot-id <SNAPSHOT_ID> --output <PATH>

# Historical quality evolution
python -m cafe_finder.history --quality
python -m cafe_finder.history --quality --json
python -m cafe_finder.history --quality --quality-output <PATH>

# Lineage report (zero snapshots: explicit error, exit 1)
python -m cafe_finder.lineage

# Lineage JSON export
python -m cafe_finder.lineage --output <PATH>
```

### Deterministic Behavior

Snapshots oldest→newest, entities by `osm_id` ascending, changes by (`snapshot_after`, `osm_id`, `field`). Repeated analysis over unchanged snapshots produces equivalent output; only report-generation timestamps differ.

### Limitations

- Analysis quality depends on snapshot history depth; a single snapshot yields observations but no changes.
- A snapshot whose processed CSV cannot be read is skipped with a warning (neighbors become adjacent).
- Within-snapshot duplicate `osm_id` values resolve last-row-wins, consistent with Phase 8 comparison.
- CSV type inference follows standard Pandas behavior (same as Phase 8 tooling).
- No schedulers, background workers, ML, databases, maps, or new dependencies.

---

## Phase 10: Data Contracts, Reproducibility & Pipeline Integrity

### Objective

Phase 10 adds **data contracts**, **manifest-based artifact integrity**, and **safe transactional promotion** to the snapshot pipeline. The goal is to make every refresh verifiable, auditable, and recoverable — while preserving all Phase 1–9 behavior.

```text
Fetch + Clean + Validate
       ↓
Schema validation (new)
       ↓
Artifact checksums (new)
       ↓
Draft manifest (new) → validate → write
       ↓
Backup current CSV (if exists)
       ↓
Atomic promotion (existing)
       ↓
Final manifest (new) → validate → write
       ↓
Cleanup draft/backup
       ↓
Verifiable snapshot
```

No AI, ML, databases, maps, schedulers, or new external dependencies are introduced.

---

### Schema Contract

**Schema Version:** 1

**Canonical Columns (13, exact order):**

| # | Column | Type Rules |
|---|--------|------------|
| 1 | `osm_id` | **Non-empty string**. Integers, floats, booleans, `None`, empty/whitespace strings **rejected**. No silent coercion. Valid: `node12345`, `way67890`. |
| 2 | `name` | String; missing allowed |
| 3 | `latitude` | Numerically coercible; range checks in Phase 7/10 validation |
| 4 | `longitude` | Numerically coercible; range checks in Phase 7/10 validation |
| 5 | `street` | String; missing allowed |
| 6 | `housenumber` | String; missing allowed |
| 7 | `city` | String; missing allowed |
| 8 | `postcode` | String; missing allowed |
| 9 | `cuisine` | String; missing allowed |
| 10 | `opening_hours` | String; missing allowed |
| 11 | `website` | String; missing allowed |
| 12 | `phone` | String; missing allowed |
| 13 | `source` | **Nullable string** — missing/empty/whitespace allowed; present non-string values rejected |

**Validation Output:**

```python
{
    "valid": bool,
    "schema_version": 1,
    "missing_columns": [...],
    "unexpected_columns": [...],
    "invalid_types": {"column": "reason", ...},
    "column_order_valid": bool
}
```

*Deterministic ordering*: `missing_columns` by canonical order, `unexpected_columns` alphabetical, `invalid_types` keys in canonical order.

**Coordinate range validation remains outside `schema.py`** (owned by Phase 7 `quality.py`).

---

### Manifest Contract

Two manifest types, two files, two validators.

| | Draft (`manifest.json.draft`) | Final (`manifest.json`) |
|---|---|---|
| **Status** | `"preparing"` | `"success"` |
| **`completed_at_utc`** | **Absent** | **Required** (ISO-8601 UTC) |
| **Validator** | `validate_manifest_draft()` | `validate_manifest()` |
| **Location** | `data/raw/snapshots/<id>/manifest.json.draft` | `data/raw/snapshots/<id>/manifest.json` |
| **Purpose** | Pre-promotion verification | Persisted success record |
| **Self-checksum** | **Never** | **Never** |

**Manifest Fields:**

```json
{
  "manifest_version": 1,
  "pipeline_name": "cafe_finder",
  "schema_version": 1,
  "status": "success",
  "snapshot_id": "2026-09-13T063235Z",
  "started_at_utc": "2026-09-13T06:32:35Z",
  "retrieved_at_utc": "2026-09-13T06:32:40Z",
  "completed_at_utc": "2026-09-13T06:32:41Z",
  "source": "OpenStreetMap",
  "retrieval_method": "Overpass API",
  "endpoint": "https://overpass-api.de/api/interpreter",
  "query": "[Overpass QL query]",
  "record_count": 33,
  "artifacts": [
    {"path": "data/raw/snapshots/.../raw.json", "sha256": "...", "size_bytes": 10240},
    {"path": "data/processed/snapshots/.../cafes.csv", "sha256": "...", "size_bytes": 20480}
  ],
  "schema": {
    "schema_version": 1,
    "columns": [...],
    "required": [...]
  }
}
```

**Rules:**
- Manifest **never contains its own checksum** (only artifact checksums).
- SHA-256: lowercase 64-char hex.
- Serialization: `json.dumps(sort_keys=True, indent=2)` for determinism.
- **Draft never contains `completed_at_utc`**.
- Final manifest written **once, atomically**, after promotion.

---

### Timestamp Semantics

| Timestamp | Captured At | Represents |
|-----------|-------------|------------|
| `started_at_utc` | Pipeline entry, before fetch | Pipeline start |
| `retrieved_at_utc` | After successful Overpass response | Data retrieval completion |
| `completed_at_utc` | After promotion + final manifest validation, before final manifest write | Finalization point |

> `completed_at_utc` records the finalization point after promotion and final-manifest validation, but before final cleanup operations.

---

### Transaction Sequence (Snapshot Mode)

```
1. started_at_utc = now()
2. snapshot_id = generate_snapshot_id() (collision: wait 1s, regenerate)
3. previous_snapshot_id = get_latest_snapshot()
4. Fetch Overpass
5. retrieved_at_utc = now() (after successful fetch)
6. save_raw_snapshot() → raw.json + metadata.json (status="success")
7. Clean + validate
8. valid_records = filter_valid_records()
9. save_processed_snapshot() → cafes.csv + metadata.json (both dirs, status="success")
10. schema.validate_schema(processed_df) → ABORT if invalid
11. sha256(raw.json), sha256(cafes.csv) → ABORT if fail
12. Build draft manifest (no completed_at_utc, status="preparing")
13. validate_manifest_draft() → ABORT if invalid
14. Write manifest.json.draft (atomic) → re-read validate → ABORT if fail
15. Backup check: if .bak exists → ABORT (manual cleanup required)
16. Backup current CSV (byte-for-byte) if exists
17. promote_csv_atomically() → if FAIL: restore backup (verified) or delete new CSV
18. completed_at_utc = now()
19. Build final manifest (draft + status="success" + completed_at_utc)
20. validate_manifest() → if invalid: rollback, write quarantine.json, ABORT
21. Write final manifest.json (atomic)
22. Cleanup: delete draft, delete backup (only after success confirmed)
23. Snapshot complete
```

**Failure branches preserve backup on failed/uncertain recovery. Backup deleted ONLY after confirmed successful restoration or confirmed successful finalization.**

---

### Explicit Quarantine Mechanism

A snapshot is **quarantined** only by explicit marker:

```text
data/raw/snapshots/<id>/quarantine.json
```

```json
{
  "snapshot_id": "2026-09-13T063235Z",
  "quarantined_at_utc": "2026-09-13T06:32:41Z",
  "reason": "final_manifest_invalid" | "final_manifest_write_failed",
  "details": {...}
}
```

- **Only** this marker causes quarantine.
- Missing final manifest **without** quarantine marker → `NO_MANIFEST`.
- Quarantine marker persists until manual cleanup.
- Not included in manifest checksums or artifact lists.

---

### Discovery vs Full Integrity Verification

| Function | Checks | Returns |
|----------|--------|---------|
| `load_snapshot_metadata()` (discovery) | metadata fields, status, artifacts exist, **final manifest exists + ID consistency, no quarantine** | metadata or `None` |
| `verify_snapshot()` (full integrity) | All 15 checks: manifest contract, sizes, checksums, schema, counts, ID consistency | `PASSED` / `QUARANTINED` / `INTEGRITY_FAILED` / `NO_MANIFEST` / `INCOMPLETE` / `SNAPSHOT_NOT_FOUND` / `RECOVERY_FAILED` |

Discovery **does not** compute checksums, validate schema, or verify counts.

---

### Authoritative Status Model (9 Public Statuses)

| Status | Meaning | Layer |
|--------|---------|-------|
| `NO_SNAPSHOTS` | No snapshot directories exist | Discovery |
| `NO_VALID_SNAPSHOTS` | Directories exist but none discoverable | Discovery |
| `SNAPSHOT_NOT_FOUND` | Requested ID directory missing | Discovery |
| `NO_MANIFEST` | Snapshot exists, no final manifest, no quarantine | Discovery/Integrity |
| `INCOMPLETE` | Required metadata/artifacts missing or malformed metadata | Discovery/Integrity |
| `QUARANTINED` | Explicit `quarantine.json` exists | Discovery/Integrity |
| `INTEGRITY_FAILED` | Checksums, sizes, schema, counts, IDs fail | Integrity |
| `PASSED` | All 15 checks pass | Integrity |
| `RECOVERY_FAILED` | Rollback cannot restore prior state | Transaction |

`FAILED` is **runtime-only** (in-process pipeline failure), not returned by `verify_snapshot()`.

**Precedence** (first match wins in `verify_snapshot`): `SNAPSHOT_NOT_FOUND` → `QUARANTINED` → `INCOMPLETE` → `NO_MANIFEST` → `INTEGRITY_FAILED` → `PASSED`. `NO_SNAPSHOTS`/`NO_VALID_SNAPSHOTS` only in `verify_latest()`.

---

### CLI: Integrity Verification

```powershell
python -m cafe_finder.integrity --help
python -m cafe_finder.integrity                    # Latest snapshot, human output
python -m cafe_finder.integrity --verbose          # + diagnostics
python -m cafe_finder.integrity --snapshot <ID>    # Targeted check
python -m cafe_finder.integrity --json             # JSON to stdout
python -m cafe_finder.integrity --output <PATH>    # Write to file
python -m cafe_finder.integrity --snapshot <ID> --json --output <PATH>
```

| Exit Code | Meaning |
|-----------|---------|
| 0 | `PASSED` |
| 1 | Any failure status |

---

### Reproducibility

- Identical inputs → equivalent logical records, same column order, same validation results, same checksums.
- **Timestamps are explicitly variable metadata** — not compared for byte-for-byte reproducibility.
- Deterministic ordering in validation error dictionaries and manifest serialization.

---

### Limitations & Manual Intervention Scenarios

| Scenario | Behavior |
|----------|----------|
| Existing `.bak` backup | Pipeline aborts; manual cleanup required |
| Failed backup restoration | `RECOVERY_FAILED`; backup preserved for manual intervention |
| Failed new-CSV deletion (no prior CSV) | `RECOVERY_FAILED`; new CSV remains |
| Crash during finalization | Snapshot quarantined; manual inspection needed |
| Stale `.draft` / `.bak` from crash | Not auto-deleted; reported in verbose diagnostics |
| Snapshot ID collision | Wait 1s, regenerate (1-second granularity) |

---

### File Changes

**New modules:**
- `src/cafe_finder/schema.py` — Schema definition + validation
- `src/cafe_finder/manifest.py` — Draft/final manifest + validation
- `src/cafe_finder/integrity.py` — SHA-256, verification, CLI

**Modified modules:**
- `src/cafe_finder/snapshot.py` — Added `manifest_file`, `manifest_draft_file`, `quarantine_file` paths; `load_snapshot_metadata()` checks manifest + quarantine
- `src/cafe_finder/pipeline.py` — Integrated schema validation, checksums, draft/final manifest, backup, rollback, quarantine

**Tests added:**
- `tests/test_schema.py`
- `tests/test_manifest.py`
- `tests/test_integrity.py`
- `tests/test_pipeline.py`

---

## Phase 11: Configuration Hardening & Portability

### Objective

Phase 11 hardens the project against environment and working-directory assumptions. All hardcoded data paths were replaced with a centralized configuration module.

### Configuration Module

All data and output paths are resolved through `src/cafe_finder/config.py`:

* **`CAFE_FINDER_DATA_DIR`** — Environment variable to override the data root directory. Defaults to `Path("data")`.
* **`DATA_DIR`** — Base data directory (derived from `CAFE_FINDER_DATA_DIR` or default).
* **`RAW_DIR`** — `DATA_DIR / "raw"`
* **`PROCESSED_DIR`** — `DATA_DIR / "processed"`
* **`SNAPSHOTS_RAW_DIR`** — `RAW_DIR / "snapshots"`
* **`SNAPSHOTS_PROCESSED_DIR`** — `PROCESSED_DIR / "snapshots"`
* **`DEFAULT_CSV_PATH`** — `Path("data/processed/lucknow_cafes.csv")`
* **`DEFAULT_OUTPUT_DIR`** — `Path("data/processed/visualizations")`

### Portability Behavior

* The project uses a `src/` package layout — installation via `pip install -e ".[test]"` makes `import cafe_finder` work from anywhere without `PYTHONPATH=src`.
* All modules import paths from `config` rather than hardcoding them.
* `CAFE_FINDER_DATA_DIR` can override the data root for different environments.
* Relative environment paths are resolved relative to the current working directory.
* Explicit CLI paths (`--csv-path`, `--output-dir`) retain their intended semantics regardless of configuration.

### Modules Updated

All modules that previously hardcoded `Path("data/...")` were updated to import from `config`:
`pipeline.py`, `integrity.py`, `analyze.py`, `search.py`, `quality.py`, `clean.py`, `fetch.py`, `validate.py`, `visualize.py`.

---

## Phase 12: Documentation & Provenance Polish

### Objective

Bring all documentation in line with the actual implementation. Verify every claim in README, `CHANGELOG.md`, `CONTRIBUTING.md`, `DATA_LICENSE.md`, and `LICENSE` against the codebase.

### Documentation Updates

* README verified against all 10 CLI commands, `pyproject.toml`, `ci.yml`, and `config.py`.
* Installation instructions use the packaging-based workflow (`pip install -e ".[test]"`).
* All 10 console commands documented: `cafe-finder-pipeline`, `cafe-finder-search`, `cafe-finder-quality`, `cafe-finder-history`, `cafe-finder-integrity`, `cafe-finder-analyze`, `cafe-finder-visualize`, `cafe-finder-snapshot`, `cafe-finder-lineage`, `cafe-finder-compare`.
* Configuration section documents `CAFE_FINDER_DATA_DIR` and path derivation.
* Portability section documents `src/` layout, packaging-based import, and configuration override.
* Data provenance documents OpenStreetMap/Overpass source with no fabrication guarantees.
* OSM/ODbL attribution preserved and clearly separated from MIT code licensing.
* `CONTRIBUTING.md` created with the actual development workflow.

---

* `CHANGELOG.md` created with factual phase history.