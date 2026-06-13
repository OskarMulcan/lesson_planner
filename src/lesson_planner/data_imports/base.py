from __future__ import annotations

import csv
import logging
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import NamedTuple, Callable, Type, List, Any, TypeVar, Optional

from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from ..models import ImportStaging

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class ImportStatus(str, Enum):
    pending = "pending"
    imported = "imported"
    skipped = "skipped"
    failed = "failed"

class ImportHandler(NamedTuple):
    row_model: Type[BaseModel]
    upsert_fn: Callable[[Session, Any], ImportStatus]


@dataclass
class RowResult:
    row_number: int
    status: ImportStatus
    detail: Optional[str] = None


def _insert_staging(session: Session, session_id: uuid.UUID, target_table: str, row_number: int, raw_data: dict) -> None:
    staging = ImportStaging(
        session_id=session_id,
        target_table=target_table,
        row_number=row_number,
        raw_data=raw_data,
        status=ImportStatus.pending.value,
    )
    session.add(staging)


def _update_staging_failure(session: Session, session_id: uuid.UUID, target_table: str, row_number: int, detail: str) -> None:
    session.query(ImportStaging).filter_by(
        session_id=session_id, target_table=target_table, row_number=row_number
    ).update({"status": ImportStatus.failed.value, "error_detail": detail})


def _update_staging_status(session: Session, session_id: uuid.UUID, target_table: str, row_number: int, status: ImportStatus) -> None:
    session.query(ImportStaging).filter_by(
        session_id=session_id, target_table=target_table, row_number=row_number
    ).update({"status": status.value})


def run_import(
    session: Session,
    path: Path,
    target_table: str,
    row_model: type[BaseModel],
    upsert_fn: Callable[[Session, Any], ImportStatus],
) -> List[RowResult]:
    """Run a CSV import into the database with staging and validation.

    Args:
        session: SQLAlchemy session
        path: Path to CSV file
        target_table: Logical name of the target table for ImportStaging.target_table
        row_model: Pydantic model class used to validate each CSV row
        upsert_fn: Callable that upserts a validated row into the DB and returns ImportStatus

    Returns:
        List of RowResult objects describing per-row outcomes
    """
    results: List[RowResult] = []
    session_id = uuid.uuid4()

    with path.open("r", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        headers = next(reader, None)
        if headers is None:
            return results

        for idx, row in enumerate(reader, start=1):
            row_dict = {h: v for h, v in zip(headers, row)}
            try:
                _insert_staging(session, session_id, target_table, idx, row_dict)
                try:
                    validated = row_model(**row_dict)
                except ValidationError as ve:
                    detail = str(ve)
                    _update_staging_failure(session, session_id, target_table, idx, detail)
                    results.append(RowResult(row_number=idx, status=ImportStatus.failed, detail=detail))
                    continue

                try:
                    status = upsert_fn(session, validated)
                    if not isinstance(status, ImportStatus):
                        status = ImportStatus.imported
                    _update_staging_status(session, session_id, target_table, idx, status)
                    results.append(RowResult(row_number=idx, status=status))
                except Exception as exc:  # pragma: no cover
                    logger.exception("Unexpected error during upsert for %s row %s: %s", target_table, idx, exc)
                    detail = str(exc)
                    _update_staging_failure(session, session_id, target_table, idx, detail)
                    results.append(RowResult(row_number=idx, status=ImportStatus.failed, detail=detail))
            except Exception as exc:  # pragma: no cover
                logger.exception("Failed to insert staging for %s row %s: %s", target_table, idx, exc)
                results.append(RowResult(row_number=idx, status=ImportStatus.failed, detail=str(exc)))

    session.commit()
    deleted = session.query(ImportStaging).filter_by(session_id=session_id).delete(synchronize_session=False)
    session.commit()
    logger.debug("Deleted %s import staging rows for session %s", deleted, session_id)
    return results


def log_summary(results: List[RowResult], target_table: str) -> None:
    """Log a one-line summary and details of failed rows.

    Args:
        results: List of RowResult produced by run_import
        target_table: Logical target table name for logging
    """
    imported = sum(1 for r in results if r.status == ImportStatus.imported)
    skipped = sum(1 for r in results if r.status == ImportStatus.skipped)
    failed = sum(1 for r in results if r.status == ImportStatus.failed)
    total = len(results)

    logger.info(
        "Import complete for %s: %s imported, %s skipped, %s failed, %s total",
        target_table,
        imported,
        skipped,
        failed,
        total,
    )

    for r in results:
        if r.status == ImportStatus.failed:
            logger.warning("Row %s failed: %s", r.row_number, r.detail)
