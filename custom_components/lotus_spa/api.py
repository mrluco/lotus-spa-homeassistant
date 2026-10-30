from __future__ import annotations

import asyncio
from typing import Any

from aiohttp import ClientError, ClientResponse
from homeassistant.exceptions import OAuth2TokenRequestBaseError
from homeassistant.helpers.config_entry_oauth2_flow import OAuth2Session

from .const import ABO_URL, API_URL, KOPF_FASSUNG

ZEITLIMIT_S = 20


class LotusFehler(Exception):

    def __init__(self, text: str = "") -> None:
        super().__init__(text)
        self.text = text


class LotusAnmeldungAbgelaufen(LotusFehler):
    pass


class LotusAboNoetig(LotusFehler):

    def __init__(self, text: str = "", abo_url: str = ABO_URL, zugang: str = "abo_noetig", fehlt: list[str] | None = None) -> None:
        super().__init__(text)
        self.abo_url = abo_url
        self.zugang = zugang
        self.fehlt = list(fehlt or [])


class LotusNichtGefunden(LotusFehler):
    pass


class LotusKeinRecht(LotusFehler):
    pass


class LotusZuOft(LotusFehler):

    def __init__(self, text: str = "", warten_s: float = 60.0) -> None:
        super().__init__(text)
        self.warten_s = warten_s


class LotusPlanGrenze(LotusZuOft):
    pass


class LotusAbgelehnt(LotusFehler):
    pass


class LotusFrost(LotusAbgelehnt):
    pass


class LotusNichtErreichbar(LotusFehler):
    pass


class LotusApi:

    def __init__(self, sitzung: OAuth2Session, fassung: str = "") -> None:
        self._sitzung = sitzung
        self._kopf = {KOPF_FASSUNG: fassung} if fassung else {}

    async def _anfrage(self, methode: str, pfad: str, koerper: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            async with asyncio.timeout(ZEITLIMIT_S):
                antwort = await self._sitzung.async_request(methode, f"{API_URL}/{pfad}", json=koerper, headers=dict(self._kopf))
                return await auswerten(antwort)
        except (LotusFehler, OAuth2TokenRequestBaseError):
            raise
        except (ClientError, TimeoutError) as err:
            raise LotusNichtErreichbar(str(err)) from err

    async def konto(self) -> dict[str, Any]:
        return await self._anfrage("GET", "konto")

    async def stand(self) -> dict[str, Any]:
        return await self._anfrage("GET", "stand")

    async def befehl(self, geraet: str, was: str, **werte: Any) -> dict[str, Any]:
        return await self._anfrage("POST", "befehl", {"geraet": geraet, "was": was, **werte})


async def auswerten(antwort: ClientResponse) -> dict[str, Any]:
    try:
        daten = await antwort.json(content_type=None)
    except (ClientError, ValueError):
        daten = {}
    if not isinstance(daten, dict):
        daten = {}
    text = str(daten.get("text") or daten.get("fehler") or "")
    status = antwort.status
    if status == 200 and daten.get("ok") is not False:
        return daten
    if status == 401:
        raise LotusAnmeldungAbgelaufen(text)
    if status == 402:
        raise LotusAboNoetig(text, str(daten.get("abo_url") or ABO_URL), str(daten.get("zugang") or "abo_noetig"),
                             [str(x_) for x_ in (daten.get("fehlt") or []) if isinstance(x_, str)])
    if status == 404:
        raise LotusNichtGefunden(text)
    if status == 409:
        raise LotusKeinRecht(text)
    if status == 429:
        try:
            warten = float(antwort.headers.get("Retry-After") or 60)
        except ValueError:
            warten = 60.0
        if daten.get("grenze") == "tag":
            raise LotusPlanGrenze(text, max(1.0, warten))
        raise LotusZuOft(text, max(1.0, warten))
    if status >= 500:
        raise LotusNichtErreichbar(text or f"HTTP {status}")
    if daten.get("frost"):
        raise LotusFrost(text)
    raise LotusAbgelehnt(text or f"HTTP {status}")
