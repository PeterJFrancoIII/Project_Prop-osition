# Proprietary Accounts Automatic Algorithmic Trading Application — Ultra‑Detailed Build Plan (v1)

> **Goal:** Build a production-grade, automated algorithmic trading application that matches (and ideally exceeds) the user experience and operational maturity of products like Arch Public, while enabling trading on *firm capital* (proprietary/funded accounts) rather than users’ personal funds.

---

## 0) Important framing (so you don’t blow up later)

### You are building **two** products
1. **The trading automation product** (algo marketplace + execution + analytics + risk controls).
2. **The capital access layer** (prop/funded accounts, or your own prop structure), with legal/compliance, vendor contracts, and operational risk controls.

Many teams build (1) and die on (2). This plan treats (2) as a first-class engineering & business workstream.

### “Emulate to the highest level” ≠ copy
You can emulate *capabilities* and *UX patterns* but you must:
- Avoid copying their code, text, images, or proprietary strategy parameters.
- Build your own algorithms (or license them).
- Validate claims with auditable backtests and live performance reporting.

### Build around **verifiability**
Anything that touches money needs:
- Deterministic audit logs
- Tamper-evident trade history
- Reproducible backtests (exact versions of data + code)
- Clear user disclosures and “not investment advice” boundaries

---

## 1) Reverse requirements: what “Arch-like” means in concrete features

Based on publicly visible marketing + docs, Arch Public positions:
- Automated algorithms for crypto and (in concierge) futures (mentions of TradeStation partnership; futures cash settlement). citeturn1view1turn1view2
- Exchange/broker connections across major venues (their docs navigation includes Kraken, Coinbase, Gemini, Robinhood). citeturn1view0
- “Preset parameters” aligned to user goals (accumulate, yield, scale out). citeturn1view1
- A simple onboarding experience: connect account → enable algorithm → choose timeframe/parameters → monitor performance. citeturn1view0
- Performance highlights with backtest windows and metrics (CAGR, net profit, etc.). citeturn1view1

**Your product parity target** should be expressed as a **Feature Parity Matrix** (below) and built in phases.

---

## 2) Product definition: who it’s for & core value

### Primary user segments (choose one for MVP; support the rest later)
1. **Retail + accredited investors** (bring their own brokerage/exchange account).
2. **Funded account traders (prop firms)** (trade with a third party’s capital after passing an evaluation).
3. **Internal prop desk / proprietary capital** (you operate as the firm).

> **Recommendation:** Start MVP with **Segment 2 (funded futures accounts)** because:
- Futures prop firms are structured around performance evaluations and risk rules.
- Execution stack is simpler than equities/complex options early.
- There is a proven “automation allowed” path at several firms (must follow each firm’s rules), e.g., Topstep explicitly allows automated strategies with conditions. citeturn2search0

Then expand to:
- Crypto (exchange APIs)
- Multi-asset (via a broker API like TradeStation/IBKR)
- Copy-trading/social features (optional, higher regulatory friction)

---

## 3) Feature Parity Matrix (build checklist)

### A) Onboarding & account connectivity
- [ ] Account creation, MFA, device trust, security hardening
- [ ] Connect to venue(s):
  - Futures connection (via supported platforms / APIs)
  - Crypto exchange API key connection (permission checks + key rotation)
- [ ] “Paper trading” sandbox and simulated fills (testing + evaluation)

### B) Strategy catalog / “algorithms”
- [ ] Strategy templates: grid/mean-reversion, trend-follow, volatility breakout, DCA optimizer, cash-yield scaler, etc.
- [ ] Parameter presets tied to **user goals** (accumulate / yield / scale out / conservative / aggressive)
- [ ] Strategy versioning + release notes + performance changes
- [ ] Strategy safeguards:
  - max position size / max contracts
  - max leverage/margin usage
  - kill switch
  - circuit breakers (slippage, spread, volatility)

### C) Execution & reliability
- [ ] Event-driven trade engine (signals → orders → fills → reconciliation)
- [ ] Order types: market/limit/stop, bracket orders, reduce-only, OCO
- [ ] Idempotency + retry safety
- [ ] Latency monitoring + degraded-mode behavior
- [ ] Venue health checks + auto-disable if connectivity degrades

