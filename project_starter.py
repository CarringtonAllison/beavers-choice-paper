import pandas as pd
import numpy as np
import os
import time
import ast
from dotenv import load_dotenv
from sqlalchemy.sql import text
from datetime import datetime, timedelta
from typing import Dict, List, Union
from sqlalchemy import create_engine, Engine
from smolagents import ToolCallingAgent, OpenAIServerModel, tool

# Load environment variables from .env file
load_dotenv()

# Create an SQLite database
db_engine = create_engine("sqlite:///munder_difflin.db")

# List containing the different kinds of papers
paper_supplies = [
    # Paper Types (priced per sheet unless specified)
    {"item_name": "A4 paper",                         "category": "paper",        "unit_price": 0.05},
    {"item_name": "Letter-sized paper",              "category": "paper",        "unit_price": 0.06},
    {"item_name": "Cardstock",                        "category": "paper",        "unit_price": 0.15},
    {"item_name": "Colored paper",                    "category": "paper",        "unit_price": 0.10},
    {"item_name": "Glossy paper",                     "category": "paper",        "unit_price": 0.20},
    {"item_name": "Matte paper",                      "category": "paper",        "unit_price": 0.18},
    {"item_name": "Recycled paper",                   "category": "paper",        "unit_price": 0.08},
    {"item_name": "Eco-friendly paper",               "category": "paper",        "unit_price": 0.12},
    {"item_name": "Poster paper",                     "category": "paper",        "unit_price": 0.25},
    {"item_name": "Banner paper",                     "category": "paper",        "unit_price": 0.30},
    {"item_name": "Kraft paper",                      "category": "paper",        "unit_price": 0.10},
    {"item_name": "Construction paper",               "category": "paper",        "unit_price": 0.07},
    {"item_name": "Wrapping paper",                   "category": "paper",        "unit_price": 0.15},
    {"item_name": "Glitter paper",                    "category": "paper",        "unit_price": 0.22},
    {"item_name": "Decorative paper",                 "category": "paper",        "unit_price": 0.18},
    {"item_name": "Letterhead paper",                 "category": "paper",        "unit_price": 0.12},
    {"item_name": "Legal-size paper",                 "category": "paper",        "unit_price": 0.08},
    {"item_name": "Crepe paper",                      "category": "paper",        "unit_price": 0.05},
    {"item_name": "Photo paper",                      "category": "paper",        "unit_price": 0.25},
    {"item_name": "Uncoated paper",                   "category": "paper",        "unit_price": 0.06},
    {"item_name": "Butcher paper",                    "category": "paper",        "unit_price": 0.10},
    {"item_name": "Heavyweight paper",                "category": "paper",        "unit_price": 0.20},
    {"item_name": "Standard copy paper",              "category": "paper",        "unit_price": 0.04},
    {"item_name": "Bright-colored paper",             "category": "paper",        "unit_price": 0.12},
    {"item_name": "Patterned paper",                  "category": "paper",        "unit_price": 0.15},

    # Product Types (priced per unit)
    {"item_name": "Paper plates",                     "category": "product",      "unit_price": 0.10},
    {"item_name": "Paper cups",                       "category": "product",      "unit_price": 0.08},
    {"item_name": "Paper napkins",                    "category": "product",      "unit_price": 0.02},
    {"item_name": "Disposable cups",                  "category": "product",      "unit_price": 0.10},
    {"item_name": "Table covers",                     "category": "product",      "unit_price": 1.50},
    {"item_name": "Envelopes",                        "category": "product",      "unit_price": 0.05},
    {"item_name": "Sticky notes",                     "category": "product",      "unit_price": 0.03},
    {"item_name": "Notepads",                         "category": "product",      "unit_price": 2.00},
    {"item_name": "Invitation cards",                 "category": "product",      "unit_price": 0.50},
    {"item_name": "Flyers",                           "category": "product",      "unit_price": 0.15},
    {"item_name": "Party streamers",                  "category": "product",      "unit_price": 0.05},
    {"item_name": "Decorative adhesive tape (washi tape)", "category": "product", "unit_price": 0.20},
    {"item_name": "Paper party bags",                 "category": "product",      "unit_price": 0.25},
    {"item_name": "Name tags with lanyards",          "category": "product",      "unit_price": 0.75},
    {"item_name": "Presentation folders",             "category": "product",      "unit_price": 0.50},

    # Large-format items (priced per unit)
    {"item_name": "Large poster paper (24x36 inches)", "category": "large_format", "unit_price": 1.00},
    {"item_name": "Rolls of banner paper (36-inch width)", "category": "large_format", "unit_price": 2.50},

    # Specialty papers
    {"item_name": "100 lb cover stock",               "category": "specialty",    "unit_price": 0.50},
    {"item_name": "80 lb text paper",                 "category": "specialty",    "unit_price": 0.40},
    {"item_name": "250 gsm cardstock",                "category": "specialty",    "unit_price": 0.30},
    {"item_name": "220 gsm poster paper",             "category": "specialty",    "unit_price": 0.35},
]

