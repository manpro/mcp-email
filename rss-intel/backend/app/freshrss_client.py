import httpx
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import hashlib
import base64
from .config import settings

class FreshRSSClient:
    def __init__(self):
        self.base_url = settings.freshrss_base_url
        self.username = settings.freshrss_api_user
        self.password = settings.freshrss_api_pass
        self.token = None
        self.client = httpx.Client(timeout=30.0)
    
    def login(self) -> bool:
        """Authenticate with FreshRSS Reader API"""
        try:
            # FreshRSS uses Google Reader-compatible API
            response = self.client.post(
                f"{self.base_url}/api/greader.php/accounts/ClientLogin",
                data={
                    "Email": self.username,
                    "Passwd": self.password,
                }
            )
            
            if response.status_code == 200:
                for line in response.text.split('\n'):
                    if line.startswith('Auth='):
                        self.token = line.split('=', 1)[1]
                        return True
            return False
        except Exception as e:
            print(f"Login error: {e}")
            return False
    
    def _api_request(self, endpoint: str, method: str = "GET", data: Dict = None) -> Optional[Dict]:
        """Make authenticated API request"""
        if not self.token and not self.login():
            return None
        
        headers = {
            "Authorization": f"GoogleLogin auth={self.token}"
        }
        
        url = f"{self.base_url}/api/greader.php{endpoint}"
        
        try:
            if method == "GET":
                response = self.client.get(url, headers=headers, params=data)
            else:
                response = self.client.post(url, headers=headers, data=data)
            
            if response.status_code == 200:
                try:
                    return response.json()
                except:
                    return {"text": response.text}
            return None
        except Exception as e:
            print(f"API request error: {e}")
            return None
    
    def get_entries(self, since_timestamp: Optional[int] = None, limit: int = 100) -> List[Dict]:
        """Fetch new entries from FreshRSS"""
        params = {
            "n": limit,
            "output": "json"
        }
        
        if since_timestamp:
            params["ot"] = since_timestamp
        
        result = self._api_request("/stream/contents/reading-list", data=params)
        
        if result and "items" in result:
            entries = []
            for item in result["items"]:
                entry = {
                    "freshrss_entry_id": item.get("id", ""),
                    "title": item.get("title", ""),
                    "url": item.get("canonical", [{}])[0].get("href", "") if item.get("canonical") else "",
                    "source": item.get("origin", {}).get("title", "Unknown"),
                    "published_at": datetime.fromtimestamp(
                        item.get("published", 0), tz=timezone.utc
                    ),
                    "content": item.get("summary", {}).get("content", ""),
                    "categories": [cat.split("/")[-1] for cat in item.get("categories", [])]
                }
                entries.append(entry)
            return entries
        return []
    
    def add_label(self, entry_id: str, label: str) -> bool:
        """Add a label to an entry"""
        data = {
            "i": entry_id,
            "a": f"user/-/label/{label}"
        }
        result = self._api_request("/edit-tag", method="POST", data=data)
        return result is not None
    
    def remove_label(self, entry_id: str, label: str) -> bool:
        """Remove a label from an entry"""
        data = {
            "i": entry_id,
            "r": f"user/-/label/{label}"
        }
        result = self._api_request("/edit-tag", method="POST", data=data)
        return result is not None
    
    def star_entry(self, entry_id: str) -> bool:
        """Star an entry"""
        data = {
            "i": entry_id,
            "a": "user/-/state/com.google/starred"
        }
        result = self._api_request("/edit-tag", method="POST", data=data)
        return result is not None
    
    def unstar_entry(self, entry_id: str) -> bool:
        """Unstar an entry"""
        data = {
            "i": entry_id,
            "r": "user/-/state/com.google/starred"
        }
        result = self._api_request("/edit-tag", method="POST", data=data)
        return result is not None
    
    def mark_as_read(self, entry_id: str) -> bool:
        """Mark an entry as read"""
        data = {
            "i": entry_id,
            "a": "user/-/state/com.google/read"
        }
        result = self._api_request("/edit-tag", method="POST", data=data)
        return result is not None
    
    def create_feed(self, feed_url: str, title: Optional[str] = None) -> bool:
        """Add a new feed to FreshRSS"""
        # Note: FreshRSS may require direct database access or admin API for feed creation
        # This is a placeholder for the functionality
        try:
            # Use subscription endpoint
            data = {
                "quickadd": feed_url
            }
            result = self._api_request("/subscription/quickadd", method="POST", data=data)
            return result is not None
        except:
            return False
    
    def get_feeds(self) -> List[Dict]:
        """Get list of subscribed feeds"""
        result = self._api_request("/subscription/list", data={"output": "json"})
        if result and "subscriptions" in result:
            return result["subscriptions"]
        return []