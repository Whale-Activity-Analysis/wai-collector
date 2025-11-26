"""JSON Storage für gesammelte Daten."""
import json
import os
from datetime import datetime
from typing import Dict, Any, List
from .config import DATA_DIR


class JsonStorage:
    """Speichert gesammelte Daten in JSON-Dateien."""
    
    def __init__(self):
        self.data_dir = DATA_DIR
        self._ensure_data_dir()
    
    def _ensure_data_dir(self):
        """Erstellt das Data-Verzeichnis falls nicht vorhanden."""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            print(f"[INFO] Created data directory: {self.data_dir}")
    
    def save(self, collector_name: str, data: Dict[str, Any]) -> str:
        """
        Speichert Daten in eine JSON-Datei.
        
        Dateiformat: {collector_name}_{YYYY-MM-DD}.json
        Jede Datei enthält ein Array aller Einträge des Tages.
        """
        today = datetime.utcnow().strftime("%Y-%m-%d")
        filename = f"{collector_name}_{today}.json"
        filepath = os.path.join(self.data_dir, filename)
        
        # Lade existierende Daten oder erstelle neues Array
        existing_data = self._load_existing(filepath)
        existing_data.append(data)
        
        # Speichere aktualisierte Daten
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, indent=2, ensure_ascii=False)
        
        print(f"[INFO] Saved data to: {filepath}")
        return filepath
    
    def _load_existing(self, filepath: str) -> List[Dict]:
        """Lädt existierende Daten aus einer Datei."""
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print(f"[WARN] Could not parse existing file: {filepath}")
                return []
        return []
    
    def get_latest(self, collector_name: str) -> Dict[str, Any]:
        """Holt den neuesten Eintrag für einen Collector."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        filename = f"{collector_name}_{today}.json"
        filepath = os.path.join(self.data_dir, filename)
        
        data = self._load_existing(filepath)
        if data:
            return data[-1]
        return {}
    
    def list_files(self) -> List[str]:
        """Listet alle gespeicherten Daten-Dateien."""
        if not os.path.exists(self.data_dir):
            return []
        return [f for f in os.listdir(self.data_dir) if f.endswith(".json")]