########################
# HELPER FUNCTIONS
########################

def generate_sample_inventory(paper_supplies: list, coverage: float = 0.4, seed: int = 137) -> pd.DataFrame:
    """
    Generate inventory for exactly a specified percentage of items from the full paper supply list.

    This function randomly selects exactly `coverage` x N items from the `paper_supplies` list,
    and assigns each selected item:
    - a random stock quantity between 200 and 800,
    - a minimum stock level between 50 and 150.

    The random seed ensures reproducibility of selection and stock levels.

    Args:
        paper_supplies (list): A list of dictionaries, each representing a paper item with
                               keys 'item_name', 'category', and 'unit_price'.
        coverage (float, optional): Fraction of items to include in the inventory (default is 0.4, or 40%).
        seed (int, optional): Random seed for reproducibility (default is 137).

    Returns:
        pd.DataFrame: A DataFrame with the selected items and assigned inventory values, including:
                      - item_name
                      - category
                      - unit_price
                      - current_stock
                      - min_stock_level
    """
    np.random.seed(seed)
    num_items = int(len(paper_supplies) * coverage)
    selected_indices = np.random.choice(
        range(len(paper_supplies)),
        size=num_items,
        replace=False
    )
    selected_items = [paper_supplies[i] for i in selected_indices]
    inventory = []
    for item in selected_items:
        inventory.append({
            "item_name": item["item_name"],
            "category": item["category"],
            "unit_price": item["unit_price"],
            "current_stock": np.random.randint(200, 800),
            "min_stock_level": np.random.randint(50, 150)
        })
    return pd.DataFrame(inventory)


