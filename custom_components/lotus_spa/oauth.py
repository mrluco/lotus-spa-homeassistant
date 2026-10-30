from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.config_entry_oauth2_flow import (
    MY_AUTH_CALLBACK_PATH,
    LocalOAuth2ImplementationWithPkce,
    async_register_implementation,
)

from .const import AUTORISIEREN_URL, CLIENT_ID, DOMAIN, TOKEN_URL


class LotusOAuth(LocalOAuth2ImplementationWithPkce):

    @property
    def name(self) -> str:
        return "Lotus Spa"

    @property
    def redirect_uri(self) -> str:
        return MY_AUTH_CALLBACK_PATH


def lotus_oauth_anmelden(hass: HomeAssistant) -> LotusOAuth:
    umsetzung = LotusOAuth(hass, DOMAIN, CLIENT_ID, AUTORISIEREN_URL, TOKEN_URL)
    async_register_implementation(hass, DOMAIN, umsetzung)
    return umsetzung
