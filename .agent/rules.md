# .agent/rules — Proprietary Accounts Auto-Trader

> **This is a living document.** Update these rules every time the program is upgraded, refactored, or a new module is added. As the system grows toward a client-facing, sellable AI-driven prop trading platform, these rules ensure consistency, scalability, and production-readiness at every stage.

---

## 🔒 Safety Invariants

Hierarchy: **Safety > Speed, Accuracy > Coverage, Reliability > Novelty**

1. **Never hold client funds.** All trading is done via secure API connections to brokers/exchanges/prop firms. We NEVER custody assets.
2. **Never store API keys in plaintext.** All secrets use encrypted storage (env vars → vault in production).
3. **Every trade must pass the Risk Management module** before execution. No bypasses, no exceptions.
4. **Kill switch is always reachable.** Emergency halt must work even if the strategy engine is unresponsive.
5. **Fail closed.** On error, preserve last-known-good state. Never execute a trade during an error state.
6. **Never escalate risk under uncertainty.** If data is stale, conflicting, or missing — reduce position size or skip the trade.

---

## 📋 Governance & Change Control

### Single Source of Truth (SSOT)
- **GitHub:** `https://github.com/PeterJFrancoIII/Project_Prop-osition` (PRIVATE)
- **GAMEPLAN_Proprietary_Auto_Trader.md** governs architecture, strategy, partnerships, and compliance.
- **SCALABLE_BUILD_PLAN.md** governs execution roadmap and layer progression.
- **This file (.agent/rules.md)** governs all development standards.
- Changes not reflected in SSOT documents are invalid. Rollback if SSOT not updated.

### Gameplan Milestone Tracking (MANDATORY)
**At every milestone (layer completion, prop firm challenge passed, strategy deployed, client onboarded), you MUST:**
1. Update `SCALABLE_BUILD_PLAN.md` — check off completed items, note actual dates
2. Update `GAMEPLAN_Proprietary_Auto_Trader.md` — reflect any architectural changes
3. Update `GAMEPLAN_SUMMARY.md` — keep the executive summary current
4. Update `.agent/rules.md` — add new rules for the current layer, log in Change Log
5. Commit all updates together as a single "milestone" commit

### Change History (Append-Only)
- The **Rules Change Log** at the bottom of this file is append-only. Never rewrite or truncate.
- Format: `Date | Change Summary | Reason | Layer`
- Unlogged changes are invalid.

### Context Preservation
Ensure the project can be rebuilt, audited, or resumed by any developer without memory loss. Maintain SSOT docs, preserve decision rationale, never delete history without Founder approval.

---

## 🎯 Asset Class Priority

| Priority | Asset Class | Why | Broker/API |
|----------|------------|-----|-----------|
| **#1 PRIMARY** | **Common Stocks (Equities)** | Safest, most data available, easiest to find signals | Alpaca (commission-free), Interactive Brokers |
| #2 Secondary | Futures (Micro E-Minis) | Tax-advantaged (60/40), market-neutral | Topstep, Apex Trader (via TradingView) |
| #3 Tertiary | Crypto (BTC, ETH, SOL) | 24/7 markets, high volatility | CCXT (Gemini, Kraken, Coinbase) |

**Stocks are the foundation. All strategies must work on stocks FIRST, then be adapted for other asset classes.**

---

## 📁 Project Structure

