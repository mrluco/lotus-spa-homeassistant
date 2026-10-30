from __future__ import annotations

from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import LotusConfigEntry
from .schalter import art, darf, schalter_liste
from .switch import LotusSchaltbar

PARALLEL_UPDATES = 1


async def async_setup_entry(hass: HomeAssistant, eintrag: LotusConfigEntry, hinzufuegen: AddConfigEntryEntitiesCallback) -> None:
    koordinator = eintrag.runtime_data
    hinzufuegen(LotusLicht(koordinator, g_, s_["titel"]) for g_, daten in koordinator.data.items()
                for s_ in schalter_liste(daten) if art(s_) == "licht" and darf(s_))


class LotusLicht(LotusSchaltbar, LightEntity):
    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}
