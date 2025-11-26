#!/usr/bin/env python3
"""
WAI Collector - Whale Activity Index Data Collector

Ein einfaches MVP zum Sammeln von On-Chain BTC Metriken.

Usage:
    python main.py              # Einmalige Sammlung
    python main.py --schedule   # Kontinuierliche Sammlung
    python main.py --interval 30  # Sammlung alle 30 Minuten
"""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        description="WAI Collector - Sammelt On-Chain BTC Whale-Metriken"
    )
    parser.add_argument(
        "--schedule", "-s",
        action="store_true",
        help="Kontinuierliche Sammlung in Intervallen"
    )
    parser.add_argument(
        "--interval", "-i",
        type=int,
        default=60,
        help="Intervall in Minuten für scheduled collection (default: 60)"
    )
    
    args = parser.parse_args()
    
    try:
        from src.collector import run_once, run_scheduled
        
        if args.schedule:
            run_scheduled(args.interval)
        else:
            results = run_once()
            
            # Zeige wo die Daten gespeichert wurden
            from src.storage import JsonStorage
            storage = JsonStorage()
            files = storage.list_files()
            if files:
                print(f"\nSaved data files:")
                for f in files:
                    print(f"  - data/{f}")
                    
    except KeyboardInterrupt:
        print("\n\n[INFO] Collection stopped by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
