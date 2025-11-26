"""Base Collector Klasse für alle Data Collectors."""
import requests
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional

from ..config import PROXIES


class BaseCollector(ABC):
    """Abstrakte Basisklasse für alle Collectors."""
    
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "WAI-Collector/0.1.0"
        })
        # Proxy-Konfiguration aus .env
        if PROXIES:
            self.session.proxies.update(PROXIES)
    
    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """HTTP GET Request mit Error Handling."""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] API Request failed: {url} - {e}")
            return {}
    
    @abstractmethod
    def collect(self) -> Dict[str, Any]:
        """Sammelt Daten und gibt sie als Dictionary zurück."""
        pass
    
    def _add_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Fügt Metadaten zu den gesammelten Daten hinzu."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "collector": self.__class__.__name__,
            "data": data
        }
