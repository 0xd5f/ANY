import requests
from types import SimpleNamespace
from typing import Dict, Any

class Hysteria2Client:
    def __init__(self, base_url: str, secret: str):
        self.base_url = base_url.rstrip('/')
        self.secret = secret
        self.headers = {'Authorization': secret}

    def get_traffic_stats(self, clear: bool = False) -> Dict[str, Any]:
        url = f"{self.base_url}/traffic"
        params = {'clear': '1'} if clear else {}
        try:
            resp = requests.get(url, headers=self.headers, params=params, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                result = {}
                for user, stats in data.items():
                    result[user] = SimpleNamespace(
                        upload_bytes=stats.get('tx', 0),
                        download_bytes=stats.get('rx', 0)
                    )
                return result
        except Exception:
            return None
        return {}

    def get_online_clients(self) -> Dict[str, Any] | None:
        url = f"{self.base_url}/online" 
        try:
            resp = requests.get(url, headers=self.headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                result = {}
                for user, conns in data.items():
                    is_online = False
                    conn_val = []
                    
                    if isinstance(conns, list):
                        is_online = len(conns) > 0
                        conn_val = conns
                    elif isinstance(conns, int):
                        is_online = conns > 0
                        conn_val = conns
                    elif conns:
                         is_online = True
                    
                    result[user] = SimpleNamespace(
                        is_online=is_online,
                        connections=conn_val
                    )
                return result
        except Exception:
             return None
        return {}
