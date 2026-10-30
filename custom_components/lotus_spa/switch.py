from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import LotusConfigEntry, LotusKoordinator
from .entity import LotusEntitaet
from .schalter import AUS, art, darf, erste_stufe, ist_an, schalter_liste

PARALLEL_UPDATES = 1


async def async_setup_entry(hass: HomeAssistant, eintrag: LotusConfigEntry, hinzufuegen: AddConfigEntryEntitiesCallback) -> None:
    koordinator = eintrag.runtime_data
    neu: list[SwitchEntity] = []
    for g_, daten in koordinator.data.items():
        neu += [LotusSchalter(koordinator, g_, s_["titel"]) for s_ in schalter_liste(daten) if art(s_) == "schalter" and darf(s_)]
        neu += [LotusBadeerkennung(koordinator, g_, str(b_)) for b_ in ((daten.get("badeerkennung") or {}).get("geraete") or [])]
    hinzufuegen(neu)


class LotusSchaltbar(LotusEntitaet):

    def __init__(self, koordinator: LotusKoordinator, geraet: str, titel: str) -> None:
        super().__init__(koordinator, geraet, f"schalter_{titel}")
        self.titel = titel
        self._attr_name = titel

    @property
    def schalter(self) -> dict[str, Any]:
        return next((s_ for s_ in schalter_liste(self.daten) if s_.get("titel") == self.titel), {})

    @property
    def available(self) -> bool:
        return super().available and bool(self.schalter)

    @property
    def is_on(self) -> bool:
        return ist_an(self.schalter)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.befehl("schalten", titel=self.titel, modus=erste_stufe(self.schalter))

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.befehl("schalten", titel=self.titel, modus=AUS)


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
