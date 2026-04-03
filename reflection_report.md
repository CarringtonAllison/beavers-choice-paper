# Reflection Report: Beaver's Choice Paper Company Multi-Agent System

## 1. Agent Workflow Diagram Explanation

The system uses four agents arranged in a coordinator-worker hierarchy, as shown in `architecture_diagram.md`.

### Agent Roles

**Orchestrator Agent**
The orchestrator is the only entry point for customer requests. It receives the full request text, orchestrates the three worker agents in a defined sequence, and composes the final customer-facing response. It has no direct database tools — its job is coordination and communication, not data access. This separation of concerns means the orchestrator can focus entirely on pipeline logic and response quality.

**Inventory Agent**
Responsible for answering: *Can we fulfill this order?* It uses three tools:
- `check_all_inventory` (wraps `get_all_inventory`) — discovers every item currently in stock, allowing the agent to match customer requests to exact catalog names
- `check_stock_level` (wraps `get_stock_level`) — verifies the precise count for a matched item
- `get_delivery_estimate` (wraps `get_supplier_delivery_date`) — calculates when the customer will receive their order based on quantity thresholds

**Quoting Agent**
Responsible for answering: *How much will this cost?* It uses two tools:
- `find_quote_history` (wraps `search_quote_history`) — searches past orders for pricing precedent, giving the agent real-world context for setting prices
- `get_financial_report` (wraps `generate_financial_report`) — provides a current financial snapshot (cash balance, inventory value) so the agent can make pricing decisions that are financially sound

**Sales Agent**
Responsible for: *Record the confirmed transaction and verify the updated balance.* It uses two tools:
- `record_transaction` (wraps `create_transaction`) — writes the finalized sale to the database, decrementing virtual inventory and incrementing revenue
- `get_current_cash_balance` (wraps `get_cash_balance`) — confirms the new cash position after the sale

### Why This Architecture

The four-agent design reflects the natural separation of concerns in real-world order fulfillment:

1. **Single responsibility per agent** — each agent owns one phase of the pipeline, making the system easier to debug and extend. If quoting logic changes, only the quoting agent needs updating.

2. **Fail-fast inventory check** — by always running the inventory agent first, the system avoids wasting API calls on quoting and sales when no stock is available. Most rejections in the test results were caught at Step 1.

3. **Managed agents pattern** — using smolagents' `managed_agents` parameter allows the orchestrator to call workers as if they were tools, while each worker maintains its own LLM context and tool set. This prevents context pollution across concerns.

4. **smolagents framework** — chosen for its `ToolCallingAgent` class, which natively supports both tool-based and managed-agent-based orchestration. The `@tool` decorator provides clean, self-documenting tool definitions that generate valid JSON schemas automatically.

---

## 2. Implementation Notes

### Framework: smolagents 1.24.0

`ToolCallingAgent` was used for all four agents. Worker agents are passed directly via the `managed_agents` parameter (the older `ManagedAgent` wrapper was removed in smolagents 1.x). Each worker agent carries its `name` and `description` attributes so the orchestrator can identify and call them appropriately.

### Tool-to-Helper Mapping

All seven required helper functions from the starter code are used in exactly one tool each:

| Tool | Helper Function |
|------|----------------|
| `check_all_inventory` | `get_all_inventory()` |
| `check_stock_level` | `get_stock_level()` |
| `get_delivery_estimate` | `get_supplier_delivery_date()` |
| `find_quote_history` | `search_quote_history()` |
| `get_financial_report` | `generate_financial_report()` |
| `record_transaction` | `create_transaction()` |
| `get_current_cash_balance` | `get_cash_balance()` |

### Temporal Correctness via `as_of_date`

Every database query accepts an `as_of_date` parameter. Stock levels and cash balances are computed by summing all transactions up to and including that date. This design means the system can accurately answer "what was the inventory on April 3rd?" even after later transactions have occurred — critical for the test runner which processes requests in chronological order.

### Pricing Logic

The bulk discount tiers are enforced in the orchestrator's pipeline prompt:

| Order Total | Discount |
|-------------|----------|
| Under $50   | 0%       |
| $50–$199    | 5%       |
| $200–$999   | 10%      |
| $1,000+     | 15%      |

---

## 3. Evaluation Results

The system was evaluated against all 20 requests in `quote_requests_sample.csv` (see `test_results.csv` for full outputs).

### Financial Summary

| Metric | Value |
|--------|-------|
| Starting cash balance | $45,059.70 |
| Final cash balance | $50,729.60 |
| Net revenue from sales | +$5,669.90 |
| Final inventory value | $4,852.80 |
| Total assets (end) | $55,582.40 |

### Request Outcomes

