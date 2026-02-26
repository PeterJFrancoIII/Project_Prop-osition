from celery import shared_task
from apps.risk_management.prop_firm_models import PropFirmAccount
from apps.execution_engine.notifications import DiscordNotifier
from apps.risk_management.evaluation_engine import EvaluationManager
import logging

logger = logging.getLogger(__name__)

@shared_task
def sweep_drawdown_warnings():
    """
    Checks all active accounts for proximity to Max Total drawdown limits (e.g. >= 80% to max loss).
    Runs intraday to ensure we catch accounts before they blow up.
    Also natively evaluates challenge accounts to pause them if they hit the profit target.
    """
    accounts = PropFirmAccount.objects.filter(
        is_active=True, 
        phase__in=["evaluation", "verification", "funded"]
    )
    notifier = DiscordNotifier()
    
    for acc in accounts:
        # Check Total Drawdown
        total_dd = acc.total_drawdown_pct
        max_dd = acc.max_total_drawdown_pct
        
        if max_dd > 0:
            pct_to_max = (total_dd / max_dd) * 100
            if pct_to_max >= 80:
                logger.warning(f"Account {acc.name} is {pct_to_max:.1f}% to max drawdown. Sending alert.")
                notifier.send_drawdown_warning(acc, pct_to_max)

    # 2. Process Passing/Failing automation
    eval_manager = EvaluationManager()
    eval_manager.process_all_accounts()

@shared_task
def send_eod_portfolio_report():
    """
    Gathers all active accounts and sends an End-of-Day summary.
    Designed to be scheduled at 4:15 PM ET.
    """
    accounts = list(PropFirmAccount.objects.filter(is_active=True))
    notifier = DiscordNotifier()
    if accounts:
        notifier.send_eod_report(accounts)
    logger.info(f"EOD report sent for {len(accounts)} accounts.")
