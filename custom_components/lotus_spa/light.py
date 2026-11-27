from __future__ import annotations

from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import LotusConfigEntry, LotusKoordinator
from .entity import nachlegen, stand_ersetzen
from .schalter import art, darf, schalter_liste
from .switch import LotusSchaltbar

PARALLEL_UPDATES = 1


async def async_setup_entry(hass: HomeAssistant, eintrag: LotusConfigEntry, hinzufuegen: AddConfigEntryEntitiesCallback) -> None:
    nachlegen(eintrag, hinzufuegen, finden)


def finden(koordinator: LotusKoordinator) -> list[LightEntity]:
    neu: list[LightEntity] = []
    for g_, daten in (koordinator.data or {}).items():
        for s_ in schalter_liste(daten):
            if art(s_) == "licht" and darf(s_):
                stand_ersetzen(koordinator.hass, "binary_sensor", f"{g_}_stand_{s_['titel']}")
                neu.append(LotusLicht(koordinator, g_, s_["titel"]))
    return neu


class LotusLicht(LotusSchaltbar, LightEntity):
    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}