def init_database(db_engine: Engine, seed: int = 137) -> Engine:
    """
    Set up the Munder Difflin database with all required tables and initial records.

    This function performs the following tasks:
    - Creates the 'transactions' table for logging stock orders and sales
    - Loads customer inquiries from 'quote_requests.csv' into a 'quote_requests' table
    - Loads previous quotes from 'quotes.csv' into a 'quotes' table, extracting useful metadata
    - Generates a random subset of paper inventory using `generate_sample_inventory`
    - Inserts initial financial records including available cash and starting stock levels

    Args:
        db_engine (Engine): A SQLAlchemy engine connected to the SQLite database.
        seed (int, optional): A random seed used to control reproducibility of inventory stock levels.
                              Default is 137.

    Returns:
        Engine: The same SQLAlchemy engine, after initializing all necessary tables and records.

    Raises:
        Exception: If an error occurs during setup, the exception is printed and raised.
    """
    try:
        transactions_schema = pd.DataFrame({
            "id": [],
            "item_name": [],
            "transaction_type": [],
            "units": [],
            "price": [],
            "transaction_date": [],
        })
        transactions_schema.to_sql("transactions", db_engine, if_exists="replace", index=False)

        initial_date = datetime(2025, 1, 1).isoformat()

        quote_requests_df = pd.read_csv("quote_requests.csv")
        quote_requests_df["id"] = range(1, len(quote_requests_df) + 1)
        quote_requests_df.to_sql("quote_requests", db_engine, if_exists="replace", index=False)

        quotes_df = pd.read_csv("quotes.csv")
        quotes_df["request_id"] = range(1, len(quotes_df) + 1)
        quotes_df["order_date"] = initial_date

        if "request_metadata" in quotes_df.columns:
            quotes_df["request_metadata"] = quotes_df["request_metadata"].apply(
                lambda x: ast.literal_eval(x) if isinstance(x, str) else x
            )
            quotes_df["job_type"] = quotes_df["request_metadata"].apply(lambda x: x.get("job_type", ""))
            quotes_df["order_size"] = quotes_df["request_metadata"].apply(lambda x: x.get("order_size", ""))
            quotes_df["event_type"] = quotes_df["request_metadata"].apply(lambda x: x.get("event_type", ""))

        quotes_df = quotes_df[[
            "request_id",
            "total_amount",
            "quote_explanation",
            "order_date",
            "job_type",
            "order_size",
            "event_type"
        ]]
        quotes_df.to_sql("quotes", db_engine, if_exists="replace", index=False)

        inventory_df = generate_sample_inventory(paper_supplies, seed=seed)

        initial_transactions = []
        initial_transactions.append({
            "item_name": None,
            "transaction_type": "sales",
            "units": None,
            "price": 50000.0,
            "transaction_date": initial_date,
        })

        for _, item in inventory_df.iterrows():
            initial_transactions.append({
                "item_name": item["item_name"],
                "transaction_type": "stock_orders",
                "units": item["current_stock"],
                "price": item["current_stock"] * item["unit_price"],
                "transaction_date": initial_date,
            })

        pd.DataFrame(initial_transactions).to_sql("transactions", db_engine, if_exists="append", index=False)
        inventory_df.to_sql("inventory", db_engine, if_exists="replace", index=False)

        return db_engine

    except Exception as e:
        print(f"Error initializing database: {e}")
        raise


def create_transaction(
    item_name: str,
    transaction_type: str,
    quantity: int,
    price: float,
    date: Union[str, datetime],
) -> int:
    """
    Record a transaction of type 'stock_orders' or 'sales' into the transactions table.

    Args:
        item_name (str): The name of the item involved in the transaction.
        transaction_type (str): Either 'stock_orders' or 'sales'.
        quantity (int): Number of units involved in the transaction.
        price (float): Total price of the transaction.
        date (str or datetime): Date of the transaction in ISO 8601 format.

    Returns:
        int: The ID of the newly inserted transaction.

    Raises:
        ValueError: If `transaction_type` is not 'stock_orders' or 'sales'.
        Exception: For other database or execution errors.
    """
    try:
        date_str = date.isoformat() if isinstance(date, datetime) else date

        if transaction_type not in {"stock_orders", "sales"}:
            raise ValueError("Transaction type must be 'stock_orders' or 'sales'")

        transaction = pd.DataFrame([{
            "item_name": item_name,
            "transaction_type": transaction_type,
            "units": quantity,
            "price": price,
            "transaction_date": date_str,
        }])

        transaction.to_sql("transactions", db_engine, if_exists="append", index=False)
        result = pd.read_sql("SELECT last_insert_rowid() as id", db_engine)
        return int(result.iloc[0]["id"])

    except Exception as e:
        print(f"Error creating transaction: {e}")
        raise


