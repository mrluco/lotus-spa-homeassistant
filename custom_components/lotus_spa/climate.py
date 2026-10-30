from __future__ import annotations

from typing import Any

from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature, HVACAction, HVACMode
from homeassistant.const import ATTR_TEMPERATURE, PRECISION_TENTHS, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .coordinator import LotusConfigEntry, LotusKoordinator
from .entity import LotusEntitaet

SOLL_MIN_VORGABE = 10.0
SOLL_MAX_VORGABE = 40.0

PARALLEL_UPDATES = 1


async def async_setup_entry(hass: HomeAssistant, eintrag: LotusConfigEntry, hinzufuegen: AddConfigEntryEntitiesCallback) -> None:
    koordinator = eintrag.runtime_data
    hinzufuegen(LotusThermostat(koordinator, g_) for g_ in koordinator.data)


class LotusThermostat(LotusEntitaet, ClimateEntity):
    _attr_name = None
    _attr_hvac_modes = [HVACMode.HEAT]
    _attr_hvac_mode = HVACMode.HEAT
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_precision = PRECISION_TENTHS
    _attr_target_temperature_step = 0.5

    def __init__(self, koordinator: LotusKoordinator, geraet: str) -> None:
        super().__init__(koordinator, geraet, "wasser")

    @property
    def supported_features(self) -> ClimateEntityFeature:
        return ClimateEntityFeature.TARGET_TEMPERATURE if self.daten.get("darf_temperatur") else ClimateEntityFeature(0)

    @property
    def current_temperature(self) -> float | None:
        return _zahl(self.daten.get("ist"))

    @property
    def target_temperature(self) -> float | None:
        return _zahl(self.daten.get("soll"))

    @property
    def hvac_action(self) -> HVACAction:
        return HVACAction.HEATING if self.daten.get("heizt") else HVACAction.IDLE

    @property
    def min_temp(self) -> float:
        bereich = self.daten.get("soll_bereich")
        return float(bereich[0]) if isinstance(bereich, list) and len(bereich) == 2 else SOLL_MIN_VORGABE

    @property
    def max_temp(self) -> float:
        bereich = self.daten.get("soll_bereich")
        return float(bereich[1]) if isinstance(bereich, list) and len(bereich) == 2 else SOLL_MAX_VORGABE

    async def async_set_temperature(self, **kwargs: Any) -> None:
        if (wert := kwargs.get(ATTR_TEMPERATURE)) is None:
            return
        await self.befehl("soll", wert=round(float(wert) * 2) / 2)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode != HVACMode.HEAT:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="nur_heizen")


def _zahl(wert: Any) -> float | None:
    try:
        return None if wert is None else float(wert)
    except (TypeError, ValueError):
        return None
