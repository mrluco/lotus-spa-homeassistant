from __future__ import annotations

from typing import Any

from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import LotusAboNoetig, LotusAnmeldungAbgelaufen, LotusFehler, LotusFrost, LotusKeinRecht, LotusNichtGefunden, LotusPlanGrenze, LotusZuOft
from .const import BASIS_URL, DOMAIN, HERSTELLER, VERSION
from .coordinator import LotusKoordinator


class LotusEntitaet(CoordinatorEntity[LotusKoordinator]):

    _attr_has_entity_name = True

    def __init__(self, koordinator: LotusKoordinator, geraet: str, schluessel: str) -> None:
        super().__init__(koordinator)
        self.geraet = geraet
        self._attr_unique_id = f"{geraet}_{schluessel}"
        anlage, _, spa = geraet.partition("/")
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, geraet)},
            name=str(self.daten.get("name") or "Spa"),
            manufacturer=HERSTELLER,
            model=str(self.daten.get("modell") or "Spa"),
            via_device_id=koordinator.box_geraete.get(str((self.daten.get("box") or {}).get("id") or "")),
            configuration_url=f"{BASIS_URL}/a/{anlage}/{spa}/",
            sw_version=VERSION,
        )

    def zustand(self, titel: str) -> dict[str, Any]:
        return next((z_ for z_ in (self.daten.get("zustaende") or []) if isinstance(z_, dict) and z_.get("titel") == titel), {})

    def aufgabe(self, schluessel: str) -> dict[str, Any]:
        return next((a_ for a_ in ((self.daten.get("wartung") or {}).get("aufgaben") or []) if isinstance(a_, dict) and a_.get("schluessel") == schluessel), {})

    @property
    def daten(self) -> dict[str, Any]:
        return (self.coordinator.data or {}).get(self.geraet) or {}

    @property
    def available(self) -> bool:
        return super().available and bool(self.daten) and bool(self.daten.get("verbunden"))

    async def befehl(self, was: str, **werte: Any) -> None:
        try:
            antwort = await self.coordinator.api.befehl(self.geraet, was, **werte)
        except LotusAnmeldungAbgelaufen as err:
            self.coordinator.config_entry.async_start_reauth(self.hass)
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="anmeldung_abgelaufen") from err
        except LotusAboNoetig as err:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="abo_noetig") from err
        except LotusKeinRecht as err:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="kein_recht") from err
        except LotusNichtGefunden as err:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="nicht_gefunden") from err
        except LotusPlanGrenze as err:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="plan_grenze") from err
        except LotusZuOft as err:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="zu_oft_warten",
                                     translation_placeholders={"sekunden": str(max(1, round(err.warten_s)))}) from err
        except LotusFrost as err:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="abgelehnt",
                                         translation_placeholders={"grund": err.text or "-"}) from err
        except LotusFehler as err:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="abgelehnt",
                                     translation_placeholders={"grund": err.text or "-"}) from err
        if antwort.get("ok") is False:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="abgelehnt",
                                     translation_placeholders={"grund": str(antwort.get("fehler") or "-")})
        await self.coordinator.nach_befehl()


class LotusBoxEntitaet(LotusEntitaet):

    def __init__(self, koordinator: LotusKoordinator, geraet: str, schluessel: str) -> None:
        super().__init__(koordinator, geraet, f"box_{schluessel}")
        box = self.daten.get("box") or {}
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, f"box_{box.get('id')}")})

    @property
    def box(self) -> dict[str, Any]:
        return self.daten.get("box") or {}

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and bool(self.box)
