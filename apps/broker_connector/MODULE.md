# Broker Connector App

## Module Name & Location
`apps.broker_connector` — `/apps/broker_connector/`

## Purpose
Manages broker/exchange API connections and executes orders on external platforms.

## Responsibilities
- Store and manage broker account configurations (Alpaca, CCXT, future brokers)
- Encrypt/decrypt API keys at rest using Fernet (AES-256)
- Provide a unified interface for order submission across brokers
- Track broker account status, connection health, and balances
- Handle order submission, fill tracking, and position queries

## Boundaries
- Does NOT decide what to trade — only executes orders received from the execution engine
- Does NOT perform risk checks — that is the risk_management app's responsibility
- Does NOT store trade history — trades are logged by the execution engine
- NEVER returns decrypted API keys in API responses (masked only)

## Success Conditions
- Orders are submitted to the correct broker via the correct API
- API keys are encrypted at rest and never appear in logs or responses
- Broker connection failures are caught and reported, never silently swallowed
