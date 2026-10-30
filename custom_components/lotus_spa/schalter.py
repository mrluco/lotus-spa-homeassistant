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

