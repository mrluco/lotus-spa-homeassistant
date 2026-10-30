from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import LESEN_TEXT
from .coordinator import LotusConfigEntry, LotusKoordinator
from .entity import LotusEntitaet

PARALLEL_UPDATES = 0
TEXT_MAX = 255


async def async_setup_entry(hass: HomeAssistant, eintrag: LotusConfigEntry, hinzufuegen: AddConfigEntryEntitiesCallback) -> None:
    koordinator = eintrag.runtime_data
    neu: list[SensorEntity] = []
    for g_, daten in koordinator.data.items():
        neu.append(LotusTemperatur(koordinator, g_, "wassertemperatur", "ist"))
        neu.append(LotusTemperatur(koordinator, g_, "solltemperatur", "soll"))
        neu.append(LotusMeldungText(koordinator, g_))
        neu += [LotusText(koordinator, g_, z_["titel"]) for z_ in (daten.get("zustaende") or [])
                if isinstance(z_, dict) and z_.get("titel") in LESEN_TEXT]
        if daten.get("heizmodus") and not daten["heizmodus"].get("darf"):
            neu.append(LotusHeizmodusStand(koordinator, g_))
    hinzufuegen(neu)


class LotusTemperatur(LotusEntitaet, SensorEntity):
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_suggested_display_precision = 1

    def __init__(self, koordinator: LotusKoordinator, geraet: str, schluessel: str, feld: str) -> None:
        super().__init__(koordinator, geraet, schluessel)
        self.feld = feld
        self._attr_translation_key = schluessel

    @property
    def native_value(self) -> float | None:
        try:
            wert = self.daten.get(self.feld)
            return None if wert is None else float(wert)
        except (TypeError, ValueError):
            return None


class LotusMeldungText(LotusEntitaet, SensorEntity):
    _attr_translation_key = "meldungstext"

    def __init__(self, koordinator: LotusKoordinator, geraet: str) -> None:
        super().__init__(koordinator, geraet, "meldungstext")

    @property
    def native_value(self) -> str:
        return (" · ".join(str(m_) for m_ in (self.daten.get("meldungen") or [])) or "-")[:TEXT_MAX]


class LotusText(LotusEntitaet, SensorEntity):

    def __init__(self, koordinator: LotusKoordinator, geraet: str, titel: str) -> None:
        schluessel = LESEN_TEXT[titel]
        super().__init__(koordinator, geraet, f"text_{schluessel}")
        self.titel = titel
        self._attr_translation_key = schluessel

    @property
    def available(self) -> bool:
        return super().available and bool(self.zustand(self.titel))

    @property
    def native_value(self) -> str:
        return str(self.zustand(self.titel).get("text") or "-")[:TEXT_MAX]


class LotusHeizmodusStand(LotusEntitaet, SensorEntity):
    _attr_translation_key = "heizmodus"

    def __init__(self, koordinator: LotusKoordinator, geraet: str) -> None:
        super().__init__(koordinator, geraet, "heizmodus_stand")

    @property
    def native_value(self) -> str | None:
        hm = self.daten.get("heizmodus") or {}
        aktiv = str(hm.get("aktiv") or "")
        return next((str(m_.get("text") or m_.get("wert")) for m_ in (hm.get("modi") or []) if str(m_.get("wert")) == aktiv), aktiv or None)