```
Propietary Accounts Auto-Trader/
├── .agent/
│   └── rules.md                    # THIS FILE — living development rules
├── config/                         # Django project settings
│   ├── settings/
│   │   ├── base.py                 # Shared settings
│   │   ├── development.py          # Local dev overrides
│   │   ├── production.py           # Production settings
│   │   └── testing.py              # Test settings
│   ├── urls.py                     # Root URL configuration
│   ├── wsgi.py
│   └── asgi.py                     # Django Channels ASGI
├── apps/
│   ├── accounts/                   # User auth, profiles, KYC
│   ├── broker_connector/           # Alpaca + CCXT integration, API key vault
│   ├── strategy_engine/            # Algo strategies, backtesting
│   ├── execution_engine/           # Order routing, fill tracking
│   ├── risk_management/            # Drawdown limits, kill switch
│   ├── prop_firm_manager/          # Prop firm accounts, rule compliance
│   ├── market_data/                # Stock data pipelines, OHLCV, fundamentals
│   ├── dashboard/                  # Real-time UI, analytics
│   ├── webhooks/                   # TradingView webhook receiver
│   └── notifications/              # Email, SMS, push alerts
├── strategies/                     # Pine Script files & Python strategies
├── tests/                          # Test suite (mirrors apps/ structure)
├── scripts/                        # Management commands, utilities
├── docker/                         # Dockerfiles, docker-compose
├── docs/                           # Technical documentation
├── GAMEPLAN_Proprietary_Auto_Trader.md
├── GAMEPLAN_SUMMARY.md
├── SCALABLE_BUILD_PLAN.md
├── manage.py
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🏗️ Tech Stack (Locked — no deviation without Founder approval)

| Component | Technology | Notes |
|-----------|-----------|-------|
| Language | Python 3.12+ | All backend code |
| Framework | Django 5.x | Web framework |
| API | Django REST Framework | All REST endpoints |
| Real-Time | Django Channels | WebSocket for live data |
| Database | MongoDB | Primary data store (Djongo/MongoEngine) |
| Cache/Queue | Redis | Caching, Celery broker, Channels layer |
| Task Queue | Celery | Async jobs (backtests, reports) |
| Stock Broker API | Alpaca (primary) | Commission-free US equities, built-in paper trading |
| Stock Broker API | Interactive Brokers (secondary) | Global markets, advanced order types |
| Crypto Exchange API | CCXT | Unified exchange integration (100+ exchanges) |
| Mobile | Flutter | iOS/Android client app |
| Containers | Docker + docker-compose | Local dev & production |

Purpose: Preserve stability, auditability, execution velocity. Non-compliance blocks merge.

---

## 🏷️ Naming Conventions

### Files & Directories
- **Apps:** `snake_case` (e.g., `broker_connector`, `risk_management`)
- **Python files:** `snake_case.py` (e.g., `order_router.py`, `stock_momentum.py`)
- **Templates:** `snake_case.html` inside `templates/[app_name]/`
- **Static assets:** `snake_case` (e.g., `dashboard_chart.js`)
- **Pine Script files:** `[strategy_name]_v[version].pine` (e.g., `stock_momentum_v2.pine`)

### Python Code
- **Classes:** `PascalCase` (e.g., `BrokerConnector`, `RiskManager`)
- **Functions/methods:** `snake_case` (e.g., `execute_trade()`, `check_drawdown()`)
- **Constants:** `UPPER_SNAKE_CASE` (e.g., `MAX_DRAWDOWN_PERCENT`, `DEFAULT_POSITION_SIZE`)
- **Django Models:** `PascalCase` singular (e.g., `Trade`, `Strategy`, `PropFirmAccount`)
- **Serializers:** `[Model]Serializer` (e.g., `TradeSerializer`)
- **Views:** `[Model]ViewSet` or `[Action]View` (e.g., `TradeViewSet`, `WebhookReceiveView`)

### MongoDB Collections & IDs
- Collections: `module_entity` snake_case (e.g., `trades`, `strategies`, `prop_firm_accounts`, `ohlcv_stocks`)
- Fields: `snake_case` (e.g., `cost_basis`, `fill_price`)
- Primary Keys: prefix + timestamp (e.g., `trd_17380...`, `stg_17380...`, `acct_17380...`)
- ID Prefixes: Trade=`trd_`, Strategy=`stg_`, Account=`acct_`, Order=`ord_`, Signal=`sig_`, PropFirm=`pf_`, User=`usr_`

### API & Networking
- Base URL: `/api/v1/` (always versioned)
- Endpoints: kebab-case (e.g., `/api/v1/trade-history/`, `/api/v1/prop-firms/`)
- Query params: `snake_case` (e.g., `?account_id=...&strategy_id=...`)
- Auth headers: `X-Custom-Header` format (e.g., `X-API-Token`)

### Environment Variables
- Prefixed by context: `DB_`, `BROKER_`, `EXCHANGE_`, `DJANGO_`, `REDIS_`, `PROP_`
- Example: `BROKER_ALPACA_API_KEY`, `EXCHANGE_GEMINI_API_KEY`, `PROP_FTMO_ACCOUNT_ID`

---

## 🔄 Workflow (Per Feature / Module)

Phases:
1. **Scope:** Confirm what may change, what safety invariants are implicated
2. **Analysis:** Schemas, risk impacts, broker/exchange impacts
3. **Design:** Select ONE canonical approach if multiples exist
4. **Implement:** Minimal file changes, annotate what/why, guards first
5. **Audit:** Verify risk controls, data contracts, test coverage
6. **Output:** Code + docs + concise rationale + SSOT update

**STOP:** Any risk management regression halts the task.

---

## 📊 Data Contracts

All data flowing through the system must conform to defined schemas:

**Input Objects:** Collections/JSON objects consumed (e.g., webhook payload, market data, broker response)
**Required Fields:** Explicit list of required keys per object
**Output Objects:** Collections updated, fields added/modified, side effects (state changes, flags, timestamps)

Rules:
- Schemas outrank implementations. Never silently drop or repurpose fields.
- All outputs MUST conform to existing schemas.
- Do NOT invent new schema without explicit instruction.

---

## 📐 Development Standards

### API Design
- All endpoints under `/api/v1/` (versioned from day one for client compatibility)
- Use DRF serializers for ALL input validation — never trust raw request data
- Paginate all list endpoints (default 25, max 100)
- Return consistent response format:
  ```json
  {"status": "success", "data": {...}, "message": ""}
  {"status": "error", "data": null, "message": "Description of error"}
  ```

### Security
- All webhook endpoints require HMAC signature or token verification
- API keys encrypted at rest (Fernet/AES-256)
- Rate limiting on all public endpoints (DRF throttling)
- No withdrawal permissions on any broker/exchange API key — trade-only + read-only
- IP whitelisting where supported

### Trading Logic
- Every strategy must implement the `BaseStrategy` interface
- Every strategy must have a backtest before going live
- All trades logged to MongoDB with: timestamp, strategy, symbol, side, qty, price, broker/exchange, fill status, P&L, cost_basis
- Risk checks run BEFORE every order submission (never after)
- **Stock-specific:** Enforce market hours, PDT rule awareness, settlement (T+1)

### Module Declaration (per new Django app)
Each new app must include a `MODULE.md` in its directory containing:
- Module Name & Location
- Purpose (1 sentence)
- Responsibilities (what it does)
- Boundaries (what it must NOT do)
- Success conditions (when is it correct?)

### Testing
- Unit tests for every model, serializer, and utility function
- Integration tests for broker/exchange connectors (mock Alpaca/CCXT responses)
- Strategy backtests count as tests — must pass minimum Sharpe > 1.0
- Run full test suite before any merge: `python manage.py test`

### Git & Version Control
- Branch naming: `feature/[module]-[description]`, `fix/[module]-[description]`
- Commit messages: `[module] verb description` (e.g., `[risk] add daily drawdown limit`)
- Milestone commits: `[milestone] Layer N complete — description`
- Never commit `.env`, API keys, or secrets

---

## 📈 Scalability Rules (Client-Ready)

> These rules ensure the system is always in a state that can be packaged and sold to clients.

1. **Multi-tenancy ready:** All models include a `user_id` / `organization_id` field. No global state.
2. **Configuration over code:** Trading parameters (position size, drawdown limits, etc.) are stored in DB, not hardcoded.
3. **White-label ready:** No hardcoded brand names in backend logic. Branding lives in templates/config only.
4. **Audit trail:** Every trade, config change, and user action is logged with timestamp and actor.
5. **API-first:** Every feature is accessible via API so clients can build their own UIs or integrate.
6. **Modular apps:** Each Django app is self-contained. A client could use `strategy_engine` without `prop_firm_manager` if they bring their own accounts.
7. **Documentation:** Every public function has a docstring. Every API endpoint is in the OpenAPI schema (DRF auto-generates this).

---

## 📝 Rules Change Log (Append-Only — Never Delete)

| Date | Change | Reason | Layer |
|------|--------|--------|-------|
| 2026-02-20 | Initial rules created | Project kickoff — established stack, structure, and conventions | 0 |
| 2026-02-20 | Added Governance & SSOT section | Adopted from Sentinel patterns — ensures change tracking and context preservation | 0 |
| 2026-02-20 | Added Gameplan Milestone Tracking rule | Ensure all SSOT docs stay current with every milestone achieved | 0 |
| 2026-02-20 | Added Asset Class Priority (Stocks #1) | Stocks are primary focus — safest, most data, easiest signals | 0 |
| 2026-02-20 | Added Safety Invariants | Adapted from Sentinel — fail closed, never escalate under uncertainty | 0 |
| 2026-02-20 | Added Workflow phases | Adapted from Sentinel — Scope→Analyze→Design→Implement→Audit→Output | 0 |
| 2026-02-20 | Added Data Contracts section | Schemas outrank implementations — prevents silent field drops | 0 |
| 2026-02-20 | Added Module Declaration requirement | Each new Django app must have MODULE.md with purpose and boundaries | 0 |
| 2026-02-20 | Added MongoDB ID prefixes | Consistent IDs: trd_, stg_, acct_, ord_, sig_, pf_, usr_ | 0 |
| 2026-02-20 | Added Alpaca + Interactive Brokers to stack | Stock broker APIs for primary asset class (equities) | 0 |
| 2026-02-20 | Renamed exchange_connector to broker_connector | Reflects stocks-first priority — brokers, not just crypto exchanges | 0 |
| 2026-02-20 | Added market_data app to structure | Dedicated app for stock data pipelines, fundamentals, OHLCV | 0 |
| 2026-02-20 | Added GitHub repo to SSOT | Private repo: PeterJFrancoIII/Project_Prop-osition | 0 |
