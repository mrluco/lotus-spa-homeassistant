# Lotus Spa für Home Assistant

Verbinde deinen Spa aus der Lotus-App mit Home Assistant. Dort siehst du die Wassertemperatur, stellst die Wunschtemperatur ein und schaltest Pumpen und Licht, mit denselben Rechten wie in der App.

## Voraussetzungen

- ein Lotus-Konto mit gültigem Abo (ein laufender Testzugang zählt dazu)
- Home Assistant 2026.10 oder neuer
- „My Home Assistant“ ist eingeschaltet (Standard). Die Anmeldung kehrt über my.home-assistant.io zu deinem Home Assistant zurück.

## Installation über HACS

1. HACS öffnen › „Benutzerdefinierte Repositories“ › diese Adresse eintragen, Typ „Integration“.
2. „Lotus Spa“ installieren und Home Assistant neu starten.
3. Einstellungen › Geräte & Dienste › „Integration hinzufügen“ › „Lotus Spa“.
4. Die Lotus-Anmeldeseite öffnet sich. Melde dich an wie in der App und tippe auf „Verbinden“.
5. Fertig: Jeder Spa deines Kontos erscheint als eigenes Gerät.

## Was du in Home Assistant bekommst

| Entität | Was sie zeigt oder tut |
|---|---|
| Thermostat (heißt wie dein Spa) | Wassertemperatur, Wunschtemperatur, ob gerade geheizt wird |
| Pumpen und Blower | an und aus, bei mehreren Stufen mit Stufenwahl |
| Licht | an und aus |
| Heizmodus | die Modi deiner Steuerung, wie in der App |
| Pflegelauf | starten (pH plus, pH minus, Chlor/SWT, Sonstiges) und beenden |
| Badeerkennung | welche Geräte als „Baden“ zählen |
| Filter | ob die Filterung gerade läuft |
| Verbindung | ob dein Spa mit Lotus verbunden ist |

Du siehst nur, was du auch in der App bedienen darfst. Jeder Befehl steht im Protokoll deiner Anlage mit „Home Assistant“.

## Wenn das Abo endet

Home Assistant zeigt deinen Spa dann als „nicht verfügbar“, und deine Automationen schalten in dieser Zeit nichts. Unter Einstellungen › Reparaturen steht ein Hinweis mit dem Weg zum Abo. Mit einem gültigen Abo geht es sofort weiter, der Hinweis verschwindet von selbst.

## Verbindung trennen

In der Lotus-App unter Konto › Home Assistant › „Trennen“. Home Assistant verliert sofort den Zugriff und bittet beim nächsten Abruf um eine neue Anmeldung. Eine Verbindung, die 90 Tage nicht genutzt wird, löst Lotus von selbst.

## Datenschutz

- Home Assistant speichert kein Passwort, nur einen Zugangsschlüssel, den Lotus ausstellt und jederzeit widerrufen kann.
- Home Assistant fragt einmal pro Minute nach dem Stand. Lotus schickt von sich aus nichts.
- Übertragen werden nur die Werte und Befehle deiner eigenen Anlagen, und zwar an dein eigenes Home Assistant.
- Die Diagnose zum Herunterladen enthält weder Schlüssel noch die Namen deiner Spas.

---

## English

Connect your spa from the Lotus app to Home Assistant: water temperature, target temperature, pumps, blowers and light, heating mode, care run, bathing detection, filter and connection, with the same permissions as in the app.

Requirements: a Lotus account with a valid subscription (an active trial counts), Home Assistant 2026.10 or newer, and „My Home Assistant“ enabled (default).

Install via HACS (custom repository, type „Integration“), restart, then add the integration „Lotus Spa“ and sign in on the Lotus page. When the subscription ends, the spa shows as unavailable and a repair notice links to the subscription page; everything continues as soon as the subscription is valid again. Disconnect any time in the Lotus app under Account › Home Assistant.
