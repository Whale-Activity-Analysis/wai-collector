#!/usr/bin/env python3
"""
Classify Whale Transaction Movements
Analyzes each whale transaction for:
- Outflow: BTC from Exchange address
- Inflow: BTC to Exchange address
- Mixed: Both inputs and outputs to exchanges
"""

import json
from pathlib import Path
from collections import defaultdict

DATA_FILE = Path("data/whale_data.json")
EXCHANGES_FILE = Path("data/exchange_wallet_adresses.json")

def load_exchange_addresses():
    """Load exchange addresses into a dictionary"""
    with open(EXCHANGES_FILE, 'r') as f:
        data = json.load(f)
    
    exchange_map = {}
    for entry in data.get("addresses", []):
        address = entry["address"]
        label = entry["label"]
        exchange_map[address] = label
    
    return exchange_map

def classify_transaction(tx, exchange_map):
    """
    Classify a transaction as inflow, outflow, or mixed
    Returns: (classification, exchange_details)
    """
    
    # Get all input and output addresses
    vin_addresses = {addr["address"] for addr in tx.get("vin_addresses", [])}
    vout_addresses = {addr["address"] for addr in tx.get("vout_addresses", [])}
    
    # Check for exchange addresses
    exchange_inputs = {addr: exchange_map[addr] for addr in vin_addresses if addr in exchange_map}
    exchange_outputs = {addr: exchange_map[addr] for addr in vout_addresses if addr in exchange_map}
    
    # Determine classification
    exchange_details = {}
    
    if exchange_inputs and exchange_outputs:
        # Both inputs and outputs to exchanges
        classification = "mixed"
        exchange_details = {
            "outflow_exchanges": exchange_inputs,
            "inflow_exchanges": exchange_outputs
        }
    elif exchange_inputs:
        # Outflow: BTC leaving exchange
        classification = "outflow"
        exchange_details = {
            "exchange_address": list(exchange_inputs.keys())[0],
            "exchange_name": list(exchange_inputs.values())[0]
        }
    elif exchange_outputs:
        # Inflow: BTC entering exchange
        classification = "inflow"
        exchange_details = {
            "exchange_address": list(exchange_outputs.keys())[0],
            "exchange_name": list(exchange_outputs.values())[0]
        }
    else:
        # No exchange involvement
        classification = "unknown"
        exchange_details = {}
    
    return classification, exchange_details

def classify_all_transactions():
    """Classify all whale transactions"""
    
    print("Loading exchange addresses...")
    exchange_map = load_exchange_addresses()
    print(f"Loaded {len(exchange_map)} exchange addresses from {len(set(exchange_map.values()))} exchanges\n")
    
    print("Loading whale transactions...")
    with open(DATA_FILE, 'r') as f:
        data = json.load(f)
    
    transactions = data.get("whale_transactions", [])
    print(f"Found {len(transactions)} whale transactions\n")
    
    # Classify each transaction
    stats = defaultdict(int)
    classified_count = 0
    
    for tx in transactions:
        classification, exchange_details = classify_transaction(tx, exchange_map)
        
        tx["classification"] = classification
        if exchange_details:
            tx["exchange_details"] = exchange_details
        
        stats[classification] += 1
        if exchange_details:
            classified_count += 1
    
    # Save classified data
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"{'='*60}")
    print(f"[SUCCESS] Classification complete!")
    print(f"{'='*60}")
    print(f"Total transactions:    {len(transactions)}")
    print(f"Outflows:              {stats['outflow']}")
    print(f"Inflows:               {stats['inflow']}")
    print(f"Mixed:                 {stats['mixed']}")
    print(f"Unknown (no exchange): {stats['unknown']}")
    print(f"With exchange details: {classified_count}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    classify_all_transactions()
