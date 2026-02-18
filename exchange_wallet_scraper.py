#!/usr/bin/env python3
"""
Exchange Wallet Scraper
Scrapes exchange wallet addresses from BitInfoCharts and Arkham Intelligence
Merges them into exchange_wallet_adresses.json
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
from datetime import datetime
from pathlib import Path

# Selenium imports (optional - fallback if not available)
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

# ============================================================
# CONFIGURATION
# ============================================================
EXCHANGES_FILE = Path("data/exchange_wallet_adresses.json")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# ============================================================
# SCRAPER FUNCTIONS
# ============================================================

def scrape_bitinfocharts():
    """Scrape exchange wallets from BitInfoCharts top 100 richest addresses"""
    print("🔍 Scraping BitInfoCharts...")
    
    url = "https://bitinfocharts.com/top-100-richest-bitcoin-addresses.html"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        if response.status_code != 200:
            print(f"   ❌ Fehler beim Laden: HTTP {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the main table (it might have different CSS classes)
        address_table = soup.find('table', {'id': 'tblOne'})
        
        if not address_table:
            # Try alternative selectors
            address_table = soup.find('table', class_='table')
        
        if not address_table:
            # Try to find any table
            tables = soup.find_all('table')
            if tables:
                address_table = tables[0]  # Use first table
                print(f"   📍 Verwende erste Tabelle (gefunden: {len(tables)} Tabellen)")
        
        if not address_table:
            print("   ⚠️  Tabelle nicht gefunden")
            return []
        
        found_wallets = []
        rows = address_table.find_all('tr')
        
        print(f"   Analysiere {len(rows)} Zeilen...")
        
        # Exchange keywords to search for
        exchange_keywords = {
            'binance': 'Binance',
            'okx': 'OKX', 
            'coinbase': 'Coinbase',
            'kraken': 'Kraken',
            'bitfinex': 'Bitfinex',
            'huobi': 'Huobi',
            'bybit': 'Bybit',
            'gate.io': 'Gate.io',
            'kucoin': 'KuCoin',
            'bitstamp': 'Bitstamp',
            'gemini': 'Gemini',
            'crypto.com': 'Crypto.com',
            'bittrex': 'Bittrex',
            'poloniex': 'Poloniex',
            'ftx': 'FTX'
        }
        
        for row in rows[1:]:  # Skip header
            cols = row.find_all('td')
            
            if len(cols) < 2:
                continue
            
            # Extract all text from the row
            row_text = row.get_text(separator=' ', strip=True).lower()
            
            # Check if row contains exchange keywords
            found_exchange = None
            for keyword, label in exchange_keywords.items():
                if keyword in row_text:
                    found_exchange = label
                    break
            
            if not found_exchange:
                continue
            
            # Now extract the address from column 1 (usually 0=rank, 1=address)
            address_col = cols[1] if len(cols) > 1 else cols[0]
            
            # Try to extract address from link
            address_link = address_col.find('a')
            if address_link:
                address = address_link.text.strip()
            else:
                address = address_col.text.strip()
            
            # Clean up address (take only the address part, not additional text)
            address_parts = address.split()
            if address_parts:
                address = address_parts[0]
            
            # Validate Bitcoin address format (basic check)
            if not address or len(address) < 26:
                continue
            
            # Bitcoin addresses start with 1, 3, or bc1
            if not (address.startswith('1') or address.startswith('3') or address.startswith('bc1')):
                continue
            
            found_wallets.append({
                "address": address,
                "label": found_exchange
            })
            print(f"   🎯 {found_exchange}: {address[:20]}...")
        
        print(f"   ✅ {len(found_wallets)} Exchange-Adressen gefunden")
        return found_wallets
        
    except Exception as e:
        print(f"   ❌ Error scraping BitInfoCharts: {e}")
        import traceback
        traceback.print_exc()
        return []

def scrape_arkham_with_selenium():
    """Scrape Arkham Intelligence using Selenium for JavaScript rendering"""
    print("🔍 Scraping Arkham Intelligence (Selenium)...")
    
    if not SELENIUM_AVAILABLE:
        print("   ⚠️  Selenium nicht installiert - überspringe Arkham")
        return []
    
    # Major exchanges to check
    exchanges = [
        ('binance', 'Binance'),
        ('coinbase', 'Coinbase'),
        ('kraken', 'Kraken'),
        ('okx', 'OKX'),
        ('bitfinex', 'Bitfinex'),
    ]
    
    found_wallets = []
    driver = None
    
    try:
        # Setup Chrome in headless mode
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument(f'user-agent={HEADERS["User-Agent"]}')
        
        print("   🚀 Starte Chrome (headless)...")
        # Use webdriver-manager to automatically download/manage ChromeDriver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(30)
        
        for exchange_slug, exchange_label in exchanges:
            try:
                url = f"https://platform.arkhamintelligence.com/explorer/entity/{exchange_slug}"
                print(f"   📍 {exchange_label}...", end=' ', flush=True)
                
                driver.get(url)
                
                # Wait for page to load (wait for body or specific elements)
                time.sleep(5)  # Give JavaScript time to render
                
                # Get page source after JavaScript execution
                page_source = driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                page_text = soup.get_text()
                
                # Find Bitcoin addresses
                pattern = r'\b(1[a-km-zA-HJ-NP-Z1-9]{25,34}|3[a-km-zA-HJ-NP-Z1-9]{25,34}|bc1[a-z0-9]{39,59})\b'
                addresses = re.findall(pattern, page_text)
                
                # Validate and deduplicate
                unique_addresses = set()
                for addr in addresses:
                    if len(addr) >= 26 and addr.startswith(('1', '3', 'bc1')):
                        unique_addresses.add(addr)
                
                if unique_addresses:
                    count = 0
                    for address in list(unique_addresses)[:10]:  # Max 10 per exchange
                        found_wallets.append({
                            "address": address,
                            "label": exchange_label
                        })
                        count += 1
                    print(f"✅ {count} Adressen")
                else:
                    print("⚠️ Keine")
                
                time.sleep(2)  # Be polite between requests
                
            except Exception as e:
                print(f"❌ Error: {str(e)[:30]}")
                continue
        
    except Exception as e:
        error_msg = str(e)
        if "proxy" in error_msg.lower() or "cannot connect" in error_msg.lower():
            print(f"\n   ❌ Corporate Proxy blockiert Selenium")
            print(f"   💡 Tipp: Nutze VPN oder führe außerhalb des Firmennetzwerks aus")
        else:
            print(f"\n   ❌ Selenium Error: {str(e)[:200]}")
            print(f"   💡 Tipp: Chrome WebDriver installieren mit 'pip install chromedriver-autoinstaller'")
        return []
    
    finally:
        if driver:
            driver.quit()
    
    if found_wallets:
        print(f"\n   ✅ Total: {len(found_wallets)} Adressen von Arkham")
    else:
        print(f"\n   ℹ️  Keine Adressen gefunden")
    
    return found_wallets

def scrape_arkham_intelligence():
    """Scrape exchange wallets from Arkham Intelligence"""
    print("🔍 Scraping Arkham Intelligence...")
    
    if SELENIUM_AVAILABLE:
        # Use Selenium for JavaScript rendering
        return scrape_arkham_with_selenium()
    else:
        # Fallback to simple scraping (limited results)
        print("   ⚠️  Selenium nicht verfügbar - Fallback zu einfachem Scraping")
        print("   💡 Installiere: pip install selenium")
        
        exchanges = [
            ('binance', 'Binance'),
            ('coinbase', 'Coinbase'),
        ]
        
        found_wallets = []
        
        for exchange_slug, exchange_label in exchanges:
            try:
                url = f"https://platform.arkhamintelligence.com/explorer/entity/{exchange_slug}"
                response = requests.get(url, headers=HEADERS, timeout=30)
                
                if response.status_code != 200:
                    continue
                
                soup = BeautifulSoup(response.text, 'html.parser')
                page_text = soup.get_text()
                
                pattern = r'\b(1[a-km-zA-HJ-NP-Z1-9]{25,34}|3[a-km-zA-HJ-NP-Z1-9]{25,34}|bc1[a-z0-9]{39,59})\b'
                addresses = re.findall(pattern, page_text)
                
                unique_addresses = set()
                for addr in addresses:
                    if len(addr) >= 26 and addr.startswith(('1', '3', 'bc1')):
                        unique_addresses.add(addr)
                
                if unique_addresses:
                    for address in list(unique_addresses)[:5]:
                        found_wallets.append({
                            "address": address,
                            "label": exchange_label
                        })
                
                time.sleep(1)
                
            except Exception as e:
                continue
        
        if found_wallets:
            print(f"   ✅ {len(found_wallets)} Adressen gefunden")
        else:
            print(f"   ℹ️  Keine Adressen gefunden")
        
        return found_wallets

# ============================================================
# DATA MANAGEMENT
# ============================================================

def load_exchanges():
    """Load existing exchange addresses"""
    if not EXCHANGES_FILE.exists():
        return {
            "meta": {
                "source": "manual + scraper",
                "last_updated": datetime.now().strftime("%Y-%m-%d")
            },
            "addresses": []
        }
    
    with open(EXCHANGES_FILE, 'r') as f:
        return json.load(f)

def save_exchanges(data):
    """Save exchange addresses"""
    EXCHANGES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(EXCHANGES_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def merge_wallets(existing_data, new_wallets):
    """Merge new wallets into existing data, avoiding duplicates"""
    
    # Build set of existing addresses
    existing_addresses = {entry["address"] for entry in existing_data.get("addresses", [])}
    
    added = 0
    for wallet in new_wallets:
        if wallet["address"] not in existing_addresses:
            existing_data["addresses"].append(wallet)
            existing_addresses.add(wallet["address"])
            added += 1
            print(f"   ➕ {wallet['label']}: {wallet['address'][:20]}...")
    
    # Update metadata
    existing_data["meta"]["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    if "scraper_last_run" not in existing_data["meta"]:
        existing_data["meta"]["scraper_last_run"] = datetime.now().isoformat()
    
    return added

# ============================================================
# MAIN
# ============================================================

def main():
    """Main scraper function"""
    print("=" * 60)
    print("   Exchange Wallet Scraper")
    print("=" * 60)
    print()
    
    # Load existing data
    print("📂 Lade bestehende Exchange-Daten...")
    data = load_exchanges()
    initial_count = len(data.get("addresses", []))
    print(f"   {initial_count} Adressen bereits vorhanden\n")
    
    all_new_wallets = []
    
    # Scrape BitInfoCharts
    bitinfo_wallets = scrape_bitinfocharts()
    all_new_wallets.extend(bitinfo_wallets)
    print()
    
    # Scrape Arkham Intelligence
    arkham_wallets = scrape_arkham_intelligence()
    all_new_wallets.extend(arkham_wallets)
    
    if not all_new_wallets:
        print("\n⚠️  Keine neuen Adressen gefunden")
        return
    
    # Merge and save
    print(f"\n💾 Merge {len(all_new_wallets)} neue Adressen...")
    added = merge_wallets(data, all_new_wallets)
    
    if added > 0:
        save_exchanges(data)
        final_count = len(data["addresses"])
        print(f"\n✅ Erfolgreich! {added} neue Adressen hinzugefügt")
        print(f"   Total: {initial_count} → {final_count} Adressen")
        print(f"   Gespeichert: {EXCHANGES_FILE}")
    else:
        print(f"\n✅ Keine neuen Adressen (alle bereits vorhanden)")
    
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Abgebrochen")
    except Exception as e:
        print(f"\n❌ Fehler: {e}")
        import traceback
        traceback.print_exc()