def get_all_inventory(as_of_date: str) -> Dict[str, int]:
    """
    Retrieve a snapshot of available inventory as of a specific date.

    Only items with positive stock are included in the result.

    Args:
        as_of_date (str): ISO-formatted date string (YYYY-MM-DD) representing the inventory cutoff.

    Returns:
        Dict[str, int]: A dictionary mapping item names to their current stock levels.
    """
    query = """
        SELECT
            item_name,
            SUM(CASE
                WHEN transaction_type = 'stock_orders' THEN units
                WHEN transaction_type = 'sales' THEN -units
                ELSE 0
            END) as stock
        FROM transactions
        WHERE item_name IS NOT NULL
        AND transaction_date <= :as_of_date
        GROUP BY item_name
        HAVING stock > 0
    """
    result = pd.read_sql(query, db_engine, params={"as_of_date": as_of_date})
    return dict(zip(result["item_name"], result["stock"]))


def get_stock_level(item_name: str, as_of_date: Union[str, datetime]) -> pd.DataFrame:
    """
    Retrieve the stock level of a specific item as of a given date.

    Args:
        item_name (str): The name of the item to look up.
        as_of_date (str or datetime): The cutoff date (inclusive) for calculating stock.

    Returns:
        pd.DataFrame: A single-row DataFrame with columns 'item_name' and 'current_stock'.
    """
    if isinstance(as_of_date, datetime):
        as_of_date = as_of_date.isoformat()

    stock_query = """
        SELECT
            item_name,
            COALESCE(SUM(CASE
                WHEN transaction_type = 'stock_orders' THEN units
                WHEN transaction_type = 'sales' THEN -units
                ELSE 0
            END), 0) AS current_stock
        FROM transactions
        WHERE item_name = :item_name
        AND transaction_date <= :as_of_date
    """

    return pd.read_sql(
        stock_query,
        db_engine,
        params={"item_name": item_name, "as_of_date": as_of_date},
    )


def get_supplier_delivery_date(input_date_str: str, quantity: int) -> str:
    """
    Estimate the supplier delivery date based on the requested order quantity and a starting date.

    Delivery lead time:
        - <=10 units: same day
        - 11-100 units: 1 day
        - 101-1000 units: 4 days
        - >1000 units: 7 days

    Args:
        input_date_str (str): The starting date in ISO format (YYYY-MM-DD).
        quantity (int): The number of units in the order.

    Returns:
        str: Estimated delivery date in ISO format (YYYY-MM-DD).
    """
    print(f"FUNC (get_supplier_delivery_date): Calculating for qty {quantity} from date string '{input_date_str}'")

    try:
        input_date_dt = datetime.fromisoformat(input_date_str.split("T")[0])
    except (ValueError, TypeError):
        print(f"WARN (get_supplier_delivery_date): Invalid date format '{input_date_str}', using today as base.")
        input_date_dt = datetime.now()

    if quantity <= 10:
        days = 0
    elif quantity <= 100:
        days = 1
    elif quantity <= 1000:
        days = 4
    else:
        days = 7

    delivery_date_dt = input_date_dt + timedelta(days=days)
    return delivery_date_dt.strftime("%Y-%m-%d")


def get_cash_balance(as_of_date: Union[str, datetime]) -> float:
    """
    Calculate the current cash balance as of a specified date.

    Balance = total sales revenue - total stock purchase costs.

    Args:
        as_of_date (str or datetime): The cutoff date (inclusive) in ISO format or as a datetime object.

    Returns:
        float: Net cash balance as of the given date. Returns 0.0 if no transactions exist.
    """
    try:
        if isinstance(as_of_date, datetime):
            as_of_date = as_of_date.isoformat()

        transactions = pd.read_sql(
            "SELECT * FROM transactions WHERE transaction_date <= :as_of_date",
            db_engine,
            params={"as_of_date": as_of_date},
        )

        if not transactions.empty:
            total_sales = transactions.loc[transactions["transaction_type"] == "sales", "price"].sum()
            total_purchases = transactions.loc[transactions["transaction_type"] == "stock_orders", "price"].sum()
            return float(total_sales - total_purchases)

        return 0.0

    except Exception as e:
        print(f"Error getting cash balance: {e}")
        return 0.0


