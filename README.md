# Bitcoin Whale Transaction Collector

Minimalistischer Python Collector für Bitcoin Whale-Transaktionen (>Schwellenwert BTC).

## Funktionen

- **Whale Tracking**: Erfasst Bitcoin-Transfers >Schwellenwert BTC
- **Mempool.space API**: Analysiert alle 10 Minuten die letzten 10 Blöcke
- **Einfache JSON-Speicherung**: Einzelne Datei, Top 500 Whales, Duplikaterkennung
- **Tägliche Aggregationen**: Tägliche Metriken für Backend/Analytics
- **Proxy-Unterstützung**: Funktioniert hinter Corporate-Proxies (optional)
- **GitHub Actions Ready**: Läuft automatisch in der Cloud

## Schnellstart

```bash
# 1. Klonen & Setup
git clone https://github.com/Whale-Activity-Analysis/wai-collector.git
cd wai-collector

# 2. Virtuelle Umgebung
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 3. Abhängigkeiten
pip install -r requirements.txt

# 4. Ausführen
python whale_collector.py

# 5. Tägliche Metriken generieren
python aggregate_daily.py
```

## Konfiguration

### Whale Collector

```bash
# Standard (200 BTC, 10 Min, kein Proxy)
python whale_collector.py

# Benutzerdefinierter Schwellenwert & Intervall
python whale_collector.py -t 500 -i 15

# Mit Corporate-Proxy
python whale_collector.py -p http://proxy:8080

# Alle Optionen
python whale_collector.py --help
```

**Optionen:**
- `-t, --threshold`: Whale-Schwellenwert in BTC (Standard: 200)
- `-i, --interval`: Erfassungsintervall in Minuten (Standard: 10)
- `-p, --proxy`: Proxy-URL falls hinter Firewall (optional)
- `--once`: Einzelner Erfassungslauf (für cron/GitHub Actions)
- `--max-tx-per-block`: Max. TXs pro Block (0 = alle, Standard: 0)

## Ausgabe

### 1. Whale-Transaktionen (`data/whale_data.json`)

```json
{
  "whale_transactions": [
    {
      "txid": "5694cdc618f05ec8cc4a92221e8be10fb10cc3d1bd57f083ce8605b2c1fac5fe",
      "value_btc": 574.00,
      "fee_btc": 0.000013,
      "timestamp": "2026-01-20T08:16:47",
      "classification": "outflow",
      "exchange_details": {
        "exchange_address": "3M219KR5vEneNb47ewrPfWyb5jQ2DjxRP6",
        "exchange_name": "Binance"
      },
      "vin_addresses": [
        {
          "address": "3M219KR5vEneNb47ewrPfWyb5jQ2DjxRP6",
          "value": 574.00
        }
      ],
      "vout_addresses": [
        {
          "address": "bc1qa7r5lqe5zsgqlsvvjvfus5gve0rhw2x80m7e2d",
          "value": 574.00
        }
      ]
    }
  ]
}
```

**Top 500 Whales** (FIFO), sortiert nach Zeitstempel (neueste zuerst).

**Klassifizierungstypen:**
- `outflow` - BTC verlässt eine Exchange
- `inflow` - BTC geht zu einer Exchange
- `mixed` - Sowohl Inputs als auch Outputs zu Exchanges
- `unknown` - Keine Exchange-Beteiligung erkannt

### 2. Tägliche Metriken (`data/daily_metrics.json`)

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

**Erforderliche Metriken pro Tag:**
- `whale_tx_count` - Anzahl der Whale-TXs
- `whale_tx_volume_btc` - Gesamtvolumen
- `avg_whale_fee_btc` - Durchschnittliche Gebühr
- `max_whale_tx_btc` - Größte Whale-TX
 - `exchange_inflow_btc` - Whale → Exchange gesamt BTC (Summe der inflow TXs)
 - `exchange_outflow_btc` - Exchange → Whale gesamt BTC (Summe der outflow TXs)
 - `exchange_netflow_btc` - Outflow − Inflow (positiv = Netto-Abfluss von Exchanges)
 - `exchange_flow_ratio` - Inflow / (Inflow + Outflow), null falls kein Flow
 - `exchange_whale_tx_count` - Anzahl der Whale-TXs mit Exchange-Beteiligung (inflow, outflow, mixed)

