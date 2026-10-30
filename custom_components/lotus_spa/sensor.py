from __future__ import annotations

from datetime import date, datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import SIGNAL_STRENGTH_DECIBELS_MILLIWATT, EntityCategory, UnitOfEnergy, UnitOfPower, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import ABO_ARTEN, ALT_FILTERUNG, DOMAIN, EMPFANG, KEINE_MELDUNG, LESEN_TEXT, SOLAR_MODI, WETTER_QUELLE
from .coordinator import LotusConfigEntry, LotusKoordinator
from .entity import LotusBoxEntitaet, LotusEntitaet

PARALLEL_UPDATES = 0
TEXT_MAX = 255


async def async_setup_entry(hass: HomeAssistant, eintrag: LotusConfigEntry, hinzufuegen: AddConfigEntryEntitiesCallback) -> None:
    koordinator = eintrag.runtime_data
    register = er.async_get(hass)
    neu: list[SensorEntity] = []
    for g_, daten in koordinator.data.items():
        if alt := register.async_get_entity_id("sensor", DOMAIN, f"{g_}_{ALT_FILTERUNG}"):
            register.async_remove(alt)
        neu.append(LotusTemperatur(koordinator, g_, "wassertemperatur", "ist"))
        neu.append(LotusTemperatur(koordinator, g_, "solltemperatur", "soll"))
        neu.append(LotusMeldungText(koordinator, g_))
        neu += [LotusText(koordinator, g_, z_["titel"]) for z_ in (daten.get("zustaende") or [])
                if isinstance(z_, dict) and z_.get("titel") in LESEN_TEXT]
        if daten.get("heizmodus") and not daten["heizmodus"].get("darf"):
            neu.append(LotusHeizmodusStand(koordinator, g_))
        neu.append(LotusSollGrund(koordinator, g_))
        neu.append(LotusFilterblock(koordinator, g_))
        if daten.get("solar") and not daten["solar"].get("darf"):
            neu.append(LotusSolarStand(koordinator, g_))
        neu += [LotusWartungTermin(koordinator, g_, str(a_["schluessel"]), str(a_.get("titel") or ""))
                for a_ in ((daten.get("wartung") or {}).get("aufgaben") or []) if isinstance(a_, dict) and a_.get("schluessel")]
        if daten.get("pflegelauf"):
            neu.append(LotusEnde(koordinator, g_, "pflegelauf"))
        neu.append(LotusAussen(koordinator, g_))
        if isinstance(daten.get("warm_um"), dict):
            neu.append(LotusWarmUm(koordinator, g_))
        if "energie" in daten and daten.get("energie") is not None:
            neu += [LotusEnergie(koordinator, g_), LotusLeistung(koordinator, g_), LotusKostenHeute(koordinator, g_)]
        box = daten.get("box") or {}
        if box.get("id"):
            neu.append(LotusEmpfang(koordinator, g_))
            if box.get("rssi") is not None:
                neu.append(LotusSignal(koordinator, g_))
            if box.get("ssid"):
                neu.append(LotusNetz(koordinator, g_))
            if box.get("seit"):
                neu.append(LotusBoxStart(koordinator, g_))
        if daten.get("wartungspause"):
            neu.append(LotusEnde(koordinator, g_, "wartungspause"))
        if daten.get("badezeiten") or daten.get("naechste_badezeit"):
            neu += [LotusBadezeitPunkt(koordinator, g_, feld) for feld in ("beginn", "ende")]
    if koordinator.konto is not None:
        neu += [LotusKontoAbo(koordinator), LotusKontoBis(koordinator)]
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
        return (" · ".join(str(m_) for m_ in (self.daten.get("meldungen") or [])) or KEINE_MELDUNG)[:TEXT_MAX]


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


class LotusSollGrund(LotusEntitaet, SensorEntity):
    _attr_translation_key = "soll_grund"

    def __init__(self, koordinator: LotusKoordinator, geraet: str) -> None:
        super().__init__(koordinator, geraet, "soll_grund")

    @property
    def native_value(self) -> str:
        return str(self.daten.get("soll_grund") or "-")[:TEXT_MAX]


