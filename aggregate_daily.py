#!/usr/bin/env python3
"""
Daily Whale Transaction Aggregator
Generates daily metrics from whale_data.json
"""

import json
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# ============================================================
# CONFIGURATION
# ============================================================
WHALE_DATA_FILE = Path("data/whale_data.json")
DAILY_METRICS_FILE = Path("data/daily_metrics.json")

# ============================================================
# AGGREGATION
# ============================================================

def load_whale_data():
    """Load whale TXs"""
    if not WHALE_DATA_FILE.exists():
        return {"whale_transactions": []}
    
    with open(WHALE_DATA_FILE, 'r') as f:
        return json.load(f)

def save_daily_metrics(metrics):
    """Save daily metrics"""
    DAILY_METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DAILY_METRICS_FILE, 'w') as f:
        json.dump(metrics, f, indent=2)

def aggregate_daily_metrics():
    """Aggregate whale TXs to daily metrics"""
    print("📊 Aggregating whale transactions to daily metrics...")
    
    data = load_whale_data()
    whale_txs = data.get("whale_transactions", [])
    
    # Group by day
    daily_groups = defaultdict(list)
    
    for tx in whale_txs:
        # Parse timestamp (ISO format: "2025-12-02T15:52:25.685738")
        timestamp = tx.get("timestamp", "")
        try:
            dt = datetime.fromisoformat(timestamp)
            date = dt.date().isoformat()  # "2025-12-02"
            daily_groups[date].append(tx)
        except ValueError:
            print(f"⚠️  Invalid timestamp: {timestamp}")
            continue
    
    # Always add entry for today (even if 0)
    today = datetime.now().date().isoformat()
    if today not in daily_groups:
        daily_groups[today] = []
    
    # Calculate metrics per day
    daily_metrics = []
    
    for date in sorted(daily_groups.keys(), reverse=True):  # Newest first
        txs = daily_groups[date]
        
        whale_tx_count = len(txs)
        whale_tx_volume_btc = round(sum(tx["value_btc"] for tx in txs), 2)
        avg_whale_fee_btc = round(sum(tx["fee_btc"] for tx in txs) / whale_tx_count, 6) if whale_tx_count > 0 else 0
        max_whale_tx_btc = round(max(tx["value_btc"] for tx in txs), 2) if txs else 0

        # Exchange flow metrics
        exchange_inflow_btc = 0.0
        exchange_outflow_btc = 0.0
        exchange_whale_tx_count = 0

        for tx in txs:
            cls = tx.get("classification", "unknown")
            if cls != "unknown":
                exchange_whale_tx_count += 1
            # Only attribute volume when direction is clear
            if cls == "inflow":
                exchange_inflow_btc += tx.get("value_btc", 0.0)
            elif cls == "outflow":
                exchange_outflow_btc += tx.get("value_btc", 0.0)
            # For 'mixed' we do not allocate to in/out volumes to avoid double counting

        exchange_inflow_btc = round(exchange_inflow_btc, 2)
        exchange_outflow_btc = round(exchange_outflow_btc, 2)
        exchange_netflow_btc = round(exchange_inflow_btc - exchange_outflow_btc, 2)
        denom = exchange_inflow_btc + exchange_outflow_btc
        exchange_flow_ratio = round(exchange_inflow_btc / denom, 4) if denom > 0 else None
        
        metric = {
            "date": date,
            "whale_tx_count": whale_tx_count,
            "whale_tx_volume_btc": whale_tx_volume_btc,
            "avg_whale_fee_btc": avg_whale_fee_btc,
            "max_whale_tx_btc": max_whale_tx_btc,
            # Exchange flow metrics
            "exchange_inflow_btc": exchange_inflow_btc,
            "exchange_outflow_btc": exchange_outflow_btc,
            "exchange_netflow_btc": exchange_netflow_btc,
            "exchange_flow_ratio": exchange_flow_ratio,
            "exchange_whale_tx_count": exchange_whale_tx_count
        }
        
        daily_metrics.append(metric)
        print(f"   {date}: {whale_tx_count} TXs, {whale_tx_volume_btc:,.2f} BTC")
    
    # Save metrics
    output = {
        "generated_at": datetime.now().isoformat(),
        "total_days": len(daily_metrics),
        "daily_metrics": daily_metrics
    }
    
    save_daily_metrics(output)
    print(f"\n✅ {len(daily_metrics)} daily metrics saved: {DAILY_METRICS_FILE}")
    
    return output

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    try:
        metrics = aggregate_daily_metrics()
        
        # Show last 5 days
        if metrics and metrics.get("daily_metrics"):
            print("\n📈 Last 5 days:")
            print("-" * 80)
            for day in metrics["daily_metrics"][:5]:
                print(f"{day['date']}: {day['whale_tx_count']:>3} TXs | "
                      f"{day['whale_tx_volume_btc']:>10,.2f} BTC | "
                      f"Max: {day['max_whale_tx_btc']:>8,.2f} BTC")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
