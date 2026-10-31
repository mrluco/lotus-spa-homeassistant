from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import issue_registry as ir

from .api import LotusApi
from .const import DOMAIN, HERSTELLER, HINWEIS_ABLAUF, HINWEIS_ABO, HINWEIS_FUNKTIONEN, HINWEIS_ZAHLUNG, KONTO_URL, VERSION
from .coordinator import LotusConfigEntry, LotusKoordinator
from .oauth import lotus_oauth_anmelden

PLATTFORMEN: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CLIMATE,
    Platform.FAN,
    Platform.LIGHT,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.TIME,
]


async def async_setup_entry(hass: HomeAssistant, eintrag: LotusConfigEntry) -> bool:
    implementierungen = await config_entry_oauth2_flow.async_get_implementations(hass, DOMAIN)
    if DOMAIN not in implementierungen:
        lotus_oauth_anmelden(hass)
    umsetzung = await config_entry_oauth2_flow.async_get_config_entry_implementation(hass, eintrag)
    sitzung = config_entry_oauth2_flow.OAuth2Session(hass, eintrag, umsetzung)
    koordinator = LotusKoordinator(hass, eintrag, LotusApi(sitzung, VERSION))
    await koordinator.async_config_entry_first_refresh()
    eintrag.runtime_data = koordinator
    geraete = dr.async_get(hass)
    if koordinator.konto is not None:
        geraete.async_get_or_create(config_entry_id=eintrag.entry_id, identifiers={(DOMAIN, f"konto_{eintrag.entry_id}")}, name="Lotus Konto",
                                    manufacturer=HERSTELLER, model="Konto", entry_type=dr.DeviceEntryType.SERVICE, configuration_url=KONTO_URL)
    for daten in koordinator.data.values():
        box = daten.get("box") or {}
        if box.get("id"):
            koordinator.box_geraete[str(box["id"])] = geraete.async_get_or_create(
                config_entry_id=eintrag.entry_id, identifiers={(DOMAIN, f"box_{box['id']}")}, name="Lotus Box",
                manufacturer=HERSTELLER, model="Lotus Box", sw_version=box.get("firmware") or None).id
    await hass.config_entries.async_forward_entry_setups(eintrag, PLATTFORMEN)
    return True


async def async_unload_entry(hass: HomeAssistant, eintrag: LotusConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(eintrag, PLATTFORMEN)


async def async_remove_entry(hass: HomeAssistant, eintrag: LotusConfigEntry) -> None:
    for art in (HINWEIS_ABO, HINWEIS_ABLAUF, HINWEIS_ZAHLUNG, HINWEIS_FUNKTIONEN):
        ir.async_delete_issue(hass, DOMAIN, f"{art}_{eintrag.entry_id}")
