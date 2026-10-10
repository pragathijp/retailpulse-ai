import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from context_builder import build_context  # noqa: E402

def ask_assistant(query: str) -> str:
    ctx = build_context()
    
    # Grounded rule: Only present figures directly from JSON context
    response = (
        f"📊 **RetailPulse AI Grounded Summary**\n"
        f"• **Total Net Revenue**: £{ctx['store_metrics']['total_net_revenue']:,.2f}\n"
        f"• **Total Valid Orders**: {ctx['store_metrics']['total_orders']:,}\n"
        f"• **Average Order Value (AOV)**: £{ctx['store_metrics']['aov']:,.2f}\n"
        f"• **Unattributed Guest Revenue**: £{ctx['reconciliation_audit']['unattributed_guest_revenue']:,.2f}\n"
        f"• **Unexplained Audit Delta**: £{ctx['reconciliation_audit']['unexplained_variance']:.4f}\n"
        f"\n*Sources: `fact_sales.parquet`, `audit_revenue_variance.parquet`*"
    )
    return response

if __name__ == "__main__":
    print(ask_assistant("What is our total revenue and order count?"))