def generate_financial_report(as_of_date: Union[str, datetime]) -> Dict:
    """
    Generate a complete financial report for the company as of a specific date.

    Includes cash balance, inventory valuation, combined asset total,
    itemized inventory breakdown, and top 5 best-selling products.

    Args:
        as_of_date (str or datetime): The date (inclusive) for which to generate the report.

    Returns:
        Dict: Financial report with cash_balance, inventory_value, total_assets,
              inventory_summary, and top_selling_products.
    """
    if isinstance(as_of_date, datetime):
        as_of_date = as_of_date.isoformat()

    cash = get_cash_balance(as_of_date)
    inventory_df = pd.read_sql("SELECT * FROM inventory", db_engine)
    inventory_value = 0.0
    inventory_summary = []

    for _, item in inventory_df.iterrows():
        stock_info = get_stock_level(item["item_name"], as_of_date)
        stock = stock_info["current_stock"].iloc[0]
        item_value = stock * item["unit_price"]
        inventory_value += item_value
        inventory_summary.append({
            "item_name": item["item_name"],
            "stock": stock,
            "unit_price": item["unit_price"],
            "value": item_value,
        })

    top_sales_query = """
        SELECT item_name, SUM(units) as total_units, SUM(price) as total_revenue
        FROM transactions
        WHERE transaction_type = 'sales' AND transaction_date <= :date
        GROUP BY item_name
        ORDER BY total_revenue DESC
        LIMIT 5
    """
    top_sales = pd.read_sql(top_sales_query, db_engine, params={"date": as_of_date})
    top_selling_products = top_sales.to_dict(orient="records")

    return {
        "as_of_date": as_of_date,
        "cash_balance": cash,
        "inventory_value": inventory_value,
        "total_assets": cash + inventory_value,
        "inventory_summary": inventory_summary,
        "top_selling_products": top_selling_products,
    }


def search_quote_history(search_terms: List[str], limit: int = 5) -> List[Dict]:
    """
    Retrieve historical quotes matching any of the provided search terms.

    Searches both the original customer request and the quote explanation.
    Results are sorted by most recent order date.

    Args:
        search_terms (List[str]): List of terms to match against requests and explanations.
        limit (int, optional): Maximum number of records to return. Default is 5.

    Returns:
        List[Dict]: Matching quotes with fields: original_request, total_amount,
                    quote_explanation, job_type, order_size, event_type, order_date.
    """
    conditions = []
    params = {}

    for i, term in enumerate(search_terms):
        param_name = f"term_{i}"
        conditions.append(
            f"(LOWER(qr.response) LIKE :{param_name} OR "
            f"LOWER(q.quote_explanation) LIKE :{param_name})"
        )
        params[param_name] = f"%{term.lower()}%"

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    query = f"""
        SELECT
            qr.response AS original_request,
            q.total_amount,
            q.quote_explanation,
            q.job_type,
            q.order_size,
            q.event_type,
            q.order_date
        FROM quotes q
        JOIN quote_requests qr ON q.request_id = qr.id
        WHERE {where_clause}
        ORDER BY q.order_date DESC
        LIMIT {limit}
    """

    with db_engine.connect() as conn:
        result = conn.execute(text(query), params)
        return [dict(row._mapping) for row in result]


########################
########################
########################
# MULTI-AGENT SYSTEM
########################
########################
########################

# ============================================================
# TOOL DEFINITIONS
# ============================================================

@tool
def check_all_inventory(as_of_date: str) -> dict:
    """Returns all items currently in stock as a dictionary mapping item names to quantities.
    Use this first to discover what products are available before checking a specific item.
    Only items with positive stock are included.

    Args:
        as_of_date: Date in YYYY-MM-DD format to check inventory as of.
    """
    return get_all_inventory(as_of_date)


