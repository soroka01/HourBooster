"""Public Steam app names with bounded requests and an in-memory cache."""

import asyncio
import time
from typing import Dict, Iterable, Optional, Tuple

import aiohttp


class GameNames:
    def __init__(self) -> None:
        self._cache: Dict[int, Tuple[float, Optional[str]]] = {}
        self._lock = asyncio.Lock()

    async def get_names(self, app_ids: Iterable[int]) -> Dict[int, str]:
        app_ids = tuple(dict.fromkeys(app_ids))
        async with self._lock:
            now = time.monotonic()
            missing = [app_id for app_id in app_ids
                       if self._cache.get(app_id, (0, None))[0] <= now]
            if missing:
                # Failed or cancelled lookups must not retry on every live refresh.
                for app_id in missing:
                    self._cache[app_id] = (now + 300, None)
                limit = asyncio.Semaphore(8)
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=3)) as session:
                    async def fetch(app_id: int) -> None:
                        try:
                            async with limit:
                                async with session.get(
                                    "https://store.steampowered.com/api/appdetails",
                                    params={"appids": str(app_id), "l": "russian", "filters": "basic"},
                                ) as response:
                                    response.raise_for_status()
                                    payload = await response.json()
                            entry = payload.get(str(app_id), {})
                            name = entry.get("data", {}).get("name") if entry.get("success") else None
                            if isinstance(name, str) and name.strip():
                                self._cache[app_id] = (time.monotonic() + 86400, " ".join(name.split()))
                        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, AttributeError):
                            pass

                    try:
                        await asyncio.wait_for(asyncio.gather(*(fetch(app_id) for app_id in missing)), 6)
                    except asyncio.TimeoutError:
                        pass
        return {app_id: self._cache[app_id][1] for app_id in app_ids
                if self._cache.get(app_id, (0, None))[1] is not None}
