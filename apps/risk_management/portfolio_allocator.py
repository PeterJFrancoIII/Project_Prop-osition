import logging
from decimal import Decimal
from apps.dashboard.models import Strategy
from apps.risk_management.kelly_criterion import KellyCriterionEngine

logger = logging.getLogger(__name__)

class PortfolioAllocator:
    """
    Distributes total account equity across multiple concurrent strategies.
    Uses Expectancy/Performance-based weighting (Risk Parity principles) 
    or Equal-Weight fallback to prevent over-leveraging.
    """
    
    def __init__(self, total_equity: float | str | Decimal):
        self.total_equity = Decimal(str(total_equity))
        
    def get_strategy_allocations(self) -> dict[str, Decimal]:
        """
        Returns a dictionary mapping strategy_name to allocated_capital.
        """
        active_strats = list(Strategy.objects.filter(is_active=True))
        if not active_strats:
            return {}
            
        allocations = {}
        engine = KellyCriterionEngine()
        
        total_score = Decimal("0")
        strategy_scores = {}
        
        for strat in active_strats:
            score = Decimal("1.0") # Base score ensures every active strategy gets *some* capital
            
            # Fetch historical Kelly metrics to adjust allocation weights (Risk Parity / Momentum)
            perf = engine.get_historical_performance(strat.name)
            if perf:
                win_rate, avg_win, avg_loss = perf
                # Expected Value (Edge) per trade
                expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
                if expectancy > 0:
                    # Boost capital weight for strategies with a proven positive statistical edge
                    score += Decimal(str(expectancy))
            
            strategy_scores[strat.name] = score
            total_score += score
            
        # Normalize weights to 100% and apply allocations
        for strat_name, score in strategy_scores.items():
            weight = score / total_score
            allocated_capital = self.total_equity * weight
            allocations[strat_name] = allocated_capital
            logger.info(f"Allocator: {strat_name} assigned {float(weight)*100:.1f}% -> ${allocated_capital:,.2f}")
            
        return allocations
