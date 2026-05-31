"""Lightweight local scheduler for MYH source monitoring."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass

from backend.app.source_monitor.service import SourceMonitorConfig, build_config_from_env, run_scheduled_check_once

logger = logging.getLogger(__name__)


@dataclass
class SourceMonitorScheduler:
    """Small stoppable scheduler based on a daemon thread."""

    config: SourceMonitorConfig
    stop_event: threading.Event
    thread: threading.Thread

    def stop(self) -> None:
        """Stop the scheduler thread."""
        self.stop_event.set()
        if self.thread.is_alive():
            self.thread.join(timeout=2)


def start_scheduler_if_enabled(config: SourceMonitorConfig | None = None) -> SourceMonitorScheduler | None:
    """Start the local source monitor when explicitly enabled by env vars."""
    config = config or build_config_from_env()
    if not config.monitor_enabled:
        return None

    stop_event = threading.Event()

    def loop() -> None:
        if config.run_on_startup:
            try:
                run_scheduled_check_once(config)
            except Exception:
                logger.exception("Scheduled startup source check failed.")
        while not stop_event.wait(config.interval_minutes * 60):
            try:
                run_scheduled_check_once(config)
            except Exception:
                logger.exception("Scheduled source check failed.")

    thread = threading.Thread(target=loop, name="myh-source-monitor", daemon=True)
    thread.start()
    logger.info("MYH source monitor scheduler started with %s minute interval.", config.interval_minutes)
    return SourceMonitorScheduler(config=config, stop_event=stop_event, thread=thread)
