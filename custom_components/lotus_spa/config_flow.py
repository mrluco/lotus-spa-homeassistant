from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from aiohttp import ClientError
from homeassistant.config_entries import SOURCE_REAUTH, ConfigFlowResult
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import LotusAboNoetig, LotusFehler, auswerten
from .const import API_URL, DOMAIN
from .oauth import lotus_oauth_anmelden

_LOGGER = logging.getLogger(__name__)


class LotusFlow(config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN):

    DOMAIN = DOMAIN

    @property
    def logger(self) -> logging.Logger:
        return _LOGGER

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        lotus_oauth_anmelden(self.hass)
        return await super().async_step_user(user_input)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is None:
            return self.async_show_form(step_id="reauth_confirm")
        lotus_oauth_anmelden(self.hass)
        return await self.async_step_pick_implementation({"implementation": DOMAIN})

    async def async_oauth_create_entry(self, data: dict[str, Any]) -> ConfigFlowResult:
        sitzung = async_get_clientsession(self.hass)
        try:
            antwort = await sitzung.get(f"{API_URL}/konto", headers={"Authorization": f"Bearer {data['token']['access_token']}"})
            konto = await auswerten(antwort)
        except LotusAboNoetig:
            return self.async_abort(reason="abo_noetig")
        except LotusFehler:
            return self.async_abort(reason="nicht_erreichbar")
        except (ClientError, TimeoutError):
            return self.async_abort(reason="nicht_erreichbar")
        kennung = str(konto.get("konto") or "")
        if not kennung:
            return self.async_abort(reason="nicht_erreichbar")
        await self.async_set_unique_id(kennung)
        if self.source == SOURCE_REAUTH:
            self._abort_if_unique_id_mismatch(reason="anderes_konto")
            return self.async_update_reload_and_abort(self._get_reauth_entry(), data_updates=data)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title="Lotus Spa", data=data)
