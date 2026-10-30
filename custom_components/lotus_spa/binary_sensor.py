from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import LESEN_AN_AUS
from .coordinator import LotusConfigEntry, LotusKoordinator
from .entity import LotusEntitaet
from .schalter import darf, ist_an, schalter_liste, stufe_text

KLASSE: dict[str, BinarySensorDeviceClass] = {
    "umwaelzpumpe": BinarySensorDeviceClass.RUNNING,
    "ozon": BinarySensorDeviceClass.RUNNING,
    "feinspuelung": BinarySensorDeviceClass.RUNNING,
}


async def async_setup_entry(hass: HomeAssistant, eintrag: LotusConfigEntry, hinzufuegen: AddConfigEntryEntitiesCallback) -> None:
    koordinator = eintrag.runtime_data
    neu: list[BinarySensorEntity] = []
    for g_, daten in koordinator.data.items():
        neu.append(LotusVerbindung(koordinator, g_))
        if daten.get("filter_laeuft") is not None:
            neu.append(LotusFilter(koordinator, g_))
        neu.append(LotusHeizung(koordinator, g_))
        neu.append(LotusMeldung(koordinator, g_))
        neu += [LotusZustand(koordinator, g_, z_["titel"]) for z_ in (daten.get("zustaende") or [])
                if isinstance(z_, dict) and z_.get("titel") in LESEN_AN_AUS and isinstance(z_.get("an"), bool)]
        neu += [LotusSchalterStand(koordinator, g_, s_["titel"], s_.get("art") == "licht") for s_ in schalter_liste(daten) if not darf(s_)]
    hinzufuegen(neu)


class LotusHeizung(LotusEntitaet, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.HEAT
    _attr_translation_key = "heizung"

    def __init__(self, koordinator: LotusKoordinator, geraet: str) -> None:
        super().__init__(koordinator, geraet, "heizung")

    @property
    def is_on(self) -> bool:
        return bool(self.daten.get("heizt"))


class LotusMeldung(LotusEntitaet, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_translation_key = "meldung"

    def __init__(self, koordinator: LotusKoordinator, geraet: str) -> None:
        super().__init__(koordinator, geraet, "meldung")

    @property
    def is_on(self) -> bool:
        return bool(self.daten.get("meldungen"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"meldungen": list(self.daten.get("meldungen") or [])}


class LotusZustand(LotusEntitaet, BinarySensorEntity):

    def __init__(self, koordinator: LotusKoordinator, geraet: str, titel: str) -> None:
        schluessel = LESEN_AN_AUS[titel]
        super().__init__(koordinator, geraet, schluessel)
        self.titel = titel
        self._attr_translation_key = schluessel
        self._attr_device_class = KLASSE.get(schluessel)

    @property
    def available(self) -> bool:
        return super().available and isinstance(self.zustand(self.titel).get("an"), bool)

    @property
    def is_on(self) -> bool:
        return bool(self.zustand(self.titel).get("an"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"text": str(self.zustand(self.titel).get("text") or "")}


class LotusSchalterStand(LotusEntitaet, BinarySensorEntity):

    def __init__(self, koordinator: LotusKoordinator, geraet: str, titel: str, licht: bool) -> None:
        super().__init__(koordinator, geraet, f"stand_{titel}")
        self.titel = titel
        self._attr_name = titel
        self._attr_device_class = BinarySensorDeviceClass.LIGHT if licht else BinarySensorDeviceClass.RUNNING

    @property
    def schalter(self) -> dict[str, Any]:
        return next((s_ for s_ in schalter_liste(self.daten) if s_.get("titel") == self.titel), {})

    @property
    def available(self) -> bool:
        return super().available and bool(self.schalter)

    @property
    def is_on(self) -> bool:
        return ist_an(self.schalter)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        stufe = stufe_text(self.schalter)
        return {"stufe": stufe} if stufe and ist_an(self.schalter) else {}


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
