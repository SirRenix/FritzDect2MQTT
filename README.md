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
- 🧹 **Container-native logging** to stdout, rotated by Docker (`json-file`)

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

The image bakes in the code, dependencies and `configdata.cfg` (see
[`docker/Dockerfile`](docker/Dockerfile)). **Only `secrets.yaml` is mounted from the
host** — it must never be committed to Git. `TIME_ZONE` is passed as an environment
variable; the container joins an external Docker network (`web_net` by default).

**Prepare the secret on the Docker host** (once):

```bash
sudo mkdir -p /opt/docker-data/fritzdect2mqtt
# create /opt/docker-data/fritzdect2mqtt/secrets.yaml from _secrets.yaml in this repo
sudo $EDITOR /opt/docker-data/fritzdect2mqtt/secrets.yaml
sudo chmod 600 /opt/docker-data/fritzdect2mqtt/secrets.yaml
docker network create web_net    # only if it does not exist yet
```

### Option A — Git deploy via dockhand (recommended, this is what is tested)

This project is **deployed and tested with [dockhand](https://github.com/fnsys/dockhand)**
using its *Deploy from Git* feature, so a `git push` is the only action needed to roll
out a change:

| Field | Value |
|-------|-------|
| Repository URL | `https://github.com/SirRenix/FritzDect2MQTT.git` |
| Branch | `main` |
| Credential | `None (public)` |
| Compose file path | `docker/compose.yaml` |
| Build images on deploy | **on** |
| Enable webhook | on (point your GitHub webhook at the dockhand URL) |
| Environment variable | `TIME_ZONE=Europe/Berlin` |

### Option B — plain Docker Compose

```bash
git clone https://github.com/SirRenix/FritzDect2MQTT.git
cd FritzDect2MQTT
TIME_ZONE=Europe/Berlin docker compose -f docker/compose.yaml up -d --build
```

Logs go to stdout and are captured/rotated by Docker (`json-file`, 10 MB × 3):

```bash
docker compose -f docker/compose.yaml logs -f
# or:  docker logs -f fritzdect2mqtt
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
