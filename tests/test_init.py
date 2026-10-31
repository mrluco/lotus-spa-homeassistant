from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker
from yarl import URL

from custom_components.lotus_spa.const import API_URL, DOMAIN, HINWEIS_ABO
from custom_components.lotus_spa.diagnostics import async_get_config_entry_diagnostics

from .conftest import GERAET, mit_plan, ohne_recht, stand_beispiel

GRUND = {
    "climate.mein_spa", "select.mein_spa_pflegelauf", "binary_sensor.mein_spa_filterung", "binary_sensor.mein_spa_verbindung",
    "switch.mein_spa_badeerkennung_pumpe_1", "switch.mein_spa_badeerkennung_pumpe_2", "binary_sensor.mein_spa_heizung",
    "binary_sensor.mein_spa_meldung", "binary_sensor.mein_spa_umwalzpumpe", "binary_sensor.mein_spa_ozon", "binary_sensor.mein_spa_abdeckung",
    "sensor.mein_spa_wassertemperatur", "sensor.mein_spa_solltemperatur", "sensor.mein_spa_meldungstext", "sensor.mein_spa_solarenergie",
    "sensor.mein_spa_grund_der_solltemperatur", "sensor.mein_spa_filterblock", "select.mein_spa_pflegelauf_dauer", "sensor.mein_spa_pflegelauf_endet",
    "sensor.mein_spa_aussentemperatur",
}
STAND = f"{API_URL}/stand"
BEFEHL = f"{API_URL}/befehl"


async def _einrichten(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker, stand: dict | None = None) -> None:
    aioclient_mock.get(STAND, json=stand or stand_beispiel())
    aioclient_mock.post(BEFEHL, json={"ok": True})
    assert await hass.config_entries.async_setup(eintrag.entry_id)
    await hass.async_block_till_done()


def _befehle(aioclient_mock: AiohttpClientMocker) -> list[dict]:
    return [c_[2] for c_ in aioclient_mock.mock_calls if c_[0] == "POST" and str(c_[1]) == BEFEHL]


async def _naechster_abruf(hass: HomeAssistant, minuten: int = 2) -> None:
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=minuten))
    await hass.async_block_till_done()


