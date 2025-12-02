# 🐋 Bitcoin Whale Transaction Collector

Minimalistischer Python-Collector für Bitcoin Whale Transactions (>200 BTC).

## Features

- 🐋 **Whale Tracking**: Erfasst Bitcoin-Transfers >200 BTC
- 📊 **Mempool.space API**: Analysiert letzte 10 Blöcke alle 30 Minuten  
- 💾 **Simple JSON Storage**: Eine Datei, Top 100 Whales, Duplikat-Erkennung
- 📈 **Daily Aggregations**: Tagesmetriken für Backend/Analytics
- 🌐 **Proxy Support**: Funktioniert hinter Corporate Proxies (optional)
- ⚡ **Single Script**: Alles in einem ~180 Zeilen Skript
- 🤖 **GitHub Actions Ready**: Läuft automatisch in der Cloud

## Schnellstart

```bash
# 1. Clone & Setup
git clone https://github.com/Whale-Activity-Analysis/wai-collector.git
cd wai-collector

# 2. Virtual Environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 3. Dependencies
pip install -r requirements.txt

# 4. Starten
python whale_collector.py

# 5. Daily Metriken erzeugen
python aggregate_daily.py
```

## Konfiguration

### Whale Collector

```bash
# Standard (200 BTC, 30 Min, kein Proxy)
python whale_collector.py

# Custom Threshold & Interval
python whale_collector.py -t 500 -i 15

# Mit Corporate Proxy
python whale_collector.py -p http://proxy:8080

# Alle Optionen
python whale_collector.py --help
```

**Optionen:**
- `-t, --threshold`: Whale-Schwellwert in BTC (default: 200)
- `-i, --interval`: Collection-Intervall in Minuten (default: 30)
- `-p, --proxy`: Proxy URL falls hinter Firewall

## Output

### 1. Whale Transactions (`data/whale_data.json`)

```json
{
  "whale_transactions": [
    {
      "txid": "5694cdc618f05ec8cc4a92221e8be10fb10cc3d1bd57f083ce8605b2c1fac5fe",
      "value_btc": 862.29,
      "fee_btc": 0.000013,
      "timestamp": "2025-12-02T15:52:25.685738"
    }
  ]
}
```

**Top 100 Whales**, sortiert nach Wert, Duplikat-Erkennung via TX-ID Set.

### 2. Daily Metrics (`data/daily_metrics.json`)

```json
{
  "generated_at": "2025-12-02T16:23:55.581286",
  "total_days": 1,
  "daily_metrics": [
    {
      "date": "2025-12-02",
      "whale_tx_count": 7,
      "whale_tx_volume_btc": 2944.31,
      "avg_whale_fee_btc": 0.000089,
      "max_whale_tx_btc": 862.29
    }
  ]
}
```

**Pflichtmetriken pro Tag:**
- `whale_tx_count` - Anzahl Whale TXs
- `whale_tx_volume_btc` - Gesamtvolumen
- `avg_whale_fee_btc` - Durchschnittliche Fee
- `max_whale_tx_btc` - Größte Whale TX

## Wie es funktioniert

1. **Alle 30 Minuten**: Fragt Mempool.space API ab
2. **Analysiert**: Letzte 10 Blöcke nach Whale TXs (>200 BTC)
3. **Duplikat-Check**: TX-ID bereits bekannt? → Skip
4. **Speichert**: Neue Whale TXs, hält Top 100
5. **Aggregiert**: Daily Metrics aus Rohdaten

⚠️ **Wichtig**: Mempool-Daten sind ephemer - TXs verschwinden nach Block-Inclusion. Daher kontinuierliche Collection alle 30 Min essentiell!

## GitHub Actions (Empfohlen)

Der Collector läuft automatisch in GitHub Actions - **kein Server nötig!**

**Setup:**
1. Repo auf GitHub pushen
2. GitHub Actions wird automatisch aktiviert
3. Läuft alle 30 Minuten
4. Committed Daten zurück ins Repo

Siehe `.github/workflows/collect.yml` für Details.

## Deployment Optionen

### Option 1: GitHub Actions ✅ (Empfohlen)
- ✅ Kostenlos (2000 Min/Monat)
- ✅ Kein Server nötig
- ✅ Automatische Backups via Git
- ✅ Einfaches Setup

### Option 2: Server/VPS
```bash
# Cron Job (Linux)
*/30 * * * * /path/to/venv/bin/python /path/to/whale_collector.py

# Task Scheduler (Windows)
# Alle 30 Min: whale_collector.py ausführen
```

### Option 3: Lokal (Development)
```bash
# Läuft endlos, alle 30 Min
python whale_collector.py
```

## Projektstruktur

```
wai-collector/
├── whale_collector.py      # Hauptskript - sammelt Whale TXs
├── aggregate_daily.py      # Erzeugt Daily Metrics
├── requirements.txt        # Dependencies
├── README.md
├── .github/
│   └── workflows/
│       └── collect.yml     # GitHub Actions Config
└── data/
    ├── whale_data.json     # Whale TXs (Top 100)
    └── daily_metrics.json  # Aggregierte Tagesmetriken
```

## Dependencies

- `requests` - HTTP Client für Mempool.space API
- `schedule` - Cron-like Job Scheduling
- `urllib3` - HTTP Connection Pooling
- Python 3.10+

## Lizenz

MIT
