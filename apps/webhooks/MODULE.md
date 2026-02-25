# Webhooks App

## Module Name & Location
`apps.webhooks` — `/apps/webhooks/`

## Purpose
Receives, validates, and dispatches incoming TradingView webhook alerts.

## Responsibilities
- Accept HTTP POST from TradingView with trade signal payloads
- Validate webhook authentication token
- Deserialize and validate signal payloads via DRF serializers
- Log every incoming webhook event to MongoDB
- Dispatch validated signals to the execution engine

## Boundaries
- Does NOT execute trades — only validates and forwards signals
- Does NOT modify risk parameters
- Does NOT connect to brokers or exchanges directly

## Success Conditions
- Every valid webhook creates a `WebhookEvent` record and triggers execution
- Every invalid webhook returns appropriate HTTP error code and is logged
- No signal is forwarded without passing validation
