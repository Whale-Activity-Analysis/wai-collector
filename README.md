# 🐋 Bitcoin Whale Transaction Collector

Minimalist Python collector for Bitcoin whale transactions (>threshold BTC).

## Features

- 🐋 **Whale Tracking**: Captures Bitcoin transfers >threshold BTC
- 📊 **Mempool.space API**: Analyzes last 10 blocks every 30 minutes  
- 💾 **Simple JSON Storage**: Single file, Top 500 whales, duplicate detection
- 📈 **Daily Aggregations**: Daily metrics for backend/analytics
- 🌐 **Proxy Support**: Works behind corporate proxies (optional)
- 🤖 **GitHub Actions Ready**: Runs automatically in the cloud

## Quick Start

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

# 4. Run
python whale_collector.py

# 5. Generate daily metrics
python aggregate_daily.py
```

## Configuration

### Whale Collector

```bash
# Default (200 BTC, 30 min, no proxy)
python whale_collector.py

# Custom threshold & interval
python whale_collector.py -t 500 -i 15

# With corporate proxy
python whale_collector.py -p http://proxy:8080

# All options
python whale_collector.py --help
```

**Options:**
- `-t, --threshold`: Whale threshold in BTC (default: 200)
- `-i, --interval`: Collection interval in minutes (default: 30)
- `-p, --proxy`: Proxy URL if behind firewall (optional)
- `--once`: Single collection run (for cron/GitHub Actions)
- `--max-tx-per-block`: Max TXs per block (0 = all, default: 0)

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

**Top 500 Whales** (FIFO), sorted by timestamp (newest first), duplicate detection via TX-ID set.

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

**Required metrics per day:**
- `whale_tx_count` - Number of whale TXs
- `whale_tx_volume_btc` - Total volume
- `avg_whale_fee_btc` - Average fee
- `max_whale_tx_btc` - Largest whale TX

## How It Works

1. **Every 30 minutes**: Queries Mempool.space API
2. **Analyzes**: Last 10 blocks for whale TXs (>200 BTC), all TXs per block
3. **Duplicate check**: TX-ID already known? → Skip
4. **Stores**: New whale TXs (Max 500, FIFO)
5. **Aggregates**: Daily metrics from raw data
6. **Retry mechanism**: 3 attempts with exponential backoff on API errors

⚠️ **Important**: Mempool data is ephemeral - TXs disappear after block inclusion. Therefore continuous collection every 30 min is essential!

## GitHub Actions

The collector runs automatically in GitHub Actions - **no server needed!**

**Setup:**
1. Push repo to GitHub
2. GitHub Actions automatically activates
3. Runs every 30 minutes
4. Commits data back to repo

See `.github/workflows/collect.yml` for details.

## Project Structure

```
wai-collector/
├── whale_collector.py      # Main script - collects whale TXs
├── aggregate_daily.py      # Generates daily metrics
├── requirements.txt        # Dependencies
├── README.md
├── .github/
│   └── workflows/
│       └── collect.yml     # GitHub Actions config
└── data/
    ├── whale_data.json     # Whale TXs (Top 500, FIFO)
    └── daily_metrics.json  # Aggregated daily metrics
```

## Performance & Reliability

- ✅ **Batch API Requests**: 10 requests instead of 1000 (all TXs of a block at once)
- ✅ **Retry Mechanism**: 3 attempts with exponential backoff (1s, 2s)
- ✅ **Exception Handling**: Robust error handling for network issues
- ✅ **FIFO Storage**: 500 whale TXs, oldest are automatically removed
- ✅ **Duplicate Detection**: Set-based, O(1) lookup

