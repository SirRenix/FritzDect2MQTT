# FritzDect2MQTT

[![en](https://img.shields.io/badge/lang-en-red.svg)](README.md) | [![de](https://img.shields.io/badge/lang-de-green.svg)](README.de.md)

Fragt **Fritz!DECT-Steckdosen** an einer FritzBox über die **AHA-HTTP-API**
([fritzconnection](https://fritzconnection.readthedocs.io)) ab und veröffentlicht Name, Temperatur,
Leistung, Energie, Spannung, Strom und Schaltzustand per **MQTT**. Steckdosen lassen sich **per MQTT
schalten**. Ein kleiner Container, keine Home-Automation-Plattform nötig.

Entstanden für einen **Voron-3D-Drucker (Klipper / Moonraker / Mainsail)**: Live-Werte der
Steckdose in Mainsail, Energie pro Druckjob in Moonrakers History, Ein/Aus-Toggle.

> **Status:** feature-complete, Maintenance-Modus. Bugs werden gefixt, neue Funktionen sind nicht geplant.
> Wer Home Assistant nutzt, braucht das hier nicht — HAs native *AVM FRITZ!SmartHome*-Integration
> plus Moonrakers `[power type: homeassistant]` reichen.
> Basiert auf [Zentris/FritzDectMQTT](https://github.com/Zentris/FritzDectMQTT) (MIT), stark überarbeitet.

---

## MQTT-Datenmodell

| Richtung | Topic | Payload |
|----------|-------|---------|
| Status (publish) | `<maintoken>/<FB>/<AIN>` | `{"AIN": "116570123456", "name": "Printer", "temp": 21.0, "power": 7.46, "energy": 29.4, "allpower": 29.4, "state": "on", "voltage": 233.3, "current": 0.032}` |
| Verfügbarkeit (publish, retained) | `<maintoken>/<FB>/status` | `online` / `offline` (Last Will) |
| Befehl (subscribe) | `<cmdtoken>/<FB>/<AIN>` | `{"action": "set_switch", "data": {"AIN": "116570123456", "switchstate": "on"}}` |

- Einheiten: `temp` °C, `power` W, `energy` kWh (Zählerstand), `voltage` V, `current` A (abgeleitet:
  power/voltage). Nicht verfügbare Werte sind `null`.
- `allpower` ist ein **veralteter Alias von `energy`** (entfällt in 2.0).
- `state` ist `on` / `off` (die FritzBox meldet einen Schaltwechsel mit ~10 s Verzögerung).
- `switchstate` akzeptiert `on`/`off`, `true`/`false`, `1`/`0` (String oder JSON-Boolean).
- Defaults: `maintoken = sensor/FB`, `cmdtoken = cmd/FB`, `<FB>` = `QUERY.FB`. Befehls- und
  Status-Baum sind getrennt, damit der Client seine eigenen Nachrichten nie zurückerhält.

```bash
mosquitto_pub -h <broker> -t "cmd/FB/MyFritzbox/116570123456" \
  -m '{"action": "set_switch", "data": {"AIN": "116570123456", "switchstate": "off"}}'
```

---

## Moonraker-/Mainsail-Beispiel

Live-Werte + Job-History über `[sensor]`, Ein/Aus-Toggle über `[power]`. `retain: true` (Default) sorgt dafür,
dass Mainsail nach einem Neustart sofort Werte zeigt.

> Auf einem Voron mit Moonraker verifiziert (Sep 2026). Die FritzBox meldet einen Schaltwechsel mit
> ~10 s Verzögerung, der Toggle in Mainsail zieht entsprechend nach.

```ini
# moonraker.conf
[mqtt]
address: <broker-ip>
port: 1883
username: {secrets.mqtt.username}
password: {secrets.mqtt.password}
enable_moonraker_api: False

[sensor printer_socket]
type: mqtt
name: Printer socket
state_topic: sensor/FB/MyFritzbox/116570123456
state_response_template:
  {% set d = payload|fromjson %}
  {set_result("power", d["power"]|float)}
  {set_result("voltage", d["voltage"]|float)}
  {set_result("current", d["current"]|float)}
  {set_result("energy", d["energy"]|float)}
  {set_result("temperature", d["temp"]|float)}
parameter_power:
  units=W
parameter_voltage:
  units=V
parameter_current:
  units=A
parameter_energy:
  units=kWh
parameter_temperature:
  units=°C
history_field_energy_consumption:
  parameter=energy
  desc=Printer energy consumption
  strategy=delta
  units=kWh
  init_tracker=true
  precision=3
  report_total=true

[power printer_socket]
type: mqtt
command_topic: cmd/FB/MyFritzbox/116570123456
command_payload:
  {"action": "set_switch", "data": {"AIN": "116570123456", "switchstate": "{command}"}}
state_topic: sensor/FB/MyFritzbox/116570123456
state_response_template:
  {% set d = payload|fromjson %}
  {d["state"]}
query_after_command: False
locked_while_printing: True
```

---

## Docker (empfohlen)

Das Image backt Code, Abhängigkeiten und `configdata.cfg` ein. **Nur `secrets.yaml` wird vom Host
gemountet** — niemals committen. Der Container läuft als **UID 1000** und hat einen `HEALTHCHECK`
(healthy = in den letzten 180 s ein erfolgreicher Abfragezyklus).

Secret einmalig auf dem Docker-Host anlegen:

```bash
sudo mkdir -p /opt/docker-data/fritzdect2mqtt
sudo cp _secrets.yaml /opt/docker-data/fritzdect2mqtt/secrets.yaml   # danach Zugangsdaten eintragen
sudo chown 1000:1000 /opt/docker-data/fritzdect2mqtt/secrets.yaml
sudo chmod 400 /opt/docker-data/fritzdect2mqtt/secrets.yaml
```

**Variante A — reines Docker Compose**

```bash
git clone https://github.com/SirRenix/FritzDect2MQTT.git && cd FritzDect2MQTT
TIME_ZONE=Europe/Berlin docker compose -f docker/compose.yaml up -d --build
docker logs -f fritzdect2mqtt
```

**Variante B — Git-Deploy über [dockhand](https://github.com/fnsys/dockhand)** (*Deploy from Git*, Build on deploy):

| Feld | Wert |
|------|------|
| Repository URL / Branch | `https://github.com/SirRenix/FritzDect2MQTT.git` / `main` |
| Compose file path | `docker/compose.yaml` |
| **Context directory** | **`.`** — zwingend, sonst findet der Build die App-Dateien nicht (`lstat .../docker: no such file`) |
| Build images on deploy | an |
| Environment | `TIME_ZONE=Europe/Berlin` (optional, Default UTC) |

---

## Ohne Docker

Python 3.12+:

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp _secrets.yaml secrets.yaml      # Zugangsdaten eintragen
python FritzDect2MQTT.py           # für Dauerbetrieb in systemd packen
```

---

## Konfiguration (`configdata.cfg`)

| Schlüssel | Bedeutung |
|-----------|-----------|
| `QUERY.FB` | Name des FritzBox-Eintrags in `secrets.yaml` |
| `QUERY.AINS` | `ALL` oder eine Liste von AINs |
| `QUERY.looptime` | Sekunden zwischen den Abfragezyklen (Default 30) |
| `MQTT.broker` | Genutzter `MQTT_BROKER`-Eintrag in `secrets.yaml` (Default `RASPI`) |
| `MQTT.maintoken` / `MQTT.cmdtoken` | Basis-Topics für Status / Befehle |
| `MQTT.clientId` | MQTT-Client-ID |
| `MQTT.qos` / `MQTT.retain` | QoS (0) / Retain (true) für veröffentlichte Statusdaten |
| `logging` | Python-`logging.config.dictConfig`-Block |

Fehlerverhalten: MQTT verbindet mit Backoff (1–60 s) neu; eine fehlgeschlagene FritzBox-Verbindung
wird nach 60 s, ein fehlgeschlagener Login nach 300 s wiederholt (vermeidet die Login-Sperre der
FritzBox); eine einzelne nicht erreichbare Steckdose wird übersprungen, die anderen werden weiter
veröffentlicht.

---

## Scope

**Drin:** Fritz!DECT-Schaltsteckdosen mit Leistungsmessung (DECT 200/210 …) an einer FritzBox → MQTT,
Schalten per MQTT. Ein Container pro FritzBox.
**Bewusst nicht drin:** Home-Assistant-Discovery (HA hat eine native AVM-Integration), Thermostate /
Rollläden / Taster, mehrere Boxen pro Instanz. Ein natives Moonraker-`[power]`-Gerät wäre der
richtige langfristige Ort dafür — hier nicht geplant.

## Lizenz

MIT — siehe [LICENSE](LICENSE). Ursprünglich ein Fork von
[Zentris/FritzDectMQTT](https://github.com/Zentris/FritzDectMQTT) (© 2024 Zentris), von SirRenix
umstrukturiert und erweitert. Änderungen: [CHANGELOG](CHANGELOG.md).
