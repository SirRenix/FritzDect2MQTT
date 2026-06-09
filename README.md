# FritzDect2MQTT

[![en](https://img.shields.io/badge/lang-en-red.svg)](README.md) | [![de](https://img.shields.io/badge/lang-de-green.svg)](README.de.md)

## 📦 Overview

This project reads data from **Fritz!DECT smart sockets** connected to a FritzBox via
the **AHA HTTP API** (using [fritzconnection](https://fritzconnection.readthedocs.io))
and publishes it to an **MQTT broker**. It can also **switch sockets on/off** via MQTT.

It runs as a small **Docker Compose** service on any Linux host (originally built for a
Raspberry Pi). A previous variant targeted QNAP NAS — that build path has been removed
in favour of the simpler Compose setup below.

> Personal/hobby project. The full change history is in the [CHANGELOG](CHANGELOG.md).

---

## 🚀 Features

- 📡 **MQTT publish** of per-socket name, temperature, power, energy, voltage, current
- 🔀 **Switching via MQTT** (`set_switch`) using the AHA HTTP interface
- 🔁 **Reconnection handling** for the MQTT connection
- 🔧 **Threading**: querying and command-listening run in parallel
- 📊 **Device statistics** via `getbasicdevicestats` (voltage / derived current)
- 🧹 **Log rotation** (app-side `TimedRotatingFileHandler` + Docker `json-file` limits)

---

## 🔌 MQTT data model

| Direction | Topic | Payload |
|-----------|-------|---------|
| publish (state) | `<maintoken>/<FB>/<AIN>` | `{"AIN": "...", "name": "...", "temp": 21.0, "power": 7.46, "allpower": 29.4, "voltage": 233.3, "current": 0.03}` |
| subscribe (command) | `<cmdtoken>/<FB>/<AIN>` | `{"action": "set_switch", "data": {"AIN": "...", "switchstate": "on"}}` |

Defaults: `maintoken = sensor/FB`, `cmdtoken = cmd/FB`, `<FB>` = the `QUERY.FB` name.
The command tree is intentionally **separate** from the state tree so the client never
receives its own published messages. `switchstate` accepts `on`/`off`, `true`/`false`,
`1`/`0` (string or JSON boolean).

Example (PowerShell with the mosquitto clients):

```powershell
.\mosquitto_pub.exe -h <broker> -p 1883 -t "cmd/FB/MyFritzbox/116570608608" `
  -m '{\"action\": \"set_switch\", \"data\": {\"AIN\": \"116570608608\", \"switchstate\": \"off\"}}'
```

---

## 🐳 Docker installation (recommended)

**Requirements:** Docker + Docker Compose v2, and an external Docker network
(`web_net` by default — see `docker/.env.example`).

```bash
# 1) Get the code onto the Docker host. The compose file mounts this exact path,
#    so clone it there (or adjust the volume path in docker/compose.yaml).
sudo git clone https://github.com/SirRenix/FritzDect2MQTT.git /opt/docker-data/fritzdect2mqtt
cd /opt/docker-data/fritzdect2mqtt

# 2) Credentials: fill in FritzBox + MQTT broker details, then rename.
cp _secrets.yaml secrets.yaml
$EDITOR secrets.yaml

# 3) Runtime config: FritzBox name, AINs, looptime, MQTT topics/broker key.
$EDITOR configdata.cfg

# 4) Environment: set the timezone (and create the network if needed).
cp docker/.env.example docker/.env
$EDITOR docker/.env
docker network create web_net   # only if it does not exist yet

# 5) Start it.
docker compose -f docker/compose.yaml --env-file docker/.env up -d
```

Dependencies are installed from `requirements.txt` at container start (no custom
image is built). Logs:

```bash
docker compose -f docker/compose.yaml logs -f      # container stdout
tail -f FritzDectMQTT.log                           # application log
```

---

## 🧪 Manual installation (without Docker, optional)

Runs on any Linux machine with Python 3.10+:

```bash
sudo apt-get install python3-venv
cd FritzDect2MQTT
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp _secrets.yaml secrets.yaml   # then edit credentials
python FritzDect2MQTT.py
```

To run it permanently, wrap it in a systemd service (or your supervisor of choice)
that starts `python FritzDect2MQTT.py` from the project directory.

---

## ⚙️ Configuration (`configdata.cfg`)

| Key | Meaning |
|-----|---------|
| `QUERY.FB` | Name of the FritzBox entry in `secrets.yaml` |
| `QUERY.AINS` | `ALL` or a list of specific AINs to query |
| `QUERY.looptime` | Seconds between query cycles (default 30; change requires restart) |
| `MQTT.broker` | Which `MQTT_BROKER` entry in `secrets.yaml` to use (default `RASPI`) |
| `MQTT.maintoken` | Base topic for published state data |
| `MQTT.cmdtoken` | Base topic for incoming switch commands |
| `MQTT.clientId` | MQTT client id |
| `logging` | Standard Python `logging.config.dictConfig` block |
