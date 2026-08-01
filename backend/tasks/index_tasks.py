"""
Index Management Celery Tasks
==============================
Scheduled jobs to automatically refresh NSE index constituents.

Schedule:
    - Daily at 02:30 AM IST (21:00 UTC previous day) — after NSE publishes updates
    - Weekly full validation on Sunday 03:00 AM IST
"""

import logging

from celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="tasks.index.refresh_all_indices")
def refresh_all_indices(self):
    """
    Daily task: Refresh all NSE index constituents from official NSE CSV sources.
    Runs at 02:30 AM IST to pick up any NSE constituent changes published after close.
    """
    task_id = self.request.id
    logger.info(f"[{task_id}] Starting daily index refresh for all indices")

    try:
        from services.index_management_service import IndexManagementService
        from database import sync_engine

        svc = IndexManagementService()
        results = []

        with sync_engine.begin() as conn:
            all_results = svc.refresh_all(conn)
            for r in all_results:
                results.append({
                    "index_name": r.index_name,
                    "status": r.status,
                    "matched_count": r.matched_count,
                    "missing_count": r.missing_count,
                    "coverage_pct": r.coverage_pct,
                    "added_count": r.added_count,
                    "removed_count": r.removed_count,
                })
                logger.info(
                    f"  {r.index_name}: status={r.status} "
                    f"matched={r.matched_count} missing={r.missing_count} "
                    f"coverage={r.coverage_pct}%"
                )

        success_count = sum(1 for r in results if r["status"] in ("success", "partial"))
        logger.info(f"[{task_id}] Index refresh complete: {success_count}/{len(results)} indices updated")
        return {"status": "complete", "results": results}

    except Exception as e:
        logger.error(f"[{task_id}] Index refresh failed: {e}")
        self.retry(exc=e, countdown=300, max_retries=2)


@celery_app.task(bind=True, name="tasks.index.refresh_single_index")
def refresh_single_index(self, index_name: str):
    """
    On-demand task: Refresh a single NSE index.
    Triggered by POST /api/indices/refresh with index_name specified.
    """
    task_id = self.request.id
    logger.info(f"[{task_id}] Refreshing index: {index_name}")

    try:
        from services.index_management_service import IndexManagementService
        from database import sync_engine

        svc = IndexManagementService()
        with sync_engine.begin() as conn:
            result = svc.refresh_index(index_name, conn)

        logger.info(
            f"[{task_id}] {index_name}: status={result.status} "
            f"matched={result.matched_count} missing={result.missing_count} "
            f"coverage={result.coverage_pct}%"
        )
        return {
            "status": result.status,
            "index_name": result.index_name,
            "matched_count": result.matched_count,
            "missing_count": result.missing_count,
            "coverage_pct": result.coverage_pct,
            "added_count": result.added_count,
            "removed_count": result.removed_count,
        }

    except Exception as e:
        logger.error(f"[{task_id}] refresh_single_index failed for {index_name}: {e}")
        self.retry(exc=e, countdown=60, max_retries=3)
