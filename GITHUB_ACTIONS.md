# GitHub Actions Setup

## Automatische Whale Transaction Collection

Der Collector läuft **kostenlos** in GitHub Actions alle 30 Minuten.

### Setup Schritte

1. **Repository auf GitHub pushen**
   ```bash
   git add .
   git commit -m "Initial commit"
   git push origin main
   ```

2. **GitHub Actions aktivieren**
   - Gehe zu deinem Repo → `Actions` Tab
   - Workflow wird automatisch erkannt
   - Klicke auf "I understand my workflows, go ahead and enable them"

3. **Fertig!** 🎉
   - Läuft automatisch alle 30 Minuten
   - Collected Daten werden ins Repo committed
   - Siehe `data/whale_data.json` und `data/daily_metrics.json`

### Manuell triggern

1. Gehe zu `Actions` → `Collect Whale Transactions`
2. Klicke `Run workflow` → `Run workflow`
3. Warte ~1-2 Minuten

### Workflow Details

`.github/workflows/collect.yml`:
- **Trigger**: Alle 30 Minuten (Cron: `*/30 * * * *`)
- **Steps**:
  1. Checkout Code
  2. Setup Python 3.11
  3. Install Dependencies
  4. Run `whale_collector.py --once`
  5. Run `aggregate_daily.py`
  6. Commit & Push results

### Kosten

- ✅ **Kostenlos** für Public Repos
- ✅ **2000 Min/Monat gratis** für Private Repos
- ✅ ~1 Min pro Run = ~48 Runs/Tag = ~1440 Min/Monat
- ✅ Bleibt deutlich unter Free Tier!

### Logs & Monitoring

1. `Actions` Tab → Workflow Run auswählen
2. Siehe Logs für jeden Step
3. Prüfe ob Whale TXs gefunden wurden

### Alternativen

Wenn du mehr Control willst oder GitHub Actions limits erreichst:

**Cron Job (Linux)**
```bash
# /etc/crontab
*/30 * * * * /path/to/venv/bin/python /path/to/whale_collector.py --once
0 0 * * * /path/to/venv/bin/python /path/to/aggregate_daily.py
```

**Task Scheduler (Windows)**
- Alle 30 Min: `python whale_collector.py --once`
- Täglich 00:00: `python aggregate_daily.py`

**Docker + Cron**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "whale_collector.py"]
```
