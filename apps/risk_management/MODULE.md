# Risk Management App

## Module Name & Location
`apps.risk_management` — `/apps/risk_management/`

## Purpose
Enforces pre-trade risk checks and account-level safety limits to prevent catastrophic losses.

## Responsibilities
- Define configurable risk parameters per account (max drawdown, position size, daily loss)
- Run pre-trade risk checks before every order submission
- Maintain kill switch capability (halt all trading instantly)
- Log every risk decision (approved or rejected) with reason
- Enforce prop firm-specific rules (trailing drawdown, max contracts, consistency) in Layer 1+

## Boundaries
- Does NOT execute trades — only approves or rejects
- Does NOT generate signals — only evaluates them
- Does NOT manage broker connections

## Success Conditions
- No trade is ever submitted without passing a risk check
- Kill switch halts all trading within 1 second
- Every risk decision is logged permanently (per data governance)
