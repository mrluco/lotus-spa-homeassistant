from __future__ import annotations

from http import HTTPStatus
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from custom_components.lotus_spa.const import API_URL, AUTORISIEREN_URL, CLIENT_ID, DOMAIN, TOKEN_URL

from .conftest import KONTO

MY_RUECK = "https://my.home-assistant.io/redirect/oauth"
TOKEN = {"access_token": "zugriff-1", "refresh_token": "erneuern-1", "token_type": "Bearer", "expires_in": 3600}


@pytest.fixture(autouse=True)
async def anmeldung_bereit(hass: HomeAssistant) -> None:
    assert await async_setup_component(hass, "auth", {})


async def _bis_zum_token(hass: HomeAssistant, client_fabrik: ClientSessionGenerator, quelle: dict) -> tuple[str, dict]:
    result = await hass.config_entries.flow.async_init(DOMAIN, context=quelle)
    if result["type"] is FlowResultType.FORM:
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.EXTERNAL_STEP
    url = urlparse(result["url"])
    q = {k: v[0] for k, v in parse_qs(url.query).items()}
    state = config_entry_oauth2_flow._encode_jwt(hass, {"flow_id": result["flow_id"], "redirect_uri": MY_RUECK})
    client = await client_fabrik()
    antwort = await client.get(f"/auth/external/callback?code=code-1&state={state}")
    assert antwort.status == HTTPStatus.OK
    return result["flow_id"], {"url": f"{url.scheme}://{url.netloc}{url.path}", **q}


async def test_einrichten(hass: HomeAssistant, hass_client_no_auth: ClientSessionGenerator, aioclient_mock: AiohttpClientMocker,
                          current_request_with_host: None) -> None:
    flow_id, q = await _bis_zum_token(hass, hass_client_no_auth, {"source": config_entries.SOURCE_USER})
    assert q["url"] == AUTORISIEREN_URL and q["client_id"] == CLIENT_ID and q["redirect_uri"] == MY_RUECK
    assert q["code_challenge_method"] == "S256" and len(q["code_challenge"]) == 43 and q["response_type"] == "code"
    aioclient_mock.post(TOKEN_URL, json=TOKEN)
    aioclient_mock.get(f"{API_URL}/konto", json={"ok": True, "api": 1, "konto": KONTO, "geraete": [], "abfrage_s": 60})
    with patch("custom_components.lotus_spa.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(flow_id)
    assert result["type"] is FlowResultType.CREATE_ENTRY and result["result"].unique_id == KONTO
    assert result["data"]["token"]["refresh_token"] == "erneuern-1" and "password" not in str(result["data"])
    token_anfrage = next(c_ for c_ in aioclient_mock.mock_calls if str(c_[1]) == TOKEN_URL)
    assert token_anfrage[2]["grant_type"] == "authorization_code" and token_anfrage[2]["redirect_uri"] == MY_RUECK
    assert len(token_anfrage[2]["code_verifier"]) >= 43


async def test_ohne_abo_kein_eintrag(hass: HomeAssistant, hass_client_no_auth: ClientSessionGenerator, aioclient_mock: AiohttpClientMocker,
                                     current_request_with_host: None) -> None:
    flow_id, _ = await _bis_zum_token(hass, hass_client_no_auth, {"source": config_entries.SOURCE_USER})
    aioclient_mock.post(TOKEN_URL, json=TOKEN)
    aioclient_mock.get(f"{API_URL}/konto", status=402, json={"ok": False, "zugang": "abo_noetig", "text": "Home Assistant gehört zum Abo."})
    result = await hass.config_entries.flow.async_configure(flow_id)
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "abo_noetig"
    assert not hass.config_entries.async_entries(DOMAIN)


async def test_konto_nur_einmal(hass: HomeAssistant, hass_client_no_auth: ClientSessionGenerator, aioclient_mock: AiohttpClientMocker,
                                current_request_with_host: None, eintrag: MockConfigEntry) -> None:
    flow_id, _ = await _bis_zum_token(hass, hass_client_no_auth, {"source": config_entries.SOURCE_USER})
    aioclient_mock.post(TOKEN_URL, json=TOKEN)
    aioclient_mock.get(f"{API_URL}/konto", json={"ok": True, "konto": KONTO, "geraete": []})
    result = await hass.config_entries.flow.async_configure(flow_id)
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "already_configured"
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1


async def test_neuanmeldung(hass: HomeAssistant, hass_client_no_auth: ClientSessionGenerator, aioclient_mock: AiohttpClientMocker,
                            current_request_with_host: None, eintrag: MockConfigEntry) -> None:
    flow_id, _ = await _bis_zum_token(hass, hass_client_no_auth, {"source": config_entries.SOURCE_REAUTH, "entry_id": eintrag.entry_id})
    aioclient_mock.post(TOKEN_URL, json={**TOKEN, "access_token": "zugriff-2", "refresh_token": "erneuern-2"})
    aioclient_mock.get(f"{API_URL}/konto", json={"ok": True, "konto": KONTO, "geraete": []})
    with patch("custom_components.lotus_spa.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(flow_id)
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "reauth_successful"
    assert eintrag.data["token"]["refresh_token"] == "erneuern-2"


async def test_neuanmeldung_anderes_konto(hass: HomeAssistant, hass_client_no_auth: ClientSessionGenerator, aioclient_mock: AiohttpClientMocker,
                                          current_request_with_host: None, eintrag: MockConfigEntry) -> None:
    flow_id, _ = await _bis_zum_token(hass, hass_client_no_auth, {"source": config_entries.SOURCE_REAUTH, "entry_id": eintrag.entry_id})
    aioclient_mock.post(TOKEN_URL, json={**TOKEN, "refresh_token": "fremd"})
    aioclient_mock.get(f"{API_URL}/konto", json={"ok": True, "konto": "ffffffffffffffff", "geraete": []})
    result = await hass.config_entries.flow.async_configure(flow_id)
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "anderes_konto"
    assert eintrag.data["token"]["refresh_token"] == "erneuern-1"
