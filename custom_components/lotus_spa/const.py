from datetime import timedelta
from typing import Final

from yarl import URL

DOMAIN: Final = "lotus_spa"

BASIS_URL: Final = "https://app.lotusswimspa.de"
AUTORISIEREN_URL: Final = f"{BASIS_URL}/oauth/autorisieren"
TOKEN_URL: Final = f"{BASIS_URL}/oauth/token"
API_URL: Final = f"{BASIS_URL}/api/ha/v1"
ABO_URL: Final = f"{BASIS_URL}/abo"
DEMO_URL: Final = f"{BASIS_URL}/demo"
KOPF_FASSUNG: Final = "X-Lotus-Integration"
CLIENT_ID: Final = "lotus-spa-homeassistant"

ABFRAGE: Final = timedelta(seconds=60)
ABFRAGE_OHNE_ABO: Final = timedelta(minutes=15)

HINWEIS_ABO: Final = "abo_noetig"

PFLEGELAUF_AUS: Final = "aus"

VERSION: Final = "0.3.3"
HERSTELLER: Final = "Lotus"

LESEN_AN_AUS: Final = {
    "Umwälzpumpe": "umwaelzpumpe",
    "Ozon": "ozon",
    "Feinspülung": "feinspuelung",
    "Abdeckung": "abdeckung",
    "Sparmodus der Steuerung": "sparmodus",
    "Frostschutz": "frostschutz",
    "Urlaubsmodus": "urlaubsmodus",
}
SOLAR_MODI: Final = ("aus", "beobachten", "zeitplan", "temperatur")
TAGE_GRUPPEN: Final = {
    "de": {"alle": "Mo–So", "werktags": "Mo–Fr", "wochenende": "Sa–So", "mo": "Mo", "di": "Di", "mi": "Mi", "do": "Do", "fr": "Fr", "sa": "Sa", "so": "So"},
    "en": {"alle": "Mon–Sun", "werktags": "Mon–Fri", "wochenende": "Sat–Sun", "mo": "Mon", "di": "Tue", "mi": "Wed", "do": "Thu", "fr": "Fri", "sa": "Sat",
           "so": "Sun"},
}
KEINE_MELDUNG: Final = "Keine Meldung"
KONTO_URL: Final = str(URL(BASIS_URL).with_path("/konto").with_fragment("kontoabo"))
HINWEIS_ABLAUF: Final = "abo_ablauf"
HINWEIS_ZAHLUNG: Final = "zahlung"
HINWEIS_FUNKTIONEN: Final = "abo_funktionen"
NACHLESEN_S: Final = (2.0, 3.0, 5.0)
ABO_FUNKTIONEN: Final = {
    "de": {"urlaub": "Urlaubsmodus", "absenkung": "Absenkung", "warm_um": "Warm um", "wartungspause": "Wartungspause", "badezeiten": "Badezeiten",
           "filterung": "Filterzeiten", "solar": "Heizen mit der Sonne", "verbrauch": "Energie und Kosten"},
    "en": {"urlaub": "vacation mode", "absenkung": "setback", "warm_um": "warm at", "wartungspause": "maintenance pause", "badezeiten": "bathing times",
           "filterung": "filter times", "solar": "heating with the sun", "verbrauch": "energy and cost"},
}
ABO_ARTEN: Final = ("abo", "abo_unbefristet", "ohne_abo")
EMPFANG: Final = {"sehr gut": "sehr_gut", "gut": "gut", "schwach": "schwach", "sehr schwach": "sehr_schwach"}
WETTER_QUELLE: Final = "Deutscher Wetterdienst"
ALT_FILTERUNG: Final = "text_filterung"
LESEN_TEXT: Final = {
    "Solarenergie": "solarenergie",
    "Absenkung": "absenkung",
}
