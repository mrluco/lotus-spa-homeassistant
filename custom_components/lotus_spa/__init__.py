from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers import issue_registry as ir

from .api import LotusApi
from .const import DOMAIN, HINWEIS_ABO
from .coordinator import LotusConfigEntry, LotusKoordinator
from .oauth import lotus_oauth_anmelden

PLATTFORMEN: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.FAN,
    Platform.LIGHT,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, eintrag: LotusConfigEntry) -> bool:
    implementierungen = await config_entry_oauth2_flow.async_get_implementations(hass, DOMAIN)
    if DOMAIN not in implementierungen:
        lotus_oauth_anmelden(hass)
    umsetzung = await config_entry_oauth2_flow.async_get_config_entry_implementation(hass, eintrag)
    sitzung = config_entry_oauth2_flow.OAuth2Session(hass, eintrag, umsetzung)
    koordinator = LotusKoordinator(hass, eintrag, LotusApi(sitzung))
    await koordinator.async_config_entry_first_refresh()
    eintrag.runtime_data = koordinator
    await hass.config_entries.async_forward_entry_setups(eintrag, PLATTFORMEN)
    return True


async def async_unload_entry(hass: HomeAssistant, eintrag: LotusConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(eintrag, PLATTFORMEN)


async def async_remove_entry(hass: HomeAssistant, eintrag: LotusConfigEntry) -> None:
    ir.async_delete_issue(hass, DOMAIN, f"{HINWEIS_ABO}_{eintrag.entry_id}")
