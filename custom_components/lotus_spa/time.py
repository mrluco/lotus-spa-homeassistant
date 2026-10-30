from __future__ import annotations

import re
from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN, TAGE_GRUPPEN
from .coordinator import LotusConfigEntry, LotusKoordinator
from .entity import LotusEntitaet

PARALLEL_UPDATES = 1
MITTERNACHT = "24:00"


async def async_setup_entry(hass: HomeAssistant, eintrag: LotusConfigEntry, hinzufuegen: AddConfigEntryEntitiesCallback) -> None:
    koordinator = eintrag.runtime_data
    sprache = "de" if str(hass.config.language or "").startswith("de") else "en"
    neu: list[TimeEntity] = []
    for g_, daten in koordinator.data.items():
        fz = daten.get("filterzeiten") or {}
        bloecke = [b_ for b_ in (fz.get("bloecke") or []) if isinstance(b_, dict)]
        kennungen_uebernehmen(er.async_get(hass), eintrag.entry_id, g_, [str(b_.get("id") or "") for b_ in bloecke])
        for nr_ in range(len(bloecke)):
            neu += [LotusFilterzeit(koordinator, g_, nr_, feld) for feld in ("von", "bis")]
        bz = daten.get("badezeiten") or {}
        if not bz.get("darf"):
            continue
        for gr_ in bz.get("gruppen") or []:
            for nr_ in range(len(gr_.get("bloecke") or [])):
                neu += [LotusBadezeit(koordinator, g_, int(gr_["nr"]), str(gr_["name"]), nr_, feld, sprache) for feld in ("von", "bis")]
    hinzufuegen(neu)


class LotusBadezeit(LotusEntitaet, TimeEntity):
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, koordinator: LotusKoordinator, geraet: str, gruppe: int, name: str, nr: int, feld: str, sprache: str) -> None:
        super().__init__(koordinator, geraet, f"badezeit_{name}_{nr + 1}_{feld}")
        self.gruppe = gruppe
        self.name_gruppe = name
        self.nr = nr
        self.feld = feld
        self._attr_translation_key = f"badezeit_{feld}"
        self._attr_translation_placeholders = {"tage": TAGE_GRUPPEN[sprache].get(name, name), "nr": str(nr + 1)}

    @property
    def _block(self) -> dict:
        bz = self.daten.get("badezeiten") or {}
        gr_ = next((x_ for x_ in (bz.get("gruppen") or []) if x_.get("nr") == self.gruppe and x_.get("name") == self.name_gruppe), {})
        bloecke = gr_.get("bloecke") or []
        return bloecke[self.nr] if bz.get("darf") and self.nr < len(bloecke) else {}

    @property
    def available(self) -> bool:
        return super().available and bool(self._block)

    @property
    def native_value(self) -> time | None:
        wert = str(self._block.get(self.feld) or "")
        if wert == MITTERNACHT:
            return time(0, 0)
        try:
            return time(int(wert[:2]), int(wert[3:5]))
        except ValueError:
            return None

    async def async_set_value(self, value: time) -> None:
        text = f"{value.hour:02d}:{value.minute:02d}"
        if self.feld == "bis" and text == "00:00":
            text = MITTERNACHT
        await self.befehl("badezeit", gruppe=self.gruppe, nr=self.nr, **{self.feld: text})


def kennungen_uebernehmen(register: er.EntityRegistry, eintrag_id: str, geraet: str, kennungen: list[str]) -> None:
    neu_muster = re.compile(rf"^{re.escape(geraet)}_filterzeit_\d+_(von|bis)$")
    alt_muster = re.compile(rf"^{re.escape(geraet)}_filterzeit_(.+)_(von|bis)$")
    alte = sorted((e_ for e_ in er.async_entries_for_config_entry(register, eintrag_id)
                   if e_.domain == "time" and alt_muster.match(e_.unique_id) and not neu_muster.match(e_.unique_id)), key=lambda e_: e_.unique_id)
    for feld in ("von", "bis"):
        frei = [nr_ for nr_ in range(len(kennungen)) if not register.async_get_entity_id("time", DOMAIN, f"{geraet}_filterzeit_{nr_}_{feld}")]
        for e_ in [x_ for x_ in alte if x_.unique_id.endswith(f"_{feld}")]:
            kennung = alt_muster.match(e_.unique_id).group(1)
            nr = next((n_ for n_ in frei if kennungen[n_].replace(":", "_") == kennung), frei[0] if frei else None)
            if nr is None:
                continue
            frei.remove(nr)
            register.async_update_entity(e_.entity_id, new_unique_id=f"{geraet}_filterzeit_{nr}_{feld}")


class LotusFilterzeit(LotusEntitaet, TimeEntity):
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, koordinator: LotusKoordinator, geraet: str, nr: int, feld: str) -> None:
        super().__init__(koordinator, geraet, f"filterzeit_{nr}_{feld}")
        self.nr = nr
        self.feld = feld
        self._attr_translation_key = f"filterzeit_{feld}"
        self._attr_translation_placeholders = {"nr": str(nr + 1)}

    @property
    def _block(self) -> dict:
        bloecke = (self.daten.get("filterzeiten") or {}).get("bloecke") or []
        return bloecke[self.nr] if self.nr < len(bloecke) and isinstance(bloecke[self.nr], dict) else {}

    @property
    def available(self) -> bool:
        return super().available and bool(self._block)

    @property
    def native_value(self) -> time | None:
        wert = str(self._block.get(self.feld) or "")
        if wert == MITTERNACHT:
            return time(0, 0)
        try:
            return time(int(wert[:2]), int(wert[3:5]))
        except ValueError:
            return None

    async def async_set_value(self, value: time) -> None:
        text = f"{value.hour:02d}:{value.minute:02d}"
        if self.feld == "bis" and text == "00:00":
            text = MITTERNACHT
        fz = self.daten.get("filterzeiten") or {}
        if not fz.get("darf"):
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="abgelehnt",
                                         translation_placeholders={"grund": str(fz.get("grund") or "-")})
        await self.befehl("filterzeit", id=str(self._block.get("id") or ""), **{self.feld: text})
