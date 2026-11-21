import logging
import httpx
from typing import Dict, Any, Optional, List
from backend.app.core.config import settings

logger = logging.getLogger("meetme.supabase")

class SupabaseService:
    def __init__(self):
        self.url = settings.SUPABASE_URL or "https://ikgsahbuhaucueffphxs.supabase.co"
        self.key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

    async def query_table(self, table: str, query_params: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """
        Queries any table via Supabase PostgREST API using the service_role key.
        """
        if not self.key or not self.url:
            return []

        endpoint = f"{self.url}/rest/v1/{table}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                res = await client.get(endpoint, headers=self.headers, params=query_params or {})
                if res.status_code == 200:
                    return res.json()
                else:
                    logger.warning(f"Supabase REST query {table} status {res.status_code}: {res.text}")
                    return []
            except Exception as e:
                logger.error(f"Supabase REST connection error: {e}")
                return []

    async def insert_record(self, table: str, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Inserts a record into any table via Supabase PostgREST API.
        """
        if not self.key or not self.url:
            return None

        endpoint = f"{self.url}/rest/v1/{table}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                res = await client.post(endpoint, headers=self.headers, json=record)
                if res.status_code in (200, 201):
                    data = res.json()
                    return data[0] if isinstance(data, list) and data else record
                else:
                    logger.warning(f"Supabase REST insert {table} failed ({res.status_code}): {res.text}")
                    return None
            except Exception as e:
                logger.error(f"Supabase REST insert error: {e}")
                return None

supabase_service = SupabaseService()
