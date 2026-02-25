# Execution Engine App

## Module Name & Location
`apps.execution_engine` — `/apps/execution_engine/`

## Purpose
Routes validated trade signals to the appropriate broker and logs every trade with full audit trail.

## Responsibilities
- Receive validated signals from the webhooks app
- Run pre-trade risk checks via the risk_management app
- Route orders to the correct broker connector
- Track order lifecycle (submitted → filled → partial → cancelled → rejected)
- Log every trade to MongoDB with full details (symbol, side, qty, fill price, cost basis, P&L)
- Provide trade history API endpoint

## Boundaries
- Does NOT generate trade signals — only executes them
- Does NOT manage broker connections — delegates to broker_connector
- Does NOT set risk parameters — consults risk_management only

## Success Conditions
- Every executed signal produces a `Trade` record with complete audit fields
- Failed orders are logged with error details, not silently dropped
- Trade history is queryable via API with pagination and filtering
