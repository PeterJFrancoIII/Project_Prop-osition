import logging
from decimal import Decimal

logger = logging.getLogger(__name__)

class KellyCriterionEngine:
    """
    Adaptive Money Management Engine using the Kelly Criterion.
    Calculates the optimal fraction of the portfolio to risk per trade to maximize long-term growth.
    """

    def __init__(self, mode: str = "half"):
        """
        :param mode: 'full', 'half', or 'quarter'. Full is mathematically optimal but brutally volatile.
        """
        self.mode = mode.lower()
        if self.mode not in ["full", "half", "quarter"]:
            logger.warning(f"Invalid Kelly mode '{self.mode}'. Defaulting to 'half'.")
            self.mode = "half"

    def calculate_fraction(self, win_rate: float, average_win: float, average_loss: float) -> float:
        """
        Calculates the Kelly fraction.
        :param win_rate: Probability of winning a trade (0.0 to 1.0)
        :param average_win: The average profit per winning trade (positive number)
        :param average_loss: The average loss per losing trade (positive number)
        :return: Fraction of total equity to risk (0.0 to 1.0)
        """
        if win_rate <= 0 or win_rate >= 1:
            return 0.0
            
        if average_win <= 0 or average_loss <= 0:
            return 0.0

        win_prob = win_rate
        loss_prob = 1.0 - win_prob
        payoff_ratio = average_win / average_loss

        # Kelly Formula: f* = W - (L / R)
        # where f* is fraction to risk, W is win prob, L is loss prob, R is win/loss payoff ratio
        
        kelly_fraction = win_prob - (loss_prob / payoff_ratio)
        
        if kelly_fraction <= 0:
            # Strategies with negative edge mathematically dictate sitting in cash
            return 0.0

        # Apply scaling
        if self.mode == "half":
            kelly_fraction *= 0.5
        elif self.mode == "quarter":
            kelly_fraction *= 0.25

        # We generally never want to risk more than 20-30% on a single trade even if Kelly says so, 
        # but the risk checker enforces global maxes. Here we cap the theoretical fractional risk.
        return min(kelly_fraction, 1.0)

    def calculate_position_size(self, account_equity: Decimal, kelly_fraction: float, entry_price: Decimal, stop_loss_price: Decimal) -> float:
        """
        Translates a Kelly fraction into an actual share quantity based on the distance to stop loss.
        If no stop loss is provided, this doesn't work well (Kelly implies you know your risk).
        """
        if kelly_fraction <= 0 or entry_price <= 0 or stop_loss_price <= 0:
            return 0.0
            
        risk_per_share = abs(float(entry_price) - float(stop_loss_price))
        if risk_per_share == 0:
            return 0.0

        capital_to_risk = float(account_equity) * kelly_fraction
        
        shares = capital_to_risk / risk_per_share
        return shares

    def get_historical_performance(self, strategy_name: str, local_pnl_history: list[float] | None = None):
        """
        Retrieves historical performance for a given strategy to feed the Kelly formula.
        Returns a tuple: (win_rate, average_win, average_loss).
        If there are < 10 closed trades, returns None.
        """
        winning_trades: list[float] = []
        losing_trades: list[float] = []
        
        if local_pnl_history is not None:
            # Backtest mode
            for pnl in local_pnl_history:
                if pnl > 0:
                    winning_trades.append(pnl)
                elif pnl < 0:
                    losing_trades.append(abs(pnl))
        else:
            # Live DB mode
            from apps.execution_engine.models import Trade
            
            # We only care about SELLs that realized P&L
            trades = Trade.objects.filter(
                strategy=strategy_name, 
                status="filled", 
                side="sell"
            )
            
            for t in trades:
                pnl = float(t.realized_pnl)
                if pnl > 0:
                    winning_trades.append(pnl)
                elif pnl < 0:
                    losing_trades.append(abs(pnl))
                
        total_resolved = len(winning_trades) + len(losing_trades)
        
        # Need a statistically significant baseline (at least 10 outcomes)
        if total_resolved < 10:
            return None
            
        win_rate = len(winning_trades) / total_resolved
        avg_win = sum(winning_trades) / len(winning_trades) if winning_trades else 0.0
        avg_loss = sum(losing_trades) / len(losing_trades) if losing_trades else 0.0
        
        return win_rate, avg_win, avg_loss

