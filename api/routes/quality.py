"""Structured data-quality endpoints.

Exposes :mod:`cafe_finder.quality` reports as JSON. The project
deliberately defines no aggregate quality score, so none is exposed:
completeness, coordinate validity, duplicates, per-record flags, and
provenance are reported separately, exactly as the domain computes them.
"""

from fastapi import APIRouter

from cafe_finder.config import DEFAULT_CSV_PATH
from cafe_finder.quality import (
    generate_provenance,
    generate_quality_report,
    generate_record_quality_flags,
)
from ..dependencies import load_dataset
from ..schemas import QualityRecordFlags, QualityResponse
from ..serializers import to_jsonable

router = APIRouter()


@router.get("/quality", response_model=QualityResponse)
def get_quality() -> QualityResponse:
    """Return the quality report, provenance, and per-record flags."""
    df = load_dataset()
    report = to_jsonable(generate_quality_report(df))
    provenance = to_jsonable(
        generate_provenance(df, source_file=str(DEFAULT_CSV_PATH))
    )
    flagged = generate_record_quality_flags(df)
    records = []
    for _, row in flagged.iterrows():
        converted_id = to_jsonable(row.get("osm_id"))
        records.append(
            QualityRecordFlags(
                osm_id=None if converted_id is None else str(converted_id),
                quality_flags=[str(flag) for flag in row.get("quality_flags", [])],
                quality_issue_count=int(row.get("quality_issue_count", 0)),
            )
        )
    return QualityResponse(report=report, provenance=provenance, records=records)
