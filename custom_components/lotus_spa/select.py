from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN, PFLEGELAUF_AUS, SOLAR_MODI
from .coordinator import LotusConfigEntry, LotusKoordinator
from .entity import LotusEntitaet
from .schalter import heizmodi, heizmodus_aktiv, heizmodus_text, heizmodus_wert

PARALLEL_UPDATES = 1


async def async_setup_entry(hass: HomeAssistant, eintrag: LotusConfigEntry, hinzufuegen: AddConfigEntryEntitiesCallback) -> None:
    koordinator = eintrag.runtime_data
    neu: list[SelectEntity] = []
    for g_, daten in koordinator.data.items():
        if (daten.get("heizmodus") or {}).get("darf"):
            neu.append(LotusHeizmodus(koordinator, g_))
        if daten.get("pflegelauf"):
            neu.append(LotusPflegelauf(koordinator, g_))
            neu.append(LotusPflegelaufDauer(koordinator, g_))
        if (daten.get("solar") or {}).get("darf"):
            neu.append(LotusSolarBetriebsart(koordinator, g_))
        if isinstance(daten.get("absenkung"), dict):
            neu.append(LotusAbsenkungModus(koordinator, g_))
    hinzufuegen(neu)


class LotusHeizmodus(LotusEntitaet, SelectEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "heizmodus"

    def __init__(self, koordinator: LotusKoordinator, geraet: str) -> None:
        super().__init__(koordinator, geraet, "heizmodus")

    @property
    def available(self) -> bool:
        return super().available and bool(heizmodi(self.daten))

    @property
    def options(self) -> list[str]:
        return [heizmodus_text(m_) for m_ in heizmodi(self.daten)]

    @property
    def current_option(self) -> str | None:
        return heizmodus_aktiv(self.daten)

    async def async_select_option(self, option: str) -> None:
        wert = heizmodus_wert(self.daten, option)
        if wert is None:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="unbekannte_stufe", translation_placeholders={"stufe": option})
        await self.befehl("heizmodus", wahl=wert)


class LotusPflegelauf(LotusEntitaet, SelectEntity):
    _attr_entity_category = EntityCategory.CONFIG
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


class LotusSolarBetriebsart(LotusEntitaet, SelectEntity):
    _attr_translation_key = "solar_betriebsart"

    def __init__(self, koordinator: LotusKoordinator, geraet: str) -> None:
        super().__init__(koordinator, geraet, "solar_betriebsart")

    @property
    def _stand(self) -> dict:
        return self.daten.get("solar") or {}

    @property
    def available(self) -> bool:
        return super().available and bool(self._stand.get("darf"))

    @property
    def options(self) -> list[str]:
        return [str(m_["wert"]) for m_ in (self._stand.get("modi") or []) if isinstance(m_, dict) and m_.get("wert") in SOLAR_MODI]

    @property
    def current_option(self) -> str | None:
        modus = str(self._stand.get("modus") or "")
        return modus if modus in self.options else None

    async def async_select_option(self, option: str) -> None:
        if option not in self.options:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="unbekannte_stufe", translation_placeholders={"stufe": option})
        if option != self.current_option:
            await self.befehl("solar_modus", modus=option)


class LotusPflegelaufDauer(LotusEntitaet, SelectEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "pflegelauf_dauer"

    def __init__(self, koordinator: LotusKoordinator, geraet: str) -> None:
        super().__init__(koordinator, geraet, "pflegelauf_dauer")

    @property
    def _stand(self) -> dict:
        return self.daten.get("pflegelauf") or {}

    @property
    def available(self) -> bool:
        return super().available and bool(self._stand.get("dauern"))

    @property
    def options(self) -> list[str]:
        return [str(int(m_)) for m_ in (self._stand.get("dauern") or [])]

    @property
    def current_option(self) -> str | None:
        dauer = str(self._stand.get("dauer") or "")
        return dauer if dauer in self.options else None

    async def async_select_option(self, option: str) -> None:
        if option not in self.options:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="unbekannte_stufe", translation_placeholders={"stufe": option})
        if option != self.current_option:
            await self.befehl("pflegelauf_dauer", minuten=int(option))


class LotusAbsenkungModus(LotusEntitaet, SelectEntity):
    _attr_translation_key = "absenkung"
    _attr_options = ["aus", "an", "auto"]

    def __init__(self, koordinator: LotusKoordinator, geraet: str) -> None:
        super().__init__(koordinator, geraet, "absenkung_modus")

    @property
    def available(self) -> bool:
        return super().available and str((self.daten.get("absenkung") or {}).get("modus") or "") in self._attr_options

    @property
    def current_option(self) -> str | None:
        modus = str((self.daten.get("absenkung") or {}).get("modus") or "")
        return modus if modus in self._attr_options else None

    async def async_select_option(self, option: str) -> None:
        if option not in self._attr_options:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="unbekannte_stufe", translation_placeholders={"stufe": option})
        await self.befehl("absenkung", wahl=option)

