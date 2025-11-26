"""Hauptmodul für den WAI Collector."""
from datetime import datetime
from typing import Dict, Any

from .collectors import MempoolCollector
from .storage import JsonStorage


class WAICollector:
    """
    Whale Activity Index Collector.
    
    Sammelt On-Chain Whale-Metriken von Mempool.space
    und speichert sie lokal als JSON.
    """
    
    def __init__(self):
        self.mempool_collector = MempoolCollector()
        self.storage = JsonStorage()
    
    def collect_all(self) -> Dict[str, Any]:
        """
        Führt Datensammlung durch und speichert die Daten.
        
        Returns:
            Dictionary mit allen gesammelten Daten
        """
        print(f"\n{'='*60}")
        print(f"WAI Collector - Starting collection at {datetime.utcnow().isoformat()}")
        print(f"{'='*60}\n")
        
        results = {}
        
        # Mempool.space - Whale Transactions & Stats
        try:
            mempool_data = self.mempool_collector.collect()
            self.storage.save("whale_data", mempool_data)
            results["whale_data"] = mempool_data
            self._print_summary(mempool_data)
        except Exception as e:
            print(f"[ERROR] Mempool collector failed: {e}")
            results["whale_data"] = {"error": str(e)}
        
        print(f"\n{'='*60}")
        print(f"Collection complete!")
        print(f"{'='*60}\n")
        
        return results
    
    def _print_summary(self, data: Dict[str, Any]):
        """Druckt eine Zusammenfassung der gesammelten Daten."""
        print(f"\n[Whale Data] Collection Summary:")
        print("-" * 40)
        
        if "data" in data:
            inner_data = data["data"]
            
            mempool = inner_data.get("mempool", {})
            whale_stats = inner_data.get("whale_stats", {})
            fees = inner_data.get("fees", {})
            
            print(f"  Mempool TX Count: {mempool.get('tx_count', 0)}")
            print(f"  Mempool Size: {mempool.get('vsize_mb', 0)} MB")
            print(f"  Fastest Fee: {fees.get('fastest_sat_vb', 0)} sat/vB")
            print(f"  ---")
            print(f"  Whale TX Count (last {whale_stats.get('blocks_analyzed', 0)} blocks): {whale_stats.get('total_whale_tx_count', 0)}")
            print(f"  Whale Volume: {whale_stats.get('total_volume_btc', 0)} BTC")
            print(f"  Max Whale TX: {whale_stats.get('max_tx_size_btc', 0)} BTC")


def run_once():
    """Führt eine einzelne Datensammlung durch."""
    collector = WAICollector()
    return collector.collect_all()


def run_scheduled(interval_minutes: int = 60):
    """
    Führt die Datensammlung in regelmäßigen Intervallen durch.
    
    Args:
        interval_minutes: Intervall zwischen Sammlungen in Minuten
    """
    import schedule
    import time
    
    collector = WAICollector()
    
    # Erste Sammlung sofort
    collector.collect_all()
    
    # Plane regelmäßige Sammlungen
    schedule.every(interval_minutes).minutes.do(collector.collect_all)
    
    print(f"\n[INFO] Scheduled collection every {interval_minutes} minutes.")
    print("[INFO] Press Ctrl+C to stop.\n")
    
    while True:
        schedule.run_pending()
        time.sleep(60)
