from __future__ import annotations

from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .coordinator import LotusConfigEntry
from .schalter import art, darf, ist_an, schalter_liste, stufen
from .switch import LotusSchaltbar

PARALLEL_UPDATES = 1


async def async_setup_entry(hass: HomeAssistant, eintrag: LotusConfigEntry, hinzufuegen: AddConfigEntryEntitiesCallback) -> None:
    koordinator = eintrag.runtime_data
    hinzufuegen(LotusPumpe(koordinator, g_, s_["titel"]) for g_, daten in koordinator.data.items()
                for s_ in schalter_liste(daten) if art(s_) == "luefter" and darf(s_))


class LotusPumpe(LotusSchaltbar, FanEntity):
    _attr_supported_features = FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF | FanEntityFeature.PRESET_MODE

    @property
    def preset_modes(self) -> list[str]:
        return [str(m_.get("text") or m_.get("wert")) for m_ in stufen(self.schalter)]

    @property
    def preset_mode(self) -> str | None:
        if not ist_an(self.schalter):
            return None
        aktiv = str(self.schalter.get("aktiv") or "").upper()
        return next((str(m_.get("text") or m_.get("wert")) for m_ in stufen(self.schalter) if str(m_.get("wert")).upper() == aktiv), None)

    async def async_turn_on(self, percentage: int | None = None, preset_mode: str | None = None, **kwargs: Any) -> None:
        if preset_mode is not None:
            await self.async_set_preset_mode(preset_mode)
            return
        await super().async_turn_on()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        wert = next((str(m_["wert"]) for m_ in stufen(self.schalter) if str(m_.get("text") or m_.get("wert")) == preset_mode), None)
        if wert is None:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="unbekannte_stufe", translation_placeholders={"stufe": preset_mode})
        await self.befehl("schalten", titel=self.titel, modus=wert)