### D) Risk & compliance controls (non-negotiable)
- [ ] Global risk limits + per-strategy limits
- [ ] Daily loss limit, trailing drawdown tracking (critical for prop firms)
- [ ] Position and exposure monitoring in real time
- [ ] “Hard stop” enforcement (server-side)
- [ ] Audit log + immutable event store
- [ ] User disclosures + suitability gates (as required)

### E) Analytics & reporting
- [ ] Backtesting engine (minute/tick support; slippage + commission models)
- [ ] Performance dashboard:
  - equity curve
  - CAGR, Sharpe/Sortino, max drawdown
  - win-rate, avg win/loss, expectancy
  - fees and slippage
- [ ] Per-trade timeline + “why did it trade?” explanation (signal trace)
- [ ] Export: CSV (tax integrations later)

### F) Support & operations
- [ ] Concierge onboarding flow (human-assisted)
- [ ] Help center + setup guides
- [ ] Incident response playbook + status page
- [ ] Billing, subscriptions, free tier limits, usage metering

---

## 4) Architecture blueprint (reference implementation)

### High-level system diagram (services)
1. **Web / Mobile Frontend**
2. **API Gateway**
3. **User & Billing Service**
4. **Connector Service (per venue)**
5. **Signal Service**
6. **Execution Service**
7. **Risk Service**
8. **Portfolio & Reconciliation Service**
9. **Market Data Service**
10. **Backtest Service**
11. **Audit/Event Store**
12. **Observability**

### Data stores (suggested)
- PostgreSQL: users, configs, billing, metadata
- Time-series DB (TimescaleDB/Postgres): bars, indicators
- Object storage (S3-compatible): backtest artifacts, reports
- Redis: caching, rate limits, queues
- Kafka/NATS: event bus for trade + risk events
- Immutable log: WORM bucket + hash chain

### Execution design principles
- **Exactly-once intent**: every trade “intent” has a unique idempotency key.
- **At-least-once delivery** between services, with idempotent handlers.
- **Server-side risk enforcement**: never rely on client-side settings.
- **Reconciliation first**: treat venue as source of truth.

---

## 5) “Capital access” strategy: how you trade with firm money

There are three viable routes. Pick one for launch.

### Route A — Integrate with existing funded/prop firms (fastest)
**Concept:** Your app becomes the automation layer that traders use while trading *their funded accounts* at third-party prop firms.

**Pros**
- Fast path to funded capital
- Avoid raising capital initially
- Validate PMF quickly

**Cons**
- You don’t control rule sets; violations can cause bans
- Platform/API limitations
- Monetization tied to third-party terms

**Implementation approach**
- Target **futures prop firms** first.
- Build around common stacks (Rithmic/Tradovate + NinjaTrader/TradingView).
- Implement **rule-aware automation** (daily loss, trailing drawdown, contract caps).

**Proof that automation can be allowed**
- Topstep states automated strategies can be used (with disclaimers). citeturn2search0

### Route B — Partner with a broker API (users connect their own accounts)
**Concept:** Users connect their broker accounts; your automation runs under a user authorization model.

**Pros**
- Cleaner end-to-end UX
- Multi-asset expansion
- Stronger long-term defensibility

**Cons**
- Higher legal/compliance scope depending on structure
- Harder onboarding and jurisdiction complexity

**Implementation approach**
- Integrate with broker APIs (example: TradeStation API supports futures and more). citeturn2search3turn2search11
- Keep “user-controlled funds” (no custody) where possible.

### Route C — Build your own proprietary trading firm (most control, most friction)
**Concept:** Raise/allocate capital; trade it internally and/or fund external traders.

**Pros**
- Full control and upside

**Cons**
- Capital raising, governance, bank/exchange due diligence
- Institutional-grade controls required

**Implementation approach**
- Start internal-only, then add funded trader program after controls are proven.

---

## 6) Partnerships: who to partner with (by category)

### A) Funded/prop account sources (Route A)
**What you’re seeking:** firms that provide *funded accounts* and allow automation via supported platforms.

