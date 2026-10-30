from __future__ import annotations

from typing import Any

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import LotusAboNoetig, LotusAnmeldungAbgelaufen, LotusFehler, LotusKeinRecht, LotusNichtGefunden, LotusZuOft
from .const import BASIS_URL, DOMAIN
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
            manufacturer="Lotus Spa",
            configuration_url=f"{BASIS_URL}/a/{anlage}/{spa}/",
        )

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
        except LotusZuOft as err:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="zu_oft") from err
        except LotusFehler as err:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="abgelehnt",
                                     translation_placeholders={"grund": err.text or "-"}) from err
        if antwort.get("ok") is False:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="abgelehnt",
                                     translation_placeholders={"grund": str(antwort.get("fehler") or "-")})
        await self.coordinator.async_request_refresh()
