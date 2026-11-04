from __future__ import annotations

import json
import re
import string
import struct
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
PAKET = WURZEL / "custom_components" / "lotus_spa"


def _schluessel(d: dict, vorne: str = "") -> set[str]:
    raus = set()
    for k_, v_ in d.items():
        raus |= _schluessel(v_, f"{vorne}{k_}.") if isinstance(v_, dict) else {f"{vorne}{k_}"}
    return raus


def test_manifest() -> None:
    m = json.loads((PAKET / "manifest.json").read_text(encoding="utf-8"))
    assert m["domain"] == PAKET.name == "lotus_spa" and m["name"] == "Lotus Spa"
    assert list(m)[:2] == ["domain", "name"] and list(m)[2:] == sorted(list(m)[2:])
    assert m["config_flow"] is True and m["iot_class"] == "cloud_polling" and m["integration_type"] == "hub"
    assert "my" in m["dependencies"] and m["version"] and m["codeowners"] and m["documentation"].startswith("https://") and m["issue_tracker"].startswith("https://")
    assert m["requirements"] == []
    kategorien = m.get("categories") or []
    assert kategorien == ["water.pools_spas"] and 1 <= len(kategorien) <= 3 and len(set(kategorien)) == len(kategorien)
    assert all(re.fullmatch(r"[a-z0-9_]+(\.[a-z0-9_]+)?", k_) for k_ in kategorien)


def test_hacs() -> None:
    h = json.loads((WURZEL / "hacs.json").read_text(encoding="utf-8"))
    assert h["name"] == "Lotus Spa" and "content_in_root" not in h
    assert (WURZEL / "LICENSE").read_text(encoding="utf-8").startswith("MIT License") and (WURZEL / "README.md").exists()


def test_uebersetzungen_gleich() -> None:
    de = json.loads((PAKET / "translations" / "de.json").read_text(encoding="utf-8"))
    en = json.loads((PAKET / "translations" / "en.json").read_text(encoding="utf-8"))
    assert _schluessel(de) == _schluessel(en)
    text = json.dumps(de, ensure_ascii=False) + json.dumps(en, ensure_ascii=False)
    assert not any(ord(z_) > 0x2FFF for z_ in text)


URL = re.compile(r"(((ftp|ftps|scp|http|https|mqtt|mqtts|socket|socks5)://|www\.)[a-z0-9]+([\-.][a-z0-9]+)*\.[a-z]{2,5}(:[0-9]{1,5})?(/.*)?)", re.IGNORECASE)
SCHLUESSEL = re.compile(r"^(?!.+[_-]{2})(?![_-])[a-z0-9-_]+(?<![_-])$")


def _texte(d: dict, vorne: str = "") -> list[tuple[str, str]]:
    raus = []
    for k_, v_ in d.items():
        raus += _texte(v_, f"{vorne}{k_}.") if isinstance(v_, dict) else [(f"{vorne}{k_}", v_)]
    return raus


def test_uebersetzungen_wie_hassfest() -> None:
    assert URL.search("Zum Abo: https://app.lotusswimspa.de/abo") and not URL.search("Zum Abo: {abo_url}")
    for sprache in ("de", "en"):
        daten = json.loads((PAKET / "translations" / f"{sprache}.json").read_text(encoding="utf-8"))
        for pfad, text in _texte(daten):
            assert isinstance(text, str) and text == text.strip(), (sprache, pfad)
            assert not URL.search(text), (sprache, pfad)
            assert not re.search(r"<[a-z/!]", text, re.IGNORECASE), (sprache, pfad)
            assert not re.search(r"'\{\w+\}'", text), (sprache, pfad)
            assert all(feld_.isidentifier() for _, feld_, _, _ in string.Formatter().parse(text) if feld_), (sprache, pfad)
        for pfad, text in _texte({k_: daten.get(k_) or {} for k_ in ("config", "options")}):
            if not pfad.startswith("config.abort."):
                assert not re.search(r"\{\w*_url\}|demo", text, re.IGNORECASE), (sprache, pfad)
        assert "{abo_url}" in daten["config"]["abort"]["abo_noetig"], sprache
        for pfad, _ in _texte(daten.get("entity") or {}):
            assert all(SCHLUESSEL.match(t_) for t_ in pfad.split(".")[1:-1] if t_ not in ("state", "state_attributes", "name")), (sprache, pfad)


def test_reparaturhinweis_sachlich() -> None:
    for sprache in ("de", "en"):
        daten = json.loads((PAKET / "translations" / f"{sprache}.json").read_text(encoding="utf-8"))
        issues = daten["issues"]
        assert "abo_funktionen" not in json.dumps(daten), sprache
        assert "{funktionen}" in issues["abo_noetig_funktionen"]["description"] and "{funktionen}" not in issues["abo_noetig"]["description"], sprache
        assert issues["abo_noetig_funktionen"]["title"] == issues["abo_noetig"]["title"]
        assert issues["abo_noetig_funktionen"]["description"].startswith(issues["abo_noetig"]["description"]), sprache
        for k_ in ("abo_noetig", "abo_noetig_funktionen", "kein_recht"):
            text = issues[k_]["title"] + " " + issues[k_]["description"]
            assert "!" not in text and "€" not in text and not re.search(r"(?i)\b(mehr|more|jetzt|now|exklusiv|exclusive)\b", text), (sprache, k_)
        for pfad, text in _texte({k_: daten.get(k_) or {} for k_ in ("config", "options")}):
            if "reauth" in pfad or not pfad.startswith("config.abort."):
                assert not URL.search(text) and not re.search(r"\{\w*_url\}", text), (sprache, pfad)


def test_kosten_geschaetzt() -> None:
    de = json.loads((PAKET / "translations" / "de.json").read_text(encoding="utf-8"))["entity"]["sensor"]
    en = json.loads((PAKET / "translations" / "en.json").read_text(encoding="utf-8"))["entity"]["sensor"]
    assert de["kosten_heute"]["name"] == "Kosten heute (geschätzt)" and de["kosten_jahr"]["name"] == "Kosten dieses Jahr (geschätzt)"
    assert en["kosten_heute"]["name"] == "Cost today (estimated)" and en["kosten_jahr"]["name"] == "Cost this year (estimated)"
    for sprache_, daten_, wort_ in (("de", de, "geschätzt"), ("en", en, "estimated")):
        for schluessel_, eintrag_ in daten_.items():
            if schluessel_.startswith("kosten"):
                assert wort_ in eintrag_["name"], (sprache_, schluessel_)


def test_markenbild() -> None:
    for datei, kante in (("icon.png", 256), ("icon@2x.png", 512)):
        kopf = (PAKET / "brand" / datei).read_bytes()[:24]
        assert kopf[:8] == b"\x89PNG\r\n\x1a\n" and struct.unpack(">II", kopf[16:24]) == (kante, kante)

