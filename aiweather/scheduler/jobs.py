from datetime import datetime
from zoneinfo import ZoneInfo

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from ..config import Settings
from .refresh import RefreshService

logger: structlog.stdlib.BoundLogger = structlog.get_logger()


class WeatherScheduler:
    """Owns the APScheduler triggers and delegates the work to RefreshService."""

    def __init__(self, settings: Settings, refresh_service: RefreshService) -> None:
        """Initialize scheduler.

        Args:
            settings: Application settings
            refresh_service: Service that performs the actual refresh cycle
        """
        self.settings = settings
        self.refresh_service = refresh_service
        self.scheduler = AsyncIOScheduler(timezone=settings.scheduler.timezone)

    async def start(self) -> None:
        """Start the scheduler, kicking off an immediate refresh when cached data is stale."""
        tz = ZoneInfo(self.settings.scheduler.timezone)

        job = self.scheduler.add_job(
            self.refresh_service.try_refresh_weather,
            CronTrigger(
                minute=self.settings.scheduler.refresh_minute,
                timezone=tz,
            ),
            id="weather_refresh",
            max_instances=1,
            replace_existing=True,
        )

        if await self.refresh_service.needs_refresh():
            logger.info("refresh_immediately")
            job.modify(next_run_time=datetime.now(tz))

        self.scheduler.start()
        logger.info("scheduler_started")
        logger.info("scheduler_jobs", jobs=[job.next_run_time for job in self.scheduler.get_jobs()])

    async def stop(self) -> None:
        """Stop the scheduler."""
        self.scheduler.shutdown()
        logger.info("scheduler_stopped")
