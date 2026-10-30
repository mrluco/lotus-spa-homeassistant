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
        "darf_schalten": True,
        "modell": "Whirlpool",
        "schalter": [
            {"titel": "Pumpe 1", "name": "Pumpe 1", "art": "geraet", "modi": [{"wert": "LO", "text": "Stufe 1"}, {"wert": "HI", "text": "Stufe 2"}],
             "aktiv": "OFF", "laeuft": False, "darf": True},
            {"titel": "Pumpe 2", "name": "Pumpe 2", "art": "geraet", "modi": [{"wert": "ON", "text": "Ein"}], "aktiv": "ON", "laeuft": True,
             "darf": True},
            {"titel": "Licht", "name": "Licht", "art": "licht", "modi": [{"wert": "ON", "text": "Ein"}], "aktiv": "OFF", "laeuft": False,
             "darf": True},
        ],
        "heizmodus": {"aktiv": "standard", "modi": [{"wert": "standard", "text": "Standard"}, {"wert": "sparen", "text": "Energiesparen"}],
                      "darf": True},
        "filter_laeuft": True,
        "pflegelauf": {"laeuft": False, "zweck": "", "rest_min": 0, "dauer": 20, "dauern": [10, 20, 30, 45, 60], "bis": None,
                       "zwecke": [{"wert": "ph_plus", "text": "pH plus"}, {"wert": "ph_minus", "text": "pH minus"},
                                  {"wert": "chlor", "text": "Chlor/SWT"}, {"wert": "sonst", "text": "Sonstiges"}]},
        "badeerkennung": {"geraete": ["Pumpe 1", "Pumpe 2"], "gewaehlt": ["Pumpe 1"]},
        "zustaende": [
            {"titel": "Umwälzpumpe", "name": "Umwälzpumpe", "text": "läuft", "an": True},
            {"titel": "Ozon", "name": "Ozon", "text": "aus", "an": False},
            {"titel": "Abdeckung", "name": "Abdeckung", "text": "zu", "an": False},
            {"titel": "Solarenergie", "name": "Solarenergie", "text": "gehalten auf 38,0 · ab 15:00 mit Sonne", "an": True},
            {"titel": "Filterung", "name": "Filterung", "text": "läuft bis 11:00", "an": True},
        ],
        "meldungen": [],
        "soll_grund": "Badezeit — gehalten auf 38,0 °C.",
        "filter_bloecke": ["08:00–12:00", "20:00–22:00"],
        "filter_aktiv": "08:00–12:00",
        "naechste_badezeit": None,
        "solar": None,
        "badezeiten": None,
        "filterzeiten": None,
        "wartung": {"darf": False, "aufgaben": []},
        "wartungspause": None,
        "aussen": 12.5,
        "box": None,
        "energie": None,
        "warm_um": None,
        "volumen": None,
        "strompreis": None,
        "urlaub": None,
        "absenkung": None,
        "abendlicht": None,
    }
    konto = aenderung.pop("konto", None)
    geraet.update(aenderung)
    return {"ok": True, "zeit": int(time.time()), "geraete": {GERAET: geraet}, "konto": konto}


def mit_plan(**aenderung: Any) -> dict[str, Any]:
    plan: dict[str, Any] = {
        "naechste_badezeit": {"beginn": "2026-10-30T18:00:00+01:00", "ende": "2026-10-30T21:00:00+01:00"},
        "solar": {"modus": "aus", "modi": [{"wert": "aus", "text": "Ohne Solar"}, {"wert": "zeitplan", "text": "Zeitplan führt"},
                                           {"wert": "temperatur", "text": "Solar führt"}], "darf": True},
        "badezeiten": {"art": "gleich", "gruppen": [{"nr": 0, "name": "alle", "bloecke": [{"von": "18:00", "bis": "21:00"}]}], "darf": True},
    }
    plan.update(aenderung)
    return stand_beispiel(**plan)


def ohne_recht(stand: dict[str, Any]) -> dict[str, Any]:
    geraet = stand["geraete"][GERAET]
    geraet["darf_schalten"] = False
    geraet["darf_temperatur"] = False
    geraet["schalter"] = [dict(s_, darf=False) for s_ in geraet["schalter"]]
    geraet["heizmodus"] = dict(geraet["heizmodus"], darf=False)
    return stand


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
