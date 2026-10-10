import duckdb
import pandas as pd
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import parquet  # noqa: E402

def build_context():
    conn = duckdb.connect()
    
    # Extract store totals
    df_fact = conn.read_parquet(parquet('fact_sales')).df()
    df_audit = conn.read_parquet(parquet('audit_revenue_variance')).df()
    
    total_net = float(df_fact['net_revenue_line'].sum())
    total_orders = int(df_fact[df_fact['is_valid_sale']]['invoice_no'].nunique())
    
    row_audit = df_audit.iloc[0]

    context = {
        "store_metrics": {
            "total_net_revenue": round(total_net, 2),
            "total_orders": total_orders,
            "aov": round(total_net / total_orders, 2) if total_orders > 0 else 0
        },
        "reconciliation_audit": {
            "store_net_revenue": float(row_audit['total_store_net_revenue']),
            "rfm_net_revenue": float(row_audit['total_rfm_net_revenue']),
            "unattributed_guest_revenue": float(row_audit['unattributed_net_revenue']),
            "unexplained_variance": float(row_audit['unexplained_revenue'])
        }
    }
    
    conn.close()
    return context

if __name__ == "__main__":
    ctx = build_context()
    print(json.dumps(ctx, indent=2))