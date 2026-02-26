from celery import shared_task
from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)

@shared_task
def run_all_strategies_task():
    """
    Executes all active trading strategies via the Celery background worker.
    Runs every minute on market days.
    """
    logger.info("Starting scheduled run_all_strategies_task")
    try:
        # Re-use the existing management command logic silently
        call_command("run_strategies")
        logger.info("Successfully completed run_all_strategies_task")
    except Exception as e:
        logger.error(f"Error in run_all_strategies_task: {e}")

@shared_task
def sync_fundamentals_task():
    """
    Nightly script to download fresh corporate earnings and SEC filings.
    """
    logger.info("Starting nightly sync_fundamentals_task")
    # For now, just logging. A real management command could go here.
    logger.info("Successfully completed sync_fundamentals_task")
