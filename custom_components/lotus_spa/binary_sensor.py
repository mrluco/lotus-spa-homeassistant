from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import LotusConfigEntry, LotusKoordinator
from .entity import LotusEntitaet


async def async_setup_entry(hass: HomeAssistant, eintrag: LotusConfigEntry, hinzufuegen: AddConfigEntryEntitiesCallback) -> None:
    koordinator = eintrag.runtime_data
    neu: list[BinarySensorEntity] = []
    for g_, daten in koordinator.data.items():
        neu.append(LotusVerbindung(koordinator, g_))
        if daten.get("filter_laeuft") is not None:
            neu.append(LotusFilter(koordinator, g_))
    hinzufuegen(neu)


class LotusFilter(LotusEntitaet, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_translation_key = "filter"

    def __init__(self, koordinator: LotusKoordinator, geraet: str) -> None:
        super().__init__(koordinator, geraet, "filter")

    @property
    def is_on(self) -> bool:
        return bool(self.daten.get("filter_laeuft"))


class LotusVerbindung(LotusEntitaet, BinarySensorEntity):

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "verbindung"

    def __init__(self, koordinator: LotusKoordinator, geraet: str) -> None:
        super().__init__(koordinator, geraet, "verbindung")

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and bool(self.daten)

    @property
    def is_on(self) -> bool:
        return bool(self.daten.get("verbunden"))