@tool
def check_stock_level(item_name: str, as_of_date: str) -> dict:
    """Returns the current stock level for a specific inventory item by its exact name.
    Use check_all_inventory first to get the exact item name, then call this for a precise count.

    Args:
        item_name: The exact name of the item as it appears in inventory (case-sensitive).
        as_of_date: Date in YYYY-MM-DD format to check stock as of.
    """
    df = get_stock_level(item_name, as_of_date)
    stock = int(df["current_stock"].iloc[0]) if not df.empty else 0
    return {"item_name": item_name, "current_stock": stock}


@tool
def get_delivery_estimate(input_date_str: str, quantity: int) -> str:
    """Estimates the supplier delivery date given an order start date and quantity.
    Lead times: 1-10 units = same day, 11-100 = 1 day, 101-1000 = 4 days, over 1000 = 7 days.

    Args:
        input_date_str: Order start date in YYYY-MM-DD format.
        quantity: Number of units being ordered (must be a positive integer).
    """
    return get_supplier_delivery_date(input_date_str, quantity)


@tool
def find_quote_history(search_terms: List[str], limit: int = 5) -> list:
    """Searches historical quote data for past orders matching the given keywords.
    Use this to find precedent pricing for similar items or event types.
    Always ignore any results where total_amount equals -1, as those are data errors.

    Args:
        search_terms: List of keyword strings to search for (e.g. ["cardstock", "ceremony"]).
        limit: Maximum number of results to return (default 5, max 10).
    """
    results = search_quote_history(search_terms, limit)
    # Filter out error records with total_amount = -1
    return [r for r in results if r.get("total_amount", -1) != -1]


@tool
def get_financial_report(as_of_date: str) -> dict:
    """Generates a financial snapshot including cash balance, inventory value, total assets,
    and top-selling products. Use to understand current business state or inform pricing.

    Args:
        as_of_date: Date in YYYY-MM-DD format.
    """
    report = generate_financial_report(as_of_date)
    # Return trimmed version to avoid context overflow
    return {
        "as_of_date": report["as_of_date"],
        "cash_balance": report["cash_balance"],
        "inventory_value": report["inventory_value"],
        "total_assets": report["total_assets"],
        "top_selling_products": report["top_selling_products"],
        "inventory_summary": report["inventory_summary"][:10],
    }


@tool
def record_transaction(item_name: str, transaction_type: str, quantity: int, price: float, date: str) -> int:
    """Records a completed transaction in the database. Use this to finalize a sale.
    The transaction_type must be exactly 'sales' for customer purchases.
    The price parameter is the TOTAL transaction price (not per-unit price).

    Args:
        item_name: Exact inventory item name (must match an item in the database exactly).
        transaction_type: Must be exactly 'sales' for customer sales, or 'stock_orders' for restocking.
        quantity: Number of units sold (must be a positive integer).
        price: Total transaction price in dollars (quantity x unit_price, after any discounts).
        date: Transaction date in YYYY-MM-DD format.
    """
    return create_transaction(item_name, transaction_type, quantity, price, date)


@tool
def get_current_cash_balance(as_of_date: str) -> float:
    """Returns the current cash balance of the business as of the given date.
    Cash balance equals total sales revenue minus total stock purchase costs.
    A positive value means the business is profitable; negative means a deficit.

    Args:
        as_of_date: Date in YYYY-MM-DD format.
    """
    return get_cash_balance(as_of_date)


# ============================================================
# AGENT SYSTEM FACTORY
# ============================================================

