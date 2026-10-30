from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.const import EntityCategory, UnitOfTemperature, UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import LotusAbgelehnt
from .const import DOMAIN
from .coordinator import LotusConfigEntry, LotusKoordinator
from .entity import LotusEntitaet

PARALLEL_UPDATES = 1


async def async_setup_entry(hass: HomeAssistant, eintrag: LotusConfigEntry, hinzufuegen: AddConfigEntryEntitiesCallback) -> None:
    koordinator = eintrag.runtime_data
    neu: list[NumberEntity] = []
    for g_, daten in koordinator.data.items():
        if isinstance(daten.get("volumen"), dict):
            neu.append(LotusGrundlage(koordinator, g_, "volumen", UnitOfVolume.LITERS, 1.0, 100000.0, 1.0))
        if isinstance(daten.get("strompreis"), dict):
            neu.append(LotusGrundlage(koordinator, g_, "strompreis", "ct/kWh", 0.0, 1000.0, 0.1))
        if isinstance(daten.get("urlaub"), dict):
            neu.append(LotusUrlaubsziel(koordinator, g_))
        if isinstance(daten.get("absenkung"), dict):
            neu.append(LotusAbsenkung(koordinator, g_))
    hinzufuegen(neu)


async def senden(entitaet: LotusEntitaet, was: str, **werte: float | int | str) -> None:
    try:
        await entitaet.befehl(was, **werte)
    except ServiceValidationError:
        raise
    except HomeAssistantError as err:
        if err.translation_key != "abgelehnt" or not isinstance(err.__cause__, LotusAbgelehnt):
            raise
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="abgelehnt",
                                     translation_placeholders=err.translation_placeholders) from err


class LotusGrundlage(LotusEntitaet, NumberEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX

    def __init__(self, koordinator: LotusKoordinator, geraet: str, was: str, einheit: str, kleinst: float, groesst: float, schritt: float) -> None:
        super().__init__(koordinator, geraet, f"grundlage_{was}")
        self.was = was
        self._attr_translation_key = was
        self._attr_native_unit_of_measurement = einheit
        self._attr_native_min_value = kleinst
        self._attr_native_max_value = groesst
        self._attr_native_step = schritt

    @property
    def available(self) -> bool:
        return super().available and isinstance(self.daten.get(self.was), dict)

    @property
    def native_value(self) -> float | None:
        wert = (self.daten.get(self.was) or {}).get("wert")
        return float(wert) if isinstance(wert, (int, float)) else None

    async def async_set_native_value(self, value: float) -> None:
        if self.native_value is not None and abs(float(value) - self.native_value) < 1e-9:
            return
        wert: float | int = int(round(value)) if self.was == "volumen" else round(float(value), 1)
        await senden(self, self.was, wert=wert)


class LotusUrlaubsziel(LotusEntitaet, NumberEntity):
    _attr_translation_key = "urlaub_ziel"
    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_step = 0.5
    _attr_mode = NumberMode.BOX

    def __init__(self, koordinator: LotusKoordinator, geraet: str) -> None:
        super().__init__(koordinator, geraet, "urlaub_ziel")

    @property
    def urlaub(self) -> dict:
        return self.daten.get("urlaub") or {}

    @property
    def available(self) -> bool:
        return super().available and isinstance(self.daten.get("urlaub"), dict)

    @property
    def native_min_value(self) -> float:
        return float(self.urlaub.get("unten") or 10.0)

    @property
    def native_max_value(self) -> float:
        return float(self.urlaub.get("oben") or 40.0)

    @property
    def native_value(self) -> float | None:
        wert = self.urlaub.get("ziel")
        return float(wert) if isinstance(wert, (int, float)) else None

    async def async_set_native_value(self, value: float) -> None:
        if self.native_value is not None and abs(float(value) - self.native_value) < 1e-9:
            return
        await senden(self, "urlaub", wahl=f"{float(value):.1f}")


class LotusAbsenkung(LotusEntitaet, NumberEntity):
    _attr_translation_key = "absenkung"
    _attr_native_unit_of_measurement = "K"
    _attr_native_min_value = 0.0
    _attr_native_max_value = 30.0
    _attr_native_step = 0.5
    _attr_mode = NumberMode.BOX

    def __init__(self, koordinator: LotusKoordinator, geraet: str) -> None:
        super().__init__(koordinator, geraet, "absenkung_grad")

    @property
    def available(self) -> bool:
        return super().available and isinstance((self.daten.get("absenkung") or {}).get("grad"), (int, float))

    @property
    def native_value(self) -> float | None:
        wert = (self.daten.get("absenkung") or {}).get("grad")
        return float(wert) if isinstance(wert, (int, float)) else None

    async def async_set_native_value(self, value: float) -> None:
        if self.native_value is not None and abs(float(value) - self.native_value) < 1e-9:
            return
        await senden(self, "absenkung", wahl=f"{float(value):.1f}")

