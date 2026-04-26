from __future__ import annotations

import time
from app.core.config import settings
from app.core.logging import setup_logging
from app.db.session import SessionLocal
from app.workers.job_runner import JobRunner


def main() -> None:
    setup_logging()
    runner = JobRunner(worker_id=settings.worker_id)

    while True:
        with SessionLocal() as db:
            runner.recover_stale_jobs(db)
            job = runner.claim_next_job(db)
            if not job:
                time.sleep(settings.worker_poll_interval_seconds)
                continue
            runner.run_job(db, job)


if __name__ == "__main__":
    main()
