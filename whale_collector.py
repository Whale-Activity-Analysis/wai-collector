#!/usr/bin/env python3
"""
Bitcoin Whale Transaction Collector
Collects whale transactions (>200 BTC net transfer) from Mempool.space every 10 minutes

Net Transfer Calculation:
- Identifies all input addresses from a transaction
- Subtracts outputs going back to input addresses (change outputs)
- Only counts actual BTC transferred to NEW addresses
- Example: 2104 BTC input → 2103.99 BTC change + 0.01 BTC transfer = 0.01 BTC net transfer
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
parser.add_argument('-i', '--interval', type=int, default=10,
                    help='Collection interval in minutes (default: 10)')
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
EXCHANGES_FILE = Path("data/exchange_wallet_adresses.json")
EXCHANGE_MAP = {}  # Will be loaded on first use

# Set proxy only if specified
if PROXY:
    os.environ["HTTP_PROXY"] = PROXY
    os.environ["HTTPS_PROXY"] = PROXY

# ============================================================
# EXCHANGE CLASSIFICATION
# ============================================================

def load_exchange_map():
    """Load exchange addresses for classification"""
    global EXCHANGE_MAP
    if EXCHANGE_MAP:
        return EXCHANGE_MAP
    
    if not EXCHANGES_FILE.exists():
        return {}
    
    try:
        with open(EXCHANGES_FILE, 'r') as f:
            data = json.load(f)
        
        for entry in data.get("addresses", []):
            address = entry["address"]
            label = entry["label"]
            EXCHANGE_MAP[address] = label
        
        return EXCHANGE_MAP
    except Exception as e:
        print(f"[WARNING] Could not load exchange addresses: {e}")
        return {}

def classify_transaction(tx, exchange_map):
    """
    Classify transaction as inflow/outflow based on exchange addresses
    Returns: (classification, exchange_details)
    """
    vin_addresses = {addr["address"] for addr in tx.get("vin_addresses", [])}
    vout_addresses = {addr["address"] for addr in tx.get("vout_addresses", [])}
    
    exchange_inputs = {addr: exchange_map[addr] for addr in vin_addresses if addr in exchange_map}
    exchange_outputs = {addr: exchange_map[addr] for addr in vout_addresses if addr in exchange_map}
    
    exchange_details = {}
    
    if exchange_inputs and exchange_outputs:
        classification = "mixed"
        exchange_details = {
            "outflow_exchanges": exchange_inputs,
            "inflow_exchanges": exchange_outputs
        }
    elif exchange_inputs:
        classification = "outflow"
        exchange_details = {
            "exchange_address": list(exchange_inputs.keys())[0],
            "exchange_name": list(exchange_inputs.values())[0]
        }
    elif exchange_outputs:
        classification = "inflow"
        exchange_details = {
            "exchange_address": list(exchange_outputs.keys())[0],
            "exchange_name": list(exchange_outputs.values())[0]
        }
    else:
        classification = "unknown"
        exchange_details = {}
    
    return classification, exchange_details

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
    
    # Load exchange map once at start of collection
    global EXCHANGE_MAP
    if not EXCHANGE_MAP:
        EXCHANGE_MAP = load_exchange_map()
        if EXCHANGE_MAP:
            print(f"[INFO] Loaded {len(EXCHANGE_MAP)} exchange addresses\n")
    
    try:
        session = requests.Session()
        if PROXY:
            session.proxies = {"http": PROXY, "https": PROXY}
            session.verify = False  # For corporate proxies
        
        # Get last 10 blocks
        print("[INFO] Fetching recent blocks from Mempool.space...")
        response = session.get(f"{MEMPOOL_API}/blocks", timeout=30)
        
        if response.status_code != 200:
            print(f"[ERROR] API Error: {response.text[:200]}")
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
                    print(f"   [WARNING] Request error for block {block_id[:8]}: {type(e).__name__}")
                    txs_response = None
                    
                if retry < 2:  # Not on last attempt
                    wait_time = 2 ** retry  # Exponential backoff: 1s, 2s
                    print(f"   Retry {retry + 1}/3 for block {block_id[:8]}... (waiting {wait_time}s)")
                    time.sleep(wait_time)
            
            if txs_response is None:
                print(f"[WARNING] Block {block_id[:8]}... no response after 3 attempts")
                continue
                
            if txs_response.status_code != 200:
                print(f"[WARNING] Block {block_id[:8]}... not available after 3 attempts (Status: {txs_response.status_code})")
                continue
                
            txs = txs_response.json()
            
            # Analyze TXs (all or limited)
            txs_to_check = txs if MAX_TX_PER_BLOCK == 0 else txs[:MAX_TX_PER_BLOCK]
            
            for tx in txs_to_check:
                txid = tx.get("txid")
                
                # Extract vin addresses (inputs)
                vin_addresses = []
                input_address_set = set()
                for vin in tx.get("vin", []):
                    if "prevout" in vin and vin["prevout"]:
                        address = vin["prevout"].get("scriptpubkey_address", "unknown")
                        value = round(vin["prevout"].get("value", 0) / 100_000_000, 8)
                        vin_addresses.append({
                            "address": address,
                            "value": value
                        })
                        input_address_set.add(address)
                
                # Extract vout addresses (outputs) and calculate net transfer
                # Net transfer = outputs that don't go back to input addresses (change excluded)
                vout_addresses = []
                net_transfer_satoshi = 0
                for vout in tx.get("vout", []):
                    address = vout.get("scriptpubkey_address", "unknown")
                    value_satoshi = vout.get("value", 0)
                    value_btc = round(value_satoshi / 100_000_000, 8)
                    vout_addresses.append({
                        "address": address,
                        "value": value_btc
                    })
                    
                    # Only count outputs that go to NEW addresses (exclude change)
                    if address not in input_address_set:
                        net_transfer_satoshi += value_satoshi
                
                # Check if net transfer (excluding change) exceeds whale threshold
                if net_transfer_satoshi >= whale_threshold_satoshi:
                    # Check duplicate
                    if txid in existing_txids:
                        duplicates += 1
                        continue
                    
                    # New whale TX found!
                    whale_tx = {
                        "txid": txid,
                        "value_btc": round(net_transfer_satoshi / 100_000_000, 2),
                        "fee_btc": round(tx.get("fee", 0) / 100_000_000, 6) if tx.get("fee") else 0,
                        "timestamp": datetime.fromtimestamp(block.get("timestamp")).isoformat() if block.get("timestamp") else datetime.now().isoformat(),
                        "vin_addresses": vin_addresses,
                        "vout_addresses": vout_addresses
                    }
                    
                    # Classify transaction (inflow/outflow/mixed/unknown)
                    classification, exchange_details = classify_transaction(whale_tx, EXCHANGE_MAP)
                    whale_tx["classification"] = classification
                    if exchange_details:
                        whale_tx["exchange_details"] = exchange_details
                    
                    new_whales.append(whale_tx)
                    print(f"[WHALE] Found: {whale_tx['value_btc']} BTC (TX: {txid[:16]}...) [{classification}]")
        
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
            
            # Update metadata
            data["metadata"]["last_collection"] = datetime.now().isoformat()
            data["metadata"]["total_collections"] = data["metadata"].get("total_collections", 0) + 1
            data["metadata"]["last_collection_found_new"] = len(new_whales)
            
            save_whale_data(data)
            print(f"\n[SUCCESS] {len(new_whales)} new whale TXs saved!")
            print(f"   Total: {len(data['whale_transactions'])} whale TXs in storage")
        else:
            # Update metadata even if no new TXs
            data["metadata"]["last_collection"] = datetime.now().isoformat()
            data["metadata"]["total_collections"] = data["metadata"].get("total_collections", 0) + 1
            data["metadata"]["last_collection_found_new"] = 0
            save_whale_data(data)
            
            print(f"\n[SUCCESS] No new whale TXs found")
        
        if duplicates > 0:
            print(f"[INFO] {duplicates} duplicates skipped")
        
        # Statistics
        data = load_whale_data()
        total_whales = len(data["whale_transactions"])
        total_volume = sum(tx["value_btc"] for tx in data["whale_transactions"])
        
        print(f"\n[STATS] Total: {total_whales} whale TXs | {total_volume:,.2f} BTC")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"[ERROR] Error: {e}")

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
    
    print(f"[INFO] Scheduler running - next collection in {COLLECTION_INTERVAL_MINUTES} minutes")
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
        print("\n\n[INFO] Collector stopped")