def build_agent_system() -> ToolCallingAgent:
    """Build and return the orchestrator agent with all worker agents attached as managed agents.

    Returns:
        ToolCallingAgent: The configured orchestrator ready to process customer requests.

    Raises:
        ValueError: If UDACITY_OPENAI_API_KEY is not set in the environment.
    """
    api_key = os.getenv("UDACITY_OPENAI_API_KEY")
    if not api_key:
        raise ValueError("UDACITY_OPENAI_API_KEY not found. Check your .env file.")

    model = OpenAIServerModel(
        model_id="gpt-4o-mini",
        api_base="https://openai.vocareum.com/v1",
        api_key=api_key,
    )

    # ---- Worker Agents ----

    inventory_worker = ToolCallingAgent(
        tools=[check_all_inventory, check_stock_level, get_delivery_estimate],
        model=model,
        name="inventory_agent",
        description=(
            "Checks current stock levels and supplier delivery estimates for paper products. "
            "Call this agent first for any customer order to verify item availability. "
            "Provide item name(s) and the request date (YYYY-MM-DD). "
            "Returns: available items, stock quantities, and estimated delivery dates."
        ),
    )

    quoting_worker = ToolCallingAgent(
        tools=[find_quote_history, get_financial_report],
        model=model,
        name="quoting_agent",
        description=(
            "Generates price quotes using historical quote data and bulk discount tiers. "
            "Call after inventory confirms availability. Provide item name, quantity, and date. "
            "Apply bulk discounts: under $50=0%, $50-$199=5%, $200-$999=10%, $1000+=15%. "
            "Ignore quote history records with total_amount=-1 (data errors). "
            "Returns: unit price, discount percentage, total price, and quote explanation."
        ),
    )

    sales_worker = ToolCallingAgent(
        tools=[record_transaction, get_current_cash_balance],
        model=model,
        name="sales_agent",
        description=(
            "Records completed sales transactions in the database and confirms updated cash balance. "
            "Call only when finalizing a confirmed purchase order. "
            "Requires: item_name (exact), quantity, total_price, date. "
            "transaction_type must be exactly 'sales' (not 'sale' or 'purchase'). "
            "price passed to record_transaction is the TOTAL price after discounts. "
            "Returns: transaction ID and updated cash balance."
        ),
    )

    # ---- Orchestrator ----

    orchestrator = ToolCallingAgent(
        tools=[],
        model=model,
        managed_agents=[inventory_worker, quoting_worker, sales_worker],
        name="orchestrator",
        description="Main coordinator for Beaver's Choice Paper Company customer requests.",
    )

    return orchestrator


def process_request(orchestrator: ToolCallingAgent, request_text: str) -> str:
    """Wrap a customer request with orchestration instructions and run it through the agent system.

    This function prepends a structured pipeline prompt to the customer request so the
    orchestrator follows the correct inventory-check -> quote -> sale -> response flow.

    Args:
        orchestrator: The configured OrchestratorAgent returned by build_agent_system().
        request_text: The raw customer request string including the date.

    Returns:
        str: Customer-facing response from the orchestrator.
    """
    task = f"""You are the order fulfillment coordinator for Beaver's Choice Paper Company \
(also known as Munder Difflin). You MUST call agents in this exact order before writing \
your final answer.

MANDATORY SEQUENCE - YOU MUST COMPLETE ALL APPLICABLE STEPS BEFORE CALLING final_answer:

STEP 1 - CALL inventory_agent (REQUIRED for every request)
Ask inventory_agent to: check all inventory as of the request date, match the customer's \
requested items to the closest available items by name, check exact stock counts, and get \
the estimated delivery date for the quantity requested.
Use the exact item names returned by check_all_inventory (e.g. "Glossy paper", "Cardstock", \
"A4 paper", "Colored paper", "Large poster paper (24x36 inches)").
If inventory_agent confirms NO matching item is in stock, skip to STEP 4.
If at least one item IS available, you MUST continue to STEP 2.

STEP 2 - CALL quoting_agent (REQUIRED when any item is available)
Ask quoting_agent to: search quote history for the available item, calculate the unit price, \
apply the correct bulk discount tier, and return the final total price.
Bulk discount tiers:
  - Order total under $50:    0% discount
  - $50 to $199:              5% discount
  - $200 to $999:             10% discount
  - $1,000 or more:           15% discount
DO NOT skip this step. DO NOT guess prices. You MUST wait for quoting_agent's response.

STEP 3 - CALL sales_agent (REQUIRED after quoting_agent responds)
Ask sales_agent to: record the transaction using the exact item name, quantity, final \
discounted total price, and the request date. transaction_type must be exactly 'sales'.
You MUST call sales_agent and receive a transaction confirmation BEFORE writing your \
final answer. DO NOT say "I will finalize" - actually call sales_agent now.

STEP 4 - WRITE final_answer
Only after completing the above steps, write a clear, professional, friendly response \
that includes ALL of the following:
  - Whether the order is fulfilled or not, and the reason
  - Item name, quantity ordered, unit price, discount percentage, and total price
  - Estimated delivery date
  - Transaction confirmation number (if a sale was completed in STEP 3)
Do NOT reveal internal database IDs, raw error messages, profit margins, or agent names.
For unavailable items, apologize and suggest contacting us for alternatives.

Customer request:
{request_text}
"""
    return orchestrator.run(task)


