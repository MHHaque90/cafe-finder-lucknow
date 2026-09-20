# Data License and Attribution

## OpenStreetMap Data

This project contains datasets derived from **OpenStreetMap** contributor data.

### Source
- **Data source**: OpenStreetMap (`amenity=cafe` elements)
- **Retrieval method**: Overpass API (`https://overpass-api.de/api/interpreter`)
- **License**: Open Database License (ODbL) 1.0

### Attribution

> **This product includes data from OpenStreetMap contributors, licensed under ODbL 1.0.**
>
> https://www.openstreetmap.org/copyright

### What Is Covered by ODbL

The ODbL license applies to the **data** produced by this project, specifically:

- `data/raw/lucknow_cafes_raw.json` — raw OSM response data
- `data/raw/lucknow_cafes_cleaned.json` — cleaned OSM records
- `data/processed/lucknow_cafes.csv` — processed CSV dataset derived from OSM data
- Any snapshot artifacts in `data/raw/snapshots/` and `data/processed/snapshots/`

### What Is NOT Covered by ODbL

The ODbL license does **not** apply to:

- The Python source code in `src/cafe_finder/`
- The test suite in `tests/`
- The documentation in `README.md`
- Analysis code, visualization code, search code, ranking code
- CLI implementations
- Pipeline orchestration code

### ODbL Requirements

Under ODbL 1.0, users who redistribute the dataset must:

1. **Attribute** the data to OpenStreetMap contributors
2. **Keep the license notice** intact
3. **Share alike** any derived database under ODbL or a compatible license
4. **Produce and offer** a transparent copy of the database under ODbL

For more details, see: https://www.openstreetmap.org/copyright

---

**Code License**: MIT License (see `LICENSE` file)
**Data License**: Open Database License (ODbL) 1.0