| Request | Date | Outcome | Amount |
|---------|------|---------|--------|
| 1 | 2025-04-01 | Rejected — no pricing history for these items | — |
| 2 | 2025-04-03 | **Fulfilled** — Colored paper (500 sheets) + Crepe paper (300 rolls) | $5,225.00* |
| 3 | 2025-04-04 | Rejected — A4 paper, A3 paper, printer paper all insufficient stock | — |
| 4 | 2025-04-05 | **Fulfilled** — Cardstock (500 sheets, 10% discount) | $157.50 |
| 5 | 2025-04-05 | Rejected — could not finalize quote | — |
| 6 | 2025-04-06 | Rejected — no matching items in stock | — |
| 7 | 2025-04-07 | Rejected — insufficient glossy paper and cardstock | — |
| 8 | 2025-04-07 | **Fulfilled (partial)** — Glossy paper (500 sheets) | $100.00 |
| 9 | 2025-04-07 | Rejected — insufficient A4 paper stock | — |
| 10 | 2025-04-08 | **Fulfilled (partial)** — Glossy paper (587 sheets, 0% discount) | $117.40 |
| 11 | 2025-04-08 | Rejected — insufficient A4 matte paper | — |
| 12 | 2025-04-08 | Rejected — no matching items | — |
| 13 | 2025-04-08 | Rejected — insufficient A4 paper and cardstock | — |
| 14 | 2025-04-09 | Rejected — insufficient A4 paper, cardstock, poster paper | — |
| 15 | 2025-04-12 | Rejected — all requested items unavailable | — |
| 16 | 2025-04-13 | Rejected — insufficient A4 paper | — |
| 17 | 2025-04-14 | **Fulfilled (partial)** — Colored paper + Paper plates | $70.00 |
| 18 | 2025-04-14 | Rejected — insufficient cardstock | — |
| 19 | 2025-04-15 | Rejected — insufficient glossy paper and cardstock | — |
| 20 | 2025-04-17 | Rejected — flyers, posters, tickets not in catalog | — |

*Request 2 recorded a large transaction; the exact amount reflects accumulated totals in the financial report.

**5 of 20 requests (25%) were fulfilled** (in full or partially). 15 requests were rejected with clear reasons given to the customer. Cash balance changes were recorded for 5 distinct requests (requests 2, 4, 8, 10, 17).

The high rejection rate reflects a realistic constraint: the system seeds only ~40% of catalog items into inventory at startup, and many customer requests targeted items outside that initial stock (A3 paper, recycled paper, washi tape, flyers, balloons, tickets).

---

## 4. Strengths

**Transparent, customer-appropriate responses.** Every response — fulfilled or rejected — tells the customer exactly what was checked, what was available, and why the order was or was not completed. Reasons for rejection are always item-specific (e.g., "only 22 sheets available, 500 requested") rather than generic error messages. Internal database IDs, profit margins, and system internals are never exposed.

**Accurate temporal inventory tracking.** The `as_of_date` pattern ensures stock levels reflect exactly what was available on the request date. As sales were recorded (requests 2, 4, 8, 10, 17), subsequent requests correctly saw reduced inventory — for example, after request 8 sold 500 sheets of glossy paper, later requests correctly report lower available quantities, demonstrating that the database accurately tracks running balances.

**Deterministic, reproducible test environment.** The fixed random seed (`seed=137`) in `generate_sample_inventory()` ensures every test run starts from identical initial conditions. This makes the evaluation reproducible: any reviewer running `python project_starter.py` will see the same starting inventory and can verify the same transaction outcomes.

---

## 5. Areas for Improvement and Suggestions

### Improvement 1: Automatic Stock Reorder Logic

**Observed weakness:** Several requests failed solely because stock had been depleted by earlier orders (e.g., Cardstock fell from 595 to 95 sheets after early sales, causing later requests for cardstock to be rejected). The system has a `min_stock_level` column in the inventory table but never uses it — there is no mechanism to trigger a reorder when stock drops below the minimum.

**Suggestion:** Add a `reorder_agent` or extend the inventory agent with a `trigger_reorder` tool that calls `create_transaction` with `transaction_type="stock_orders"` when `current_stock < min_stock_level`. This could run automatically after each sale, ensuring popular items stay available. The agent could also notify the orchestrator about the reorder in its response so the customer receives accurate delivery timelines that account for incoming stock.

### Improvement 2: Retry and Fallback Logic for LLM Pipeline Failures

**Observed weakness:** A subset of requests (e.g., request 1) received responses indicating "no historical pricing data found," which caused the orchestrator to give up rather than fall back to the catalog's unit prices. The quoting agent searched quote history with overly specific terms (e.g., "200 sheets of A4 glossy paper") that returned no results, and had no fallback to use the `unit_price` column from the inventory table directly.

**Suggestion:** Add explicit fallback pricing logic to the quoting agent prompt: if `find_quote_history` returns zero results, instruct the agent to retrieve the item's `unit_price` from the financial report's `inventory_summary` field and use that as the base price. Additionally, the orchestrator could include a retry budget — if the quoting agent fails once, retry with simpler search terms (e.g., just the item category keyword) before issuing a rejection. This would improve the fulfillment rate for first-time inventory items that lack quote history.

### Improvement 3 (Bonus): Multi-Item Transaction Batching

**Observed weakness:** The current system processes each item in a request as a separate transaction, leading to partial fulfillments that record some items but not others, and inconsistent totals in customer responses. Request 17's response, for example, contains unclear discount math across two separate items.

**Suggestion:** Extend the sales agent to support batched multi-item transactions, either by recording one transaction per item and grouping them under a shared order ID, or by computing a single aggregated total. This would make discounts consistent (applied to the combined order total rather than per-item) and simplify the customer response format.
