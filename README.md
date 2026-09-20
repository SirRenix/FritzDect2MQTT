# FritzDect2MQTT

[![en](https://img.shields.io/badge/lang-en-red.svg)](README.md) | [![de](https://img.shields.io/badge/lang-de-green.svg)](README.de.md)

Polls **Fritz!DECT smart sockets** on a FritzBox via the **AHA HTTP API**
([fritzconnection](https://fritzconnection.readthedocs.io)) and publishes name, temperature, power,
energy, voltage, current and switch state to **MQTT**. Sockets can be **switched via MQTT**.
One small container, no home automation platform required.

Built to feed a **Voron 3D printer (Klipper / Moonraker / Mainsail)**: live socket stats in
Mainsail, energy per print job in Moonraker's history, on/off toggle.

> **Status:** feature-complete, maintenance mode. Bugs get fixed, no new features planned.
> If you run Home Assistant you don't need this — use HA's native *AVM FRITZ!SmartHome*
> integration and Moonraker's `[power type: homeassistant]`.
> Based on [Zentris/FritzDectMQTT](https://github.com/Zentris/FritzDectMQTT) (MIT), heavily reworked.

---

## MQTT data model

| Direction | Topic | Payload |
|-----------|-------|---------|
| state (publish) | `<maintoken>/<FB>/<AIN>` | `{"AIN": "116570123456", "name": "Printer", "temp": 21.0, "power": 7.46, "energy": 29.4, "allpower": 29.4, "state": "on", "voltage": 233.3, "current": 0.032}` |
| availability (publish, retained) | `<maintoken>/<FB>/status` | `online` / `offline` (last will) |
| command (subscribe) | `<cmdtoken>/<FB>/<AIN>` | `{"action": "set_switch", "data": {"AIN": "116570123456", "switchstate": "on"}}` |

- Units: `temp` °C, `power` W, `energy` kWh (total meter), `voltage` V, `current` A (derived: power/voltage).
  Unavailable values are `null`.
- `allpower` is a **deprecated alias of `energy`** (removed in 2.0).
- `state` is `on` / `off` (the FritzBox reports a switch change with ~10 s delay).
- `switchstate` accepts `on`/`off`, `true`/`false`, `1`/`0` (string or JSON boolean).
- Defaults: `maintoken = sensor/FB`, `cmdtoken = cmd/FB`, `<FB>` = `QUERY.FB`. Command and state
  trees are separate so the client never receives its own messages.

```bash
mosquitto_pub -h <broker> -t "cmd/FB/MyFritzbox/116570123456" \
  -m '{"action": "set_switch", "data": {"AIN": "116570123456", "switchstate": "off"}}'
```

---

## Moonraker / Mainsail example

Live values + job history via `[sensor]`, on/off toggle via `[power]`. `retain: true` (default) lets
Mainsail show values right after a restart.

> Verified with Moonraker on a Voron (Sep 2026). The FritzBox reports a switch change with ~10 s delay,
> so the toggle in Mainsail follows a moment later.

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

## Docker (recommended)

The image bakes in code, dependencies and `configdata.cfg`. **Only `secrets.yaml` is mounted**
from the host — never commit it. The container runs as **UID 1000** and has a `HEALTHCHECK`
(healthy = a query cycle succeeded within the last 180 s).

Prepare the secret on the Docker host (once):

```bash
sudo mkdir -p /opt/docker-data/fritzdect2mqtt
sudo cp _secrets.yaml /opt/docker-data/fritzdect2mqtt/secrets.yaml   # then edit the credentials
sudo chown 1000:1000 /opt/docker-data/fritzdect2mqtt/secrets.yaml
sudo chmod 400 /opt/docker-data/fritzdect2mqtt/secrets.yaml
```

**Option A — plain Docker Compose**

```bash
git clone https://github.com/SirRenix/FritzDect2MQTT.git && cd FritzDect2MQTT
TIME_ZONE=Europe/Berlin docker compose -f docker/compose.yaml up -d --build
docker logs -f fritzdect2mqtt
```

**Option B — Git deploy via [dockhand](https://github.com/fnsys/dockhand)** (*Deploy from Git*, build on deploy):

| Field | Value |
|-------|-------|
| Repository URL / Branch | `https://github.com/SirRenix/FritzDect2MQTT.git` / `main` |
| Compose file path | `docker/compose.yaml` |
| **Context directory** | **`.`** — required, otherwise the build cannot find the app files (`lstat .../docker: no such file`) |
| Build images on deploy | on |
| Environment | `TIME_ZONE=Europe/Berlin` (optional, default UTC) |

---

## Without Docker

Python 3.12+:

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp _secrets.yaml secrets.yaml      # edit credentials
python FritzDect2MQTT.py           # wrap in systemd for permanent use
```

---

## Configuration (`configdata.cfg`)

| Key | Meaning |
|-----|---------|
| `QUERY.FB` | Name of the FritzBox entry in `secrets.yaml` |
| `QUERY.AINS` | `ALL` or a list of AINs |
| `QUERY.looptime` | Seconds between query cycles (default 30) |
| `MQTT.broker` | `MQTT_BROKER` entry in `secrets.yaml` to use (default `RASPI`) |
| `MQTT.maintoken` / `MQTT.cmdtoken` | Base topics for state / commands |
| `MQTT.clientId` | MQTT client id |
| `MQTT.qos` / `MQTT.retain` | QoS (0) / retain (true) for published state |
| `logging` | Python `logging.config.dictConfig` block |

Behaviour on errors: MQTT reconnects with back-off (1–60 s); a failing FritzBox connection is
retried after 60 s, a failed login after 300 s (avoids the FritzBox login lock-out); a single
unreachable socket is skipped, the others are still published.

---

## Scope

**In:** Fritz!DECT switchable sockets with power metering (DECT 200/210 …) on one FritzBox → MQTT,
switching via MQTT. One container per FritzBox.
**Out (by design):** Home Assistant discovery (HA has a native AVM integration), thermostats /
blinds / buttons, several boxes per instance. A native Moonraker `[power]` device would be the
proper long-term home for this — not planned here.

## License

MIT — see [LICENSE](LICENSE). Originally forked from
[Zentris/FritzDectMQTT](https://github.com/Zentris/FritzDectMQTT) (© 2024 Zentris), restructured
and extended by SirRenix. Changes: [CHANGELOG](CHANGELOG.md).
