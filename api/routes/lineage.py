"""Lineage endpoint.

Thin read-only adapter over :mod:`cafe_finder.lineage`. Historical
lineage can only be established from successful snapshots; when none
exist the domain raises :class:`LineageError`, which this route reports
honestly as an unavailable lineage instead of inventing stages.
"""

from fastapi import APIRouter

from cafe_finder.lineage import LineageError, generate_lineage
from ..schemas import LineageReport, LineageResponse
from ..serializers import to_jsonable

router = APIRouter()


@router.get("/lineage", response_model=LineageResponse)
def get_lineage() -> LineageResponse:
    """Return historical-analysis lineage, or its honest absence."""
    try:
        report = generate_lineage()
    except LineageError as exc:
        return LineageResponse(available=False, report=None, reason=str(exc))
    return LineageResponse(
        available=True, report=LineageReport(**to_jsonable(report)), reason=None
    )
