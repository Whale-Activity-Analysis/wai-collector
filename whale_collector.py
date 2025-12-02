#!/usr/bin/env python3
"""
Bitcoin Whale Transaction Collector
Sammelt Whale Transactions (>200 BTC) von Mempool.space alle 30 Minuten
"""

import os
import json
import requests
import schedule
import time
import urllib3
import argparse
from datetime import datetime
from pathlib import Path

# Disable SSL warnings für Corporate Proxies
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ============================================================
# CONFIGURATION
# ============================================================

# Parse Command Line Arguments
parser = argparse.ArgumentParser(
    prog='Whale Transaction Collector',
    description='Sammelt Bitcoin Whale Transactions (>t BTC) von Mempool.space'
)
parser.add_argument('-t', '--threshold', type=float, default=200,
                    help='Whale-Schwellwert in BTC (default: 200)')
parser.add_argument('-i', '--interval', type=int, default=30,
                    help='Collection-Intervall in Minuten (default: 30)')
parser.add_argument('-p', '--proxy', type=str, default=None,
                    help='Proxy URL falls hinter Corporate Firewall (z.B. http://proxy:8080)')
parser.add_argument('--once', action='store_true',
                    help='Einmalige Collection (kein Scheduler, gut für Cron/GitHub Actions)')
args = parser.parse_args()

# Config aus Args
WHALE_THRESHOLD_BTC = args.threshold
COLLECTION_INTERVAL_MINUTES = args.interval
PROXY = args.proxy
MEMPOOL_API = "https://mempool.space/api"
DATA_FILE = Path("data/whale_data.json")

# Setze Proxy nur wenn angegeben
if PROXY:
    os.environ["HTTP_PROXY"] = PROXY
    os.environ["HTTPS_PROXY"] = PROXY

# ============================================================
# COLLECTOR
# ============================================================

def load_whale_data():
    """Lade existierende Whale TXs"""
    if not DATA_FILE.exists():
        return {"whale_transactions": []}
    
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_whale_data(data):
    """Speichere Whale TXs"""
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def get_existing_txids():
    """Hole Set aller bekannten TX-IDs für Duplikat-Check"""
    data = load_whale_data()
    return {tx["txid"] for tx in data.get("whale_transactions", [])}

def collect_whale_transactions():
    """Sammle Whale TXs von Mempool.space"""
    print(f"\n{'='*60}")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starte Collection...")
    print(f"{'='*60}")
    
    try:
        session = requests.Session()
        if PROXY:
            session.proxies = {"http": PROXY, "https": PROXY}
            session.verify = False  # Für Corporate Proxies
        
        # Hole letzte 10 Blöcke
        print("📡 Hole letzte Blöcke von Mempool.space...")
        response = session.get(f"{MEMPOOL_API}/blocks", timeout=30)
        
        if response.status_code != 200:
            print(f"❌ API Error: {response.text[:200]}")
            return
            
        recent_blocks = response.json()[:10]  # Letzte 10 Blöcke
        print(f"   Analysiere {len(recent_blocks)} Blöcke...")
        
        whale_threshold_satoshi = WHALE_THRESHOLD_BTC * 100_000_000
        new_whales = []
        existing_txids = get_existing_txids()
        duplicates = 0
        
        # Analysiere letzte 10 Blöcke
        for block in recent_blocks:
            block_id = block.get("id")
            
            txids_response = session.get(f"{MEMPOOL_API}/block/{block_id}/txids", timeout=30)
            
            if txids_response.status_code != 200:
                print(f"⚠️  Block {block_id[:8]}... nicht verfügbar")
                continue
                
            txids = txids_response.json()
            
            for txid in txids[:100]:  # Erste 100 TXs pro Block
                # Hole TX Details
                tx_response = session.get(f"{MEMPOOL_API}/tx/{txid}", timeout=30)
                
                if tx_response.status_code != 200:
                    continue
                    
                tx = tx_response.json()
                total_output = sum(out.get("value", 0) for out in tx.get("vout", []))
                
                if total_output >= whale_threshold_satoshi:
                    # Check Duplikat
                    if txid in existing_txids:
                        duplicates += 1
                        continue
                    
                    # Neue Whale TX gefunden!
                    whale_tx = {
                        "txid": txid,
                        "value_btc": round(total_output / 100_000_000, 2),
                        "fee_btc": round(tx.get("fee", 0) / 100_000_000, 6) if tx.get("fee") else 0,
                        "timestamp": datetime.now().isoformat()
                    }
                    new_whales.append(whale_tx)
                    print(f"🐋 Whale gefunden: {whale_tx['value_btc']} BTC (TX: {txid[:16]}...)")
        
        # Speichere neue Whales
        if new_whales:
            data = load_whale_data()
            data["whale_transactions"].extend(new_whales)
            
            # Sortiere nach Wert (größte zuerst) und behalte Top 100
            data["whale_transactions"] = sorted(
                data["whale_transactions"], 
                key=lambda x: x["value_btc"], 
                reverse=True
            )[:100]
            
            save_whale_data(data)
            print(f"\n✅ {len(new_whales)} neue Whale TXs gespeichert!")
        else:
            print(f"\n✅ Keine neuen Whale TXs gefunden")
        
        if duplicates > 0:
            print(f"ℹ️  {duplicates} Duplikate übersprungen")
        
        # Statistik
        data = load_whale_data()
        total_whales = len(data["whale_transactions"])
        total_volume = sum(tx["value_btc"] for tx in data["whale_transactions"])
        
        print(f"\n📊 Gesamt: {total_whales} Whale TXs | {total_volume:,.2f} BTC")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"❌ Fehler: {e}")

# ============================================================
# SCHEDULER
# ============================================================

def run_scheduler():
    """Starte kontinuierliche Collection"""
    print(f"""
══════════════════════════════════════════════════════════
     Bitcoin Whale Transaction Collector                  
                                                          
  Threshold: {WHALE_THRESHOLD_BTC} BTC                    
  Interval:  {COLLECTION_INTERVAL_MINUTES} Minuten        
  API:       Mempool.space                                
  Storage:   {DATA_FILE}                                  
══════════════════════════════════════════════════════════
    """)
    
    # Erste Collection sofort
    collect_whale_transactions()
    
    # Schedule alle 30 Minuten
    schedule.every(COLLECTION_INTERVAL_MINUTES).minutes.do(collect_whale_transactions)
    
    print(f"⏰ Scheduler läuft - nächste Collection in {COLLECTION_INTERVAL_MINUTES} Minuten")
    print("   (Strg+C zum Beenden)\n")
    
    while True:
        schedule.run_pending()
        time.sleep(1)

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    try:
        if args.once:
            # Einmalige Collection (für Cron/GitHub Actions)
            collect_whale_transactions()
        else:
            # Kontinuierlicher Scheduler Mode
            run_scheduler()
    except KeyboardInterrupt:
        print("\n\n👋 Collector gestoppt")
