import logging
from decimal import Decimal
from apps.risk_management.prop_firm_models import PropFirmAccount
from apps.execution_engine.notifications import DiscordNotifier

logger = logging.getLogger(__name__)

class EvaluationManager:
    """
    Manages the lifecycle of Prop Firm evaluation phases.
    Auto-pauses accounts (is_active=False) when profit targets are hit or max drawdown is breached,
    protecting the account state while awaiting manual review or firm graduation.
    """

    def __init__(self):
        self.notifier = DiscordNotifier()

    def process_all_accounts(self):
        """
        Iterates over all active prop firm accounts and determines if they should be paused
        due to passing or failing their respective phases.
        """
        active_accounts = PropFirmAccount.objects.filter(is_active=True)
        for account in active_accounts:
            self._evaluate_account(account)

    def _evaluate_account(self, account: PropFirmAccount):
        """
        Check an individual account against its profit target and drawdown limits.
        """
        # 1. Check for Max Drawdown Breach (Failure)
        if account.check_compliance() is False:
            self._halt_account(
                account, 
                reason="FAILED: Max Drawdown or Daily Loss limit breached.", 
                new_phase="failed"
            )
            return

        # 2. Check for Profit Target Hit (Pass)
        if account.phase in ["evaluation", "verification"]:
            # Example: $50k account with 10% target needs $5k profit.
            # Total PNL must be >= $5k
            total_pnl = account.total_pnl
            profit_target = account.profit_target_amount
            
            # If target > 0, check if we hit or exceeded it
            if profit_target > 0 and total_pnl >= profit_target:
                pct_gained = (total_pnl / account.account_size) * Decimal("100")
                self._halt_account(
                    account,
                    reason=f"PASSED {account.phase.upper()}: Hit profit target! ({pct_gained:.2f}% / ${total_pnl:,.2f})",
                    new_phase=account.phase # keep phase the same until manual review graduates it to Verification/Funded
                )
                
    def _halt_account(self, account: PropFirmAccount, reason: str, new_phase: str):
        """
        Safely halts trading on the account and sends high-priority alerts.
        """
        logger.info(f"EvaluationManager halting {account.name}: {reason}")
        
        # Deactivate so the Strategy Runner and Allocator skip it
        account.is_active = False
        if new_phase != account.phase:
            account.phase = new_phase
            
        account.save()
        
        # Determine alert color
        is_pass = "PASSED" in reason
        color = 0x2ECC71 if is_pass else 0xE74C3C # Green or Red
        
        embed = {
            "title": f"🛑 ACCOUNT HALTED: {account.name}",
            "color": color,
            "description": reason,
            "fields": [
                {"name": "Current Equity", "value": f"${account.current_equity:,.2f}", "inline": True},
                {"name": "Total P&L", "value": f"${account.total_pnl:,.2f}", "inline": True},
                {"name": "Firm", "value": account.get_firm_display(), "inline": True},
            ],
            "footer": {"text": "Evaluation Engine"}
        }
        self.notifier._dispatch(embed)