class LotusFilterblock(LotusEntitaet, SensorEntity):
    _attr_translation_key = "filterblock"

    def __init__(self, koordinator: LotusKoordinator, geraet: str) -> None:
        super().__init__(koordinator, geraet, "filterblock")

    @property
    def native_value(self) -> str:
        return str(self.daten.get("filter_aktiv") or "-")

    @property
    def extra_state_attributes(self) -> dict[str, list[str] | str]:
        attribute: dict[str, list[str] | str] = {"bloecke": [str(b_) for b_ in (self.daten.get("filter_bloecke") or [])]}
        grund = (self.daten.get("filterzeiten") or {}).get("grund")
        if grund:
            attribute["hinweis"] = str(grund)
        return attribute


class LotusSolarStand(LotusEntitaet, SensorEntity):
    _attr_translation_key = "solar_betriebsart"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = list(SOLAR_MODI)

    def __init__(self, koordinator: LotusKoordinator, geraet: str) -> None:
        super().__init__(koordinator, geraet, "solar_betriebsart_stand")

    @property
    def native_value(self) -> str | None:
        modus = str((self.daten.get("solar") or {}).get("modus") or "")
        return modus if modus in SOLAR_MODI else None


class LotusBadezeitPunkt(LotusEntitaet, SensorEntity):
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, koordinator: LotusKoordinator, geraet: str, feld: str) -> None:
        super().__init__(koordinator, geraet, f"badezeit_{feld}")
        self.feld = feld
        self._attr_translation_key = f"badezeit_{feld}"

    @property
    def native_value(self) -> datetime | None:
        wert = (self.daten.get("naechste_badezeit") or {}).get(self.feld)
        return dt_util.parse_datetime(str(wert)) if wert else None


class LotusWartungTermin(LotusEntitaet, SensorEntity):
    _attr_device_class = SensorDeviceClass.DATE
    _attr_translation_key = "wartung"

    def __init__(self, koordinator: LotusKoordinator, geraet: str, schluessel: str, titel: str) -> None:
        super().__init__(koordinator, geraet, f"wartung_{schluessel.replace(':', '_')}")
        self.schluessel = schluessel
        self._attr_translation_placeholders = {"titel": titel}

    @property
    def available(self) -> bool:
        return super().available and bool(self.aufgabe(self.schluessel))

    @property
    def native_value(self) -> date | None:
        wert = self.aufgabe(self.schluessel).get("faellig_am")
        try:
            return date.fromisoformat(str(wert)) if wert else None
        except ValueError:
            return None

    @property
    def extra_state_attributes(self) -> dict[str, int | str | bool | None]:
        a_ = self.aufgabe(self.schluessel)
        return {"tage_uebrig": a_.get("tage_uebrig"), "text": str(a_.get("text") or ""), "vorwarnung": bool(a_.get("vorwarnung"))}


class LotusEnde(LotusEntitaet, SensorEntity):
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, koordinator: LotusKoordinator, geraet: str, was: str) -> None:
        super().__init__(koordinator, geraet, f"{was}_ende")
        self.was = was
        self._attr_translation_key = f"{was}_ende"

    @property
    def available(self) -> bool:
        return super().available and bool(self.daten.get(self.was))

    @property
    def native_value(self) -> datetime | None:
        wert = (self.daten.get(self.was) or {}).get("bis")
        return dt_util.parse_datetime(str(wert)) if wert else None


class LotusAussen(LotusEntitaet, SensorEntity):
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_translation_key = "aussen"
    _attr_attribution = WETTER_QUELLE

    def __init__(self, koordinator: LotusKoordinator, geraet: str) -> None:
        super().__init__(koordinator, geraet, "aussen")

    @property
    def native_value(self) -> float | None:
        wert = self.daten.get("aussen")
        return float(wert) if isinstance(wert, (int, float)) else None


class LotusWarmUm(LotusEntitaet, SensorEntity):
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_translation_key = "warm_um"

    def __init__(self, koordinator: LotusKoordinator, geraet: str) -> None:
        super().__init__(koordinator, geraet, "warm_um")

    @property
    def native_value(self) -> datetime | None:
        wert = (self.daten.get("warm_um") or {}).get("zeit")
        return dt_util.parse_datetime(str(wert)) if wert else None


