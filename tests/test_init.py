from __future__ import annotations

import json
from datetime import timedelta

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import issue_registry as ir
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.lotus_spa.const import API_URL, DOMAIN, HINWEIS_ABO
from custom_components.lotus_spa.diagnostics import async_get_config_entry_diagnostics

from .conftest import GERAET, stand_beispiel

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
    assert hass.states.get("binary_sensor.mein_spa_filter").state == STATE_ON
    assert hass.states.get("binary_sensor.mein_spa_verbindung").state == STATE_ON
    assert hass.states.get("switch.mein_spa_badeerkennung_pumpe_1").state == STATE_ON
    assert hass.states.get("switch.mein_spa_badeerkennung_pumpe_2").state == STATE_OFF
    alle = {s_.entity_id for s_ in hass.states.async_all()}
    assert alle == {
        "climate.mein_spa", "fan.mein_spa_pumpe_1", "switch.mein_spa_pumpe_2", "light.mein_spa_licht", "select.mein_spa_heizmodus",
        "select.mein_spa_pflegelauf", "binary_sensor.mein_spa_filter", "binary_sensor.mein_spa_verbindung",
        "switch.mein_spa_badeerkennung_pumpe_1", "switch.mein_spa_badeerkennung_pumpe_2",
    }
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
    await _einrichten(hass, eintrag, aioclient_mock, stand_beispiel(darf_temperatur=False))
    assert hass.states.get("climate.mein_spa").attributes["supported_features"] == 0
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call("climate", "set_temperature", {"entity_id": "climate.mein_spa", "temperature": 36}, blocking=True)
    assert _befehle(aioclient_mock) == []


async def test_ohne_schaltrecht_keine_schalter(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    await _einrichten(hass, eintrag, aioclient_mock, stand_beispiel(schalter=[], heizmodus=None, pflegelauf=None, badeerkennung=None))
    alle = {s_.entity_id for s_ in hass.states.async_all()}
    assert "climate.mein_spa" in alle and "binary_sensor.mein_spa_verbindung" in alle
    assert not any(e_.split(".")[0] in ("fan", "switch", "light", "select") for e_ in alle), alle


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
    assert fehler.value.translation_key == "zu_oft"


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
