# Dashboard App

## Module Name & Location
`apps.dashboard` — `/apps/dashboard/`

## Purpose
Provides a real-time web dashboard for monitoring system activity, managing strategies, configuring risk, and viewing AI model status.

## Responsibilities
- Display system overview: active strategies, recent trades, P&L, account status
- Show trade history with filtering and search
- Present strategy configuration with ability to toggle and modify parameters
- Expose risk management controls including kill switch
- Show system health: broker connections, webhook activity, error rates
- Support HTMX-based dynamic updates without full page reloads

## Boundaries
- Does NOT execute trades — only displays and configures
- Does NOT directly call broker APIs — reads from models
- Does NOT modify trade records — trades are immutable

## Success Conditions
- Dashboard loads in < 1 second
- All system states are visible at a glance from the overview page
- Kill switch is accessible from every page
- Strategy parameters can be modified and saved without page reload
