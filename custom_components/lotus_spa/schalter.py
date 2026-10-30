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


def erste_stufe(schalter: dict[str, Any]) -> str:
    s_ = stufen(schalter)
    return str(s_[0]["wert"]) if s_ else "ON"
