# Beaver's Choice Paper Company — Multi-Agent System Architecture

## Agent Workflow Diagram

```mermaid
flowchart TD
    Customer(["🧑 Customer\nSubmits paper supply request"])

    subgraph Orchestrator["🎯 Orchestrator Agent\nRole: Receives customer requests, delegates tasks\nto worker agents in sequence, and composes\nthe final customer-facing response."]
        Orch["orchestrator\n(ToolCallingAgent — no direct tools)\nCoordinates Step 1 → 2 → 3 → 4 pipeline"]
    end

    subgraph InventoryAgent["📦 Inventory Agent\nRole: Verify item availability and\nestimate supplier delivery dates."]
        T1["check_all_inventory(as_of_date)\nPurpose: Discover all items currently in stock\nHelper: get_all_inventory()"]
        T2["check_stock_level(item_name, as_of_date)\nPurpose: Get exact stock count for a specific item\nHelper: get_stock_level()"]
        T3["get_delivery_estimate(input_date_str, quantity)\nPurpose: Calculate supplier delivery date by order size\nHelper: get_supplier_delivery_date()"]
    end

    subgraph QuotingAgent["💰 Quoting Agent\nRole: Generate price quotes using historical\ndata and apply bulk discount tiers."]
        T4["find_quote_history(search_terms, limit)\nPurpose: Search past quotes for pricing precedent\nHelper: search_quote_history()"]
        T5["get_financial_report(as_of_date)\nPurpose: Get cash balance and inventory snapshot\nHelper: generate_financial_report()"]
    end

    subgraph SalesAgent["🧾 Sales Agent\nRole: Record finalized transactions and\nconfirm updated cash balance."]
        T6["record_transaction(item_name, type, qty, price, date)\nPurpose: Write completed sale to the database\nHelper: create_transaction()"]
        T7["get_current_cash_balance(as_of_date)\nPurpose: Return net cash as of a given date\nHelper: get_cash_balance()"]
    end

    DB[("🗄️ SQLite Database\nTables: transactions,\ninventory, quotes,\nquote_requests")]

    Response(["📄 Customer Response\nFulfillment status · Item & quantity\nUnit price · Discount applied · Total\nDelivery date · Transaction confirmation"])

    %% Main flow
    Customer -- "Request text + date" --> Orch

    %% Step 1
    Orch -- "STEP 1: Check availability" --> T1
    Orch -- "STEP 1: Verify stock count" --> T2
    Orch -- "STEP 1: Get delivery date" --> T3

    %% Step 2
    Orch -- "STEP 2: Find pricing precedent" --> T4
    Orch -- "STEP 2: Check business state" --> T5

    %% Step 3
    Orch -- "STEP 3: Finalize sale" --> T6
    Orch -- "STEP 3: Confirm cash balance" --> T7

    %% DB reads/writes
    T1 -- "SELECT stock" --> DB
    T2 -- "SELECT stock" --> DB
    T4 -- "SELECT quotes" --> DB
    T5 -- "SELECT transactions + inventory" --> DB
    T6 -- "INSERT transaction" --> DB
    T7 -- "SELECT transactions" --> DB

    %% Final response
    Orch -- "STEP 4: Compose response" --> Response
```

---

## Pipeline Sequence

| Step | Agent | Action | Output |
|------|-------|--------|--------|
| 1 | Inventory Agent | Call `check_all_inventory` to discover available items, match to customer request, call `check_stock_level` for exact count, call `get_delivery_estimate` for lead time | Available item name, stock level, estimated delivery date |
| 2 | Quoting Agent | Call `find_quote_history` for pricing precedent, apply bulk discount tier, call `get_financial_report` for business context | Unit price, discount %, total price, quote rationale |
| 3 | Sales Agent | Call `record_transaction` to write sale to DB, call `get_current_cash_balance` to confirm updated balance | Transaction ID, new cash balance |
| 4 | Orchestrator | Compose professional customer-facing response with all details | Final response to customer |

If no matching item is in stock after Step 1, the orchestrator skips Steps 2–3 and goes directly to Step 4 with a polite rejection.

---

## Bulk Discount Tiers (applied in Step 2)

| Order Total | Discount |
|-------------|----------|
| Under $50   | 0%       |
| $50 – $199  | 5%       |
| $200 – $999 | 10%      |
| $1,000+     | 15%      |

---

## Tool-to-Helper Function Mapping

| Tool (Agent-facing) | Helper Function (Starter Code) | Agent |
|---------------------|-------------------------------|-------|
| `check_all_inventory` | `get_all_inventory()` | Inventory Agent |
| `check_stock_level` | `get_stock_level()` | Inventory Agent |
| `get_delivery_estimate` | `get_supplier_delivery_date()` | Inventory Agent |
| `find_quote_history` | `search_quote_history()` | Quoting Agent |
| `get_financial_report` | `generate_financial_report()` | Quoting Agent |
| `record_transaction` | `create_transaction()` | Sales Agent |
| `get_current_cash_balance` | `get_cash_balance()` | Sales Agent |
