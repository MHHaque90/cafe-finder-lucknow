"""History, snapshot, and comparison endpoints.

Thin read-only adapters over :mod:`cafe_finder.snapshot`,
:mod:`cafe_finder.history`, :mod:`cafe_finder.compare`, and
:mod:`cafe_finder.integrity`. No snapshot is created here, no comparison
is computed here, and no history is reconstructed here — the routes only
validate identifiers, call domain functions, and serialize their outputs.
"""

from fastapi import APIRouter, HTTPException, Query

from cafe_finder.compare import compare_datasets
from cafe_finder.history import (
    SnapshotDataError,
    load_snapshot_dataframe,
    summarize_history,
)
from cafe_finder.integrity import verify_snapshot
from cafe_finder.snapshot import list_snapshots, load_snapshot_metadata
from ..schemas import (
    ComparisonResponse,
    HistoryResponse,
    SnapshotDetailResponse,
    SnapshotMetadata,
)
from ..serializers import to_jsonable

router = APIRouter()


@router.get("/history", response_model=HistoryResponse)
def get_history() -> HistoryResponse:
    """List successful snapshots newest-first plus the history summary."""
    snapshots = list_snapshots()
    summary = summarize_history(snapshots)
    return HistoryResponse(
        snapshots=[SnapshotMetadata(**to_jsonable(meta)) for meta in snapshots],
        summary=to_jsonable(summary),
    )


@router.get("/history/compare", response_model=ComparisonResponse)
def compare_snapshots(
    baseline: str = Query(description="Baseline snapshot identifier"),
    target: str = Query(description="Comparison snapshot identifier"),
) -> ComparisonResponse:
    """Compare two snapshots with the domain comparator.

    Both frames are loaded read-only; the backend computes the result.
    """
    if baseline == target:
        raise HTTPException(
            status_code=400,
            detail="baseline and target must be different snapshots",
        )
    try:
        old_df = load_snapshot_dataframe(baseline)
    except SnapshotDataError:
        raise HTTPException(status_code=404, detail=f"Unknown snapshot: {baseline}")
    try:
        new_df = load_snapshot_dataframe(target)
    except SnapshotDataError:
        raise HTTPException(status_code=404, detail=f"Unknown snapshot: {target}")
    result = compare_datasets(old_df, new_df)
    return ComparisonResponse(
        baseline=baseline,
        target=target,
        old_record_count=int(result["old_record_count"]),
        new_record_count=int(result["new_record_count"]),
        added=[to_jsonable(row.to_dict()) for row in result["added"]],
        removed=[to_jsonable(row.to_dict()) for row in result["removed"]],
        modified=to_jsonable(result["modified"]),
        unchanged=to_jsonable(result["unchanged"]),
        field_changes=to_jsonable(result["field_changes"]),
    )


@router.get("/history/{snapshot_id}", response_model=SnapshotDetailResponse)
def get_snapshot(snapshot_id: str) -> SnapshotDetailResponse:
    """Return one snapshot's recorded metadata plus its integrity verdict."""
    meta = load_snapshot_metadata(snapshot_id)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"Unknown snapshot: {snapshot_id}")
    verification = verify_snapshot(snapshot_id)
    return SnapshotDetailResponse(
        metadata=SnapshotMetadata(**to_jsonable(meta)),
        integrity_status=str(verification["status"]),
        integrity_errors=[str(error) for error in verification["errors"]],
    )
