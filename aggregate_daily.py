#!/usr/bin/env python3
"""
Daily Whale Transaction Aggregator
Erzeugt Tagesmetriken aus whale_data.json
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
    """Lade Whale TXs"""
    if not WHALE_DATA_FILE.exists():
        return {"whale_transactions": []}
    
    with open(WHALE_DATA_FILE, 'r') as f:
        return json.load(f)

def save_daily_metrics(metrics):
    """Speichere Daily Metrics"""
    DAILY_METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DAILY_METRICS_FILE, 'w') as f:
        json.dump(metrics, f, indent=2)

def aggregate_daily_metrics():
    """Aggregiere Whale TXs zu Tagesmetriken"""
    print("📊 Aggregiere Whale Transactions zu Tagesmetriken...")
    
    data = load_whale_data()
    whale_txs = data.get("whale_transactions", [])
    
    # Gruppiere nach Tag
    daily_groups = defaultdict(list)
    
    for tx in whale_txs:
        # Parse Timestamp (ISO format: "2025-12-02T15:52:25.685738")
        timestamp = tx.get("timestamp", "")
        try:
            dt = datetime.fromisoformat(timestamp)
            date = dt.date().isoformat()  # "2025-12-02"
            daily_groups[date].append(tx)
        except ValueError:
            print(f"⚠️  Ungültiger Timestamp: {timestamp}")
            continue
    
    # Füge immer einen Eintrag für heute hinzu (auch wenn 0)
    today = datetime.now().date().isoformat()
    if today not in daily_groups:
        daily_groups[today] = []
    
    # Berechne Metriken pro Tag
    daily_metrics = []
    
    for date in sorted(daily_groups.keys(), reverse=True):  # Neueste zuerst
        txs = daily_groups[date]
        
        whale_tx_count = len(txs)
        whale_tx_volume_btc = round(sum(tx["value_btc"] for tx in txs), 2)
        avg_whale_fee_btc = round(sum(tx["fee_btc"] for tx in txs) / whale_tx_count, 6) if whale_tx_count > 0 else 0
        max_whale_tx_btc = round(max(tx["value_btc"] for tx in txs), 2) if txs else 0
        
        metric = {
            "date": date,
            "whale_tx_count": whale_tx_count,
            "whale_tx_volume_btc": whale_tx_volume_btc,
            "avg_whale_fee_btc": avg_whale_fee_btc,
            "max_whale_tx_btc": max_whale_tx_btc
        }
        
        daily_metrics.append(metric)
        print(f"   {date}: {whale_tx_count} TXs, {whale_tx_volume_btc:,.2f} BTC")
    
    # Speichere Metriken
    output = {
        "generated_at": datetime.now().isoformat(),
        "total_days": len(daily_metrics),
        "daily_metrics": daily_metrics
    }
    
    save_daily_metrics(output)
    print(f"\n✅ {len(daily_metrics)} Tages-Metriken gespeichert: {DAILY_METRICS_FILE}")
    
    return output

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    try:
        metrics = aggregate_daily_metrics()
        
        # Zeige letzte 5 Tage
        if metrics and metrics.get("daily_metrics"):
            print("\n📈 Letzte 5 Tage:")
            print("-" * 80)
            for day in metrics["daily_metrics"][:5]:
                print(f"{day['date']}: {day['whale_tx_count']:>3} TXs | "
                      f"{day['whale_tx_volume_btc']:>10,.2f} BTC | "
                      f"Max: {day['max_whale_tx_btc']:>8,.2f} BTC")
            
    except Exception as e:
        print(f"❌ Fehler: {e}")
        import traceback
        traceback.print_exc()