# ============================================================
# TEST SCENARIO RUNNER
# ============================================================

def run_test_scenarios():
    """Run all test scenarios from quote_requests_sample.csv through the multi-agent system.

    Initializes the database, builds the agent system, processes each request in date order,
    tracks cash and inventory state after each request, and saves all results to test_results.csv.

    Returns:
        list: List of result dictionaries, one per processed request.
    """
    print("Initializing Database...")
    init_database(db_engine)  # fixed: original had init_database() with no args

    try:
        quote_requests_sample = pd.read_csv("quote_requests_sample.csv")
        quote_requests_sample["request_date"] = pd.to_datetime(
            quote_requests_sample["request_date"], format="%m/%d/%y", errors="coerce"
        )
        quote_requests_sample.dropna(subset=["request_date"], inplace=True)
        quote_requests_sample = quote_requests_sample.sort_values("request_date")
    except Exception as e:
        print(f"FATAL: Error loading test data: {e}")
        return

    # Get initial financial state
    initial_date = quote_requests_sample["request_date"].min().strftime("%Y-%m-%d")
    report = generate_financial_report(initial_date)
    current_cash = report["cash_balance"]
    current_inventory = report["inventory_value"]

    # Build multi-agent system once before the request loop
    print("Building multi-agent system...")
    orchestrator = build_agent_system()

    results = []
    for idx, row in quote_requests_sample.iterrows():
        request_date = row["request_date"].strftime("%Y-%m-%d")

        print(f"\n=== Request {idx + 1} ===")
        print(f"Context: {row['job']} organizing {row['event']}")
        print(f"Request Date: {request_date}")
        print(f"Cash Balance: ${current_cash:.2f}")
        print(f"Inventory Value: ${current_inventory:.2f}")

        # Append date context to the request string
        request_with_date = f"{row['request']} (Date of request: {request_date})"

        # Process request through the multi-agent system
        try:
            response = process_request(orchestrator, request_with_date)
        except Exception as e:
            print(f"ERROR processing request {idx + 1}: {e}")
            response = (
                "We were unable to process your request at this time due to a system error. "
                "Please contact us directly and we will be happy to assist you."
            )

        # Refresh financial state after the request
        report = generate_financial_report(request_date)
        current_cash = report["cash_balance"]
        current_inventory = report["inventory_value"]

        print(f"Response: {response}")
        print(f"Updated Cash: ${current_cash:.2f}")
        print(f"Updated Inventory: ${current_inventory:.2f}")

        results.append(
            {
                "request_id": idx + 1,
                "request_date": request_date,
                "cash_balance": current_cash,
                "inventory_value": current_inventory,
                "response": response,
            }
        )

        time.sleep(1)

    # Print final financial report
    final_date = quote_requests_sample["request_date"].max().strftime("%Y-%m-%d")
    final_report = generate_financial_report(final_date)
    print("\n===== FINAL FINANCIAL REPORT =====")
    print(f"Final Cash: ${final_report['cash_balance']:.2f}")
    print(f"Final Inventory: ${final_report['inventory_value']:.2f}")

    # Save results to CSV
    pd.DataFrame(results).to_csv("test_results.csv", index=False)
    return results


if __name__ == "__main__":
    results = run_test_scenarios()
