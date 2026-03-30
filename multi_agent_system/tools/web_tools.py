"""
Herramientas para acceso a internet
"""
import asyncio
import aiohttp
from typing import Optional, Dict, Any
import json


class WebTools:
    """Herramientas de internet para agentes"""

    def __init__(self, timeout: int = 30):
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Obtener o crear sesión HTTP"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self.timeout)
        return self._session

    async def get_request(self, url: str, headers: Optional[Dict] = None) -> dict:
        """Realizar una petición GET"""
        try:
            session = await self._get_session()
            async with session.get(url, headers=headers) as response:
                content = await response.text()
                return {
                    "success": True,
                    "status_code": response.status,
                    "content": content,
                    "headers": dict(response.headers),
                    "url": str(response.url)
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "url": url
            }

    async def post_request(
        self,
        url: str,
        data: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> dict:
        """Realizar una petición POST"""
        try:
            session = await self._get_session()
            async with session.post(
                url,
                data=data,
                json=json_data,
                headers=headers
            ) as response:
                content = await response.text()
                return {
                    "success": True,
                    "status_code": response.status,
                    "content": content,
                    "headers": dict(response.headers),
                    "url": str(response.url)
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "url": url
            }

    async def download_file(self, url: str, destination: str) -> dict:
        """Descargar un archivo"""
        try:
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status == 200:
                    content = await response.read()

                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(
                        None,
                        lambda: open(destination, 'wb').write(content)
                    )

                    return {
                        "success": True,
                        "destination": destination,
                        "size": len(content),
                        "url": url
                    }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}",
                        "url": url
                    }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "url": url
            }

    async def search_web(self, query: str) -> dict:
        """Simulación de búsqueda web (placeholder)"""
        # En un sistema real, esto usaría una API de búsqueda
        return {
            "success": True,
            "query": query,
            "results": [
                {"title": f"Result for: {query}", "url": "https://example.com"}
            ],
            "note": "This is a simulated search. Integrate real search API."
        }

    async def close(self):
        """Cerrar sesión HTTP"""
        if self._session and not self._session.closed:
            await self._session.close()