**Do this first**
1. Build a **Prop Firm Compatibility Matrix**:
   - Automation allowed (eval/funded)
   - Platforms supported (TradingView/NinjaTrader/Sierra)
   - Execution provider (Rithmic/Tradovate/etc.)
   - Core rules (daily loss, trailing DD method, payout cadence)
2. Choose 1–2 target stacks and implement those connectors.
3. Add “Pass the Evaluation” mode:
   - sizing throttles near limits
   - auto-disable on rule proximity
   - journaling and rule compliance reports

**Example implementation references**
- NinjaTrader support docs describe how evaluation accounts connect to Tradovate/Rithmic under Apex programs, indicating the ecosystem’s common stacks. citeturn2search1turn2search25

### B) Brokerage / execution partners (Route B)
- Broker API partner: TradeStation trading API for automation and multi-asset support. citeturn2search3turn2search11turn2search15
- Later: prime brokers/FCMs for institutional routing (FIX).

### C) Market data
- Futures: via broker/FCM (licensed) or vendor
- Crypto: exchange websockets; consider consolidated feeds later

### D) Infrastructure
- VPS near venue data centers (for stable execution)
- Cloud with multi-region failover for control plane

### E) Legal/compliance
- CFTC/NFA + SEC counsel depending on assets and structure
- Privacy counsel (GDPR/CCPA)

### F) Payments
- Stripe (billing), fraud tooling, chargeback management

---

## 7) MVP definition (90-day build target)

### MVP thesis
Ship an Arch-like automation experience **for funded futures accounts**, emphasizing:
- smooth setup
- strict risk controls
- rule-aware automation
- transparent reporting

### MVP scope (must-have)
1. **User app**
   - signup/login/MFA
   - connect funded futures account (via chosen stack)
   - choose **one** strategy + preset
   - configure risk limits
   - start/stop automation
2. **Execution**
   - market/limit orders, bracket support
   - order lifecycle + retries
3. **Risk**
   - daily loss limit
   - trailing drawdown tracking
   - max contracts/exposure
   - kill switch
4. **Analytics**
   - trade list, PnL, drawdown
   - basic equity curve
   - config snapshots
5. **Ops**
   - logs/metrics/alerts
   - incident playbook + support tooling

### MVP out-of-scope
- Large strategy marketplace
- Copy trading/social feed
- Multi-asset unless required for partner launch
- Any “guaranteed returns” marketing

---

## 8) Detailed engineering plan (WBS)

### Phase 0 — Discovery & constraints (Week 1–2)
**Outputs**
- Feature parity matrix finalized
- Asset class decision (futures-first)
- Partner shortlist (2 prop firms + 1 broker API fallback)
- Compliance scoping memo (external counsel)

**Tasks**
- Competitive teardown (UX flow diagrams)
- Decide execution stack:
  - TradingView webhooks → your signal API → execution
  - and/or native platform addon (e.g., NinjaTrader plugin) → your backend
- Define “source of truth” for orders/positions

### Phase 1 — Core platform skeleton (Week 3–5)
**Backend**
- Auth, users, entitlements
- Strategy config service
- Event bus + audit store
- Minimal market data ingestion

**Frontend**
- Onboarding flow
- Strategy selection + configuration
- Start/stop automation controls

### Phase 2 — Execution + risk (Week 6–9)
- Connector implementation for chosen stack
- Execution service (order lifecycle)
- Risk service (pre-trade + runtime)
- Reconciliation loop (venue truth vs internal)

### Phase 3 — Analytics + backtesting lite (Week 10–12)
- Performance dashboard MVP
- Backtest engine v0 (minute bars, simple slippage)
- Trade trace view (signal → order → fill)

### Phase 4 — Hardening & launch (Week 13+)
- Security review, pen test
- Load testing + chaos testing
- Canary deployments
- Help center and documentation

---

## 9) Strategy R&D plan (how you build algorithms without snake oil)

### Principles
- Start with 1–2 robust, interpretable strategies.
- Publish full assumptions: fees, slippage, latency.
- Use strategy versioning and “no silent changes” policy.

