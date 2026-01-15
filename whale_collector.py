#!/usr/bin/env python3
"""
Bitcoin Whale Transaction Collector
Collects whale transactions (>200 BTC) from Mempool.space every 30 minutes
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

# Disable SSL warnings for corporate proxies
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ============================================================
# CONFIGURATION
# ============================================================

# Parse Command Line Arguments
parser = argparse.ArgumentParser(
    prog='Whale Transaction Collector',
    description='Collects Bitcoin whale transactions (>threshold BTC) from Mempool.space'
)
parser.add_argument('-t', '--threshold', type=float, default=200,
                    help='Whale threshold in BTC (default: 200)')
parser.add_argument('-i', '--interval', type=int, default=30,
                    help='Collection interval in minutes (default: 30)')
parser.add_argument('-p', '--proxy', type=str, default=None,
                    help='Proxy URL if behind corporate firewall (e.g. http://proxy:8080)')
parser.add_argument('--once', action='store_true',
                    help='Single collection run (no scheduler, good for cron/GitHub Actions)')
parser.add_argument('--max-tx-per-block', type=int, default=0,
                    help='Max TXs to analyze per block (0 = all, default: 0)')
args = parser.parse_args()

# Config from Args
WHALE_THRESHOLD_BTC = args.threshold
COLLECTION_INTERVAL_MINUTES = args.interval
PROXY = args.proxy
MAX_TX_PER_BLOCK = args.max_tx_per_block
MEMPOOL_API = "https://mempool.space/api"
DATA_FILE = Path("data/whale_data.json")

# Storage Config
MAX_WHALE_TXS = 500  # Maximum number of whale TXs (FIFO when full)

# Set proxy only if specified
if PROXY:
    os.environ["HTTP_PROXY"] = PROXY
    os.environ["HTTPS_PROXY"] = PROXY

# ============================================================
# COLLECTOR
# ============================================================

def load_whale_data():
    """Load existing whale TXs"""
    if not DATA_FILE.exists():
        return {
            "whale_transactions": [],
            "metadata": {
                "last_collection": None,
                "total_collections": 0
            }
        }
    
    with open(DATA_FILE, 'r') as f:
        data = json.load(f)
        # Add metadata if not present (backwards compatibility)
        if "metadata" not in data:
            data["metadata"] = {
                "last_collection": None,
                "total_collections": 0
            }
        return data

def save_whale_data(data):
    """Save whale TXs"""
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def get_existing_txids():
    """Get set of all known TX-IDs for duplicate check"""
    data = load_whale_data()
    return {tx["txid"] for tx in data.get("whale_transactions", [])}

def collect_whale_transactions():
    """Collect whale TXs from Mempool.space"""
    print(f"\n{'='*60}")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting collection...")
    print(f"{'='*60}")
    
    try:
        session = requests.Session()
        if PROXY:
            session.proxies = {"http": PROXY, "https": PROXY}
            session.verify = False  # For corporate proxies
        
        # Get last 10 blocks
        print("📡 Fetching recent blocks from Mempool.space...")
        response = session.get(f"{MEMPOOL_API}/blocks", timeout=30)
        
        if response.status_code != 200:
            print(f"❌ API Error: {response.text[:200]}")
            return
            
        recent_blocks = response.json()[:10]  # Last 10 blocks
        print(f"   Analyzing {len(recent_blocks)} blocks...")
        if MAX_TX_PER_BLOCK > 0:
            print(f"   Limit: {MAX_TX_PER_BLOCK} TXs per block")
        else:
            print(f"   Analyzing ALL TXs per block")
        
        whale_threshold_satoshi = WHALE_THRESHOLD_BTC * 100_000_000
        new_whales = []
        existing_txids = get_existing_txids()
        duplicates = 0
        
        # Analyze last 10 blocks
        for block in recent_blocks:
            block_id = block.get("id")
            
            # Get all TXs of the block (batch instead of individual) with retry
            txs_response = None
            for retry in range(3):  # Max 3 attempts
                try:
                    txs_response = session.get(f"{MEMPOOL_API}/block/{block_id}/txs", timeout=30)
                    
                    if txs_response.status_code == 200:
                        break
                        
                except requests.exceptions.RequestException as e:
                    print(f"   ⚠️  Request error for block {block_id[:8]}: {type(e).__name__}")
                    txs_response = None
                    
                if retry < 2:  # Not on last attempt
                    wait_time = 2 ** retry  # Exponential backoff: 1s, 2s
                    print(f"   Retry {retry + 1}/3 for block {block_id[:8]}... (waiting {wait_time}s)")
                    time.sleep(wait_time)
            
            if txs_response is None:
                print(f"⚠️  Block {block_id[:8]}... no response after 3 attempts")
                continue
                
            if txs_response.status_code != 200:
                print(f"⚠️  Block {block_id[:8]}... not available after 3 attempts (Status: {txs_response.status_code})")
                continue
                
            txs = txs_response.json()
            
            # Analyze TXs (all or limited)
            txs_to_check = txs if MAX_TX_PER_BLOCK == 0 else txs[:MAX_TX_PER_BLOCK]
            
            for tx in txs_to_check:
                txid = tx.get("txid")
                total_output = sum(out.get("value", 0) for out in tx.get("vout", []))
                
                if total_output >= whale_threshold_satoshi:
                    # Check duplicate
                    if txid in existing_txids:
                        duplicates += 1
                        continue
                    
                    # Extract vin addresses
                    vin_addresses = []
                    for vin in tx.get("vin", []):
                        if "prevout" in vin and vin["prevout"]:
                            address = vin["prevout"].get("scriptpubkey_address", "unknown")
                            value = round(vin["prevout"].get("value", 0) / 100_000_000, 8)
                            vin_addresses.append({
                                "address": address,
                                "value": value
                            })
                    
                    # Extract vout addresses
                    vout_addresses = []
                    for vout in tx.get("vout", []):
                        address = vout.get("scriptpubkey_address", "unknown")
                        value = round(vout.get("value", 0) / 100_000_000, 8)
                        vout_addresses.append({
                            "address": address,
                            "value": value
                        })
                    
                    # New whale TX found!
                    whale_tx = {
                        "txid": txid,
                        "value_btc": round(total_output / 100_000_000, 2),
                        "fee_btc": round(tx.get("fee", 0) / 100_000_000, 6) if tx.get("fee") else 0,
                        "timestamp": datetime.fromtimestamp(block.get("timestamp")).isoformat() if block.get("timestamp") else datetime.now().isoformat(),
                        "vin_addresses": vin_addresses,
                        "vout_addresses": vout_addresses
                    }
                    new_whales.append(whale_tx)
                    print(f"🐋 Whale found: {whale_tx['value_btc']} BTC (TX: {txid[:16]}...)")
        
        # Load data (always, even if no new whales)
        data = load_whale_data()
        
        # Save new whales
        if new_whales:
            data["whale_transactions"].extend(new_whales)
            
            # Sort by timestamp (newest first for better overview)
            data["whale_transactions"] = sorted(
                data["whale_transactions"], 
                key=lambda x: x.get("timestamp", "1970-01-01T00:00:00"), 
                reverse=True
            )
            
            # FIFO: If more than MAX_WHALE_TXS, remove oldest
            removed = 0
            if len(data["whale_transactions"]) > MAX_WHALE_TXS:
                removed = len(data["whale_transactions"]) - MAX_WHALE_TXS
                data["whale_transactions"] = data["whale_transactions"][:MAX_WHALE_TXS]
            
            # Update metadata
            data["metadata"]["last_collection"] = datetime.now().isoformat()
            data["metadata"]["total_collections"] = data["metadata"].get("total_collections", 0) + 1
            data["metadata"]["last_collection_found_new"] = len(new_whales)
            
            save_whale_data(data)
            print(f"\n✅ {len(new_whales)} new whale TXs saved!")
            if removed > 0:
                print(f"   FIFO: {removed} oldest TXs removed (Max: {MAX_WHALE_TXS})")
            print(f"   Total: {len(data['whale_transactions'])} TXs in storage")
        else:
            # Update metadata even if no new TXs
            data["metadata"]["last_collection"] = datetime.now().isoformat()
            data["metadata"]["total_collections"] = data["metadata"].get("total_collections", 0) + 1
            data["metadata"]["last_collection_found_new"] = 0
            save_whale_data(data)
            
            print(f"\n✅ No new whale TXs found")
        
        if duplicates > 0:
            print(f"ℹ️  {duplicates} duplicates skipped")
        
        # Statistics
        data = load_whale_data()
        total_whales = len(data["whale_transactions"])
        total_volume = sum(tx["value_btc"] for tx in data["whale_transactions"])
        
        print(f"\n📊 Total: {total_whales} whale TXs | {total_volume:,.2f} BTC")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")

# ============================================================
# SCHEDULER
# ============================================================

def run_scheduler():
    """Start continuous collection"""
    print(f"""
══════════════════════════════════════════════════════════
     Bitcoin Whale Transaction Collector                  
                                                          
  Threshold: {WHALE_THRESHOLD_BTC} BTC                    
  Interval:  {COLLECTION_INTERVAL_MINUTES} minutes        
  API:       Mempool.space                                
  Storage:   {DATA_FILE}                                  
══════════════════════════════════════════════════════════
    """)
    
    # First collection immediately
    collect_whale_transactions()
    
    # Schedule every N minutes
    schedule.every(COLLECTION_INTERVAL_MINUTES).minutes.do(collect_whale_transactions)
    
    print(f"⏰ Scheduler running - next collection in {COLLECTION_INTERVAL_MINUTES} minutes")
    print("   (Ctrl+C to stop)\n")
    
    while True:
        schedule.run_pending()
        time.sleep(1)

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    try:
        if args.once:
            # Single collection run (for cron/GitHub Actions)
            collect_whale_transactions()
        else:
            # Continuous scheduler mode
            run_scheduler()
    except KeyboardInterrupt:
        print("\n\n👋 Collector stopped")
