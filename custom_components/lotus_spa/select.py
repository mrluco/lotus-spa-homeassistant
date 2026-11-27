from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import C8Z_BEFEHL, C8Z_WAHL, DOMAIN, PFLEGELAUF_AUS, SOLAR_MODI, WP_MODI
from .coordinator import LotusConfigEntry, LotusKoordinator
from .entity import LotusEntitaet, nachlegen, stand_ersetzen
from .schalter import c8z_aktiv, c8z_optionen, c8z_wahl, heizmodi, heizmodus_aktiv, heizmodus_text, heizmodus_wert, wp_modi, wp_modus

PARALLEL_UPDATES = 1


async def async_setup_entry(hass: HomeAssistant, eintrag: LotusConfigEntry, hinzufuegen: AddConfigEntryEntitiesCallback) -> None:
    nachlegen(eintrag, hinzufuegen, finden)


def finden(koordinator: LotusKoordinator) -> list[SelectEntity]:
    hass = koordinator.hass
    neu: list[SelectEntity] = []
    for g_, daten in (koordinator.data or {}).items():
        if (daten.get("heizmodus") or {}).get("darf"):
            stand_ersetzen(hass, "sensor", f"{g_}_heizmodus_stand")
            neu.append(LotusHeizmodus(koordinator, g_))
        if (daten.get("waermepumpe") or {}).get("darf") and wp_modi(daten, WP_MODI):
            stand_ersetzen(hass, "sensor", f"{g_}_waermepumpe_modus_stand")
            neu.append(LotusWaermepumpe(koordinator, g_))
        for was in C8Z_WAHL:
            if c8z_wahl(daten, was).get("darf") and c8z_optionen(daten, was, C8Z_WAHL[was]):
                stand_ersetzen(hass, "sensor", f"{g_}_c8z_{was}_stand")
                neu.append(LotusC8zWahl(koordinator, g_, was))
        if (daten.get("schwimmen") or {}).get("darf"):
            neu += [LotusSchwimmwahl(koordinator, g_, "programm"), LotusSchwimmwahl(koordinator, g_, "stufe"), LotusSchwimmwahl(koordinator, g_, "belastung")]
        if daten.get("pflegelauf"):
            neu.append(LotusPflegelauf(koordinator, g_))
            neu.append(LotusPflegelaufDauer(koordinator, g_))
        if (daten.get("solar") or {}).get("darf"):
            stand_ersetzen(hass, "sensor", f"{g_}_solar_betriebsart_stand")
            neu.append(LotusSolarBetriebsart(koordinator, g_))
        if isinstance(daten.get("absenkung"), dict):
            neu.append(LotusAbsenkungModus(koordinator, g_))
    return neu


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


class LotusWaermepumpe(LotusEntitaet, SelectEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "waermepumpe_modus"

    def __init__(self, koordinator: LotusKoordinator, geraet: str) -> None:
        super().__init__(koordinator, geraet, "waermepumpe_modus")

    @property
    def available(self) -> bool:
        return super().available and bool((self.daten.get("waermepumpe") or {}).get("darf")) and bool(self.options)

    @property
    def options(self) -> list[str]:
        return wp_modi(self.daten, WP_MODI)

    @property
    def current_option(self) -> str | None:
        modus = wp_modus(self.daten, WP_MODI)
        return modus if modus in self.options else None

    async def async_select_option(self, option: str) -> None:
        if option not in self.options:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="unbekannte_stufe", translation_placeholders={"stufe": option})
        if option != self.current_option:
            await self.befehl("waermepumpe_modus", wahl=option.upper())


class LotusC8zWahl(LotusEntitaet, SelectEntity):
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, koordinator: LotusKoordinator, geraet: str, was: str) -> None:
        super().__init__(koordinator, geraet, f"c8z_{was}")
        self.was = was
        self._attr_translation_key = f"c8z_{was}"

    @property
    def available(self) -> bool:
        return super().available and bool(c8z_wahl(self.daten, self.was).get("darf")) and bool(self.options)

    @property
    def options(self) -> list[str]:
        return c8z_optionen(self.daten, self.was, C8Z_WAHL[self.was])

    @property
    def current_option(self) -> str | None:
        return c8z_aktiv(self.daten, self.was, C8Z_WAHL[self.was])

    async def async_select_option(self, option: str) -> None:
        if option not in self.options:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="unbekannte_stufe", translation_placeholders={"stufe": option})
        if option != self.current_option:
            await self.befehl(C8Z_BEFEHL[self.was], wahl=option)


class LotusSchwimmwahl(LotusEntitaet, SelectEntity):
    LISTE = {"programm": "programme", "belastung": "belastungen"}

    def __init__(self, koordinator: LotusKoordinator, geraet: str, was: str) -> None:
        super().__init__(koordinator, geraet, f"schwimm{was}")
        self.was = was
        self._attr_translation_key = f"schwimm{was}"

    @property
    def _stand(self) -> dict:
        return self.daten.get("schwimmen") or {}

    @property
    def _paare(self) -> list[tuple[str, str]]:
        if self.was == "stufe":
            return [(str(int(n_)), str(int(n_))) for n_ in (self._stand.get("stufen") or [])]
        return [(str(m_.get("wert")), str(m_.get("text") or m_.get("wert"))) for m_ in (self._stand.get(self.LISTE[self.was]) or []) if isinstance(m_, dict)]

    @property
    def available(self) -> bool:
        return super().available and bool(self._stand.get("darf")) and bool(self._paare)

    @property
    def options(self) -> list[str]:
        return [text for _, text in self._paare]

    @property
    def current_option(self) -> str | None:
        aktiv = str(self._stand.get(self.was) if self._stand.get(self.was) is not None else "")
        return next((text for wert, text in self._paare if wert == aktiv), None)

    async def async_select_option(self, option: str) -> None:
        wert = next((wert for wert, text in self._paare if text == option), None)
        if wert is None:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="unbekannte_stufe", translation_placeholders={"stufe": option})
        if option != self.current_option:
            await self.befehl("schwimm_wahl", **{self.was: int(wert) if self.was == "stufe" else wert})


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