### Recommended first two strategies (futures-focused)
1. **Trend-following breakout**
2. **Mean-reversion with volatility filter**

### Validation checklist
- Walk-forward testing
- Out-of-sample tests
- Stress: slippage x2, commission changes, missing data, fast markets

---

## 10) Risk engine: the “secret sauce” for funded accounts

### Rule templates
- Rule set per firm + per account type
- Simulation mode (“would this violate rule X?”)
- Soft brake (warn/limit) and hard brake (block/disable)

### Core computations
- Real-time PnL including unrealized
- Intraday drawdown tracking
- Trailing drawdown based on peak equity (varies by firm)
- Exposure by symbol and correlated instruments (v2)

---

## 11) Security & operations

### Security baseline
- MFA, device trust, session management
- Encrypt API keys at rest (KMS/HSM)
- Signed webhooks + replay protection
- WAF + rate limiting
- Secure SDLC (dependency scanning, SAST/DAST)

### Reliability baseline
- Circuit breakers if market data fails
- Safe mode on outage: cancel orders; disable new entries
- Disaster recovery plan + restore drills

### Monitoring
- Order rejection rate
- Slippage vs model
- Connector heartbeat
- Near-breaches of risk rules
- Position mismatch alarms

---

## 12) Compliance & legal workstream (get counsel early)

**Questions counsel must answer**
- Are you providing investment advice?
- Are you operating as a CTA/CPO (commodities) or RIA (securities)?
- Are you custodying funds or touching customer assets?
- What jurisdictions will you serve?

**Practical guidance**
- Prefer user-controlled funds structures.
- Use transparent performance reporting and avoid “guarantee” language.
- Separate “software tooling” from discretionary management.

---

## 13) Monetization options

### SaaS subscription (cleanest)
- Free tier: limited volume/strategies
- Pro: higher limits, more strategies, better analytics
- Concierge: human onboarding and risk setup

### Performance fees (harder)
- Adds regulatory/accounting complexity; only under proper structures.

### Affiliate revenue with prop firms (optional)
- Referral-based, with clear disclosures.

---

## 14) Team plan (minimum for MVP)

- Product lead (trading + UX)
- 2 backend engineers (execution, risk, data)
- 1 frontend engineer
- 1 quant/strategy engineer
- 1 DevOps/SRE (part-time early)
- External: securities/commodities counsel + security consultant

---

## 15) Outreach checklists

### To prop firms (Route A)
- Automation allowed in eval + funded?
- Supported platforms (TradingView/NinjaTrader/Sierra)?
- Execution provider (Rithmic/Tradovate)?
- VPS restrictions?
- Copy trading restrictions?
- “Approved technology partner” program?

### To brokers/FCMs (Route B/C)
- API/FIX routing support?
- Market data licensing terms?
- Subaccounts and risk controls?
- Compliance requirements for third-party automation platforms?

---

## 16) Deliverables to produce in the next 7 days

1. UX flow maps (onboarding → connect → choose algo → configure → go live)
2. Feature parity matrix (0–3 score per feature)
3. Architecture Decision Record (ADR): futures-first + connector stack
4. Prop firm compatibility matrix (top 10 candidates)
5. Counsel memo: regulatory scope + do/don’t list
6. MVP PRD with acceptance criteria

---

## Appendix A — Prop Firm Compatibility Matrix fields

| Firm | Asset class | Automation (eval) | Automation (funded) | Platforms | Execution provider | Core rules | Notes |
|---|---|---:|---:|---|---|---|---|
| Example | Futures | Yes/No | Yes/No | TV/NT/SC | Rithmic/Tradovate | DLL, trailing DD | … |

---

## Appendix B — MVP Acceptance Criteria (sample)

### “Start automation”
- Creates a strategy instance with an immutable config snapshot
- Runs dry-run risk checks
- Starts market data subscription
- Begins evaluating signals
- Emits audit events for every decision point
- Shows live status + last heartbeat

### “Hard stop”
- Cancels open orders
- Flattens positions (configurable)
- Disables new orders until manual re-enable
- Generates incident record
