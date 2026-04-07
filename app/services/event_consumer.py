#!/usr/bin/env python
"""
Event Consumer Service
Runs as a background service to consume and process domain events in real-time.

This can be run as:
1. Part of the main API process
2. Separate worker process
3. Multiple scaled workers
"""

import asyncio
import logging
import signal
import sys
from typing import Optional

from app.config import get_settings
from app.database import init_db
from app.services.event_bus import event_bus
from app.services.event_handlers import *  # Import all handlers

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EventConsumerService:
    """
    Main event consumer service that processes domain events.
    """

    def __init__(self):
        self.settings = get_settings()
        self.running = False
        self.tasks = []

    async def start(self):
        """Start the event consumer service."""
        logger.info("Starting Event Consumer Service...")

        # Initialize database
        init_db()

        # Connect to Redis event bus
        redis_url = self.settings.redis_url or "redis://localhost:6379"
        event_bus.redis_url = redis_url
        await event_bus.connect()

        # Start consuming events
        self.running = True

        # Create consumer task
        consumer_task = asyncio.create_task(event_bus.start_consumer())
        self.tasks.append(consumer_task)

        # Create monitoring task
        monitor_task = asyncio.create_task(self._monitor_events())
        self.tasks.append(monitor_task)

        # Create health check task
        health_task = asyncio.create_task(self._health_check())
        self.tasks.append(health_task)

        logger.info("Event Consumer Service started successfully")

        # Wait for all tasks
        try:
            await asyncio.gather(*self.tasks)
        except asyncio.CancelledError:
            logger.info("Event Consumer Service shutting down...")

    async def stop(self):
        """Stop the event consumer service gracefully."""
        logger.info("Stopping Event Consumer Service...")
        self.running = False

        # Stop event bus consumer
        await event_bus.stop_consumer()

        # Cancel all tasks
        for task in self.tasks:
            task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*self.tasks, return_exceptions=True)

        # Disconnect from Redis
        await event_bus.disconnect()

        logger.info("Event Consumer Service stopped")

    async def _monitor_events(self):
        """Monitor event processing and log metrics."""
        while self.running:
            try:
                # Get metrics every 60 seconds
                await asyncio.sleep(60)

                metrics = await event_bus.get_metrics()

                logger.info("Event Processing Metrics:")
                logger.info(f"  Total events processed: {sum(int(v) for v in metrics['event_counts'].values())}")

                for event_type, count in metrics['event_counts'].items():
                    logger.info(f"  - {event_type}: {count} events")

                # Check for stale event types (no events in 24 hours)
                from datetime import datetime, timezone, timedelta
                now = datetime.now(timezone.utc)

                for event_type, last_seen_str in metrics['last_seen'].items():
                    if last_seen_str:
                        last_seen = datetime.fromisoformat(last_seen_str)
                        if (now - last_seen) > timedelta(hours=24):
                            logger.warning(f"No {event_type} events in 24+ hours")

            except Exception as e:
                logger.error(f"Error monitoring events: {e}")

    async def _health_check(self):
        """Perform health checks on the event processing system."""
        while self.running:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds

                # Check Redis connection
                await event_bus.redis.ping()

                # Check for stuck messages (would implement xpending in production)
                # pending = await event_bus.redis.xpending(...)

            except Exception as e:
                logger.error(f"Health check failed: {e}")
                # In production, this would alert monitoring systems


def handle_shutdown(signame):
    """Handle shutdown signals gracefully."""
    logger.info(f"Received {signame}, initiating graceful shutdown...")
    asyncio.create_task(consumer.stop())


async def main():
    """Main entry point for the event consumer."""
    global consumer
    consumer = EventConsumerService()

    # Setup signal handlers for graceful shutdown
    loop = asyncio.get_running_loop()
    for signame in {'SIGTERM', 'SIGINT'}:
        if hasattr(signal, signame):
            loop.add_signal_handler(
                getattr(signal, signame),
                lambda: handle_shutdown(signame)
            )

    # Start the consumer
    try:
        await consumer.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        await consumer.stop()


if __name__ == "__main__":
    # Run the event consumer
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Event Consumer Service terminated")
        sys.exit(0)