## Funktionsweise

1. **Alle 10 Minuten**: Abfrage der Mempool.space API
2. **Analysiert**: Letzte 10 Blöcke auf Whale-TXs (>200 BTC), alle TXs pro Block
3. **Change-Erkennung**: Outputs, die zurück an Input-Adressen gehen, werden ausgeschlossen (Change-Outputs)
4. **Netto-Transfer-Berechnung**: Zählt nur BTC, die tatsächlich an NEUE Adressen übertragen werden
5. **Klassifizierung**: Prüft Inputs/Outputs gegen 200+ bekannte Exchange-Adressen (Binance, OKX, etc.)
6. **Duplikatsprüfung**: TX-ID bereits bekannt? → Überspringen
7. **Speichert**: Neue Whale-TXs (Max. 500, FIFO)
8. **Aggregiert**: Tägliche Metriken aus Rohdaten
9. **Retry-Mechanismus**: 3 Versuche mit exponentiellem Backoff bei API-Fehlern

Hinweise zu Exchange-Metriken:
- Bei `mixed` Transaktionen (sowohl Input als auch Output beinhalten Exchanges) wird das Volumen nicht zu inflow/outflow zugeordnet, um Doppelzählungen zu vermeiden; sie erhöhen dennoch `exchange_whale_tx_count`.

**Wichtig**: Mempool-Daten sind kurzlebig - TXs verschwinden nach Block-Einbindung. Daher ist kontinuierliche Erfassung alle 10 Min. essentiell!

### Behandlung von Change-Outputs

Der Collector behandelt nun korrekt Bitcoins Change-Mechanismus:
- **Problem**: Eine Transaktion mit 2104 BTC Input könnte 2103.9906 BTC zurück an dieselbe Adresse (Change) haben und nur 0.0094 BTC tatsächlich übertragen
- **Lösung**: Der Collector identifiziert alle Input-Adressen und subtrahiert alle Outputs, die zurück an diese Adressen gehen
- **Ergebnis**: Nur der **Netto-Transfer** (tatsächlich bewegter Betrag an neue Adressen) wird mit dem Whale-Schwellenwert verglichen
- **Beispiel**: Im obigen Fall würden nur 0.0094 BTC gezählt, sodass es nicht als Whale-Transaktion qualifiziert (< 200 BTC)

## GitHub Actions

Der Collector läuft automatisch in GitHub Actions - **kein Server benötigt!**

**Setup:**
1. Repo zu GitHub pushen
2. GitHub Actions aktiviert sich automatisch
3. Läuft alle 10 Minuten
4. Committed Daten zurück ins Repo

Siehe `.github/workflows/collect.yml` für Details.

## Projektstruktur

```
wai-collector/
├── whale_collector.py      # Hauptskript - erfasst Whale-TXs
├── aggregate_daily.py      # Generiert tägliche Metriken
├── requirements.txt        # Abhängigkeiten
├── README.md
├── .github/
│   └── workflows/
│       └── collect.yml     # GitHub Actions Konfiguration
└── data/
    ├── whale_data.json     # Whale-TXs (Top 500, FIFO)
    └── daily_metrics.json  # Aggregierte tägliche Metriken
```

## Performance & Zuverlässigkeit

- **Batch-API-Anfragen**: 10 Anfragen statt 1000 (alle TXs eines Blocks auf einmal)
- **Retry-Mechanismus**: 3 Versuche mit exponentiellem Backoff (1s, 2s)
- **Exception Handling**: Robuste Fehlerbehandlung für Netzwerkprobleme
- **FIFO-Speicherung**: 500 Whale-TXs, älteste werden automatisch entfernt
- **Duplikaterkennung**: Set-basiert, O(1) Lookup

