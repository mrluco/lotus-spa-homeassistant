from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import LotusAboNoetig, LotusAnmeldungAbgelaufen, LotusApi, LotusFehler, LotusZuOft
from .const import ABFRAGE, ABFRAGE_OHNE_ABO, DOMAIN, HINWEIS_ABO

_LOGGER = logging.getLogger(__name__)

type LotusConfigEntry = ConfigEntry[LotusKoordinator]


class LotusKoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):

    config_entry: LotusConfigEntry

    def __init__(self, hass: HomeAssistant, eintrag: LotusConfigEntry, api: LotusApi) -> None:
        super().__init__(hass, _LOGGER, config_entry=eintrag, name=DOMAIN, update_interval=ABFRAGE)
        self.api = api
        self.abo_noetig = False

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

    def _abo_wieder_da(self) -> None:
        if self.abo_noetig:
            _LOGGER.info("Lotus Spa: Abo gilt wieder")
        self.abo_noetig = False
        self.update_interval = ABFRAGE
        ir.async_delete_issue(self.hass, DOMAIN, self._hinweis_id)
