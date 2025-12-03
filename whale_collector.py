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
    description='Sammelt Bitcoin Whale Transactions (>threshold BTC) von Mempool.space'
)
parser.add_argument('-t', '--threshold', type=float, default=200,
                    help='Whale-Schwellwert in BTC (default: 200)')
parser.add_argument('-i', '--interval', type=int, default=30,
                    help='Collection-Intervall in Minuten (default: 30)')
parser.add_argument('-p', '--proxy', type=str, default=None,
                    help='Proxy URL falls hinter Corporate Firewall (z.B. http://proxy:8080)')
parser.add_argument('--once', action='store_true',
                    help='Einmalige Collection (kein Scheduler, gut für Cron/GitHub Actions)')
parser.add_argument('--max-tx-per-block', type=int, default=0,
                    help='Max TXs pro Block analysieren (0 = alle, default: 0)')
args = parser.parse_args()

# Config aus Args
WHALE_THRESHOLD_BTC = args.threshold
COLLECTION_INTERVAL_MINUTES = args.interval
PROXY = args.proxy
MAX_TX_PER_BLOCK = args.max_tx_per_block
MEMPOOL_API = "https://mempool.space/api"
DATA_FILE = Path("data/whale_data.json")

# Storage Config
MAX_WHALE_TXS = 500  # Maximale Anzahl Whale TXs (FIFO wenn voll)

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
        if MAX_TX_PER_BLOCK > 0:
            print(f"   Limit: {MAX_TX_PER_BLOCK} TXs pro Block")
        else:
            print(f"   Analysiere ALLE TXs pro Block")
        
        whale_threshold_satoshi = WHALE_THRESHOLD_BTC * 100_000_000
        new_whales = []
        existing_txids = get_existing_txids()
        duplicates = 0
        
        # Analysiere letzte 10 Blöcke
        for block in recent_blocks:
            block_id = block.get("id")
            
            # Hole alle TXs des Blocks (batch statt einzeln) mit Retry
            txs_response = None
            for retry in range(3):  # Max 3 Versuche
                txs_response = session.get(f"{MEMPOOL_API}/block/{block_id}/txs", timeout=30)
                
                if txs_response.status_code == 200:
                    break
                    
                if retry < 2:  # Nicht beim letzten Versuch
                    wait_time = 2 ** retry  # Exponential backoff: 1s, 2s
                    print(f"   Retry {retry + 1}/3 für Block {block_id[:8]}... (warte {wait_time}s)")
                    time.sleep(wait_time)
            
            if txs_response.status_code != 200:
                print(f"⚠️  Block {block_id[:8]}... nicht verfügbar nach 3 Versuchen (Status: {txs_response.status_code})")
                continue
                
            txs = txs_response.json()
            
            # Analysiere TXs (alle oder limitiert)
            txs_to_check = txs if MAX_TX_PER_BLOCK == 0 else txs[:MAX_TX_PER_BLOCK]
            
            for tx in txs_to_check:
                txid = tx.get("txid")
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
                        "timestamp": datetime.fromtimestamp(block.get("timestamp")).isoformat() if block.get("timestamp") else datetime.now().isoformat()
                    }
                    new_whales.append(whale_tx)
                    print(f"🐋 Whale gefunden: {whale_tx['value_btc']} BTC (TX: {txid[:16]}...)")
        
        # Speichere neue Whales
        if new_whales:
            data = load_whale_data()
            data["whale_transactions"].extend(new_whales)
            
            # Sortiere nach Timestamp (neueste zuerst für bessere Übersicht)
            data["whale_transactions"] = sorted(
                data["whale_transactions"], 
                key=lambda x: x.get("timestamp", ""), 
                reverse=True
            )
            
            # FIFO: Wenn mehr als MAX_WHALE_TXS, entferne älteste
            removed = 0
            if len(data["whale_transactions"]) > MAX_WHALE_TXS:
                removed = len(data["whale_transactions"]) - MAX_WHALE_TXS
                data["whale_transactions"] = data["whale_transactions"][:MAX_WHALE_TXS]
            
            save_whale_data(data)
            print(f"\n✅ {len(new_whales)} neue Whale TXs gespeichert!")
            if removed > 0:
                print(f"   FIFO: {removed} älteste TXs entfernt (Max: {MAX_WHALE_TXS})")
            print(f"   Total: {len(data['whale_transactions'])} TXs im Speicher")
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
