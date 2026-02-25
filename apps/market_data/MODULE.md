# Market Data App

## Module Name & Location
`apps.market_data` — `/apps/market_data/`

## Purpose
Ingests, stores, and serves market price data (OHLCV bars, fundamentals) for strategies and backtesting.

## Responsibilities
- Store OHLCV price bars for stocks, futures, and crypto
- Ingest historical data from yfinance, Alpaca, and CCXT (Layer 1+)
- Provide real-time price feeds via WebSocket (Layer 2+)
- Store fundamental data: earnings, SEC filings, analyst ratings (Layer 1+)

## Boundaries
- Does NOT generate trade signals — only provides data
- Does NOT execute trades
- Does NOT make trading decisions

## Success Conditions
- OHLCV data is stored in a consistent schema across all asset classes
- Data is queryable by symbol, timeframe, and date range
- No data gaps in ingested historical series
