"""Main pipeline orchestration for Lucknow Cafe Finder data ingestion."""

import csv
import json
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from . import clean, compare, fetch, integrity, manifest, schema, snapshot, validate

from cafe_finder.config import DATA_DIR, RAW_DIR, PROCESSED_DIR

CSV_FIELDS = [
    "osm_id",
    "name",
    "latitude",
    "longitude",
    "street",
    "housenumber",
    "city",
    "postcode",
    "cuisine",
    "opening_hours",
    "website",
    "phone",
    "source",
]

RAW_JSON_PATH = RAW_DIR / "lucknow_cafes_raw.json"
CLEANED_JSON_PATH = RAW_DIR / "lucknow_cafes_cleaned.json"
PROCESSED_CSV_PATH = PROCESSED_DIR / "lucknow_cafes.csv"


def save_csv(records: list[dict[str, Any]], output_path: Path) -> None:
    """
    Save records to CSV file.

    Args:
        records: List of validated records
        output_path: Path to output CSV file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()

        for record in records:
            row = {field: record.get(field, "") for field in CSV_FIELDS}
            writer.writerow(row)


def promote_csv_atomically(records: list[dict[str, Any]], output_path: Path) -> None:
    """
    Write records to a temp file and atomically replace the target CSV.

    The existing dataset is only replaced once the new file is fully written,
    so a failure mid-write never corrupts the current dataset.

    Args:
        records: List of validated records
        output_path: Target CSV path
    """
    temp_path = output_path.with_name(f"{output_path.stem}.tmp{output_path.suffix}")
    save_csv(records, temp_path)
    temp_path.replace(output_path)


def run_pipeline(
    user_agent: str = fetch.DEFAULT_USER_AGENT,
    timeout: int = 30,
    snapshot_mode: bool = False,
) -> dict[str, Any]:
    """
    Run the complete data ingestion pipeline.

    Steps:
    1. Fetch raw data from Overpass API
    2. Save raw JSON
    3. Clean and deduplicate
    4. Validate
    5. Save processed CSV
    6. Print summary

    When snapshot_mode is enabled:
    - A timestamped snapshot (raw + processed + metadata) is created
    - A real UTC retrieval timestamp is recorded on successful fetch
    - The processed dataset is atomically promoted to the current CSV
    - The new dataset is compared against the latest successful snapshot

    Args:
        user_agent: User-Agent for Overpass API requests
        timeout: Request timeout in seconds
        snapshot_mode: Whether to create snapshots of this refresh

    Returns:
        Dictionary with pipeline statistics
    """
    pipeline_start = time.time()
    stats: dict[str, Any] = {}

    snapshot_id = None
    previous_snapshot_id = None
    retrieved_at_utc = None
    started_at_utc = None
    backup_existed = False
    original_csv_present = False
    backup_path = None

    if snapshot_mode:
        started_at_utc = datetime.now(timezone.utc).isoformat()
        snapshot_id = snapshot.generate_snapshot_id()
        # Collision handling: wait and regenerate if directory exists
        snapshots_raw_dir = Path("data/raw/snapshots")
        snapshots_raw_dir.mkdir(parents=True, exist_ok=True)
        while (snapshots_raw_dir / snapshot_id).exists():
            time.sleep(1)
            snapshot_id = snapshot.generate_snapshot_id()
        previous_snapshot_id = snapshot.get_latest_snapshot()
        print(f"\nSnapshot mode enabled (snapshot ID: {snapshot_id})")

    print("=" * 50)
    print("Lucknow Cafe Finder - Data Ingestion Pipeline")
    print("=" * 50)

    print("\n[1/5] Fetching data from OpenStreetMap...")
    fetch_start = time.time()
    try:
        raw_records = fetch.fetch_lucknow_cafes(user_agent=user_agent, timeout=timeout)
    except Exception as e:
        print(f"  ERROR: Failed to fetch data: {e}")
        sys.exit(1)

    if snapshot_mode:
        retrieved_at_utc = datetime.now(timezone.utc).isoformat()
        query = fetch.build_overpass_query(*fetch.LUCKNOW_BBOX)
        snapshot.save_raw_snapshot(
            records=raw_records,
            snapshot_id=snapshot_id,
            retrieved_at_utc=retrieved_at_utc,
            query=query,
        )
        stats["retrieved_at_utc"] = retrieved_at_utc

    fetch_time = time.time() - fetch_start
    stats["fetch_time_seconds"] = round(fetch_time, 1)
    stats["total_fetched"] = len(raw_records)
    print(f"  Fetched {len(raw_records)} records in {fetch_time:.1f}s")
    if retrieved_at_utc:
        print(f"  Retrieved at (UTC): {retrieved_at_utc}")

    print("\n[2/5] Saving raw data...")
    fetch.save_raw_data(raw_records, RAW_JSON_PATH)
    print(f"  Saved to {RAW_JSON_PATH}")

    print("\n[3/5] Cleaning and deduplicating...")
    clean_start = time.time()
    cleaned_records, clean_stats = clean.clean_records(raw_records)
    clean_time = time.time() - clean_start
    stats["clean_time_seconds"] = round(clean_time, 1)
    stats.update(clean_stats)
    print(f"  Input: {clean_stats['input_count']}")
    print(f"  Cleaned: {clean_stats['cleaned_count']}")
    print(f"  Discarded (no usable identity): {clean_stats['discarded_count']}")
    print(f"  Duplicates removed: {clean_stats['duplicates_removed']}")
    print(f"  Output: {clean_stats['output_count']}")

    with CLEANED_JSON_PATH.open("w", encoding="utf-8") as f:
        json.dump(cleaned_records, f, ensure_ascii=False, indent=2)
    print(f"  Saved cleaned data to {CLEANED_JSON_PATH}")

    print("\n[4/5] Validating...")
    validation_summary = validate.validate_dataset(cleaned_records)
    stats["valid_records"] = validation_summary["valid_records"]
    stats["invalid_records"] = validation_summary["invalid_records"]
    stats["records_with_warnings"] = validation_summary["records_with_warnings"]
    stats["duplicate_osm_ids"] = validation_summary["duplicate_osm_ids"]

    print(f"  Total: {validation_summary['total_records']}")
    print(f"  Valid: {validation_summary['valid_records']}")
    print(f"  Invalid: {validation_summary['invalid_records']}")
    print(f"  Warnings: {validation_summary['records_with_warnings']}")
    if validation_summary["duplicate_osm_ids"]:
        print(f"  Duplicate OSM IDs: {len(validation_summary['duplicate_osm_ids'])}")
    if validation_summary["errors_by_type"]:
        print("  Errors:")
        for error, count in sorted(validation_summary["errors_by_type"].items(), key=lambda x: -x[1]):
            print(f"    {count}x: {error}")

    valid_records = validate.filter_valid_records(cleaned_records)

    print("\n[5/5] Saving processed CSV...")
    if snapshot_mode and snapshot_id and retrieved_at_utc:
        processed_df = pd.DataFrame(valid_records)[CSV_FIELDS]
        query = fetch.build_overpass_query(*fetch.LUCKNOW_BBOX)
        snapshot_paths = snapshot.get_snapshot_paths(snapshot_id)
        snapshot.save_processed_snapshot(
            df=processed_df,
            snapshot_id=snapshot_id,
            retrieved_at_utc=retrieved_at_utc,
            query=query,
        )
        print(f"  Snapshot processed CSV saved to {snapshot_paths['processed_file']}")

        # Phase 10: Schema validation
        print("  Validating processed schema...")
        schema_result = schema.validate_schema(processed_df)
        if not schema_result["valid"]:
            print("  ERROR: Schema validation failed", file=sys.stderr)
            sys.exit(1)
        print("  Schema validation: PASSED")

        # Phase 10: Calculate artifact checksums
        print("  Calculating artifact checksums...")
        raw_sha = integrity.sha256_file(snapshot_paths["raw_file"])
        processed_sha = integrity.sha256_file(snapshot_paths["processed_file"])

        # Phase 10: Build and validate draft manifest
        print("  Building draft manifest...")
        artifacts = [
            manifest.compute_artifact_entry(snapshot_paths["raw_file"], f"data/raw/snapshots/{snapshot_id}/raw.json"),
            manifest.compute_artifact_entry(snapshot_paths["processed_file"], f"data/processed/snapshots/{snapshot_id}/cafes.csv"),
        ]
        draft = manifest.build_manifest_draft(
            snapshot_id=snapshot_id,
            started_at_utc=started_at_utc,
            retrieved_at_utc=retrieved_at_utc,
            endpoint=fetch.OVERPASS_URL,
            query=query,
            record_count=len(valid_records),
            artifacts=artifacts,
            schema_result=schema_result,
        )
        draft_validation = manifest.validate_manifest_draft(draft)
        if not draft_validation["valid"]:
            print("  ERROR: Draft manifest validation failed", file=sys.stderr)
            for error in draft_validation["errors"]:
                print(f"  {error}", file=sys.stderr)
            sys.exit(1)
        print("  Draft manifest validation: PASSED")

        # Phase 10: Write draft manifest
        manifest_draft_path = snapshot_paths["manifest_draft_file"]
        manifest.write_manifest(draft, manifest_draft_path)
        # Re-read and validate
        try:
            manifest.load_manifest(manifest_draft_path)
            manifest.validate_manifest_draft(draft)
        except Exception as e:
            print(f"  ERROR: Draft manifest write/read validation failed: {e}", file=sys.stderr)
            manifest_draft_path.unlink(missing_ok=True)
            sys.exit(1)
        print("  Draft manifest written and validated")

        # Phase 10: Backup check
        backup_path = PROCESSED_CSV_PATH.with_suffix(".csv.bak")
        if backup_path.exists():
            print("  ERROR: Backup already exists — possible prior recovery artifact requires manual inspection", file=sys.stderr)
            snapshot_paths["manifest_draft_file"].unlink(missing_ok=True)
            sys.exit(1)

        if PROCESSED_CSV_PATH.exists():
            shutil.copy2(PROCESSED_CSV_PATH, backup_path)
            backup_existed = True
            original_csv_present = True
        else:
            backup_existed = False
            original_csv_present = False

        # Phase 10: Promote CSV
        print("  Promoting CSV...")
        try:
            promote_csv_atomically(valid_records, PROCESSED_CSV_PATH)
        except Exception as e:
            print(f"  ERROR: CSV promotion failed: {e}", file=sys.stderr)
            snapshot_paths["manifest_draft_file"].unlink(missing_ok=True)
            if backup_existed:
                try:
                    expected_bytes = backup_path.read_bytes()
                    backup_path.replace(PROCESSED_CSV_PATH)
                    if PROCESSED_CSV_PATH.exists():
                        restored = PROCESSED_CSV_PATH.read_bytes()
                        if restored == expected_bytes:
                            print("  Promotion failed; previous CSV restored successfully.")
                        else:
                            print("  RECOVERY_FAILED: Restored CSV does not match backup", file=sys.stderr)
                except Exception as restore_e:
                    print(f"  RECOVERY_FAILED: Restore failed: {restore_e}", file=sys.stderr)
            sys.exit(1)

        # Phase 10: Final manifest
        completed_at_utc = datetime.now(timezone.utc).isoformat()
        final_manifest = manifest.build_manifest(draft, completed_at_utc)
        final_validation = manifest.validate_manifest(final_manifest)
        if not final_validation["valid"]:
            print("  ERROR: Final manifest validation failed", file=sys.stderr)
            for error in final_validation["errors"]:
                print(f"  {error}", file=sys.stderr)
            # Rollback
            snapshot_paths["manifest_draft_file"].unlink(missing_ok=True)
            if backup_existed:
                try:
                    expected_bytes = backup_path.read_bytes()
                    backup_path.replace(PROCESSED_CSV_PATH)
                    if PROCESSED_CSV_PATH.exists():
                        restored = PROCESSED_CSV_PATH.read_bytes()
                        if restored == expected_bytes:
                            print("  Final manifest invalid; previous CSV restored successfully.")
                        else:
                            print("  RECOVERY_FAILED: Restored CSV does not match backup", file=sys.stderr)
                except Exception as restore_e:
                    print(f"  RECOVERY_FAILED: Restore failed: {restore_e}", file=sys.stderr)
            else:
                try:
                    PROCESSED_CSV_PATH.unlink()
                    if not PROCESSED_CSV_PATH.exists():
                        print("  Final manifest invalid; original CSV absence restored.")
                    else:
                        print("  RECOVERY_FAILED: Could not delete new CSV", file=sys.stderr)
                except Exception:
                    print("  RECOVERY_FAILED: Could not delete new CSV", file=sys.stderr)
            # Write quarantine
            quarantine_path = snapshot_paths["quarantine_file"]
            quarantine_path.write_text(json.dumps({
                "snapshot_id": snapshot_id,
                "quarantined_at_utc": datetime.now(timezone.utc).isoformat(),
                "reason": "final_manifest_invalid",
                "details": {"errors": final_validation["errors"]}
            }, indent=2))
            sys.exit(1)

        # Phase 10: Write final manifest
        manifest_path = snapshot_paths["manifest_file"]
        manifest.write_manifest(final_manifest, manifest_path)

        # Phase 10: Cleanup
        snapshot_paths["manifest_draft_file"].unlink(missing_ok=True)
        if backup_existed:
            backup_path.unlink(missing_ok=True)

        promote_csv_atomically(valid_records, PROCESSED_CSV_PATH)
        print(f"  Atomically promoted snapshot to {PROCESSED_CSV_PATH}")
        stats["snapshot_id"] = snapshot_id
    else:
        save_csv(valid_records, PROCESSED_CSV_PATH)

    stats["csv_records"] = len(valid_records)
    print(f"  Saved {len(valid_records)} records to {PROCESSED_CSV_PATH}")

    if snapshot_mode and snapshot_id and previous_snapshot_id:
        print("\n[COMPARE] Comparing against previous snapshot...")
        try:
            previous_paths = snapshot.get_snapshot_paths(previous_snapshot_id)
            previous_df = pd.read_csv(previous_paths["processed_file"], encoding="utf-8")
            result = compare.compare_datasets(previous_df, processed_df)
            print(compare.format_comparison(result))
            stats["comparison"] = {
                "old_snapshot_id": previous_snapshot_id,
                "new_snapshot_id": snapshot_id,
                "old_record_count": result["old_record_count"],
                "new_record_count": result["new_record_count"],
                "added": len(result["added"]),
                "removed": len(result["removed"]),
                "modified": len(result["modified"]),
                "unchanged": len(result["unchanged"]),
            }
        except Exception as e:
            print(f"  WARNING: Could not compare with previous snapshot: {e}")

    total_time = time.time() - pipeline_start
    stats["total_time_seconds"] = round(total_time, 1)

    print("\n" + "=" * 50)
    print("PIPELINE SUMMARY")
    print("=" * 50)
    print(f"Total fetched:        {stats['total_fetched']}")
    print(f"Valid records:        {stats['valid_records']}")
    print(f"Invalid records:      {stats['invalid_records']}")
    print(f"Duplicates removed:   {stats['duplicates_removed']}")
    print(f"Discarded (no ID):    {stats['discarded_count']}")
    print(f"CSV records written:  {stats['csv_records']}")
    if snapshot_mode:
        print(f"Snapshot ID:          {snapshot_id}")
        print(f"Retrieved at (UTC):   {retrieved_at_utc}")
        if previous_snapshot_id:
            print(f"Compared with:        {previous_snapshot_id}")
    print(f"Total time:           {stats['total_time_seconds']:.1f}s")
    print("=" * 50)

    return stats


def main() -> None:
    """Command-line entry point for the pipeline."""
    import argparse

    parser = argparse.ArgumentParser(description="Lucknow Cafe Finder Data Pipeline")
    parser.add_argument(
        "--user-agent",
        default=fetch.DEFAULT_USER_AGENT,
        help="User-Agent header for Overpass API requests",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Request timeout in seconds",
    )
    parser.add_argument(
        "--snapshot",
        action="store_true",
        help="Create a timestamped snapshot of this refresh (raw + processed + metadata)",
    )
    args = parser.parse_args()

    try:
        run_pipeline(user_agent=args.user_agent, timeout=args.timeout, snapshot_mode=args.snapshot)
    except KeyboardInterrupt:
        print("\nPipeline interrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"\nPipeline failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()