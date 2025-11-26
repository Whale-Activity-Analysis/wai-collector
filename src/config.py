"""Konfiguration für den WAI Collector."""
import os
from dotenv import load_dotenv

load_dotenv()

# Whale Threshold
WHALE_THRESHOLD_BTC = int(os.getenv("WHALE_THRESHOLD_BTC", 200))  # BTC

# Collection Settings
COLLECTION_INTERVAL_MINUTES = int(os.getenv("COLLECTION_INTERVAL_MINUTES", 60))

# Proxy Settings (für Corporate Networks)
# Setze Umgebungsvariablen für requests-Bibliothek
HTTP_PROXY = os.getenv("HTTP_PROXY", "")
HTTPS_PROXY = os.getenv("HTTPS_PROXY", "")

if HTTP_PROXY:
    os.environ["HTTP_PROXY"] = HTTP_PROXY
if HTTPS_PROXY:
    os.environ["HTTPS_PROXY"] = HTTPS_PROXY

PROXIES = {}
if HTTP_PROXY:
    PROXIES["http"] = HTTP_PROXY
if HTTPS_PROXY:
    PROXIES["https"] = HTTPS_PROXY

# API Endpoint
MEMPOOL_API = "https://mempool.space/api"

# Data Storage
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
