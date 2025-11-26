"""
Historischer Daten-Loader für Whale-Transaktionen.

Lädt rückwirkend Daten der letzten X Tage von der Blockchain.
Nutzt die Blockstream/Mempool.space API für historische Block-Daten.
"""
import json
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List
import requests

from src.config import DATA_DIR, WHALE_THRESHOLD_BTC, PROXIES

# API Endpunkte
MEMPOOL_API = "https://mempool.space/api"
BLOCKSTREAM_API = "https://blockstream.info/api"

# Rate Limiting
REQUEST_DELAY = 0.2  # Sekunden zwischen Requests


class HistoricalLoader:
    """Lädt historische Whale-Transaktionen."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "WAI-Collector/0.1.0"})
        self.whale_threshold_satoshi = WHALE_THRESHOLD_BTC * 100_000_000
        self.data_dir = DATA_DIR
        
        # Setze Proxy
        if PROXIES:
            self.session.proxies.update(PROXIES)
        
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
    
    def _get(self, url: str) -> Any:
        """HTTP GET mit Rate Limiting."""
        time.sleep(REQUEST_DELAY)
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            # Manche Endpunkte geben Plain Text zurück
            try:
                return response.json()
            except:
                return response.text
        except Exception as e:
            print(f"[ERROR] Request failed: {url} - {e}")
            return None
    
    def get_block_height(self) -> int:
        """Aktuelle Block-Höhe."""
        data = self._get(f"{MEMPOOL_API}/blocks/tip/height")
        return data if data else 0
    
    def get_block_at_timestamp(self, timestamp: int) -> int:
        """Findet Block-Höhe für einen Timestamp."""
        data = self._get(f"{MEMPOOL_API}/v1/mining/blocks/timestamp/{timestamp}")
        if data:
            return data.get("height", 0)
        return 0
    
    def get_blocks_in_range(self, start_height: int, end_height: int) -> List[Dict]:
        """Holt Block-Hashes in einem Bereich."""
        blocks = []
        current = end_height
        
        while current >= start_height:
            data = self._get(f"{MEMPOOL_API}/v1/blocks/{current}")
            if data:
                blocks.extend(data)
                current = data[-1]["height"] - 1 if data else current - 10
            else:
                current -= 10
            
            # Fortschritt anzeigen
            progress = ((end_height - current) / (end_height - start_height)) * 100
            print(f"\r[INFO] Loading blocks... {progress:.1f}%", end="", flush=True)
        
        print()  # Newline
        return [b for b in blocks if b["height"] >= start_height]
    
    def get_block_transactions(self, block_hash: str) -> List[Dict]:
        """Holt alle Transaktionen eines Blocks."""
        txs = []
        start_index = 0
        
        while True:
            url = f"{MEMPOOL_API}/block/{block_hash}/txs/{start_index}"
            data = self._get(url)
            
            if not data:
                break
            
            txs.extend(data)
            
            if len(data) < 25:  # Letzte Seite
                break
            
            start_index += 25
        
        return txs
    
    def filter_whale_transactions(self, transactions: List[Dict], block_time: int) -> List[Dict]:
        """Filtert Whale-Transaktionen aus einer Liste."""
        whale_txs = []
        
        for tx in transactions:
            # Berechne Gesamtoutput
            total_output = sum(
                out.get("value", 0) 
                for out in tx.get("vout", [])
            )
            
            if total_output >= self.whale_threshold_satoshi:
                whale_txs.append({
                    "txid": tx.get("txid", ""),
                    "value_btc": total_output / 100_000_000,
                    "inputs_count": len(tx.get("vin", [])),
                    "outputs_count": len(tx.get("vout", [])),
                    "block_time": block_time,
                    "fee_btc": tx.get("fee", 0) / 100_000_000 if tx.get("fee") else 0
                })
        
        return whale_txs
    
    def load_historical_data(self, days: int = 365) -> Dict[str, Any]:
        """
        Lädt historische Whale-Transaktionen der letzten X Tage.
        
        Args:
            days: Anzahl Tage rückwirkend (default: 365)
        
        Returns:
            Dictionary mit täglichen Whale-Statistiken
        """
        print(f"\n{'='*60}")
        print(f"WAI Historical Loader - Loading {days} days of data")
        print(f"Whale Threshold: {WHALE_THRESHOLD_BTC} BTC")
        print(f"{'='*60}\n")
        
        # Zeitrahmen berechnen
        now = datetime.now(timezone.utc)
        start_date = now - timedelta(days=days)
        start_timestamp = int(start_date.timestamp())
        
        # Block-Höhen ermitteln
        current_height = self.get_block_height()
        start_height = self.get_block_at_timestamp(start_timestamp)
        
        if not current_height or not start_height:
            print("[ERROR] Could not determine block range")
            return {}
        
        print(f"[INFO] Block range: {start_height} - {current_height}")
        print(f"[INFO] Approximately {current_height - start_height} blocks to process")
        print(f"[INFO] This will take a while...\n")
        
        # Tägliche Aggregation
        daily_stats = {}
        total_whale_txs = 0
        total_volume = 0
        
        # Blocks in Batches laden
        # ~144 Blocks pro Tag, wir samplen jeden 24. Block für schnellere Ergebnisse
        sample_interval = max(1, (current_height - start_height) // (days * 6))  # ~6 Samples pro Tag
        
        print(f"[INFO] Sampling every {sample_interval} blocks (~6 samples per day)")
        print()
        
        blocks_processed = 0
        for height in range(start_height, current_height + 1, sample_interval):
            # Block-Info holen
            block_data = self._get(f"{MEMPOOL_API}/block-height/{height}")
            if not block_data:
                continue
            
            block_hash = block_data
            block_info = self._get(f"{MEMPOOL_API}/block/{block_hash}")
            if not block_info:
                continue
            
            block_time = block_info.get("timestamp", 0)
            date_str = datetime.fromtimestamp(block_time, timezone.utc).strftime("%Y-%m-%d")
            
            # Transaktionen des Blocks holen
            txs = self.get_block_transactions(block_hash)
            whale_txs = self.filter_whale_transactions(txs, block_time)
            
            # Tägliche Statistik aktualisieren
            if date_str not in daily_stats:
                daily_stats[date_str] = {
                    "date": date_str,
                    "whale_tx_count": 0,
                    "total_volume_btc": 0,
                    "max_tx_btc": 0,
                    "blocks_sampled": 0,
                    "transactions": []
                }
            
            stats = daily_stats[date_str]
            stats["whale_tx_count"] += len(whale_txs)
            stats["total_volume_btc"] += sum(tx["value_btc"] for tx in whale_txs)
            stats["blocks_sampled"] += 1
            
            if whale_txs:
                max_tx = max(tx["value_btc"] for tx in whale_txs)
                stats["max_tx_btc"] = max(stats["max_tx_btc"], max_tx)
                # Top 5 TXs pro Tag speichern
                stats["transactions"].extend(whale_txs)
                stats["transactions"] = sorted(
                    stats["transactions"], 
                    key=lambda x: x["value_btc"], 
                    reverse=True
                )[:5]
            
            total_whale_txs += len(whale_txs)
            total_volume += sum(tx["value_btc"] for tx in whale_txs)
            blocks_processed += 1
            
            # Fortschritt
            progress = ((height - start_height) / (current_height - start_height)) * 100
            print(f"\r[INFO] Progress: {progress:.1f}% | Blocks: {blocks_processed} | "
                  f"Whale TXs: {total_whale_txs} | Volume: {total_volume:.0f} BTC", 
                  end="", flush=True)
        
        print(f"\n\n[INFO] Processing complete!")
        print(f"[INFO] Total Whale Transactions: {total_whale_txs}")
        print(f"[INFO] Total Volume: {total_volume:.2f} BTC")
        
        # Ergebnis speichern
        result = {
            "metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "days_covered": days,
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": now.strftime("%Y-%m-%d"),
                "whale_threshold_btc": WHALE_THRESHOLD_BTC,
                "blocks_sampled": blocks_processed,
                "sample_interval": sample_interval
            },
            "summary": {
                "total_whale_tx_count": total_whale_txs,
                "total_volume_btc": round(total_volume, 4),
                "days_with_data": len(daily_stats)
            },
            "daily_stats": daily_stats
        }
        
        # Speichern
        filepath = os.path.join(self.data_dir, "historical_whale_data.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"\n[INFO] Saved to: {filepath}")
        
        return result


def main():
    """Hauptfunktion für den historischen Loader."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Load historical whale transaction data")
    parser.add_argument(
        "--days", "-d",
        type=int,
        default=365,
        help="Number of days to load (default: 365)"
    )
    
    args = parser.parse_args()
    
    loader = HistoricalLoader()
    loader.load_historical_data(args.days)


if __name__ == "__main__":
    main()
