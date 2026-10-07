"""Integrity endpoints.

Exposes the repository's existing read-only integrity checks as JSON:
snapshot-manifest verification (:mod:`cafe_finder.integrity`), schema
validation (:mod:`cafe_finder.schema`), and artifact existence/readability
for the dataset file currently served by the API. No new checks are
invented here; unavailable information keeps its domain status (such as
NO_SNAPSHOTS) instead of being converted into a pass.
"""

from fastapi import APIRouter

from cafe_finder.config import DEFAULT_CSV_PATH
from cafe_finder.integrity import verify_artifact, verify_latest
from cafe_finder.schema import validate_schema
from ..dependencies import load_dataset
from ..schemas import (
    ArtifactVerification,
    IntegrityResponse,
    SchemaValidation,
    SnapshotIntegrity,
)
from ..serializers import to_jsonable

router = APIRouter()


@router.get("/integrity", response_model=IntegrityResponse)
def get_integrity() -> IntegrityResponse:
    """Return snapshot integrity, schema validation, and artifact checks."""
    df = load_dataset()
    snapshot_report = to_jsonable(verify_latest())
    schema_report = validate_schema(df)
    artifact_report = verify_artifact(DEFAULT_CSV_PATH, None, None)
    return IntegrityResponse(
        snapshot_integrity=SnapshotIntegrity(**snapshot_report),
        schema=SchemaValidation(**to_jsonable(schema_report)),
        artifact=ArtifactVerification(**to_jsonable(artifact_report)),
    )
