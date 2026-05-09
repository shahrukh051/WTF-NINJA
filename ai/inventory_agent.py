import os
from datetime import datetime, date

try:
    from langchain.agents import AgentExecutor, create_react_agent
    from langchain_openai import ChatOpenAI
    from langchain.tools import Tool
    from langchain.prompts import PromptTemplate
    LANGCHAIN_IMPORT_ERROR = None
except ImportError as exc:
    AgentExecutor = create_react_agent = ChatOpenAI = None
    LANGCHAIN_IMPORT_ERROR = exc

    class Tool:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class PromptTemplate:
        @staticmethod
        def from_template(template):
            return template

from database import (
    get_all_inventory,
    get_sales_summary,
    get_expiring_medicines,
    get_low_stock_medicines
)

# LangChain points to your local vLLM server
llm = None
if ChatOpenAI is not None:
    llm = ChatOpenAI(
        base_url=os.getenv("VLLM_BASE_URL", "http://localhost:8001/v1"),
        api_key=os.getenv("VLLM_API_KEY", "dummy-key"),
        model=os.getenv("VISION_MODEL", "meta-llama/Llama-3.2-11B-Vision-Instruct"),
        temperature=0.2,
        max_tokens=2048
    )

# ── TOOL FUNCTIONS ─────────────────────────────────────────────────────────────

