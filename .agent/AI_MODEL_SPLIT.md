# AI Development Tracking

This document tracks which AI models built which components of the Auto-Trader, allowing for easier auditing and targeted refactoring later.

## LAYER 0: Foundation
*Built by: Claude 3.5 Sonnet (Opus equivalent / previous sessions)*
- Django project setup, MongoDB integration, DRF setup
- Base Dashboard (HTMX, CSS design system, 10 view templates)
- TradingView webhook receiver (`/api/v1/webhooks/tradingview/`)
- Base Executor (stub, Alpaca client, basic Trade model)
- Initial Risk Checker (passthrough stub)
- Account configs and API key vault

## LAYER 1: Income Engine
*Built by: Claude 3.5 Sonnet / Gemini (prior session context)*
- Full Risk Checker (Kill switch, Market Hours, Drawdown, Loss Limit, Trade Count, Max Positions, Position Size)
- Prop Firm Manager (`PropFirmAccount` model, dashboard view, progress tracking)
- Cost Basis Tracking & Realized P&L in `executor.py`
- Sell-Above-Cost constraint in `risk_checker.py` (Arch Public principle)
- Live Alpaca Market Data integration (equity, open positions, health ping)
- Ingestion command `fetch_market_data.py`
- Test suites (`test_risk_management.py`, `test_integration.py`, `test_dashboard.py`)

## LAYER 2: Multi-Strategy Engine
*Built by: Gemini (Current Session - Experimental M37)*
- **Core Framework**: `BaseStrategy` abstract class, `Signal` data class (`apps/strategies/base.py`)
- **Technical Indicators**: 8 pure-Python indicators (SMA, EMA, RSI, BBands, Z-Score, ATR, MACD, VWAP) (`apps/strategies/indicators.py`)
- **Stock Strategies**: `MomentumBreakout` and `MeanReversion` implementations (`apps/strategies/*.py`)
- **Backtesting Engine**: Vectorized backtester with Sharpe/drawdown/win-rate metrics (`apps/market_data/management/commands/backtest.py`)
- **Strategy Runner**: Signal dispatch scanner (`apps/market_data/management/commands/run_strategies.py`)
- **Test Suite**: `test_strategies.py` covering indicators and logic
- **Multi-Account Routing**: `accounts` routing logic in `executor.py` mapped to PropFirmAccounts (Completed)

---
*Note: This split assumes components built prior to the current context window were built by the previous AI sessions (Opus/Sonnet framework), while all Layer 2 multi-strategy engine work was explicitly written by Gemini.*
