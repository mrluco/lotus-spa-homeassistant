from __future__ import annotations

from typing import Any

AUS = "OFF"


def schalter_liste(daten: dict[str, Any]) -> list[dict[str, Any]]:
    return [s_ for s_ in (daten.get("schalter") or []) if isinstance(s_, dict) and s_.get("titel")]


def stufen(schalter: dict[str, Any]) -> list[dict[str, str]]:
    return [m_ for m_ in (schalter.get("modi") or []) if isinstance(m_, dict) and str(m_.get("wert") or "").upper() != AUS]


def art(schalter: dict[str, Any]) -> str:
    if schalter.get("art") == "licht":
        return "licht"
    return "luefter" if len(stufen(schalter)) > 1 else "schalter"


def ist_an(schalter: dict[str, Any]) -> bool:
    return str(schalter.get("aktiv") or AUS).upper() != AUS


def darf(schalter: dict[str, Any]) -> bool:
    return bool(schalter.get("darf"))


def stufe_text(schalter: dict[str, Any]) -> str | None:
    aktiv = str(schalter.get("aktiv") or AUS).upper()
    return next((str(m_.get("text") or m_.get("wert")) for m_ in stufen(schalter) if str(m_.get("wert")).upper() == aktiv), None)


def symbol(schalter: dict[str, Any]) -> str:
    titel = str(schalter.get("titel") or "").lower()
    if schalter.get("art") == "licht" or titel.startswith("licht"):
        return "licht"
    if titel.startswith(("blower", "gebläse", "luftsprudel")):
        return "blower"
    if titel.startswith("umwälz"):
        return "umwaelzpumpe"
    if titel.startswith("wasserfall"):
        return "wasserfall"
    if titel.startswith("pumpe"):
        return "pumpe"
    return "schalter"


def erste_stufe(schalter: dict[str, Any]) -> str:
    s_ = stufen(schalter)
    return str(s_[0]["wert"]) if s_ else "ON"


def heizmodi(daten: dict[str, Any]) -> list[dict[str, str]]:
    heizmodus = daten.get("heizmodus") or {}
    return [m_ for m_ in (heizmodus.get("modi") or []) if isinstance(m_, dict)] if heizmodus.get("darf") else []


def heizmodus_text(modus: dict[str, str]) -> str:
    return str(modus.get("text") or modus.get("wert"))


def heizmodus_aktiv(daten: dict[str, Any]) -> str | None:
    aktiv = str((daten.get("heizmodus") or {}).get("aktiv") or "")
    return next((heizmodus_text(m_) for m_ in heizmodi(daten) if str(m_.get("wert")) == aktiv), None)


def heizmodus_wert(daten: dict[str, Any], text: str) -> str | None:
    return next((str(m_["wert"]) for m_ in heizmodi(daten) if heizmodus_text(m_) == text), None)


def wp_modi(daten: dict[str, Any], bekannt: tuple[str, ...]) -> list[str]:
    stand = daten.get("waermepumpe") or {}
    return [str(m_.get("wert") or "").lower() for m_ in (stand.get("modi") or []) if isinstance(m_, dict) and str(m_.get("wert") or "").lower() in bekannt]


def wp_modus(daten: dict[str, Any], bekannt: tuple[str, ...]) -> str | None:
    aktiv = str((daten.get("waermepumpe") or {}).get("aktiv") or "").lower()
    return aktiv if aktiv in bekannt else None


def betriebsarten(daten: dict[str, Any]) -> list[dict[str, str]]:
    betriebsart = daten.get("betriebsart") or {}
    return [m_ for m_ in (betriebsart.get("modi") or []) if isinstance(m_, dict)] if betriebsart.get("darf") else []


def voreinstellung(daten: dict[str, Any]) -> tuple[str, str, list[dict[str, str]]]:
    if heizmodi(daten):
        return "heizmodus", "heizmodus", heizmodi(daten)
    return "betriebsart", "betriebsart", betriebsarten(daten)


def voreinstellung_aktiv(daten: dict[str, Any]) -> str | None:
    feld, _, modi = voreinstellung(daten)
    aktiv = str((daten.get(feld) or {}).get("aktiv") or "")
    return next((heizmodus_text(m_) for m_ in modi if str(m_.get("wert")) == aktiv), None)


def voreinstellung_wert(daten: dict[str, Any], text: str) -> tuple[str, str | None]:
    _, befehl, modi = voreinstellung(daten)
    return befehl, next((str(m_["wert"]) for m_ in modi if heizmodus_text(m_) == text), None)



def c8z(daten: dict[str, Any]) -> dict[str, Any]:
    wert = daten.get("clim8zone")
    return wert if isinstance(wert, dict) else {}


def c8z_wahl(daten: dict[str, Any], was: str) -> dict[str, Any]:
    wert = c8z(daten).get(was)
    return wert if isinstance(wert, dict) else {}


def c8z_optionen(daten: dict[str, Any], was: str, bekannt: tuple[str, ...]) -> list[str]:
    return [str(m_.get("wert")) for m_ in (c8z_wahl(daten, was).get("modi") or []) if isinstance(m_, dict) and str(m_.get("wert")) in bekannt]


def c8z_aktiv(daten: dict[str, Any], was: str, bekannt: tuple[str, ...]) -> str | None:
    aktiv = str(c8z_wahl(daten, was).get("aktiv") or "")
    return aktiv if aktiv in c8z_optionen(daten, was, bekannt) else None
