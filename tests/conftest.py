from __future__ import annotations

import time
from typing import Any

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.lotus_spa.const import DOMAIN

GERAET = "musterspa/spa1"
KONTO = "a1b2c3d4e5f6a7b8"


@pytest.fixture(autouse=True)
def freigeben(enable_custom_integrations: None, hass: HomeAssistant) -> None:
    hass.config.components.add("my")
    hass.config.language = "de"


def stand_beispiel(**aenderung: Any) -> dict[str, Any]:
    geraet: dict[str, Any] = {
        "id": GERAET,
        "name": "Mein Spa",
        "verbunden": True,
        "ist": 37.5,
        "soll": 38.0,
        "heizt": True,
        "soll_bereich": [10.0, 40.0],
        "darf_temperatur": True,
        "schalter": [
            {"titel": "Pumpe 1", "name": "Pumpe 1", "art": "geraet", "modi": [{"wert": "LO", "text": "Stufe 1"}, {"wert": "HI", "text": "Stufe 2"}],
             "aktiv": "OFF", "laeuft": False},
            {"titel": "Pumpe 2", "name": "Pumpe 2", "art": "geraet", "modi": [{"wert": "ON", "text": "Ein"}], "aktiv": "ON", "laeuft": True},
            {"titel": "Licht", "name": "Licht", "art": "licht", "modi": [{"wert": "ON", "text": "Ein"}], "aktiv": "OFF", "laeuft": False},
        ],
        "heizmodus": {"aktiv": "standard", "modi": [{"wert": "standard", "text": "Standard"}, {"wert": "sparen", "text": "Energiesparen"}]},
        "filter_laeuft": True,
        "pflegelauf": {"laeuft": False, "zweck": "", "rest_min": 0,
                       "zwecke": [{"wert": "ph_plus", "text": "pH plus"}, {"wert": "ph_minus", "text": "pH minus"},
                                  {"wert": "chlor", "text": "Chlor/SWT"}, {"wert": "sonst", "text": "Sonstiges"}]},
        "badeerkennung": {"geraete": ["Pumpe 1", "Pumpe 2"], "gewaehlt": ["Pumpe 1"]},
    }
    geraet.update(aenderung)
    return {"ok": True, "zeit": int(time.time()), "geraete": {GERAET: geraet}}


@pytest.fixture
def eintrag(hass: HomeAssistant) -> MockConfigEntry:
    e = MockConfigEntry(
        domain=DOMAIN,
        title="Lotus Spa",
        unique_id=KONTO,
        data={"auth_implementation": DOMAIN,
              "token": {"access_token": "zugriff-1", "refresh_token": "erneuern-1", "token_type": "Bearer",
                        "expires_in": 3600, "expires_at": time.time() + 3600}},
    )
    e.add_to_hass(hass)
    return e
