"""Collector für Mempool.space API - Whale Transactions & Mempool Stats."""
from typing import Dict, Any, List
from .base_collector import BaseCollector
from ..config import MEMPOOL_API, WHALE_THRESHOLD_BTC


class MempoolCollector(BaseCollector):
    """
    Sammelt Mempool-Daten und Whale-Transaktionen von mempool.space.
    
    Metriken:
    - Whale-Transaktionen > X BTC (aus recent blocks)
    - Mempool Größe und Fee-Raten
    - Block-Statistiken
    """
    
    def __init__(self):
        super().__init__(MEMPOOL_API)
        self.whale_threshold_satoshi = WHALE_THRESHOLD_BTC * 100_000_000
    
    def collect(self) -> Dict[str, Any]:
        """Sammelt aktuelle Mempool-Daten und Whale-Transaktionen."""
        print(f"[INFO] Collecting mempool data and whale transactions (threshold: {WHALE_THRESHOLD_BTC} BTC)...")
        
        # Mempool Stats
        mempool_stats = self._get_mempool_stats()
        
        # Fee Estimates
        fee_estimates = self._get_fee_estimates()
        
        # Recent Blocks mit Whale-TX Analyse
        recent_blocks = self._get_recent_blocks_with_whales(count=10)
        
        # Aggregiere Whale-Statistiken
        whale_stats = self._aggregate_whale_stats(recent_blocks)
        
        metrics = {
            "mempool": mempool_stats,
            "fees": fee_estimates,
            "whale_stats": whale_stats,
            "recent_blocks": recent_blocks[:3],  # Top 3 für Details
            "whale_threshold_btc": WHALE_THRESHOLD_BTC
        }
        
        return self._add_metadata(metrics)
    
    def _get_mempool_stats(self) -> Dict[str, Any]:
        """Holt allgemeine Mempool-Statistiken."""
        data = self._get("/mempool")
        
        if not data:
            return {}
        
        vsize_mb = data.get("vsize", 0) / 1_000_000
        
        return {
            "tx_count": data.get("count", 0),
            "vsize_mb": round(vsize_mb, 2),
            "total_fee_btc": round(data.get("total_fee", 0) / 100_000_000, 4),
        }
    
    def _get_fee_estimates(self) -> Dict[str, Any]:
        """Holt aktuelle Fee-Schätzungen."""
        data = self._get("/v1/fees/recommended")
        
        if not data:
            return {}
        
        return {
            "fastest_sat_vb": data.get("fastestFee", 0),
            "half_hour_sat_vb": data.get("halfHourFee", 0),
            "hour_sat_vb": data.get("hourFee", 0),
            "economy_sat_vb": data.get("economyFee", 0),
            "minimum_sat_vb": data.get("minimumFee", 0)
        }
    
    def _get_recent_blocks_with_whales(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        Holt die letzten Blöcke und analysiert Whale-Transaktionen.
        
        Args:
            count: Anzahl der zu analysierenden Blöcke
        """
        blocks_data = self._get("/v1/blocks")
        
        if not blocks_data:
            return []
        
        blocks_with_whales = []
        
        for block in blocks_data[:count]:
            block_hash = block.get("id", "")
            
            # Hol Transaktionen des Blocks (erste 25)
            txs = self._get(f"/block/{block_hash}/txs")
            
            if not txs:
                continue
            
            # Filtere Whale-Transaktionen
            whale_txs = []
            for tx in txs:
                total_output = sum(out.get("value", 0) for out in tx.get("vout", []))
                
                if total_output >= self.whale_threshold_satoshi:
                    whale_txs.append({
                        "txid": tx.get("txid", "")[:16] + "...",  # Gekürzt
                        "value_btc": round(total_output / 100_000_000, 2),
                        "fee_btc": round(tx.get("fee", 0) / 100_000_000, 6) if tx.get("fee") else 0
                    })
            
            blocks_with_whales.append({
                "height": block.get("height", 0),
                "timestamp": block.get("timestamp", 0),
                "tx_count": block.get("tx_count", 0),
                "whale_tx_count": len(whale_txs),
                "whale_txs": whale_txs[:5]  # Top 5 Whales pro Block
            })
        
        return blocks_with_whales
    
    def _aggregate_whale_stats(self, blocks: List[Dict]) -> Dict[str, Any]:
        """Aggregiert Whale-Statistiken über mehrere Blöcke."""
        total_whale_txs = sum(b.get("whale_tx_count", 0) for b in blocks)
        
        all_whale_txs = []
        for block in blocks:
            all_whale_txs.extend(block.get("whale_txs", []))
        
        if not all_whale_txs:
            return {
                "total_whale_tx_count": 0,
                "total_volume_btc": 0,
                "avg_tx_size_btc": 0,
                "max_tx_size_btc": 0,
                "blocks_analyzed": len(blocks)
            }
        
        volumes = [tx["value_btc"] for tx in all_whale_txs]
        
        return {
            "total_whale_tx_count": total_whale_txs,
            "total_volume_btc": round(sum(volumes), 2),
            "avg_tx_size_btc": round(sum(volumes) / len(volumes), 2),
            "max_tx_size_btc": round(max(volumes), 2),
            "blocks_analyzed": len(blocks),
            "top_whales": sorted(all_whale_txs, key=lambda x: x["value_btc"], reverse=True)[:5]
        }
