from __future__ import annotations

import json
import re
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


def test_markenbild() -> None:
    for datei, kante in (("icon.png", 256), ("icon@2x.png", 512)):
        kopf = (PAKET / "brand" / datei).read_bytes()[:24]
        assert kopf[:8] == b"\x89PNG\r\n\x1a\n" and struct.unpack(">II", kopf[16:24]) == (kante, kante)