async def test_entitaeten(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    await _einrichten(hass, eintrag, aioclient_mock)
    assert eintrag.state is ConfigEntryState.LOADED
    klima = hass.states.get("climate.mein_spa")
    assert klima.state == "heat" and klima.attributes["current_temperature"] == 37.5 and klima.attributes["temperature"] == 38.0
    assert klima.attributes["hvac_action"] == "heating" and klima.attributes["min_temp"] == 10.0 and klima.attributes["max_temp"] == 40.0
    assert hass.states.get("fan.mein_spa_pumpe_1").state == STATE_OFF
    assert hass.states.get("fan.mein_spa_pumpe_1").attributes["preset_modes"] == ["Stufe 1", "Stufe 2"]
    assert hass.states.get("switch.mein_spa_pumpe_2").state == STATE_ON
    assert hass.states.get("light.mein_spa_licht").state == STATE_OFF
    assert hass.states.get("select.mein_spa_heizmodus").state == "Standard"
    assert hass.states.get("select.mein_spa_pflegelauf").state == "aus"
    assert hass.states.get("binary_sensor.mein_spa_filterung").state == STATE_ON
    assert hass.states.get("binary_sensor.mein_spa_verbindung").state == STATE_ON
    assert hass.states.get("switch.mein_spa_badeerkennung_pumpe_1").state == STATE_ON
    assert hass.states.get("switch.mein_spa_badeerkennung_pumpe_2").state == STATE_OFF
    alle = {s_.entity_id for s_ in hass.states.async_all()}
    assert alle == GRUND | {"fan.mein_spa_pumpe_1", "switch.mein_spa_pumpe_2", "light.mein_spa_licht", "select.mein_spa_heizmodus"}
    assert _befehle(aioclient_mock) == [] and all(c_[0] == "GET" for c_ in aioclient_mock.mock_calls)


async def test_befehle(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    await _einrichten(hass, eintrag, aioclient_mock)
    await hass.services.async_call("climate", "set_temperature", {"entity_id": "climate.mein_spa", "temperature": 37.3}, blocking=True)
    await hass.services.async_call("fan", "set_preset_mode", {"entity_id": "fan.mein_spa_pumpe_1", "preset_mode": "Stufe 2"}, blocking=True)
    await hass.services.async_call("fan", "turn_on", {"entity_id": "fan.mein_spa_pumpe_1"}, blocking=True)
    await hass.services.async_call("switch", "turn_off", {"entity_id": "switch.mein_spa_pumpe_2"}, blocking=True)
    await hass.services.async_call("light", "turn_on", {"entity_id": "light.mein_spa_licht"}, blocking=True)
    await hass.services.async_call("select", "select_option", {"entity_id": "select.mein_spa_heizmodus", "option": "Energiesparen"}, blocking=True)
    await hass.services.async_call("select", "select_option", {"entity_id": "select.mein_spa_pflegelauf", "option": "chlor"}, blocking=True)
    await hass.services.async_call("switch", "turn_on", {"entity_id": "switch.mein_spa_badeerkennung_pumpe_2"}, blocking=True)
    await hass.services.async_call("switch", "turn_off", {"entity_id": "switch.mein_spa_badeerkennung_pumpe_1"}, blocking=True)
    assert _befehle(aioclient_mock) == [
        {"geraet": GERAET, "was": "soll", "wert": 37.5},
        {"geraet": GERAET, "was": "schalten", "titel": "Pumpe 1", "modus": "HI"},
        {"geraet": GERAET, "was": "schalten", "titel": "Pumpe 1", "modus": "LO"},
        {"geraet": GERAET, "was": "schalten", "titel": "Pumpe 2", "modus": "OFF"},
        {"geraet": GERAET, "was": "schalten", "titel": "Licht", "modus": "ON"},
        {"geraet": GERAET, "was": "heizmodus", "wahl": "sparen"},
        {"geraet": GERAET, "was": "pflegelauf", "zweck": "chlor"},
        {"geraet": GERAET, "was": "badeerkennung", "geraete": ["Pumpe 1", "Pumpe 2"]},
        {"geraet": GERAET, "was": "badeerkennung", "geraete": []},
    ]


async def test_pflegelauf_beenden(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    stand = stand_beispiel(pflegelauf={"laeuft": True, "zweck": "ph_plus", "rest_min": 12, "zwecke": [{"wert": "ph_plus", "text": "pH plus"}]})
    await _einrichten(hass, eintrag, aioclient_mock, stand)
    zustand = hass.states.get("select.mein_spa_pflegelauf")
    assert zustand.state == "ph_plus" and zustand.attributes["restminuten"] == 12
    await hass.services.async_call("select", "select_option", {"entity_id": "select.mein_spa_pflegelauf", "option": "aus"}, blocking=True)
    assert _befehle(aioclient_mock) == [{"geraet": GERAET, "was": "pflegelauf", "beenden": True}]


async def test_ohne_recht_temperatur_nur_anzeigen(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    await _einrichten(hass, eintrag, aioclient_mock, stand_beispiel(darf_temperatur=False, heizmodus=None))
    assert hass.states.get("climate.mein_spa").attributes["supported_features"] == 0
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call("climate", "set_temperature", {"entity_id": "climate.mein_spa", "temperature": 36}, blocking=True)
    assert _befehle(aioclient_mock) == []


async def test_ohne_schaltrecht_keine_schalter(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    await _einrichten(hass, eintrag, aioclient_mock, stand_beispiel(schalter=[], heizmodus=None, pflegelauf=None, badeerkennung=None))
    alle = {s_.entity_id for s_ in hass.states.async_all()}
    assert "climate.mein_spa" in alle and "binary_sensor.mein_spa_verbindung" in alle and "sensor.mein_spa_wassertemperatur" in alle
    assert not any(e_.split(".")[0] in ("fan", "switch", "light", "select") for e_ in alle), alle


async def test_lesewerte(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    await _einrichten(hass, eintrag, aioclient_mock)
    wasser = hass.states.get("sensor.mein_spa_wassertemperatur")
    assert wasser.state == "37.5" and wasser.attributes["state_class"] == "measurement" and wasser.attributes["unit_of_measurement"] == "°C"
    assert hass.states.get("sensor.mein_spa_solltemperatur").state == "38.0"
    assert hass.states.get("binary_sensor.mein_spa_heizung").state == STATE_ON
    assert hass.states.get("binary_sensor.mein_spa_umwalzpumpe").state == STATE_ON
    assert hass.states.get("binary_sensor.mein_spa_ozon").state == STATE_OFF
    assert hass.states.get("binary_sensor.mein_spa_abdeckung").attributes["text"] == "zu"
    assert hass.states.get("sensor.mein_spa_solarenergie").state == "gehalten auf 38,0 · ab 15:00 mit Sonne"
    assert hass.states.get("binary_sensor.mein_spa_filterung").attributes["text"] == "läuft bis 11:00"
    assert hass.states.get("binary_sensor.mein_spa_meldung").state == STATE_OFF
    assert hass.states.get("sensor.mein_spa_meldungstext").state == "Keine Meldung"


async def test_meldung_mit_kundentext(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    await _einrichten(hass, eintrag, aioclient_mock, stand_beispiel(meldungen=["Bitte den Filter reinigen."]))
    meldung = hass.states.get("binary_sensor.mein_spa_meldung")
    assert meldung.state == STATE_ON and meldung.attributes["meldungen"] == ["Bitte den Filter reinigen."]
    assert hass.states.get("sensor.mein_spa_meldungstext").state == "Bitte den Filter reinigen."


async def test_ohne_schaltrecht_nur_anzeige(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    await _einrichten(hass, eintrag, aioclient_mock, ohne_recht(stand_beispiel()))
    alle = {s_.entity_id for s_ in hass.states.async_all()}
    assert alle == GRUND | {
        "binary_sensor.mein_spa_pumpe_1", "binary_sensor.mein_spa_pumpe_2", "binary_sensor.mein_spa_licht", "sensor.mein_spa_heizmodus",
    }
    assert not any(e_.split(".")[0] in ("fan", "light") for e_ in alle)
    assert not any(e_.startswith("switch.") and "badeerkennung" not in e_ for e_ in alle)
    assert hass.states.get("binary_sensor.mein_spa_pumpe_2").state == STATE_ON
    assert hass.states.get("binary_sensor.mein_spa_pumpe_1").state == STATE_OFF
    assert hass.states.get("sensor.mein_spa_heizmodus").state == "Standard"
    assert hass.states.get("climate.mein_spa").attributes["supported_features"] == 0
    for dienst, daten in (("fan", {"entity_id": "fan.mein_spa_pumpe_1"}), ("light", {"entity_id": "light.mein_spa_licht"}),
                          ("switch", {"entity_id": "switch.mein_spa_pumpe_2"})):
        await hass.services.async_call(dienst, "turn_on", daten, blocking=True)
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call("climate", "set_temperature", {"entity_id": "climate.mein_spa", "temperature": 36}, blocking=True)
    assert _befehle(aioclient_mock) == []


async def test_stufe_ohne_recht(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    stand = ohne_recht(stand_beispiel())
    stand["geraete"][GERAET]["schalter"][0]["aktiv"] = "HI"
    await _einrichten(hass, eintrag, aioclient_mock, stand)
    pumpe = hass.states.get("binary_sensor.mein_spa_pumpe_1")
    assert pumpe.state == STATE_ON and pumpe.attributes["stufe"] == "Stufe 2"


async def test_keine_elektrik(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    stand = stand_beispiel()
    stand["geraete"][GERAET]["zustaende"] += [{"titel": "Leistung", "name": "Leistung", "text": "3,2 kW", "an": True},
                                               {"titel": "Nennstrom", "name": "Nennstrom", "text": "16 A", "an": True}]
    await _einrichten(hass, eintrag, aioclient_mock, stand)
    alle = {s_.entity_id for s_ in hass.states.async_all()}
    assert alle == GRUND | {"fan.mein_spa_pumpe_1", "switch.mein_spa_pumpe_2", "light.mein_spa_licht", "select.mein_spa_heizmodus"}


async def test_geraeteinfo(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    from homeassistant.helpers import device_registry as dr

    from custom_components.lotus_spa.const import VERSION

    await _einrichten(hass, eintrag, aioclient_mock)
    geraet = dr.async_get(hass).async_get_device_by_identifier((DOMAIN, GERAET), eintrag.entry_id)
    assert geraet.name == "Mein Spa" and geraet.manufacturer == "Lotus" and geraet.model == "Whirlpool" and geraet.sw_version == VERSION and VERSION == "0.3.2"
    assert geraet.configuration_url == "https://app.lotusswimspa.de/a/musterspa/spa1/"


async def test_badeerkennung_name(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    await _einrichten(hass, eintrag, aioclient_mock)
    assert hass.states.get("switch.mein_spa_badeerkennung_pumpe_1").attributes["friendly_name"] == "Mein Spa Badeerkennung Pumpe 1"
    assert hass.states.get("binary_sensor.mein_spa_verbindung").attributes["friendly_name"] == "Mein Spa Verbindung"


async def test_befehl_ohne_recht(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(STAND, json=stand_beispiel())
    aioclient_mock.post(BEFEHL, status=409, json={"ok": False, "fehler": "Dafür fehlt dir die Berechtigung."})
    assert await hass.config_entries.async_setup(eintrag.entry_id)
    await hass.async_block_till_done()
    with pytest.raises(HomeAssistantError) as fehler:
        await hass.services.async_call("light", "turn_on", {"entity_id": "light.mein_spa_licht"}, blocking=True)
    assert fehler.value.translation_key == "kein_recht"
    assert hass.states.get("light.mein_spa_licht").state == STATE_OFF and not hass.config_entries.flow.async_progress()


async def test_befehl_zu_oft(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(STAND, json=stand_beispiel())
    aioclient_mock.post(BEFEHL, status=429, headers={"Retry-After": "30"}, json={"ok": False, "fehler": "Zu viele Befehle in kurzer Zeit."})
    assert await hass.config_entries.async_setup(eintrag.entry_id)
    await hass.async_block_till_done()
    with pytest.raises(HomeAssistantError) as fehler:
        await hass.services.async_call("switch", "turn_on", {"entity_id": "switch.mein_spa_pumpe_2"}, blocking=True)
    assert fehler.value.translation_key == "zu_oft_warten"


async def test_abo_endet_und_kommt_wieder(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    await _einrichten(hass, eintrag, aioclient_mock)
    aioclient_mock.clear_requests()
    aioclient_mock.get(STAND, status=402, json={"ok": False, "zugang": "abo_noetig", "text": "Home Assistant gehört zum Abo.", "abo_url": "https://app.lotusswimspa.de/abo"})
    await _naechster_abruf(hass)
    assert hass.states.get("climate.mein_spa").state == STATE_UNAVAILABLE
    assert hass.states.get("switch.mein_spa_pumpe_2").state == STATE_UNAVAILABLE
    hinweis = ir.async_get(hass).async_get_issue(DOMAIN, f"{HINWEIS_ABO}_{eintrag.entry_id}")
    assert hinweis is not None and hinweis.learn_more_url == "https://app.lotusswimspa.de/abo" and hinweis.severity == ir.IssueSeverity.ERROR
    assert not hass.config_entries.flow.async_progress()
    assert eintrag.runtime_data.update_interval == timedelta(minutes=15)
    aioclient_mock.clear_requests()
    aioclient_mock.get(STAND, json=stand_beispiel())
    await _naechster_abruf(hass, 16)
    assert hass.states.get("climate.mein_spa").state == "heat"
    assert ir.async_get(hass).async_get_issue(DOMAIN, f"{HINWEIS_ABO}_{eintrag.entry_id}") is None
    assert eintrag.runtime_data.update_interval == timedelta(seconds=60)


async def test_anmeldung_ungueltig(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    await _einrichten(hass, eintrag, aioclient_mock)
    aioclient_mock.clear_requests()
    aioclient_mock.get(STAND, status=401, json={"ok": False, "fehler": "token"})
    await _naechster_abruf(hass)
    flows = hass.config_entries.flow.async_progress()
    assert len(flows) == 1 and flows[0]["context"]["source"] == "reauth"
    assert hass.states.get("climate.mein_spa").state == STATE_UNAVAILABLE


async def test_spa_getrennt(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    await _einrichten(hass, eintrag, aioclient_mock, stand_beispiel(verbunden=False))
    assert hass.states.get("climate.mein_spa").state == STATE_UNAVAILABLE
    assert hass.states.get("binary_sensor.mein_spa_verbindung").state == STATE_OFF


async def test_erster_abruf_ohne_abo(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(STAND, status=402, json={"ok": False, "zugang": "abo_noetig", "text": "Home Assistant gehört zum Abo."})
    await hass.config_entries.async_setup(eintrag.entry_id)
    await hass.async_block_till_done()
    assert eintrag.state is ConfigEntryState.SETUP_RETRY
    assert ir.async_get(hass).async_get_issue(DOMAIN, f"{HINWEIS_ABO}_{eintrag.entry_id}") is not None
    assert _befehle(aioclient_mock) == []


async def test_diagnose_ohne_schluessel_und_namen(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    await _einrichten(hass, eintrag, aioclient_mock)
    text = json.dumps(await async_get_config_entry_diagnostics(hass, eintrag))
    assert "zugriff-1" not in text and "erneuern-1" not in text and "Mein Spa" not in text and GERAET not in text
    assert "37.5" in text


async def test_plan_lesen(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    await _einrichten(hass, eintrag, aioclient_mock, mit_plan())
    assert hass.states.get("sensor.mein_spa_grund_der_solltemperatur").state == "Badezeit — gehalten auf 38,0 °C."
    block = hass.states.get("sensor.mein_spa_filterblock")
    assert block.state == "08:00–12:00" and block.attributes["bloecke"] == ["08:00–12:00", "20:00–22:00"]
    assert hass.states.get("sensor.mein_spa_nachste_badezeit_beginn").state == "2026-10-30T17:00:00+00:00"
    assert hass.states.get("sensor.mein_spa_nachste_badezeit_ende").state == "2026-10-30T20:00:00+00:00"
    assert hass.states.get("time.mein_spa_badezeit_mo_so_1_beginn").state == "18:00:00"
    assert hass.states.get("time.mein_spa_badezeit_mo_so_1_ende").state == "21:00:00"
    assert hass.states.get("select.mein_spa_solar_betriebsart").state == "aus"
    assert hass.states.get("select.mein_spa_solar_betriebsart").attributes["options"] == ["aus", "zeitplan", "temperatur"]
    assert _befehle(aioclient_mock) == []


async def test_badezeit_aendern(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    await _einrichten(hass, eintrag, aioclient_mock, mit_plan())
    await hass.services.async_call("time", "set_value", {"entity_id": "time.mein_spa_badezeit_mo_so_1_beginn", "time": "17:30"}, blocking=True)
    await hass.services.async_call("time", "set_value", {"entity_id": "time.mein_spa_badezeit_mo_so_1_ende", "time": "00:00"}, blocking=True)
    assert _befehle(aioclient_mock) == [{"geraet": GERAET, "was": "badezeit", "gruppe": 0, "nr": 0, "von": "17:30"},
                                        {"geraet": GERAET, "was": "badezeit", "gruppe": 0, "nr": 0, "bis": "24:00"}]


async def test_badezeiten_werktag_und_wochenende(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    gruppen = [{"nr": 0, "name": "werktags", "bloecke": [{"von": "18:00", "bis": "21:00"}]},
               {"nr": 1, "name": "wochenende", "bloecke": [{"von": "10:00", "bis": "12:00"}, {"von": "16:00", "bis": "24:00"}]}]
    await _einrichten(hass, eintrag, aioclient_mock, mit_plan(badezeiten={"art": "werktag", "gruppen": gruppen, "darf": True}))
    zeiten = {s_.entity_id for s_ in hass.states.async_all("time")}
    assert zeiten == {"time.mein_spa_badezeit_mo_fr_1_beginn", "time.mein_spa_badezeit_mo_fr_1_ende", "time.mein_spa_badezeit_sa_so_1_beginn",
                      "time.mein_spa_badezeit_sa_so_1_ende", "time.mein_spa_badezeit_sa_so_2_beginn", "time.mein_spa_badezeit_sa_so_2_ende"}
    assert hass.states.get("time.mein_spa_badezeit_sa_so_2_ende").state == "00:00:00"
    await hass.services.async_call("time", "set_value", {"entity_id": "time.mein_spa_badezeit_sa_so_2_beginn", "time": "15:00"}, blocking=True)
    assert _befehle(aioclient_mock) == [{"geraet": GERAET, "was": "badezeit", "gruppe": 1, "nr": 1, "von": "15:00"}]


async def test_badezeiten_ohne_recht(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    await _einrichten(hass, eintrag, aioclient_mock, mit_plan(badezeiten=None, solar=None))
    alle = {s_.entity_id for s_ in hass.states.async_all()}
    assert not any(e_.startswith("time.") for e_ in alle) and "select.mein_spa_solar_betriebsart" not in alle
    assert hass.states.get("sensor.mein_spa_nachste_badezeit_beginn").state == "2026-10-30T17:00:00+00:00"
    assert _befehle(aioclient_mock) == []


async def test_solar_betriebsart(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    await _einrichten(hass, eintrag, aioclient_mock, mit_plan())
    await hass.services.async_call("select", "select_option", {"entity_id": "select.mein_spa_solar_betriebsart", "option": "aus"}, blocking=True)
    assert _befehle(aioclient_mock) == []
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call("select", "select_option", {"entity_id": "select.mein_spa_solar_betriebsart", "option": "beobachten"}, blocking=True)
    await hass.services.async_call("select", "select_option", {"entity_id": "select.mein_spa_solar_betriebsart", "option": "temperatur"}, blocking=True)
    assert _befehle(aioclient_mock) == [{"geraet": GERAET, "was": "solar_modus", "modus": "temperatur"}]


async def test_solar_nur_anzeige(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    solar = {"modus": "temperatur", "modi": [{"wert": "temperatur", "text": "Solar führt"}], "darf": False}
    await _einrichten(hass, eintrag, aioclient_mock, mit_plan(solar=solar))
    alle = {s_.entity_id for s_ in hass.states.async_all()}
    assert "select.mein_spa_solar_betriebsart" not in alle
    assert hass.states.get("sensor.mein_spa_solar_betriebsart").state == "temperatur"


async def test_plan_grenze(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(STAND, json=mit_plan())
    aioclient_mock.post(BEFEHL, status=429, headers={"Retry-After": "3600"}, json={"ok": False, "fehler": "Heute schon viermal.", "grenze": "tag"})
    assert await hass.config_entries.async_setup(eintrag.entry_id)
    await hass.async_block_till_done()
    with pytest.raises(HomeAssistantError) as fehler:
        await hass.services.async_call("time", "set_value", {"entity_id": "time.mein_spa_badezeit_mo_so_1_beginn", "time": "17:00"}, blocking=True)
    assert fehler.value.translation_key == "plan_grenze"
    assert hass.states.get("time.mein_spa_badezeit_mo_so_1_beginn").state == "18:00:00"


async def test_filterzeit_aendern(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    bloecke = [{"id": "wc:1:0:0:6", "von": "08:00", "bis": "12:00", "tage": ""}, {"id": "wc:1:1:0:6", "von": "20:00", "bis": "24:00", "tage": ""}]
    filterzeiten = {"bloecke": bloecke, "darf": True, "grund": None}
    await _einrichten(hass, eintrag, aioclient_mock, stand_beispiel(filterzeiten=filterzeiten))
    assert hass.states.get("time.mein_spa_filterzeit_1_beginn").state == "08:00:00"
    assert hass.states.get("time.mein_spa_filterzeit_2_ende").state == "00:00:00"
    await hass.services.async_call("time", "set_value", {"entity_id": "time.mein_spa_filterzeit_1_ende", "time": "13:00"}, blocking=True)
    await hass.services.async_call("time", "set_value", {"entity_id": "time.mein_spa_filterzeit_2_ende", "time": "00:00"}, blocking=True)
    assert _befehle(aioclient_mock) == [{"geraet": GERAET, "was": "filterzeit", "id": "wc:1:0:0:6", "bis": "13:00"},
                                        {"geraet": GERAET, "was": "filterzeit", "id": "wc:1:1:0:6", "bis": "24:00"}]


async def test_filterzeiten_solar_fuehrt(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    grund = "Solar führt — Lotus legt die Filterzeiten."
    filterzeiten = {"bloecke": [{"id": "wc:1:0:0:6", "von": "08:00", "bis": "12:00", "tage": ""}], "darf": False, "grund": grund}
    await _einrichten(hass, eintrag, aioclient_mock, stand_beispiel(filterzeiten=filterzeiten))
    assert hass.states.get("time.mein_spa_filterzeit_1_beginn").state == "08:00:00"
    assert hass.states.get("sensor.mein_spa_filterblock").attributes["hinweis"] == "Solar führt — Lotus legt die Filterzeiten."
    with pytest.raises(ServiceValidationError) as fehler:
        await hass.services.async_call("time", "set_value", {"entity_id": "time.mein_spa_filterzeit_1_beginn", "time": "09:00"}, blocking=True)
    assert fehler.value.translation_placeholders == {"grund": grund}
    assert _befehle(aioclient_mock) == []


async def test_wartung(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    wartung = {"darf": True, "aufgaben": [
        {"schluessel": "filter_reinigen", "titel": "Filter reinigen", "text": "heute", "faellig": True, "vorwarnung": True, "faellig_am": "2026-10-30",
         "tage_uebrig": 0, "erledigen": True},
        {"schluessel": "pack:Filter", "titel": "Filter (Steuerung)", "text": "noch nicht gelesen", "faellig": False, "vorwarnung": False, "faellig_am": None,
         "tage_uebrig": None, "erledigen": False, "hinweis": "Die Erinnerungen deiner Steuerung erscheinen hier, sobald du eine zurücksetzt."},
        {"schluessel": "pack:Spa", "titel": "Spa (Steuerung)", "text": "noch nicht gelesen", "faellig": False, "vorwarnung": False, "faellig_am": None,
         "tage_uebrig": None, "erledigen": False},
        {"schluessel": "pack:ChangeWater", "titel": "Wasser wechseln", "text": "in 90 Tagen", "faellig": False, "vorwarnung": False, "faellig_am": "2027-01-28",
         "tage_uebrig": 90, "erledigen": True, "ruht": True, "grund": "chlorfreie Pflege — Erinnerung der Steuerung ausgeblendet"},
    ]}
    await _einrichten(hass, eintrag, aioclient_mock, stand_beispiel(wartung=wartung))
    termin = hass.states.get("sensor.mein_spa_filter_reinigen")
    assert termin.state == "2026-10-30" and termin.attributes["tage_uebrig"] == 0 and termin.attributes["text"] == "heute"
    assert termin.attributes["ruht"] is False and termin.attributes["grund"] == ""
    ruhend = hass.states.get("sensor.mein_spa_wasser_wechseln")
    assert ruhend.state == "2027-01-28" and ruhend.attributes["ruht"] is True and ruhend.attributes["tage_uebrig"] == 90
    assert ruhend.attributes["grund"].startswith("chlorfreie Pflege")
    assert hass.states.get("binary_sensor.mein_spa_wasser_wechseln_fallig").state == STATE_OFF
    leer = hass.states.get("sensor.mein_spa_filter_steuerung")
    assert leer.state == STATE_UNKNOWN and leer.attributes["hinweis"].startswith("Die Erinnerungen deiner Steuerung")
    assert hass.states.get("sensor.mein_spa_spa_steuerung").state == STATE_UNAVAILABLE
    assert termin.attributes["hinweis"] == ""
    assert hass.states.get("binary_sensor.mein_spa_filter_reinigen_fallig").state == STATE_ON
    assert hass.states.get("binary_sensor.mein_spa_filter_steuerung_fallig").state == STATE_OFF
    assert hass.states.get("button.mein_spa_filter_steuerung_erledigt").state == STATE_UNAVAILABLE
    await hass.services.async_call("button", "press", {"entity_id": "button.mein_spa_filter_reinigen_erledigt"}, blocking=True)
    assert _befehle(aioclient_mock) == [{"geraet": GERAET, "was": "wartung_erledigt", "aufgabe": "filter_reinigen"}]


async def test_wartung_ohne_recht(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    await _einrichten(hass, eintrag, aioclient_mock)
    alle = {s_.entity_id for s_ in hass.states.async_all()}
    assert not any(e_.startswith("button.") for e_ in alle) and _befehle(aioclient_mock) == []


async def test_schalter_zeigt_sofort(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker,
                                     monkeypatch: pytest.MonkeyPatch) -> None:
    uhr = {"jetzt": 1000.0}
    monkeypatch.setattr("custom_components.lotus_spa.switch.time.monotonic", lambda: uhr["jetzt"])
    await _einrichten(hass, eintrag, aioclient_mock)
    await hass.services.async_call("light", "turn_on", {"entity_id": "light.mein_spa_licht"}, blocking=True)
    await hass.services.async_call("fan", "set_preset_mode", {"entity_id": "fan.mein_spa_pumpe_1", "preset_mode": "Stufe 1"}, blocking=True)
    assert hass.states.get("light.mein_spa_licht").state == STATE_ON
    assert hass.states.get("fan.mein_spa_pumpe_1").state == STATE_ON and hass.states.get("fan.mein_spa_pumpe_1").attributes["preset_mode"] == "Stufe 1"
    uhr["jetzt"] += 10
    await _naechster_abruf(hass)
    assert hass.states.get("light.mein_spa_licht").state == STATE_ON and hass.states.get("fan.mein_spa_pumpe_1").state == STATE_ON
    uhr["jetzt"] += 6
    await _naechster_abruf(hass)
    assert hass.states.get("light.mein_spa_licht").state == STATE_OFF
    assert hass.states.get("fan.mein_spa_pumpe_1").state == STATE_OFF


async def test_schnelle_befehle_flattern_nicht(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker,
                                               monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("custom_components.lotus_spa.coordinator.NACHLESEN_S", (0.0, 0.0, 0.0))
    await _einrichten(hass, eintrag, aioclient_mock)
    zustaende: list[str] = []
    hass.bus.async_listen("state_changed", lambda ev_: zustaende.append(ev_.data["new_state"].state)
                          if ev_.data["entity_id"] == "fan.mein_spa_pumpe_1" else None)
    for stufe in ("Stufe 1", "Stufe 2"):
        await hass.services.async_call("fan", "set_preset_mode", {"entity_id": "fan.mein_spa_pumpe_1", "preset_mode": stufe}, blocking=True)
        await hass.async_block_till_done(wait_background_tasks=True)
    await hass.services.async_call("fan", "turn_off", {"entity_id": "fan.mein_spa_pumpe_1"}, blocking=True)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert zustaende and zustaende[-1] == STATE_OFF and STATE_OFF not in zustaende[:-1]


async def test_abgelehnter_schaltbefehl_faellt_zurueck(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(STAND, json=stand_beispiel())
    aioclient_mock.post(BEFEHL, status=400, json={"ok": False, "fehler": "Nicht möglich."})
    assert await hass.config_entries.async_setup(eintrag.entry_id)
    await hass.async_block_till_done()
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call("light", "turn_on", {"entity_id": "light.mein_spa_licht"}, blocking=True)
    assert hass.states.get("light.mein_spa_licht").state == STATE_OFF


async def test_pumpe_stufen(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    await _einrichten(hass, eintrag, aioclient_mock)
    pumpe = hass.states.get("fan.mein_spa_pumpe_1")
    assert pumpe.attributes["percentage_step"] == 50 and pumpe.attributes["percentage"] == 0
    for prozent in (50, 100, 0):
        await hass.services.async_call("fan", "set_percentage", {"entity_id": "fan.mein_spa_pumpe_1", "percentage": prozent}, blocking=True)
    assert _befehle(aioclient_mock) == [{"geraet": GERAET, "was": "schalten", "titel": "Pumpe 1", "modus": "LO"},
                                        {"geraet": GERAET, "was": "schalten", "titel": "Pumpe 1", "modus": "HI"},
                                        {"geraet": GERAET, "was": "schalten", "titel": "Pumpe 1", "modus": "OFF"}]
    assert "fan.mein_spa_pumpe_2" not in {s_.entity_id for s_ in hass.states.async_all()}


async def test_symbole_einheitlich(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    stand = stand_beispiel()
    stand["geraete"][GERAET]["schalter"].append({"titel": "Blower", "name": "Blower", "art": "geraet", "modi": [{"wert": "ON", "text": "Ein"}],
                                                 "aktiv": "OFF", "laeuft": False, "darf": True})
    await _einrichten(hass, eintrag, aioclient_mock, stand)
    register = er.async_get(hass)
    assert {e_: register.async_get(e_).translation_key for e_ in ("fan.mein_spa_pumpe_1", "switch.mein_spa_pumpe_2", "switch.mein_spa_blower",
                                                                    "light.mein_spa_licht")} == \
        {"fan.mein_spa_pumpe_1": "pumpe", "switch.mein_spa_pumpe_2": "pumpe", "switch.mein_spa_blower": "blower", "light.mein_spa_licht": "licht"}
    _jeder_zustand_ein_symbol(hass)


async def test_symbole_ohne_recht(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    await _einrichten(hass, eintrag, aioclient_mock, ohne_recht(stand_beispiel()))
    register = er.async_get(hass)
    assert register.async_get("binary_sensor.mein_spa_pumpe_1").translation_key == "pumpe"
    assert register.async_get("binary_sensor.mein_spa_licht").translation_key == "licht"
    _jeder_zustand_ein_symbol(hass)


def _jeder_zustand_ein_symbol(hass: HomeAssistant) -> None:
    symbole = json.loads((Path(__file__).parent.parent / "custom_components" / "lotus_spa" / "icons.json").read_text(encoding="utf-8"))["entity"]
    for eintrag_ in er.async_get(hass).entities.values():
        bereich = eintrag_.entity_id.split(".")[0]
        if bereich not in ("fan", "switch", "light", "binary_sensor") or eintrag_.platform != DOMAIN:
            continue
        symbol = symbole.get(bereich, {}).get(eintrag_.translation_key or "", {})
        zustand = symbol.get("state") or {}
        assert symbol.get("default") and zustand.get("on") and zustand.get("off"), eintrag_.entity_id
        assert zustand["on"] != zustand["off"] or eintrag_.translation_key in ("blower", "wasserfall"), eintrag_.entity_id


async def test_filterung_eine_entitaet(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    register = er.async_get(hass)
    alt = register.async_get_or_create("sensor", DOMAIN, f"{GERAET}_text_filterung", config_entry=eintrag, suggested_object_id="mein_spa_filterung_alt")
    await _einrichten(hass, eintrag, aioclient_mock)
    assert register.async_get(alt.entity_id) is None
    assert register.async_get_entity_id("binary_sensor", DOMAIN, f"{GERAET}_filter") == "binary_sensor.mein_spa_filterung"
    assert not [e_ for e_ in register.entities.values() if e_.platform == DOMAIN and e_.unique_id.endswith("_text_filterung")]


async def test_reihenfolge_schaltbares_zuerst(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    await _einrichten(hass, eintrag, aioclient_mock, mit_plan(wartung={"darf": True, "aufgaben": [
        {"schluessel": "filter_reinigen", "titel": "Filter reinigen", "text": "heute", "faellig": True, "vorwarnung": True, "faellig_am": "2026-10-30",
         "tage_uebrig": 0, "erledigen": True}]}))
    register = er.async_get(hass)
    kategorie = {e_.entity_id: e_.entity_category for e_ in register.entities.values() if e_.platform == DOMAIN}
    steuern = {e_ for e_, k_ in kategorie.items() if k_ is None and e_.split(".")[0] in ("climate", "fan", "switch", "light", "select")}
    assert steuern == {"climate.mein_spa", "fan.mein_spa_pumpe_1", "switch.mein_spa_pumpe_2", "light.mein_spa_licht", "select.mein_spa_solar_betriebsart"}
    assert kategorie["select.mein_spa_pflegelauf"] == EntityCategory.CONFIG and kategorie["button.mein_spa_filter_reinigen_erledigt"] == EntityCategory.CONFIG
    assert kategorie["binary_sensor.mein_spa_verbindung"] == EntityCategory.DIAGNOSTIC
    assert kategorie["sensor.mein_spa_meldungstext"] is None and hass.states.get("sensor.mein_spa_meldungstext").state == "Keine Meldung"


async def test_pflegelauf_dauer_und_ende(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    stand = stand_beispiel()
    stand["geraete"][GERAET]["pflegelauf"].update({"laeuft": True, "zweck": "chlor", "rest_min": 12, "bis": "2026-10-30T15:20:00+01:00"})
    await _einrichten(hass, eintrag, aioclient_mock, stand)
    dauer = hass.states.get("select.mein_spa_pflegelauf_dauer")
    assert dauer.state == "20" and dauer.attributes["options"] == ["10", "20", "30", "45", "60"]
    assert hass.states.get("sensor.mein_spa_pflegelauf_endet").state == "2026-10-30T14:20:00+00:00"
    await hass.services.async_call("select", "select_option", {"entity_id": "select.mein_spa_pflegelauf_dauer", "option": "20"}, blocking=True)
    await hass.services.async_call("select", "select_option", {"entity_id": "select.mein_spa_pflegelauf_dauer", "option": "45"}, blocking=True)
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call("select", "select_option", {"entity_id": "select.mein_spa_pflegelauf_dauer", "option": "25"}, blocking=True)
    assert _befehle(aioclient_mock) == [{"geraet": GERAET, "was": "pflegelauf_dauer", "minuten": 45}]


async def test_wartungspause(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    pause = {"laeuft": True, "minuten": 30, "bis": "2026-10-30T15:00:00+01:00"}
    await _einrichten(hass, eintrag, aioclient_mock, stand_beispiel(wartungspause=pause))
    assert hass.states.get("switch.mein_spa_wartungspause").state == STATE_ON
    assert hass.states.get("sensor.mein_spa_wartungspause_endet").state == "2026-10-30T14:00:00+00:00"
    await hass.services.async_call("switch", "turn_off", {"entity_id": "switch.mein_spa_wartungspause"}, blocking=True)
    await hass.services.async_call("switch", "turn_on", {"entity_id": "switch.mein_spa_wartungspause"}, blocking=True)
    assert _befehle(aioclient_mock) == [{"geraet": GERAET, "was": "wartungspause", "an": False}, {"geraet": GERAET, "was": "wartungspause", "an": True}]


async def test_wartungspause_frost(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(STAND, json=stand_beispiel(wartungspause={"laeuft": False, "minuten": 30, "bis": None}))
    aioclient_mock.post(BEFEHL, status=400, json={"ok": False, "fehler": "Frostgefahr: die Pause startet nicht.", "frost": True})
    assert await hass.config_entries.async_setup(eintrag.entry_id)
    await hass.async_block_till_done()
    with pytest.raises(ServiceValidationError) as fehler:
        await hass.services.async_call("switch", "turn_on", {"entity_id": "switch.mein_spa_wartungspause"}, blocking=True)
    assert fehler.value.translation_placeholders == {"grund": "Frostgefahr: die Pause startet nicht."}
    assert hass.states.get("switch.mein_spa_wartungspause").state == STATE_OFF


async def test_wartungspause_ohne_recht(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    await _einrichten(hass, eintrag, aioclient_mock)
    alle = {s_.entity_id for s_ in hass.states.async_all()}
    assert "switch.mein_spa_wartungspause" not in alle and "sensor.mein_spa_wartungspause_endet" not in alle


async def test_konto_und_hinweise(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    await _einrichten(hass, eintrag, aioclient_mock, stand_beispiel(konto={"art": "abo", "bis": "2026-11-05", "hinweis": "abo_ablauf"}))
    assert hass.states.get("sensor.lotus_konto_abo").state == "abo"
    assert hass.states.get("sensor.lotus_konto_abo").attributes["options"] == ["abo", "abo_unbefristet", "ohne_abo"]
    assert hass.states.get("sensor.lotus_konto_abo_gultig_bis").state == "2026-11-05"
    geraet = dr.async_get(hass).async_get_device_by_identifier((DOMAIN, f"konto_{eintrag.entry_id}"), eintrag.entry_id)
    adresse = URL(geraet.configuration_url)
    assert geraet.entry_type is dr.DeviceEntryType.SERVICE and adresse.path == "/konto" and adresse.fragment == "kontoabo"
    hinweise = ir.async_get(hass)
    assert hinweise.async_get_issue(DOMAIN, f"abo_ablauf_{eintrag.entry_id}") is not None
    assert hinweise.async_get_issue(DOMAIN, f"zahlung_{eintrag.entry_id}") is None
    aioclient_mock.clear_requests()
    aioclient_mock.get(STAND, json=stand_beispiel(konto={"art": "abo", "bis": "2027-10-30", "hinweis": None}))
    await _naechster_abruf(hass)
    assert hinweise.async_get_issue(DOMAIN, f"abo_ablauf_{eintrag.entry_id}") is None
    assert hass.states.get("sensor.lotus_konto_abo").state == "abo"
    aioclient_mock.clear_requests()
    aioclient_mock.get(STAND, json=stand_beispiel(konto={"art": "abo", "bis": "2026-11-01", "hinweis": "zahlung"}))
    await _naechster_abruf(hass)
    assert hinweise.async_get_issue(DOMAIN, f"zahlung_{eintrag.entry_id}") is not None
    assert _befehle(aioclient_mock) == []


async def test_ohne_konto_kein_kontogeraet(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    await _einrichten(hass, eintrag, aioclient_mock)
    assert dr.async_get(hass).async_get_device_by_identifier((DOMAIN, f"konto_{eintrag.entry_id}"), eintrag.entry_id) is None
    assert hass.states.get("sensor.lotus_konto_abo") is None


async def test_box(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    box = {"id": "a1b2c3d4e5f6a7b8", "verbunden": True, "empfang": "gut", "rssi": -67, "ssid": "Musternetz", "firmware": None, "seit": None}
    await _einrichten(hass, eintrag, aioclient_mock, stand_beispiel(box=box))
    register = dr.async_get(hass)
    box_geraet = register.async_get_device_by_identifier((DOMAIN, "box_a1b2c3d4e5f6a7b8"), eintrag.entry_id)
    spa = register.async_get_device_by_identifier((DOMAIN, GERAET), eintrag.entry_id)
    assert box_geraet is not None and box_geraet.sw_version is None and spa.via_device_id == box_geraet.id
    assert hass.states.get("binary_sensor.lotus_box_verbindung").state == STATE_ON
    assert hass.states.get("sensor.lotus_box_wlan_empfang").state == "gut"
    assert hass.states.get("sensor.lotus_box_wlan").state == "Musternetz"
    signal = er.async_get(hass).async_get_entity_id("sensor", DOMAIN, f"{GERAET}_box_signal")
    assert signal is not None and er.async_get(hass).async_get(signal).disabled_by is er.RegistryEntryDisabler.INTEGRATION
    assert er.async_get(hass).async_get_entity_id("sensor", DOMAIN, f"{GERAET}_box_start") is None


async def test_ohne_box_keine_box(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    await _einrichten(hass, eintrag, aioclient_mock)
    alle = {s_.entity_id for s_ in hass.states.async_all()}
    assert not any("lotus_box" in e_ for e_ in alle)
    assert dr.async_get(hass).async_get_device_by_identifier((DOMAIN, GERAET), eintrag.entry_id).via_device_id is None


async def test_box_ohne_veraltetes_via_device(
    hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker, caplog: pytest.LogCaptureFixture
) -> None:
    box = {"id": "a1b2c3d4e5f6a7b8", "verbunden": True, "empfang": "gut", "rssi": -67, "ssid": "Musternetz", "firmware": None, "seit": None}
    register = dr.async_get(hass)
    alt_box = register.async_get_or_create(config_entry_id=eintrag.entry_id, identifiers={(DOMAIN, "box_a1b2c3d4e5f6a7b8")}, name="Lotus Box")
    alt_spa = register.async_get_or_create(config_entry_id=eintrag.entry_id, identifiers={(DOMAIN, GERAET)}, name="Mein Spa", via_device_id=alt_box.id)
    vorher = len(dr.async_entries_for_config_entry(register, eintrag.entry_id))
    await _einrichten(hass, eintrag, aioclient_mock, stand_beispiel(box=box))
    box_geraet = register.async_get_device_by_identifier((DOMAIN, "box_a1b2c3d4e5f6a7b8"), eintrag.entry_id)
    spa = register.async_get_device_by_identifier((DOMAIN, GERAET), eintrag.entry_id)
    assert box_geraet.id == alt_box.id and spa.id == alt_spa.id and spa.via_device_id == box_geraet.id
    assert len(dr.async_entries_for_config_entry(register, eintrag.entry_id)) == vorher == 2
    assert await hass.config_entries.async_reload(eintrag.entry_id)
    await hass.async_block_till_done()
    assert len(dr.async_entries_for_config_entry(register, eintrag.entry_id)) == vorher == 2
    assert register.async_get_device_by_identifier((DOMAIN, GERAET), eintrag.entry_id).via_device_id == box_geraet.id
    assert "via_device" not in caplog.text


async def test_energie_und_aussen(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    energie = {"kwh": 123.456, "w": 2800, "kosten_heute": 1.84, "geschaetzt": True}
    await _einrichten(hass, eintrag, aioclient_mock, stand_beispiel(energie=energie, warm_um={"zeit": "2026-10-30T18:40:00+01:00"}))
    zaehler = hass.states.get("sensor.mein_spa_energie_geschatzt")
    assert zaehler.state == "123.456" and zaehler.attributes["state_class"] == "total_increasing" and zaehler.attributes["unit_of_measurement"] == "kWh"
    assert hass.states.get("sensor.mein_spa_leistung_geschatzt").state == "2800.0"
    assert hass.states.get("sensor.mein_spa_kosten_heute").state == "1.84"
    assert hass.states.get("sensor.mein_spa_aussentemperatur").attributes["attribution"] == "Deutscher Wetterdienst"
    assert hass.states.get("sensor.mein_spa_warm_um").state == "2026-10-30T17:40:00+00:00"
    aioclient_mock.clear_requests()
    aioclient_mock.get(STAND, json=stand_beispiel(energie={}, warm_um={"zeit": None}))
    await _naechster_abruf(hass)
    assert hass.states.get("sensor.mein_spa_energie_geschatzt").state == STATE_UNAVAILABLE
    assert hass.states.get("sensor.mein_spa_warm_um").state == STATE_UNAVAILABLE


async def test_ohne_recht_keine_energie(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    await _einrichten(hass, eintrag, aioclient_mock)
    alle = {s_.entity_id for s_ in hass.states.async_all()}
    assert not any(e_.endswith(("_energie_geschatzt", "_leistung_geschatzt", "_kosten_heute", "_warm_um")) for e_ in alle)
    assert not any(e_.startswith("number.") for e_ in alle)


async def test_grundlagen(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    await _einrichten(hass, eintrag, aioclient_mock, stand_beispiel(volumen={"wert": 1480}, strompreis={"wert": 32.5}))
    assert hass.states.get("number.mein_spa_beckeninhalt").state == "1480.0"
    assert hass.states.get("number.mein_spa_strompreis").state == "32.5"
    await hass.services.async_call("number", "set_value", {"entity_id": "number.mein_spa_beckeninhalt", "value": 1480}, blocking=True)
    await hass.services.async_call("number", "set_value", {"entity_id": "number.mein_spa_beckeninhalt", "value": 1600}, blocking=True)
    await hass.services.async_call("number", "set_value", {"entity_id": "number.mein_spa_strompreis", "value": 29.9}, blocking=True)
    assert _befehle(aioclient_mock) == [{"geraet": GERAET, "was": "volumen", "wert": 1600}, {"geraet": GERAET, "was": "strompreis", "wert": 29.9}]


async def test_grundlagen_abgelehnt(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(STAND, json=stand_beispiel(volumen={"wert": 1480}))
    aioclient_mock.post(BEFEHL, status=400, json={"ok": False, "fehler": "Spa: Beckeninhalt 200 bis 30.000 Liter."})
    assert await hass.config_entries.async_setup(eintrag.entry_id)
    await hass.async_block_till_done()
    with pytest.raises(ServiceValidationError) as fehler:
        await hass.services.async_call("number", "set_value", {"entity_id": "number.mein_spa_beckeninhalt", "value": 50}, blocking=True)
    assert fehler.value.translation_placeholders == {"grund": "Spa: Beckeninhalt 200 bis 30.000 Liter."}


async def test_heizmodus_als_preset(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    await _einrichten(hass, eintrag, aioclient_mock)
    thermostat = hass.states.get("climate.mein_spa")
    assert thermostat.attributes["supported_features"] == 17 and thermostat.attributes["preset_modes"] == ["Standard", "Energiesparen"]
    assert thermostat.attributes["preset_mode"] == "Standard"
    assert _befehle(aioclient_mock) == []
    await hass.services.async_call("climate", "set_preset_mode", {"entity_id": "climate.mein_spa", "preset_mode": "Energiesparen"}, blocking=True)
    assert _befehle(aioclient_mock) == [{"geraet": GERAET, "was": "heizmodus", "wahl": "sparen"}]


async def test_heizmodus_ohne_recht_kein_preset(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    beispiel = stand_beispiel()
    beispiel["geraete"][GERAET]["heizmodus"]["darf"] = False
    await _einrichten(hass, eintrag, aioclient_mock, beispiel)
    thermostat = hass.states.get("climate.mein_spa")
    assert thermostat.attributes["supported_features"] == 1 and "preset_modes" not in thermostat.attributes


async def test_urlaub_absenkung_abendlicht(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    alt = er.async_get(hass).async_get_or_create("binary_sensor", DOMAIN, f"{GERAET}_urlaubsmodus", config_entry=eintrag)
    await _einrichten(hass, eintrag, aioclient_mock, stand_beispiel(
        urlaub={"an": False, "ziel": 30.0, "unten": 10.0, "oben": 40.0}, absenkung={"modus": "an", "grad": 2.0}, abendlicht={"an": True}))
    assert er.async_get(hass).async_get(alt.entity_id) is None
    assert hass.states.get("switch.mein_spa_urlaubsmodus").state == STATE_OFF
    assert hass.states.get("switch.mein_spa_abendlicht").state == STATE_ON
    ziel = hass.states.get("number.mein_spa_urlaubstemperatur")
    assert ziel.state == "30.0" and ziel.attributes["min"] == 10.0 and ziel.attributes["max"] == 40.0
    assert hass.states.get("select.mein_spa_absenkung").state == "an" and hass.states.get("number.mein_spa_absenkung").state == "2.0"
    assert _befehle(aioclient_mock) == []
    await hass.services.async_call("switch", "turn_on", {"entity_id": "switch.mein_spa_urlaubsmodus"}, blocking=True)
    await hass.services.async_call("number", "set_value", {"entity_id": "number.mein_spa_urlaubstemperatur", "value": 28}, blocking=True)
    await hass.services.async_call("number", "set_value", {"entity_id": "number.mein_spa_urlaubstemperatur", "value": 30}, blocking=True)
    await hass.services.async_call("select", "select_option", {"entity_id": "select.mein_spa_absenkung", "option": "auto"}, blocking=True)
    await hass.services.async_call("number", "set_value", {"entity_id": "number.mein_spa_absenkung", "value": 3.5}, blocking=True)
    await hass.services.async_call("switch", "turn_off", {"entity_id": "switch.mein_spa_abendlicht"}, blocking=True)
    assert _befehle(aioclient_mock) == [
        {"geraet": GERAET, "was": "urlaub", "wahl": "an"}, {"geraet": GERAET, "was": "urlaub", "wahl": "28.0"},
        {"geraet": GERAET, "was": "absenkung", "wahl": "auto"}, {"geraet": GERAET, "was": "absenkung", "wahl": "3.5"},
        {"geraet": GERAET, "was": "abendlicht", "wahl": "aus"}]


async def test_absenkung_im_urlaub_ohne_zahl(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    await _einrichten(hass, eintrag, aioclient_mock, stand_beispiel(
        urlaub={"an": True, "ziel": 25.0, "unten": 10.0, "oben": 40.0}, absenkung={"modus": None, "grad": None}))
    assert hass.states.get("number.mein_spa_absenkung").state == STATE_UNAVAILABLE
    assert hass.states.get("select.mein_spa_absenkung").state == STATE_UNAVAILABLE
    assert hass.states.get("switch.mein_spa_urlaubsmodus").state == STATE_ON
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call("number", "set_value", {"entity_id": "number.mein_spa_urlaubstemperatur", "value": 45}, blocking=True)
    assert _befehle(aioclient_mock) == []


async def test_ohne_kachel_keine_einstellung(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    await _einrichten(hass, eintrag, aioclient_mock)
    alle = {s_.entity_id for s_ in hass.states.async_all()}
    assert not any(e_.endswith(("_urlaubsmodus", "_abendlicht", "_urlaubstemperatur")) or e_ in ("select.mein_spa_absenkung", "number.mein_spa_absenkung")
                   for e_ in alle)



async def test_abo_funktionen_hinweis(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    await _einrichten(hass, eintrag, aioclient_mock)
    kennung = f"abo_funktionen_{eintrag.entry_id}"
    assert ir.async_get(hass).async_get_issue(DOMAIN, kennung) is None
    aioclient_mock.clear_requests()
    aioclient_mock.get(STAND, status=402, json={"ok": False, "zugang": "abo_noetig", "text": "Home Assistant gehört zum Abo.",
                                                "fehlt": ["urlaub", "absenkung", "warm_um", "unbekannt"]})
    await _naechster_abruf(hass)
    hinweis = ir.async_get(hass).async_get_issue(DOMAIN, kennung)
    assert hinweis is not None and hinweis.severity == ir.IssueSeverity.WARNING and URL(hinweis.learn_more_url).fragment == "kontoabo"
    assert hinweis.translation_placeholders == {"funktionen": "Urlaubsmodus, Absenkung, Warm um"} and not hinweis.is_fixable
    assert _befehle(aioclient_mock) == []
    aioclient_mock.clear_requests()
    aioclient_mock.get(STAND, json=stand_beispiel())
    await _naechster_abruf(hass, 16)
    assert ir.async_get(hass).async_get_issue(DOMAIN, kennung) is None


async def test_kein_recht_ohne_funktionen_hinweis(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    await _einrichten(hass, eintrag, aioclient_mock)
    aioclient_mock.clear_requests()
    aioclient_mock.get(STAND, status=402, json={"ok": False, "zugang": "kein_recht", "text": "Nicht freigeschaltet.", "fehlt": ["urlaub"]})
    await _naechster_abruf(hass)
    assert ir.async_get(hass).async_get_issue(DOMAIN, f"abo_funktionen_{eintrag.entry_id}") is None


def _abrufe(aioclient_mock: AiohttpClientMocker) -> int:
    return sum(1 for c_ in aioclient_mock.mock_calls if c_[0] == "GET" and str(c_[1]) == STAND)


async def test_nachlesen_nach_befehl(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker,
                                     monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("custom_components.lotus_spa.coordinator.NACHLESEN_S", (0.0, 0.0, 0.0))
    await _einrichten(hass, eintrag, aioclient_mock)
    vorher = _abrufe(aioclient_mock)
    aioclient_mock.post(BEFEHL, json={"ok": True})
    await hass.services.async_call("fan", "turn_on", {"entity_id": "fan.mein_spa_pumpe_1"}, blocking=True)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert _abrufe(aioclient_mock) - vorher == 4


async def test_abgelehnt_kein_nachlesen(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker,
                                        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("custom_components.lotus_spa.coordinator.NACHLESEN_S", (0.0, 0.0, 0.0))
    aioclient_mock.get(STAND, json=stand_beispiel())
    aioclient_mock.post(BEFEHL, status=400, json={"ok": False, "fehler": "Nicht möglich."})
    assert await hass.config_entries.async_setup(eintrag.entry_id)
    await hass.async_block_till_done()
    vorher = _abrufe(aioclient_mock)
    zustand = hass.states.get("fan.mein_spa_pumpe_1").state
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call("fan", "turn_on", {"entity_id": "fan.mein_spa_pumpe_1"}, blocking=True)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert _abrufe(aioclient_mock) == vorher and hass.states.get("fan.mein_spa_pumpe_1").state == zustand



async def test_fassung_im_kopf(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    from custom_components.lotus_spa.const import VERSION
    await _einrichten(hass, eintrag, aioclient_mock)
    abrufe = [c_ for c_ in aioclient_mock.mock_calls if c_[0] == "GET" and str(c_[1]) == STAND]
    assert abrufe and all((c_[3] or {}).get("X-Lotus-Integration") == VERSION for c_ in abrufe)


async def test_filterzeit_kennung_bleibt(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    register = er.async_get(hass)
    alt = register.async_get_or_create("time", DOMAIN, f"{GERAET}_filterzeit_wc_1_0_0_6_von", config_entry=eintrag,
                                       suggested_object_id="mein_spa_filterzeit_1_beginn")
    verwaist = register.async_get_or_create("time", DOMAIN, f"{GERAET}_filterzeit_wc_2_0_0_6_bis", config_entry=eintrag,
                                            suggested_object_id="mein_spa_filterzeit_1_ende")
    filterzeiten = {"bloecke": [{"id": "wc:1:0:0:6", "von": "08:00", "bis": "12:00", "tage": ""}], "darf": True, "grund": None}
    await _einrichten(hass, eintrag, aioclient_mock, stand_beispiel(filterzeiten=filterzeiten))
    assert register.async_get(alt.entity_id).unique_id == f"{GERAET}_filterzeit_0_von"
    assert register.async_get(verwaist.entity_id).unique_id == f"{GERAET}_filterzeit_0_bis"
    assert hass.states.get(alt.entity_id).state == "08:00:00" and hass.states.get(verwaist.entity_id).state == "12:00:00"
    aioclient_mock.clear_requests()
    aioclient_mock.get(STAND, json=stand_beispiel(filterzeiten={**filterzeiten, "bloecke": [{"id": "wc:2:0:0:6", "von": "09:00", "bis": "12:00", "tage": ""}]}))
    await _naechster_abruf(hass)
    assert hass.states.get(alt.entity_id).state == "09:00:00"


async def test_ohne_termin_nicht_verfuegbar(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    wartung = {"darf": True, "aufgaben": [{"schluessel": "pack:Filter", "titel": "Filter (Steuerung)", "text": "noch nicht gelesen", "faellig": False,
                                           "vorwarnung": False, "faellig_am": None, "tage_uebrig": None, "erledigen": False}]}
    await _einrichten(hass, eintrag, aioclient_mock, stand_beispiel(wartung=wartung, pflegelauf=None))
    termin = er.async_get(hass).async_get_entity_id("sensor", DOMAIN, f"{GERAET}_wartung_pack_Filter")
    assert termin is not None and hass.states.get(termin).state == STATE_UNAVAILABLE



async def test_abo_unbefristet(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    await _einrichten(hass, eintrag, aioclient_mock, stand_beispiel(konto={"art": "abo", "bis": "2026-12-10", "hinweis": None, "unbefristet": False}))
    register = er.async_get(hass)
    bis_id = register.async_get_entity_id("sensor", DOMAIN, f"konto_{eintrag.entry_id}_abo_bis")
    assert bis_id is not None and hass.states.get(bis_id).state == "2026-12-10"
    aioclient_mock.clear_requests()
    aioclient_mock.get(STAND, json=stand_beispiel(konto={"art": "abo_unbefristet", "bis": None, "hinweis": None, "unbefristet": True}))
    await _naechster_abruf(hass)
    assert hass.states.get("sensor.lotus_konto_abo").state == "abo_unbefristet"
    assert register.async_get_entity_id("sensor", DOMAIN, f"konto_{eintrag.entry_id}_abo_bis") is None and hass.states.get(bis_id) is None
    assert ir.async_get(hass).async_get_issue(DOMAIN, f"abo_ablauf_{eintrag.entry_id}") is None
    aioclient_mock.clear_requests()
    aioclient_mock.get(STAND, json=stand_beispiel(konto={"art": "abo", "bis": "2027-01-31", "hinweis": None, "unbefristet": False}))
    await _naechster_abruf(hass)
    neu_id = register.async_get_entity_id("sensor", DOMAIN, f"konto_{eintrag.entry_id}_abo_bis")
    assert neu_id is not None and hass.states.get(neu_id).state == "2027-01-31"
    assert _befehle(aioclient_mock) == []


async def test_energie_sonne_netz(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    energie = {"kwh": 200.0, "w": 0, "kosten_heute": 0.9, "geschaetzt": True, "kwh_heute": 4.0, "sonne_heute": 1.0, "netz_heute": 3.0,
               "sonnenanteil_heute": 25.0, "kosten_jahr": 36.12, "sonne_jahr": 80.0}
    await _einrichten(hass, eintrag, aioclient_mock, stand_beispiel(energie=energie))
    assert hass.states.get("sensor.mein_spa_sonne_heute_geschatzt").state == "1.0"
    assert hass.states.get("sensor.mein_spa_netz_heute_geschatzt").state == "3.0"
    assert hass.states.get("sensor.mein_spa_sonnenanteil_heute").state == "25.0"
    kosten = hass.states.get("sensor.mein_spa_kosten_dieses_jahr")
    assert kosten.state == "36.12" and kosten.attributes["state_class"] == "total" and kosten.attributes["unit_of_measurement"] == "EUR"
    aioclient_mock.clear_requests()
    aioclient_mock.get(STAND, json=stand_beispiel(energie={**energie, "kwh_heute": 0.0, "sonne_heute": 0.0, "netz_heute": 0.0, "sonnenanteil_heute": None}))
    await _naechster_abruf(hass)
    assert hass.states.get("sensor.mein_spa_sonnenanteil_heute").state == STATE_UNAVAILABLE
    assert hass.states.get("sensor.mein_spa_sonne_heute_geschatzt").state == "0.0"
    aioclient_mock.clear_requests()
    aioclient_mock.get(STAND, json=stand_beispiel(energie={}))
    await _naechster_abruf(hass)
    assert hass.states.get("sensor.mein_spa_kosten_dieses_jahr").state == STATE_UNAVAILABLE


async def test_energie_tage(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    tage = [{"datum": f"2026-10-{17 + i_:02d}", "kwh": 0.0 if i_ == 3 else 6.5, "sonne": 0.0 if i_ == 3 else 4.0, "netz": 0.0 if i_ == 3 else 2.5,
             "kosten": 0.0 if i_ == 3 else 0.87} for i_ in range(14)]
    energie = {"kwh": 200.0, "w": 0, "kosten_heute": 0.9, "geschaetzt": True, "kwh_heute": 6.5, "sonne_heute": 4.0, "netz_heute": 2.5,
               "sonnenanteil_heute": 61.5, "kosten_jahr": 36.12, "sonne_jahr": 80.0, "tage": tage}
    await _einrichten(hass, eintrag, aioclient_mock, stand_beispiel(energie=energie))
    heute = hass.states.get("sensor.mein_spa_energie_heute_geschatzt")
    assert heute.attributes["tage"] == tage and len(heute.attributes["tage"]) == 14 and heute.attributes["tage"][3]["kwh"] == 0.0
    assert "tage" not in hass.states.get("sensor.mein_spa_sonne_heute_geschatzt").attributes
    aioclient_mock.clear_requests()
    aioclient_mock.get(STAND, json=stand_beispiel(energie=None))
    await _naechster_abruf(hass)
    assert hass.states.get("sensor.mein_spa_energie_heute_geschatzt").state == STATE_UNAVAILABLE


async def test_zu_oft_nennt_wartezeit(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(STAND, json=stand_beispiel())
    aioclient_mock.post(BEFEHL, status=429, json={"ok": False, "fehler": "Zu viele Befehle in kurzer Zeit."}, headers={"Retry-After": "40"})
    assert await hass.config_entries.async_setup(eintrag.entry_id)
    await hass.async_block_till_done()
    with pytest.raises(HomeAssistantError) as fehler:
        await hass.services.async_call("light", "turn_on", {"entity_id": "light.mein_spa_licht"}, blocking=True)
    assert fehler.value.translation_key == "zu_oft_warten" and fehler.value.translation_placeholders == {"sekunden": "40"}
    assert hass.states.get("light.mein_spa_licht").state == STATE_OFF


async def test_pack_erinnerung_knopf_erst_nach_dem_lesen(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    ungelesen = {"schluessel": "pack:Filter", "titel": "Filter mit Schlauch spülen", "text": "noch nicht gelesen", "faellig": False, "vorwarnung": False,
                 "faellig_am": None, "tage_uebrig": None, "erledigen": False}
    await _einrichten(hass, eintrag, aioclient_mock, stand_beispiel(wartung={"darf": True, "aufgaben": [ungelesen]}, pflegelauf=None))
    register = er.async_get(hass)
    knopf = register.async_get_entity_id("button", DOMAIN, f"{GERAET}_wartung_pack_Filter_erledigt")
    assert knopf is not None and hass.states.get(knopf).state == STATE_UNAVAILABLE
    await hass.services.async_call("button", "press", {"entity_id": knopf}, blocking=True)
    assert _befehle(aioclient_mock) == []
    gelesen = {**ungelesen, "text": "in 25 Tagen", "faellig_am": "2026-11-24", "tage_uebrig": 25, "erledigen": True}
    neu_aufgabe = {**gelesen, "schluessel": "eigen:abdeckung", "titel": "Abdeckung pflegen"}
    aioclient_mock.clear_requests()
    aioclient_mock.get(STAND, json=stand_beispiel(wartung={"darf": True, "aufgaben": [gelesen, neu_aufgabe]}, pflegelauf=None))
    await _naechster_abruf(hass)
    assert hass.states.get(knopf).state != STATE_UNAVAILABLE and _befehle(aioclient_mock) == []
    assert register.async_get_entity_id("button", DOMAIN, f"{GERAET}_wartung_eigen_abdeckung_erledigt") is not None
    aioclient_mock.post(BEFEHL, json={"ok": True})
    await hass.services.async_call("button", "press", {"entity_id": knopf}, blocking=True)
    assert _befehle(aioclient_mock) == [{"geraet": GERAET, "was": "wartung_erledigt", "aufgabe": "pack:Filter"}]
    aioclient_mock.clear_requests()
    aioclient_mock.get(STAND, json=stand_beispiel(wartung={"darf": True, "aufgaben": [ungelesen]}, pflegelauf=None))
    await _naechster_abruf(hass, 16)
    assert hass.states.get(knopf).state == STATE_UNAVAILABLE
