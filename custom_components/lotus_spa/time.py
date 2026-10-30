from __future__ import annotations

from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import TAGE_GRUPPEN
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
        for nr_, b_ in enumerate(fz.get("bloecke") or []):
            neu += [LotusFilterzeit(koordinator, g_, str(b_["id"]), nr_, feld) for feld in ("von", "bis")]
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


class LotusFilterzeit(LotusEntitaet, TimeEntity):
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, koordinator: LotusKoordinator, geraet: str, kennung: str, nr: int, feld: str) -> None:
        super().__init__(koordinator, geraet, f"filterzeit_{kennung.replace(':', '_')}_{feld}")
        self.kennung = kennung
        self.feld = feld
        self._attr_translation_key = f"filterzeit_{feld}"
        self._attr_translation_placeholders = {"nr": str(nr + 1)}

    @property
    def _block(self) -> dict:
        fz = self.daten.get("filterzeiten") or {}
        return next((b_ for b_ in (fz.get("bloecke") or []) if b_.get("id") == self.kennung), {}) if fz.get("darf") else {}

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
        await self.befehl("filterzeit", id=self.kennung, **{self.feld: text})
