from __future__ import annotations

import time
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import LotusConfigEntry, LotusKoordinator
from .entity import LotusEntitaet
from .schalter import AUS, art, darf, erste_stufe, ist_an, schalter_liste, symbol

PARALLEL_UPDATES = 1
QUELLE = {"urlaubsmodus": "urlaub", "abendlicht": "abendlicht"}
WUNSCH_S = 15.0


async def async_setup_entry(hass: HomeAssistant, eintrag: LotusConfigEntry, hinzufuegen: AddConfigEntryEntitiesCallback) -> None:
    koordinator = eintrag.runtime_data
    neu: list[SwitchEntity] = []
    for g_, daten in koordinator.data.items():
        neu += [LotusSchalter(koordinator, g_, s_["titel"]) for s_ in schalter_liste(daten) if art(s_) == "schalter" and darf(s_)]
        neu += [LotusBadeerkennung(koordinator, g_, str(b_)) for b_ in ((daten.get("badeerkennung") or {}).get("geraete") or [])]
        if daten.get("wartungspause"):
            neu.append(LotusWartungspause(koordinator, g_))
        neu += [LotusEinstellung(koordinator, g_, was) for was in ("urlaubsmodus", "abendlicht") if isinstance(daten.get(QUELLE[was]), dict)]
    hinzufuegen(neu)


class LotusSchaltbar(LotusEntitaet):

    def __init__(self, koordinator: LotusKoordinator, geraet: str, titel: str) -> None:
        super().__init__(koordinator, geraet, f"schalter_{titel}")
        self.titel = titel
        self._attr_name = titel
        self._attr_translation_key = symbol(self._gemeldet)
        self._wunsch: tuple[str, float] | None = None

    @property
    def _gemeldet(self) -> dict[str, Any]:
        return next((s_ for s_ in schalter_liste(self.daten) if s_.get("titel") == self.titel), {})

    @property
    def schalter(self) -> dict[str, Any]:
        gemeldet = self._gemeldet
        if self._wunsch is None or not gemeldet:
            return gemeldet
        modus, seit = self._wunsch
        if time.monotonic() - seit > WUNSCH_S or str(gemeldet.get("aktiv") or AUS).upper() == modus.upper():
            self._wunsch = None
            return gemeldet
        return {**gemeldet, "aktiv": modus}

    @property
    def available(self) -> bool:
        return super().available and bool(self._gemeldet)

    @property
    def is_on(self) -> bool:
        return ist_an(self.schalter)

    async def schalten(self, modus: str) -> None:
        self._wunsch = (modus, time.monotonic())
        self.async_write_ha_state()
        try:
            await self.befehl("schalten", titel=self.titel, modus=modus)
        except Exception:
            self._wunsch = None
            self.async_write_ha_state()
            raise

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.schalten(erste_stufe(self.schalter))

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.schalten(AUS)


class LotusSchalter(LotusSchaltbar, SwitchEntity):
    pass


class LotusBadeerkennung(LotusEntitaet, SwitchEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "badeerkennung"

    def __init__(self, koordinator: LotusKoordinator, geraet: str, teil: str) -> None:
        super().__init__(koordinator, geraet, f"badeerkennung_{teil}")
        self.teil = teil
        self._attr_translation_placeholders = {"geraet": teil}

    @property
    def _auswahl(self) -> dict[str, Any]:
        return self.daten.get("badeerkennung") or {}

    @property
    def available(self) -> bool:
        return super().available and self.teil in (self._auswahl.get("geraete") or [])

    @property
    def is_on(self) -> bool:
        return self.teil in (self._auswahl.get("gewaehlt") or [])

    async def async_turn_on(self, **kwargs: Any) -> None:
        gewaehlt = [str(x_) for x_ in (self._auswahl.get("gewaehlt") or []) if str(x_) != self.teil]
        await self.befehl("badeerkennung", geraete=[*gewaehlt, self.teil])

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.befehl("badeerkennung", geraete=[str(x_) for x_ in (self._auswahl.get("gewaehlt") or []) if str(x_) != self.teil])


class LotusWartungspause(LotusEntitaet, SwitchEntity):
    _attr_translation_key = "wartungspause"

    def __init__(self, koordinator: LotusKoordinator, geraet: str) -> None:
        super().__init__(koordinator, geraet, "wartungspause")

    @property
    def available(self) -> bool:
        return super().available and bool(self.daten.get("wartungspause"))

    @property
    def is_on(self) -> bool:
        return bool((self.daten.get("wartungspause") or {}).get("laeuft"))

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.befehl("wartungspause", an=True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.befehl("wartungspause", an=False)


class LotusEinstellung(LotusEntitaet, SwitchEntity):

    def __init__(self, koordinator: LotusKoordinator, geraet: str, was: str) -> None:
        super().__init__(koordinator, geraet, was)
        self.quelle = QUELLE[was]
        self._attr_translation_key = was

    @property
    def available(self) -> bool:
        return super().available and isinstance(self.daten.get(self.quelle), dict)

    @property
    def is_on(self) -> bool:
        return bool((self.daten.get(self.quelle) or {}).get("an"))

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.befehl(self.quelle, wahl="an")

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.befehl(self.quelle, wahl="aus")