class LotusEnergieBasis(LotusEntitaet, SensorEntity):

    @property
    def energie(self) -> dict:
        return self.daten.get("energie") or {}

    @property
    def available(self) -> bool:
        return super().available and bool(self.energie)


class LotusEnergie(LotusEnergieBasis):
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_suggested_display_precision = 2
    _attr_translation_key = "energie"

    def __init__(self, koordinator: LotusKoordinator, geraet: str) -> None:
        super().__init__(koordinator, geraet, "energie")

    @property
    def native_value(self) -> float | None:
        wert = self.energie.get("kwh")
        return float(wert) if isinstance(wert, (int, float)) else None


class LotusLeistung(LotusEnergieBasis):
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_translation_key = "leistung"

    def __init__(self, koordinator: LotusKoordinator, geraet: str) -> None:
        super().__init__(koordinator, geraet, "leistung")

    @property
    def native_value(self) -> float | None:
        wert = self.energie.get("w")
        return float(wert) if isinstance(wert, (int, float)) else None


class LotusKostenHeute(LotusEnergieBasis):
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "EUR"
    _attr_suggested_display_precision = 2
    _attr_translation_key = "kosten_heute"

    def __init__(self, koordinator: LotusKoordinator, geraet: str) -> None:
        super().__init__(koordinator, geraet, "kosten_heute")

    @property
    def native_value(self) -> float | None:
        wert = self.energie.get("kosten_heute")
        return float(wert) if isinstance(wert, (int, float)) else None


class LotusEmpfang(LotusBoxEntitaet, SensorEntity):
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_options = list(EMPFANG.values())
    _attr_translation_key = "empfang"

    def __init__(self, koordinator: LotusKoordinator, geraet: str) -> None:
        super().__init__(koordinator, geraet, "empfang")

    @property
    def native_value(self) -> str | None:
        return EMPFANG.get(str(self.box.get("empfang") or ""))


class LotusSignal(LotusBoxEntitaet, SensorEntity):
    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "signal"

    def __init__(self, koordinator: LotusKoordinator, geraet: str) -> None:
        super().__init__(koordinator, geraet, "signal")

    @property
    def native_value(self) -> int | None:
        wert = self.box.get("rssi")
        return int(wert) if isinstance(wert, (int, float)) else None


class LotusNetz(LotusBoxEntitaet, SensorEntity):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "netz"

    def __init__(self, koordinator: LotusKoordinator, geraet: str) -> None:
        super().__init__(koordinator, geraet, "netz")

    @property
    def native_value(self) -> str | None:
        return str(self.box.get("ssid") or "") or None


class LotusBoxStart(LotusBoxEntitaet, SensorEntity):
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "box_start"

    def __init__(self, koordinator: LotusKoordinator, geraet: str) -> None:
        super().__init__(koordinator, geraet, "start")

    @property
    def native_value(self) -> datetime | None:
        wert = self.box.get("seit")
        return dt_util.parse_datetime(str(wert)) if wert else None


class LotusKontoEntitaet(CoordinatorEntity[LotusKoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, koordinator: LotusKoordinator, schluessel: str) -> None:
        super().__init__(koordinator)
        eintrag = koordinator.config_entry.entry_id
        self._attr_unique_id = f"konto_{eintrag}_{schluessel}"
        self._attr_translation_key = schluessel
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, f"konto_{eintrag}")})

    @property
    def konto(self) -> dict:
        return self.coordinator.konto or {}

    @property
    def available(self) -> bool:
        return super().available and bool(self.konto)


class LotusKontoAbo(LotusKontoEntitaet):
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = list(ABO_ARTEN)

    def __init__(self, koordinator: LotusKoordinator) -> None:
        super().__init__(koordinator, "abo")

    @property
    def native_value(self) -> str | None:
        art = str(self.konto.get("art") or "")
        return art if art in ABO_ARTEN else None


class LotusKontoBis(LotusKontoEntitaet):
    _attr_device_class = SensorDeviceClass.DATE

    def __init__(self, koordinator: LotusKoordinator) -> None:
        super().__init__(koordinator, "abo_bis")

    @property
    def native_value(self) -> date | None:
        wert = self.konto.get("bis")
        try:
            return date.fromisoformat(str(wert)) if wert else None
        except ValueError:
            return None
