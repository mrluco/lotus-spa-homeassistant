from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import LotusConfigEntry, LotusKoordinator
from .entity import LotusEntitaet

PARALLEL_UPDATES = 1


async def async_setup_entry(hass: HomeAssistant, eintrag: LotusConfigEntry, hinzufuegen: AddConfigEntryEntitiesCallback) -> None:
    koordinator = eintrag.runtime_data
    bekannt: set[tuple[str, str]] = set()

    @callback
    def nachziehen() -> None:
        neu: list[ButtonEntity] = []
        for g_, daten in (koordinator.data or {}).items():
            for a_ in (daten.get("wartung") or {}).get("aufgaben") or []:
                if isinstance(a_, dict) and a_.get("schluessel") and (g_, str(a_["schluessel"])) not in bekannt:
                    bekannt.add((g_, str(a_["schluessel"])))
                    neu.append(LotusWartungErledigt(koordinator, g_, str(a_["schluessel"]), str(a_.get("titel") or "")))
        if neu:
            hinzufuegen(neu)

    nachziehen()
    eintrag.async_on_unload(koordinator.async_add_listener(nachziehen))


class LotusWartungErledigt(LotusEntitaet, ButtonEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "wartung_erledigt"

    def __init__(self, koordinator: LotusKoordinator, geraet: str, schluessel: str, titel: str) -> None:
        super().__init__(koordinator, geraet, f"wartung_{schluessel.replace(':', '_')}_erledigt")
        self.schluessel = schluessel
        self._attr_translation_placeholders = {"titel": titel}

    @property
    def available(self) -> bool:
        return super().available and bool(self.aufgabe(self.schluessel).get("erledigen"))

    async def async_press(self) -> None:
        await self.befehl("wartung_erledigt", aufgabe=self.schluessel)
