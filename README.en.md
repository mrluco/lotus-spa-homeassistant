<p align="center"><img src="https://raw.githubusercontent.com/mrluco/lotus-spa-homeassistant/main/bilder/logo.png" alt="Lotus" width="120"></p>

<h1 align="center">Lotus Spa for Home Assistant</h1>

<p align="center">Your spa from the Lotus app in Home Assistant, with the same permissions as in the app.</p>

<p align="center">
<a href="https://hacs.xyz"><img src="https://img.shields.io/badge/HACS-Custom-41BDF5.svg" alt="HACS Custom"></a>
<a href="https://github.com/mrluco/lotus-spa-homeassistant/releases"><img src="https://img.shields.io/github/v/release/mrluco/lotus-spa-homeassistant" alt="Release"></a>
<a href="https://github.com/mrluco/lotus-spa-homeassistant/blob/main/LICENSE"><img src="https://img.shields.io/github/license/mrluco/lotus-spa-homeassistant" alt="License"></a>
</p>

<p align="center">
<a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=mrluco&repository=lotus-spa-homeassistant&category=integration"><img src="https://my.home-assistant.io/badges/hacs_repository.svg" alt="Open your Home Assistant instance and open a repository inside the Home Assistant Community Store."></a>
<a href="https://my.home-assistant.io/redirect/config_flow_start/?domain=lotus_spa"><img src="https://my.home-assistant.io/badges/config_flow_start.svg" alt="Open your Home Assistant instance and start setting up a new integration."></a>
</p>

<p align="center"><a href="https://github.com/mrluco/lotus-spa-homeassistant/blob/main/README.md">Deutsch</a> · <b>English</b></p>

| | | | |
|:---:|:---:|:---:|:---:|
| <img src="https://raw.githubusercontent.com/mrluco/lotus-spa-homeassistant/main/bilder/ha-geraet.png" width="200" alt="Device"> | <img src="https://raw.githubusercontent.com/mrluco/lotus-spa-homeassistant/main/bilder/ha-steuerung.png" width="200" alt="Controls"> | <img src="https://raw.githubusercontent.com/mrluco/lotus-spa-homeassistant/main/bilder/ha-wartung.png" width="200" alt="Maintenance and schedules"> | <img src="https://raw.githubusercontent.com/mrluco/lotus-spa-homeassistant/main/bilder/ha-energie.png" width="200" alt="Energy and account"> |
| Device | Controls | Maintenance and schedules | Energy and account |

## What you get with the subscription

- **Control:** target temperature, heating mode, pumps, blowers and light, vacation mode, setback and evening light. A two-speed pump offers low and high.
- **Status:** water temperature, outdoor temperature, filtering, messages with the text from the app, "Warm at" while heating up.
- **Schedules:** bathing times, filter times and solar mode. A change in Home Assistant is the same as in the app.
- **Care:** care run with duration, maintenance pause, maintenance tasks with due date and a "done" button.
- **Consumption:** energy for the energy dashboard, power and today's cost. You can change pool volume and electricity price here.
- **Lotus Box and account:** connection and Wi-Fi reception of the box, your subscription and its end date.

You can only switch what you may switch in the app. Every command appears in your spa's log with "Home Assistant".

Without a subscription, Home Assistant shows your spa as "unavailable" and a note under Settings › Repairs on what the subscription adds. In the Lotus app you keep using your spa as usual.

Filter time changes take effect at the next start, never immediately. While solar leads, filter times are read-only. Home Assistant changes schedules at most four times a day.

## Requirements

- a Lotus account with a valid subscription
- Home Assistant 2026.10 or newer
- "My Home Assistant" enabled (default). The sign-in returns to your Home Assistant through it.

## Installation

With the two buttons above:

1. The first button opens the repository in HACS. Tap "Download", then restart Home Assistant.
2. The second button starts the setup. Sign in on the Lotus page as in the app and tap "Connect".

Without the buttons: add this repository in HACS as a custom repository of type "Integration", install "Lotus Spa", restart, then add the integration "Lotus Spa" under Settings › Devices & services.

You also find the buttons in the Lotus app under Account › Home Assistant.

## Subscription

Home Assistant is part of the Lotus subscription. When the subscription ends, Home Assistant shows your spa as unavailable and your automations switch nothing during that time. Shortly before the end and when a payment is open, a notice appears under Settings › Repairs. With a valid subscription everything continues right away.

You can disconnect at any time in the Lotus app under Account › Home Assistant. A connection unused for 90 days is removed by Lotus.

## Privacy

Home Assistant stores no password, only a key issued by Lotus that you can revoke at any time. Only the values and commands of your own spas are transferred when your Home Assistant asks: once a minute and shortly after a command.

## The Lotus app

| | | |
|:---:|:---:|:---:|
| <img src="https://raw.githubusercontent.com/mrluco/lotus-spa-homeassistant/main/bilder/bedienung.png" width="160" alt="Controls"> | <img src="https://raw.githubusercontent.com/mrluco/lotus-spa-homeassistant/main/bilder/heizen.png" width="160" alt="Heating"> | <img src="https://raw.githubusercontent.com/mrluco/lotus-spa-homeassistant/main/bilder/verbrauch.png" width="160" alt="Consumption"> |
| Controls | Heating | Consumption |

Sample spa, simulated values. [View the live demo](https://app.lotusswimspa.de/demo)

## Help

Report problems with the integration here under [Issues](https://github.com/mrluco/lotus-spa-homeassistant/issues). For questions about your spa and subscription, ask your Lotus dealer.
