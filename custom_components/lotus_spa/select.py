from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN, PFLEGELAUF_AUS
from .coordinator import LotusConfigEntry, LotusKoordinator
from .entity import LotusEntitaet

PARALLEL_UPDATES = 1


async def async_setup_entry(hass: HomeAssistant, eintrag: LotusConfigEntry, hinzufuegen: AddConfigEntryEntitiesCallback) -> None:
    koordinator = eintrag.runtime_data
    neu: list[SelectEntity] = []
    for g_, daten in koordinator.data.items():
        if daten.get("heizmodus"):
            neu.append(LotusHeizmodus(koordinator, g_))
        if daten.get("pflegelauf"):
            neu.append(LotusPflegelauf(koordinator, g_))
    hinzufuegen(neu)


class LotusHeizmodus(LotusEntitaet, SelectEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "heizmodus"

    def __init__(self, koordinator: LotusKoordinator, geraet: str) -> None:
        super().__init__(koordinator, geraet, "heizmodus")

    @property
    def _modi(self) -> list[dict[str, str]]:
        return [m_ for m_ in ((self.daten.get("heizmodus") or {}).get("modi") or []) if isinstance(m_, dict)]

    @property
    def available(self) -> bool:
        return super().available and bool(self._modi)

    @property
    def options(self) -> list[str]:
        return [str(m_.get("text") or m_.get("wert")) for m_ in self._modi]

    @property
    def current_option(self) -> str | None:
        aktiv = str((self.daten.get("heizmodus") or {}).get("aktiv") or "")
        return next((str(m_.get("text") or m_.get("wert")) for m_ in self._modi if str(m_.get("wert")) == aktiv), None)

    async def async_select_option(self, option: str) -> None:
        wert = next((str(m_["wert"]) for m_ in self._modi if str(m_.get("text") or m_.get("wert")) == option), None)
        if wert is None:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="unbekannte_stufe", translation_placeholders={"stufe": option})
        await self.befehl("heizmodus", wahl=wert)


class LotusPflegelauf(LotusEntitaet, SelectEntity):
    _attr_translation_key = "pflegelauf"

    def __init__(self, koordinator: LotusKoordinator, geraet: str) -> None:
        super().__init__(koordinator, geraet, "pflegelauf")

    @property
    def _stand(self) -> dict:
        return self.daten.get("pflegelauf") or {}

    @property
    def available(self) -> bool:
        return super().available and bool(self._stand)

    @property
    def options(self) -> list[str]:
        return [PFLEGELAUF_AUS, *(str(z_["wert"]) for z_ in (self._stand.get("zwecke") or []) if isinstance(z_, dict) and z_.get("wert"))]

    @property
    def current_option(self) -> str | None:
        if not self._stand.get("laeuft"):
            return PFLEGELAUF_AUS
        zweck = str(self._stand.get("zweck") or "")
        return zweck if zweck in self.options else None

    @property
    def extra_state_attributes(self) -> dict[str, int]:
        return {"restminuten": int(self._stand.get("rest_min") or 0)} if self._stand.get("laeuft") else {}

    async def async_select_option(self, option: str) -> None:
        if option == PFLEGELAUF_AUS:
            if self._stand.get("laeuft"):
                await self.befehl("pflegelauf", beenden=True)
            return
        if option not in self.options:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="unbekannte_stufe", translation_placeholders={"stufe": option})
        await self.befehl("pflegelauf", zweck=option)
