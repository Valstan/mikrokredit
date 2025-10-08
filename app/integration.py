from __future__ import annotations
import redis
import requests
import json
from typing import Optional, Dict, Any
from app.config import REDIS_URL, API_GATEWAY_URL, PROJECT_NAME


class CacheManager:
    """Redis cache manager for MikroKredit project"""
    
    def __init__(self):
        try:
            self.redis_client = redis.from_url(REDIS_URL, decode_responses=True)
            self.redis_client.ping()  # Test connection
        except Exception as e:
            print(f"Warning: Redis connection failed: {e}")
            self.redis_client = None
    
    def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        if not self.redis_client:
            return None
        try:
            return self.redis_client.get(f"{PROJECT_NAME}:{key}")
        except Exception:
            return None
    
    def set(self, key: str, value: str, expire: int = 3600) -> bool:
        """Set value in cache with expiration"""
        if not self.redis_client:
            return False
        try:
            return self.redis_client.setex(f"{PROJECT_NAME}:{key}", expire, value)
        except Exception:
            return False
    
    def delete(self, key: str) -> bool:
        """Delete value from cache"""
        if not self.redis_client:
            return False
        try:
            return self.redis_client.delete(f"{PROJECT_NAME}:{key}")
        except Exception:
            return False
    
    def cache_loans_data(self, data: Dict[str, Any], expire: int = 300) -> bool:
        """Cache loans data for quick access"""
        try:
            json_data = json.dumps(data, ensure_ascii=False)
            return self.set("loans_data", json_data, expire)
        except Exception:
            return False
    
    def get_cached_loans_data(self) -> Optional[Dict[str, Any]]:
        """Get cached loans data"""
        try:
            cached_data = self.get("loans_data")
            if cached_data:
                return json.loads(cached_data)
        except Exception:
            pass
        return None


class APIGatewayClient:
    """Client for inter-project communication via API Gateway"""
    
    def __init__(self):
        self.base_url = API_GATEWAY_URL
        self.project_name = PROJECT_NAME
    
    def register_project(self) -> bool:
        """Register this project with the API Gateway"""
        try:
            payload = {
                "project_name": self.project_name,
                "service_url": f"http://localhost:8002",
                "health_endpoint": "/healthz",
                "capabilities": ["loans_management", "financial_tracking"]
            }
            
            response = requests.post(
                f"{self.base_url}/projects/register",
                json=payload,
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Warning: Failed to register with API Gateway: {e}")
            return False
    
    def get_project_status(self, project_name: str) -> Optional[Dict[str, Any]]:
        """Get status of another project"""
        try:
            response = requests.get(
                f"{self.base_url}/projects/{project_name}/status",
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return None
    
    def send_notification(self, message: str, target_projects: list = None) -> bool:
        """Send notification to other projects"""
        try:
            payload = {
                "from_project": self.project_name,
                "message": message,
                "target_projects": target_projects or [],
                "timestamp": json.dumps({"timestamp": "now"})
            }
            
            response = requests.post(
                f"{self.base_url}/notifications/send",
                json=payload,
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Warning: Failed to send notification: {e}")
            return False


# Global instances
cache_manager = CacheManager()
api_gateway_client = APIGatewayClient()
