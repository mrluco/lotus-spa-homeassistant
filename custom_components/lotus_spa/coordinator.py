from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import LotusAboNoetig, LotusAnmeldungAbgelaufen, LotusApi, LotusFehler, LotusZuOft
from .const import (
    ABFRAGE,
    ABFRAGE_OHNE_ABO,
    ABO_FUNKTIONEN,
    ABO_URL,
    DOMAIN,
    HINWEIS_ABLAUF,
    HINWEIS_ABO,
    HINWEIS_FUNKTIONEN,
    HINWEIS_ZAHLUNG,
    KONTO_URL,
    NACHLESEN_S,
)

_LOGGER = logging.getLogger(__name__)

type LotusConfigEntry = ConfigEntry[LotusKoordinator]


class LotusKoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):

    config_entry: LotusConfigEntry

    def __init__(self, hass: HomeAssistant, eintrag: LotusConfigEntry, api: LotusApi) -> None:
        super().__init__(hass, _LOGGER, config_entry=eintrag, name=DOMAIN, update_interval=ABFRAGE)
        self.api = api
        self.abo_noetig = False
        self.konto: dict[str, Any] | None = None
        self._nachlesen_lauf: asyncio.Task[None] | None = None

    async def nach_befehl(self) -> None:
        await self.async_request_refresh()
        if self._nachlesen_lauf is not None and not self._nachlesen_lauf.done():
            self._nachlesen_lauf.cancel()
        self._nachlesen_lauf = self.config_entry.async_create_background_task(self.hass, self._nachlesen(), f"{DOMAIN}_nachlesen")

    async def _nachlesen(self) -> None:
        for warten in NACHLESEN_S:
            await asyncio.sleep(warten)
            await self.async_refresh()

    @property
    def _hinweis_id(self) -> str:
        return f"{HINWEIS_ABO}_{self.config_entry.entry_id}"

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        try:
            stand = await self.api.stand()
        except LotusAnmeldungAbgelaufen as err:
            raise ConfigEntryAuthFailed(translation_domain=DOMAIN, translation_key="anmeldung_abgelaufen") from err
        except LotusAboNoetig as err:
            self._abo_fehlt(err)
            raise UpdateFailed(translation_domain=DOMAIN, translation_key="abo_noetig") from err
        except LotusZuOft as err:
            raise UpdateFailed(translation_domain=DOMAIN, translation_key="zu_oft", retry_after=err.warten_s) from err
        except LotusFehler as err:
            raise UpdateFailed(translation_domain=DOMAIN, translation_key="nicht_erreichbar") from err
        self._abo_wieder_da()
        self.konto = stand.get("konto") if isinstance(stand.get("konto"), dict) else None
        self._konto_hinweise()
        geraete = stand.get("geraete")
        return {str(k): v for k, v in geraete.items() if isinstance(v, dict)} if isinstance(geraete, dict) else {}

    def _abo_fehlt(self, err: LotusAboNoetig) -> None:
        if not self.abo_noetig:
            _LOGGER.info("Lotus Spa: ohne gültiges Abo keine Werte und keine Befehle")
        self.abo_noetig = True
        self.update_interval = ABFRAGE_OHNE_ABO
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            self._hinweis_id,
            is_fixable=False,
            is_persistent=False,
            severity=ir.IssueSeverity.ERROR,
            learn_more_url=err.abo_url,
            translation_key=HINWEIS_ABO if err.zugang == "abo_noetig" else "kein_recht",
        )
        namen = ABO_FUNKTIONEN.get(self.hass.config.language[:2], ABO_FUNKTIONEN["de"])
        fehlt = [namen[x_] for x_ in err.fehlt if x_ in namen] if err.zugang == "abo_noetig" else []
        if fehlt:
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                f"{HINWEIS_FUNKTIONEN}_{self.config_entry.entry_id}",
                is_fixable=False,
                is_persistent=False,
                severity=ir.IssueSeverity.WARNING,
                learn_more_url=KONTO_URL,
                translation_key=HINWEIS_FUNKTIONEN,
                translation_placeholders={"funktionen": ", ".join(fehlt)},
            )
        else:
            ir.async_delete_issue(self.hass, DOMAIN, f"{HINWEIS_FUNKTIONEN}_{self.config_entry.entry_id}")

    def _abo_wieder_da(self) -> None:
        if self.abo_noetig:
            _LOGGER.info("Lotus Spa: Abo gilt wieder")
        self.abo_noetig = False
        self.update_interval = ABFRAGE
        ir.async_delete_issue(self.hass, DOMAIN, self._hinweis_id)
        ir.async_delete_issue(self.hass, DOMAIN, f"{HINWEIS_FUNKTIONEN}_{self.config_entry.entry_id}")

    def _konto_hinweise(self) -> None:
        hinweis = (self.konto or {}).get("hinweis")
        for art in (HINWEIS_ABLAUF, HINWEIS_ZAHLUNG):
            kennung = f"{art}_{self.config_entry.entry_id}"
            if hinweis == art:
                ir.async_create_issue(
                    self.hass,
                    DOMAIN,
                    kennung,
                    is_fixable=False,
                    is_persistent=False,
                    severity=ir.IssueSeverity.WARNING,
                    learn_more_url=ABO_URL,
                    translation_key=art,
                    translation_placeholders={"bis": str((self.konto or {}).get("bis") or "-")},
                )
            else:
                ir.async_delete_issue(self.hass, DOMAIN, kennung)
