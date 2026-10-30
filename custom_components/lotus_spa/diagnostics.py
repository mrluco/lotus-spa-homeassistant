from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .coordinator import LotusConfigEntry

SCHWAERZEN = {"token", "access_token", "refresh_token", "name", "id", "unique_id", "title"}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, eintrag: LotusConfigEntry) -> dict[str, Any]:
    koordinator = eintrag.runtime_data
    geraete = {f"spa_{i + 1}": async_redact_data(daten, SCHWAERZEN) for i, daten in enumerate((koordinator.data or {}).values())}
    return {
        "eintrag": async_redact_data(eintrag.as_dict(), SCHWAERZEN),
        "abo_noetig": koordinator.abo_noetig,
        "letzter_abruf_ok": koordinator.last_update_success,
        "geraete": geraete,
    }
