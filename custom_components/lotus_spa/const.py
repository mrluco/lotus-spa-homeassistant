from datetime import timedelta
from typing import Final

DOMAIN: Final = "lotus_spa"

BASIS_URL: Final = "https://app.lotusswimspa.de"
AUTORISIEREN_URL: Final = f"{BASIS_URL}/oauth/autorisieren"
TOKEN_URL: Final = f"{BASIS_URL}/oauth/token"
API_URL: Final = f"{BASIS_URL}/api/ha/v1"
ABO_URL: Final = f"{BASIS_URL}/abo"
CLIENT_ID: Final = "lotus-spa-homeassistant"

ABFRAGE: Final = timedelta(seconds=60)
ABFRAGE_OHNE_ABO: Final = timedelta(minutes=15)

HINWEIS_ABO: Final = "abo_noetig"

PFLEGELAUF_AUS: Final = "aus"
