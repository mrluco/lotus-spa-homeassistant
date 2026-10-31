<p align="center"><img src="https://raw.githubusercontent.com/mrluco/lotus-spa-homeassistant/main/bilder/logo.png" alt="Lotus" width="120"></p>

<h1 align="center">Lotus Spa für Home Assistant</h1>

<p align="center">Dein Spa aus der Lotus-App in Home Assistant, mit denselben Rechten wie in der App.</p>

<p align="center">
<a href="https://hacs.xyz"><img src="https://img.shields.io/badge/HACS-Custom-41BDF5.svg" alt="HACS Custom"></a>
<a href="https://github.com/mrluco/lotus-spa-homeassistant/releases"><img src="https://img.shields.io/github/v/release/mrluco/lotus-spa-homeassistant" alt="Release"></a>
<a href="LICENSE"><img src="https://img.shields.io/github/license/mrluco/lotus-spa-homeassistant" alt="Lizenz"></a>
</p>

<p align="center">
<a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=mrluco&repository=lotus-spa-homeassistant&category=integration"><img src="https://my.home-assistant.io/badges/hacs_repository.svg" alt="Open your Home Assistant instance and open a repository inside the Home Assistant Community Store."></a>
<a href="https://my.home-assistant.io/redirect/config_flow_start/?domain=lotus_spa"><img src="https://my.home-assistant.io/badges/config_flow_start.svg" alt="Open your Home Assistant instance and start setting up a new integration."></a>
</p>

<p align="center"><b>Deutsch</b> · <a href="README.en.md">English</a></p>

| | | | |
|:---:|:---:|:---:|:---:|
| <img src="https://raw.githubusercontent.com/mrluco/lotus-spa-homeassistant/main/bilder/ha-geraet.png" width="200" alt="Gerät"> | <img src="https://raw.githubusercontent.com/mrluco/lotus-spa-homeassistant/main/bilder/ha-steuerung.png" width="200" alt="Steuerung"> | <img src="https://raw.githubusercontent.com/mrluco/lotus-spa-homeassistant/main/bilder/ha-wartung.png" width="200" alt="Wartung und Pläne"> | <img src="https://raw.githubusercontent.com/mrluco/lotus-spa-homeassistant/main/bilder/ha-energie.png" width="200" alt="Energie und Konto"> |
| Gerät | Steuerung | Wartung und Pläne | Energie und Konto |

## Was du bekommst

- **Bedienen:** Wunschtemperatur, Heizmodus, Pumpen, Blower und Licht, Urlaubsmodus, Absenkung und Abendlicht. Eine Pumpe mit zwei Stufen bietet „Niedrig“ und „Hoch“.
- **Sehen:** Wassertemperatur, Außentemperatur, Filterung, Meldungen mit dem Text aus der App, „Warm um“ beim Aufheizen.
- **Planen:** Badezeiten, Filterzeiten und Solar-Betriebsart. Eine Änderung in Home Assistant ist dieselbe wie in der App.
- **Pflegen:** Pflegelauf mit Dauer, Wartungspause, Wartungsaufgaben mit Termin und Knopf „erledigt“.
- **Verbrauch:** Energie für das Energie-Dashboard, Leistung und Kosten von heute. Beckeninhalt und Strompreis kannst du hier ändern.
- **Lotus Box und Konto:** Verbindung und WLAN-Empfang der Box, dein Abo und bis wann es gilt.

Schalten kannst du nur, was du auch in der App schalten darfst. Jeder Befehl steht im Protokoll deiner Anlage mit „Home Assistant“.

<details>
<summary>Alle Entitäten im Einzelnen</summary>

