# WAI Collector v0.1.0

🐋 **Whale Activity Index Data Collector**

Schlankes Python-MVP zur Erfassung von On-Chain BTC Whale-Metriken über Mempool.space API.

## 🎯 Milestone v0.1

- [x] Einfacher Python-Collector
- [x] Mempool.space API Integration
- [x] Lokale JSON-Speicherung
- [x] Whale-Transaktionen > 200 BTC aus letzten Blöcken
- [x] Mempool-Analyse (TX-Count, Fees, Größe)
- [x] Historischer Daten-Loader (365 Tage rückwirkend)
- [x] Proxy-Support für Corporate Networks

## 📊 Gesammelte Metriken

### Whale Transactions (aus letzten 10 Blöcken)
- Anzahl Whale-Transaktionen > 200 BTC
- Gesamtvolumen der Whale-TXs
- Durchschnittliche & maximale TX-Größe
- Top 5 Whale-Transaktionen mit Details

### Mempool Stats
- TX-Count und Mempool-Größe
- Fee-Schätzungen (fastest, halfHour, hour, economy)
- Recent Block Infos (Höhe, TX-Count, Whale-Aktivität)

## 🚀 Schnellstart

```bash
# 1. Virtual Environment erstellen
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 2. Dependencies installieren (mit Proxy falls nötig)
pip install --proxy http://your-proxy:8080 -r requirements.txt

# 3. .env Datei erstellen
copy .env.example .env  # und anpassen

# 4. Einmalige Datensammlung
python main.py

# 5. Historische Daten laden (einmalig!)
python load_historical.py --days 365

# 6. Kontinuierliche Sammlung (stündlich)
python main.py --schedule

# 7. Eigenes Intervall (z.B. alle 30 Min)
python main.py --schedule --interval 30
```

## 📁 Projektstruktur

```
wai-collector/
├── main.py                 # Entry Point für tägliche Sammlung
├── load_historical.py      # Einmaliger historischer Loader
├── requirements.txt        # Python Dependencies
├── .env.example           # Beispiel-Konfiguration
├── src/
│   ├── __init__.py
│   ├── config.py          # Konfiguration
│   ├── collector.py       # Hauptlogik
│   ├── storage.py         # JSON-Speicherung
│   └── collectors/
│       ├── __init__.py
│       ├── base_collector.py      # Abstrakte Basisklasse
│       └── mempool_collector.py   # Mempool.space API
└── data/                  # Gesammelte JSON-Daten
    ├── whale_data_YYYY-MM-DD.json
    └── historical_whale_data.json
```

## ⚙️ Konfiguration

Kopiere `.env.example` zu `.env` und passe die Werte an:

```env
# Proxy (für Corporate Networks)
HTTP_PROXY=http://sia-lb.telekom.de:8080
HTTPS_PROXY=http://sia-lb.telekom.de:8080

# Whale Threshold (200 BTC empfohlen)
WHALE_THRESHOLD_BTC=200

## 📈 Beispiel-Output

```json
{
  "timestamp": "2025-11-26T11:30:39.123456",
  "collector": "MempoolCollector",
  "data": {
    "mempool": {
      "tx_count": 47717,
      "vsize_mb": 23.87,
      "total_fee_btc": 0.0529
    },
    "fees": {
      "fastest_sat_vb": 2,
      "half_hour_sat_vb": 1,
      "hour_sat_vb": 1
    },
    "whale_stats": {
      "total_whale_tx_count": 1,
      "total_volume_btc": 215.18,
      "max_tx_size_btc": 215.18,
      "blocks_analyzed": 10,
      "top_whales": [
        {
          "txid": "7fa99bcb0efe8b63...",
          "value_btc": 215.18,
          "fee_btc": 0.000107
        }
      ]
    },
    "whale_threshold_btc": 200
  }
}
```

## 🔮 Roadmap (nächste Schritte)

- [ ] CryptoQuant API Integration (Exchange Flows)
- [ ] Glassnode API (Whale Metrics)
- [ ] Score-Berechnung (Linear Weighted Score)
- [ ] Z-Score Normalisierung
- [ ] 24h Rolling Window Smoothing
- [ ] PostgreSQL Backend
- [ ] REST API für Abfragen

## 📝 Geplante Metriken

| Metrik | Quelle | Status |
|--------|--------|--------|
| Whale TX aus Blocks | Mempool.space | ✅ |
| Mempool Stats & Fees | Mempool.space | ✅ |
| Historische Daten | Mempool.space | ✅ |
| Exchange Whale Inflows | CryptoQuant | 🔜 |
| OTC Outflows | CryptoQuant | 🔜 |
| Miners to Exchange | Glassnode | 🔜 |
| Large Wallet Accumulation | Glassnode | 🔜 |
| Whale Net Position Change | CryptoQuant | 🔜 |
| Stablecoin Whale Pressure | CryptoQuant | 🔜 |

## 🛠️ Tech Stack

- Python 3.10+
- requests - HTTP Client
- python-dotenv - Environment Variables
- schedule - Job Scheduling
- Mempool.space API (kostenlos)

## 📄 Lizenz

MIT
