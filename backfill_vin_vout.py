#!/usr/bin/env python3
"""
Backfill vin/vout details for previously collected whale transactions.
Fetches transaction details from mempool.space and enriches entries in data/whale_data.json.
"""

import argparse
import json
import time
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

MEMPOOL_API = "https://mempool.space/api"
DATA_FILE = Path("data/whale_data.json")


def load_data():
    if not DATA_FILE.exists():
        return {"whale_transactions": []}

    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_data(data):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def needs_backfill(tx, force=False):
    if force:
        return True
    return not tx.get("vin_addresses") or not tx.get("vout_addresses")


def to_address_list(vins_or_vouts, is_vin):
    addresses = []
    if is_vin:
        for vin in vins_or_vouts or []:
            prevout = vin.get("prevout") or {}
            address = prevout.get("scriptpubkey_address", "unknown")
            value = prevout.get("value", 0)
            addresses.append({
                "address": address,
                "value": round(value / 100_000_000, 8),
            })
    else:
        for vout in vins_or_vouts or []:
            address = vout.get("scriptpubkey_address", "unknown")
            value = vout.get("value", 0)
            addresses.append({
                "address": address,
                "value": round(value / 100_000_000, 8),
            })
    return addresses


def fetch_tx_details(txid, session):
    url = f"{MEMPOOL_API}/tx/{txid}"
    try:
        response = session.get(url, timeout=30)
        if response.status_code == 404:
            print(f"- {txid[:16]}... not found (404)")
            return None
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as exc:
        print(f"- {txid[:16]}... request failed: {type(exc).__name__}")
        return None


def backfill(proxy=None, force=False, limit=0, delay=0.5):
    session = requests.Session()
    if proxy:
        session.proxies = {"http": proxy, "https": proxy}
        session.verify = False

    data = load_data()
    txs = data.get("whale_transactions", [])

    candidates = [tx for tx in txs if needs_backfill(tx, force)]
    if limit > 0:
        candidates = candidates[:limit]

    if not candidates:
        print("Nothing to backfill. All entries already contain vin/vout data.")
        return

    print(f"Backfilling {len(candidates)} transaction(s)...")
    updated = 0

    for tx in candidates:
        txid = tx.get("txid") or ""
        details = fetch_tx_details(txid, session)
        if not details:
            continue

        tx["vin_addresses"] = to_address_list(details.get("vin"), is_vin=True)
        tx["vout_addresses"] = to_address_list(details.get("vout"), is_vin=False)

        if "fee_btc" not in tx and details.get("fee") is not None:
            tx["fee_btc"] = round(details["fee"] / 100_000_000, 6)

        if "value_btc" not in tx:
            total_output = sum(vout.get("value", 0) for vout in details.get("vout") or [])
            tx["value_btc"] = round(total_output / 100_000_000, 2)

        updated += 1
        if delay > 0:
            time.sleep(delay)

    if updated > 0:
        save_data(data)
        print(f"Updated {updated} transaction(s). Saved to {DATA_FILE}.")
    else:
        print("Finished with no updates written.")


def main():
    parser = argparse.ArgumentParser(
        prog="Backfill vin/vout",
        description="Enrich whale_data.json with vin/vout details from mempool.space",
    )
    parser.add_argument("--proxy", type=str, default=None, help="Proxy URL if needed")
    parser.add_argument("--force", action="store_true", help="Re-download even when vin/vout exists")
    parser.add_argument("--limit", type=int, default=0, help="Max number of TXs to process (0 = all)")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay in seconds between requests")
    args = parser.parse_args()

    backfill(proxy=args.proxy, force=args.force, limit=args.limit, delay=args.delay)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted by user.")
