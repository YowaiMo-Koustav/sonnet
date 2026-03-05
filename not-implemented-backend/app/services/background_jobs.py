"""Background job scheduler for periodic tasks."""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.services.scheme_service import SchemeService

logger = logging.getLogger(__name__)


class BackgroundJobScheduler:
    """Manages scheduled background jobs for the application."""
    
    def __init__(self):
        """Initialize the background job scheduler."""
        self.scheduler = BackgroundScheduler()
        self._setup_jobs()
    
    def _setup_jobs(self):
        """Set up all scheduled jobs."""
        # Daily job to mark expired schemes as CLOSED
        # Runs every day at 00:00 (midnight)
        self.scheduler.add_job(
            func=self._mark_expired_schemes_job,
            trigger=CronTrigger(hour=0, minute=0),
            id='mark_expired_schemes',
            name='Mark expired schemes as CLOSED',
            replace_existing=True
        )
        logger.info("Background jobs configured successfully")
    
    def _mark_expired_schemes_job(self):
        """
        Job to mark expired schemes as CLOSED.
        
        This job runs daily and updates all schemes with past deadlines
        to have a status of CLOSED.
        
        Requirements: 8.5
        """
        db: Session = SessionLocal()
        try:
            scheme_service = SchemeService(db)
            count = scheme_service.mark_expired_schemes_as_closed()
            logger.info(f"Marked {count} expired schemes as CLOSED")
        except Exception as e:
            logger.error(f"Error marking expired schemes: {str(e)}", exc_info=True)
        finally:
            db.close()
    
    def start(self):
        """Start the background job scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Background job scheduler started")
    
    def shutdown(self):
        """Shutdown the background job scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Background job scheduler stopped")
    
    def run_job_now(self, job_id: str):
        """
        Manually trigger a job to run immediately.
        
        Args:
            job_id: ID of the job to run
            
        Useful for testing or manual execution.
        """
        job = self.scheduler.get_job(job_id)
        if job:
            job.func()
            logger.info(f"Manually executed job: {job_id}")
        else:
            logger.warning(f"Job not found: {job_id}")


# Global scheduler instance
_scheduler_instance = None


def get_scheduler() -> BackgroundJobScheduler:
    """Get or create the global scheduler instance."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = BackgroundJobScheduler()
    return _scheduler_instance