def tool_check_expiry(days_str: str = "30") -> str:
    try:
        days = int(days_str.strip()) if days_str.strip().isdigit() else 30
        rows = get_expiring_medicines(days)
        if not rows:
            return f"✅ No medicines expiring within {days} days."
        lines = [f"⚠️ Medicines expiring within {days} days:"]
        for r in rows:
            lines.append(
                f"  - {r['medicine_name']} | Stock: {r['quantity']} units | "
                f"Expiry: {r['expiry_date']} | Batch: {r['batch_number']}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


def tool_check_low_stock(threshold_str: str = "10") -> str:
    try:
        threshold = int(threshold_str.strip()) if threshold_str.strip().isdigit() else 10
        rows = get_low_stock_medicines(threshold)
        if not rows:
            return f"✅ All medicines are above {threshold} units."
        lines = [f"🔴 Low stock medicines (below {threshold} units):"]
        for r in rows:
            lines.append(
                f"  - {r['medicine_name']} | Current: {r['quantity']} units | "
                f"Reorder Level: {r['reorder_level']} units"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


def tool_get_sales(_: str = "") -> str:
    try:
        sales = get_sales_summary()
        if not sales:
            return "No sales data available yet."
        lines = ["📊 Sales Summary (total units sold):"]
        for s in sales:
            lines.append(f"  - {s['medicine_name']}: {s['total_sold']} units")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


def tool_get_inventory(_: str = "") -> str:
    try:
        items = get_all_inventory()
        lines = [f"📦 Full Inventory ({len(items)} medicines):"]
        for item in items:
            lines.append(
                f"  - {item['medicine_name']} | Stock: {item['quantity']} | "
                f"Price: ₹{item['unit_price']} | Expiry: {item['expiry_date']}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


def tool_reorder_suggestions(_: str = "") -> str:
    """Calculate reorder suggestions based on sales velocity"""
    try:
        sales = get_sales_summary()
        low_stock = get_low_stock_medicines(10)
        low_names = {r["medicine_name"] for r in low_stock}
        sales_map = {s["medicine_name"]: s["total_sold"] for s in sales}

        suggestions = []
        for name in low_names:
            sold = sales_map.get(name, 5)
            # Suggest 30-day buffer based on sales velocity
            suggested_qty = max(sold * 2, 20)
            suggestions.append(
                f"  - {name}: Order {suggested_qty} units "
                f"(based on {sold} units sold history)"
            )

        if not suggestions:
            return "✅ No reorder needed right now."

        lines = ["🛒 Reorder Suggestions:"] + suggestions
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


# ── AGENT SETUP ────────────────────────────────────────────────────────────────

tools = [
    Tool(
        name="CheckExpiryMedicines",
        func=tool_check_expiry,
        description=(
            "Checks which medicines are expiring soon. "
            "Input: number of days as string e.g. '30'"
        )
    ),
    Tool(
        name="CheckLowStock",
        func=tool_check_low_stock,
        description=(
            "Checks medicines with stock below a threshold. "
            "Input: threshold number as string e.g. '10'"
        )
    ),
    Tool(
        name="GetSalesPattern",
        func=tool_get_sales,
        description="Gets sales history to understand demand. Input: empty string"
    ),
    Tool(
        name="GetFullInventory",
        func=tool_get_inventory,
        description="Gets complete current inventory list. Input: empty string"
    ),
    Tool(
        name="GetReorderSuggestions",
        func=tool_reorder_suggestions,
        description="Calculates suggested reorder quantities for low-stock items. Input: empty string"
    ),
]

AGENT_PROMPT = PromptTemplate.from_template("""You are a pharmacy inventory management assistant for an Indian medical store called Aushadhi Vault.
Your job is to generate a clear, actionable daily inventory report.

You have access to these tools:
{tools}

Tool names: {tool_names}

Use this exact format:
Thought: Think about what you need to check
Action: ToolName
Action Input: input string
Observation: result from tool
... (use each tool once)
Thought: I now have all the information needed
Final Answer: Write the complete daily report

The report must include:
1. 🚨 URGENT - Medicines expiring within 30 days
2. 🔴 LOW STOCK - Medicines below 10 units
3. 🛒 REORDER - Suggested reorder quantities
4. ✅ SUMMARY - Overall pharmacy health in 2-3 lines

Keep the report clear and easy to read for a pharmacy owner.
Use ₹ for prices. Use Indian medicine names.

{agent_scratchpad}

Begin!

Question: {input}""")


def generate_daily_report() -> dict:
    """
    Main entry point.
    Returns a full daily inventory report from the LangChain agent.
    """
    try:
        if LANGCHAIN_IMPORT_ERROR is not None:
            raise RuntimeError(
                f"LangChain dependencies are not installed: {LANGCHAIN_IMPORT_ERROR}"
            )
        agent = create_react_agent(llm, tools, AGENT_PROMPT)
        executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            max_iterations=8,
            handle_parsing_errors=True,
            return_intermediate_steps=False
        )

        result = executor.invoke({
            "input": (
                "Generate the complete daily inventory report for today. "
                "Check expiry alerts, low stock, and provide reorder suggestions."
            )
        })

        return {
            "success": True,
            "report": result["output"],
            "generated_at": datetime.now().isoformat(),
            "date": date.today().isoformat()
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "report": "Agent failed to generate report. Check if vLLM server is running.",
            "generated_at": datetime.now().isoformat(),
            "date": date.today().isoformat()
        }


def generate_report_mock() -> dict:
    """Returns mock report when vLLM is not running — for testing"""
    return {
        "success": True,
        "report": (
            "🚨 URGENT — EXPIRY ALERTS\n"
            "  - Amoxicillin 500mg: 3 units | Expires in 10 days\n"
            "  - Ibuprofen 400mg: 4 units | Expires in 15 days\n"
            "  - Metformin 500mg: 5 units | Expires in 18 days\n\n"
            "🔴 LOW STOCK\n"
            "  - Amoxicillin 500mg: only 3 units remaining\n"
            "  - Ibuprofen 400mg: only 4 units remaining\n"
            "  - Metformin 500mg: only 5 units remaining\n"
            "  - Azithromycin 250mg: only 8 units remaining\n\n"
            "🛒 REORDER SUGGESTIONS\n"
            "  - Amoxicillin 500mg: Order 20 units\n"
            "  - Ibuprofen 400mg: Order 30 units\n"
            "  - Paracetamol 500mg: Order 50 units (high demand)\n\n"
            "✅ SUMMARY\n"
            "  Pharmacy has 20 medicines in inventory. "
            "5 medicines need urgent attention due to low stock or expiry. "
            "Overall stock health is moderate — reorder recommended for 3 items."
        ),
        "generated_at": datetime.now().isoformat(),
        "date": date.today().isoformat(),
        "model": "MOCK"
    }