| Entität | Was sie zeigt oder tut |
|---|---|
| Thermostat (heißt wie dein Spa) | Wassertemperatur, Wunschtemperatur, ob gerade geheizt wird |
| Pumpen und Blower | an und aus; eine Pumpe mit zwei Stufen bietet „Niedrig“ und „Hoch“ an (Einschalten = erste Stufe) |
| Licht | an und aus |
| Heizmodus | die Modi deiner Steuerung, wie in der App; auch am Thermostat als Voreinstellung |
| Pflegelauf | starten (pH plus, pH minus, Chlor/SWT, Sonstiges) und beenden; dazu „Pflegelauf Dauer“ für den nächsten Lauf und „Pflegelauf endet“ |
| Wartungspause | anhalten und wieder starten wie in der App, mit „Wartungspause endet“; bei Frostgefahr startet sie nicht, der Frostschutz hat Vorrang |
| Urlaubsmodus, Urlaubstemperatur | ein- und ausschalten und die Temperatur im Urlaub, wie die Kachel der App |
| Absenkung | Aus, An oder Automatisch und um wie viel Grad; im Urlaub gilt die Urlaubstemperatur |
| Abendlicht | Licht geht bei einem Bad nach Sonnenuntergang von selbst an, wenn dein Spa Licht hat |
| Badeerkennung | welche Geräte als „Baden“ zählen |
| Filterung | ob die Filterung gerade läuft, dazu der Satz aus der App |
| Verbindung | ob dein Spa mit Lotus verbunden ist |
| Wassertemperatur, Solltemperatur | als Sensoren, auch für Verlauf und Statistik |
| Heizung, Umwälzpumpe, Ozon, Feinspülung, Abdeckung, Sparmodus, Frostschutz, Urlaubsmodus | Zustand wie in der App, soweit deine Steuerung ihn meldet |
| Solarenergie, Absenkung | der Satz aus der App |
| Meldung, Meldungstext | ob dein Spa gerade etwas meldet, mit demselben Text wie in der App („Keine Meldung“, wenn alles in Ordnung ist) |
| Badezeiten | Beginn und Ende deiner Badezeiten, änderbar wie in der App |
| Nächste Badezeit | Beginn und Ende der laufenden oder nächsten Badezeit |
| Solar-Betriebsart | wie in der App, zum Beispiel „Solar führt“ |
| Grund der Solltemperatur | derselbe Satz wie in der App, zum Beispiel „Badezeit, gehalten auf 38,0 °C“ |
| Filterblock | der laufende Filterblock, dazu die Filterläufe von heute |
| Filterzeiten | Beginn und Ende je Filterlauf; eine Änderung übernimmt Lotus zum nächsten Beginn, nie sofort. Solange „Solar führt“, nur zum Ansehen |
| Wartung | je Aufgabe aus der App: nächster Termin, ob sie fällig ist, und ein Knopf „erledigt“; ruht eine Erinnerung deiner Steuerung (zum Beispiel bei chlorfreier Pflege), steht das mit dem Grund dabei; hat deine Steuerung ihre Erinnerungen noch nicht gemeldet, steht dort, was du tun kannst |
| Außentemperatur | der Wert aus der App (Deutscher Wetterdienst) |
| Warm um | wann dein Wasser warm ist, solange geheizt wird |
| Energie, Leistung, Kosten heute | wie die Verbrauchsseite der App: Energie dieses Jahres für das Energie-Dashboard, Leistung jetzt, Kosten heute (geschätzt, wenn deine Steuerung nicht misst) |
| Beckeninhalt, Strompreis | ansehen und ändern wie in der App; eine Änderung gilt auch dort |
| Lotus Box | nur wenn dein Spa über eine Lotus Box verbunden ist: Verbindung und WLAN-Empfang, dazu WLAN-Name und Signal, soweit du sie in der App siehst |
| Energie, Sonne und Netz heute, Sonnenanteil, Kosten und Sonne dieses Jahr | wie die Verbrauchsseite der App, geschätzt |
| Lotus Konto | dein Abo und bis wann es gilt (bei einem Abo ohne Ende entfällt das Datum) |

Badezeiten, Filterzeiten und Betriebsart ändert Home Assistant höchstens viermal am Tag, in der App jederzeit. Aufgaben anlegen oder löschen geht in der App. Was du in der App nur ansehen kannst, erscheint in Home Assistant als Anzeige.

</details>

## Voraussetzungen

- ein Lotus-Konto mit gültigem Abo
- Home Assistant 2026.10 oder neuer
- „My Home Assistant“ ist eingeschaltet (Standard). Die Anmeldung kehrt darüber zu deinem Home Assistant zurück.

## Installation

Mit den beiden Knöpfen oben:

1. Der erste Knopf öffnet das Repository in HACS. Auf „Herunterladen“ tippen, dann Home Assistant neu starten.
2. Der zweite Knopf startet die Einrichtung. Auf der Lotus-Seite anmelden wie in der App und auf „Verbinden“ tippen.

Ohne Knöpfe:

1. HACS öffnen › „Benutzerdefinierte Repositories“ › diese Adresse eintragen, Typ „Integration“.
2. „Lotus Spa“ installieren und Home Assistant neu starten.
3. Einstellungen › Geräte & Dienste › „Integration hinzufügen“ › „Lotus Spa“.
4. Die Lotus-Anmeldeseite öffnet sich. Melde dich an wie in der App und tippe auf „Verbinden“.
5. Jeder Spa deines Kontos erscheint als eigenes Gerät.

Die Knöpfe findest du auch in der Lotus-App unter Konto › Home Assistant.

## Abo

Home Assistant gehört zum Lotus-Abo. Endet das Abo, zeigt Home Assistant deinen Spa als „nicht verfügbar“, und deine Automationen schalten in dieser Zeit nichts. Kurz vor dem Ablauf und bei einer offenen Zahlung steht ein Hinweis unter Einstellungen › Reparaturen. Mit einem gültigen Abo geht es sofort weiter.

Trennen kannst du die Verbindung jederzeit in der Lotus-App unter Konto › Home Assistant. Eine Verbindung, die 90 Tage nicht genutzt wird, löst Lotus von selbst.

## Datenschutz

Home Assistant speichert kein Passwort, nur einen Schlüssel, den Lotus ausstellt und den du jederzeit widerrufen kannst. Übertragen werden nur die Werte und Befehle deiner eigenen Anlagen, auf Abruf deines Home Assistant: einmal pro Minute und kurz nach einem Befehl.

## Die Lotus-App

| | | |
|:---:|:---:|:---:|
| <img src="https://raw.githubusercontent.com/mrluco/lotus-spa-homeassistant/main/bilder/bedienung.png" width="160" alt="Bedienung"> | <img src="https://raw.githubusercontent.com/mrluco/lotus-spa-homeassistant/main/bilder/heizen.png" width="160" alt="Heizen"> | <img src="https://raw.githubusercontent.com/mrluco/lotus-spa-homeassistant/main/bilder/verbrauch.png" width="160" alt="Verbrauch"> |
| Bedienung | Heizen | Verbrauch |

Musteranlage, Werte simuliert. [Live-Demo ansehen](https://app.lotusswimspa.de/demo)

## Hilfe

Fehler in der Integration meldest du hier unter [Issues](https://github.com/mrluco/lotus-spa-homeassistant/issues). Fragen zu deinem Spa und deinem Abo beantwortet dein Lotus-Fachhändler.
