"""
ingestion/main.py — ECS task entry point for the Ingestion service.

Purpose:
    Entry point for the ingestion ECS task. Receives an ingestion job ID,
    reads job details from the database, processes the document, and
    updates the job status.

Intended Usage:
    python -m ingestion.main --job-id <ingestion_job_id>

Execution Flow:
    1. Receive ingestion_job_id from command argument or environment variable.
    2. Read ingestion job details from the database (document_id, tenant schema).
    3. Update job status to 'in_progress'.
    4. Download the document from S3.
    5. Run the ingestion pipeline: Parse → Chunk → Embed → Store.
    6. Update the documents record with chunk_count, embedding_model, vector_index_path.
    7. Archive prior vector index to S3 under folder named with job ID.
    8. Update job status to 'success' (or 'failed' with error_message).

Notes:
    - The task exits after processing. It does not run as a long-lived service.
    - One vector index exists per client, rebuilt with all active documents.
"""

import argparse
import asyncio
import os
import sys

from shared.db.connection import close_pool, get_pool
from shared.utils.logging import get_logger

logger = get_logger("ingestion.main")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Minerva Ingestion ECS Task — processes a single document ingestion job."
    )
    parser.add_argument(
        "--job-id",
        dest="job_id",
        default=os.environ.get("INGESTION_JOB_ID"),
        help="UUID of the ingestion_jobs record to process. "
             "Falls back to the INGESTION_JOB_ID environment variable.",
    )
    return parser.parse_args()


async def _run(job_id: str) -> int:
    """Async execution wrapper. Returns 0 on success, 1 on failure."""
    logger.info(f"Ingestion task started — job_id={job_id}")

    # Eagerly initialise the connection pool so failures surface early
    await get_pool()

    # Import here to avoid circular imports at module load time
    from ingestion.services.ingestion_service import process_job

    try:
        success = await process_job(job_id)
        return 0 if success else 1
    finally:
        await close_pool()


def main() -> None:
    """CLI entry point."""
    args = _parse_args()

    if not args.job_id:
        logger.error(
            "No job ID provided. Pass --job-id <uuid> or set INGESTION_JOB_ID."
        )
        sys.exit(2)

    exit_code = asyncio.run(_run(args.job_id))
    logger.info(f"Ingestion task finished with exit code {exit_code}.")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
