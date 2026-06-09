# FritzDect2MQTT

[![en](https://img.shields.io/badge/lang-en-red.svg)](README.md) | [![de](https://img.shields.io/badge/lang-de-green.svg)](README.de.md)

## 📦 Überblick

Dieses Projekt liest Daten von **Fritz!DECT-Steckdosen** an einer FritzBox über die
**AHA-HTTP-API** aus (mittels [fritzconnection](https://fritzconnection.readthedocs.io))
und veröffentlicht sie über **MQTT**. Zusätzlich lassen sich Steckdosen **per MQTT
schalten**.

Es läuft als kleiner **Docker-Compose-Dienst** auf einem beliebigen Linux-Host
(ursprünglich für einen Raspberry Pi gebaut). Eine frühere Variante zielte auf ein
QNAP NAS — dieser Build-Weg wurde zugunsten des einfacheren Compose-Setups unten
entfernt.

> Privates/Hobby-Projekt. Das vollständige Änderungsprotokoll steht im [CHANGELOG](CHANGELOG.md).

---

## 🎯 Hintergrund & Ziel

Das Projekt ist entstanden, um Fritz!DECT-Steckdosen an einen **Voron-3D-Drucker** mit
**Klipper / Moonraker / Mainsail** anzubinden. Die Ziele:

1. **History-Werte in der Datenbank** — den Verbrauch der Steckdose (Leistung/Energie)
   erfassen und zusammen mit Moonrakers Job-History-Tabelle ablegen.
2. **Live-Anzeige in Mainsail** — die aktuellen Steckdosen-Werte (Verbrauch, Spannung,
   Strom, Temperatur) direkt in der Mainsail-Weboberfläche anzeigen.

Beides wird erreicht, indem dieses Projekt die Steckdosendaten nach MQTT veröffentlicht und
Moonraker sie über seine `[mqtt]`-, `[sensor]`- und `[power]`-Integration konsumiert.

---

## 🚀 Funktionen

- 📡 **MQTT-Veröffentlichung** je Steckdose: Name, Temperatur, Leistung, Energie, Spannung, Strom
- 🔀 **Schalten per MQTT** (`set_switch`) über das AHA-HTTP-Interface
- 🔁 **Reconnection-Handling** der MQTT-Verbindung
- 🔧 **Threading**: Abfrage und Befehls-Empfang laufen parallel
- 📊 **Gerätestatistik** via `getbasicdevicestats` (Spannung / abgeleiteter Strom)
- 🧹 **Container-natives Logging** nach stdout, rotiert durch Docker (`json-file`)

---

## 🔌 MQTT-Datenmodell

| Richtung | Topic | Payload |
|----------|-------|---------|
| publish (Status) | `<maintoken>/<FB>/<AIN>` | `{"AIN": "...", "name": "...", "temp": 21.0, "power": 7.46, "allpower": 29.4, "voltage": 233.3, "current": 0.03}` |
| subscribe (Befehl) | `<cmdtoken>/<FB>/<AIN>` | `{"action": "set_switch", "data": {"AIN": "...", "switchstate": "on"}}` |

Defaults: `maintoken = sensor/FB`, `cmdtoken = cmd/FB`, `<FB>` = der Name aus `QUERY.FB`.
Der Befehls-Baum ist bewusst **getrennt** vom Status-Baum, damit der Client seine eigenen
Status-Nachrichten nicht zurückerhält. `switchstate` akzeptiert `on`/`off`, `true`/`false`,
`1`/`0` (als String oder JSON-Boolean).

Beispiel (PowerShell mit den mosquitto-Clients):

```powershell
.\mosquitto_pub.exe -h <broker> -p 1883 -t "cmd/FB/MyFritzbox/116570608608" `
  -m '{\"action\": \"set_switch\", \"data\": {\"AIN\": \"116570608608\", \"switchstate\": \"off\"}}'
```

---

## 🐳 Docker-Installation (empfohlen)

Das Image backt Code, Abhängigkeiten und `configdata.cfg` ein (siehe
[`docker/Dockerfile`](docker/Dockerfile)). **Nur `secrets.yaml` wird vom Host
gemountet** — es darf niemals ins Git. `TIME_ZONE` kommt als Umgebungsvariable; der
Container hängt an einem externen Docker-Netz (standardmäßig `web_net`).

**Secret einmalig auf dem Docker-Host bereitstellen:**

```bash
sudo mkdir -p /opt/docker-data/fritzdect2mqtt
# /opt/docker-data/fritzdect2mqtt/secrets.yaml aus _secrets.yaml dieses Repos erstellen
sudo $EDITOR /opt/docker-data/fritzdect2mqtt/secrets.yaml
sudo chmod 600 /opt/docker-data/fritzdect2mqtt/secrets.yaml
docker network create web_net    # nur falls noch nicht vorhanden
```

### Variante A — Git-Deploy über dockhand (empfohlen, so getestet)

Dieses Projekt wird mit [dockhand](https://github.com/fnsys/dockhand) über dessen
*Deploy from Git* **deployt und getestet** — ein `git push` genügt zum Ausrollen:

| Feld | Wert |
|------|------|
| Repository URL | `https://github.com/SirRenix/FritzDect2MQTT.git` |
| Branch | `main` |
| Credential | `None (public)` |
| Compose file path | `docker/compose.yaml` |
| **Context directory** | **`.`** (Repo-Root — **erforderlich**) |
| Build images on deploy | **an** |
| Enable webhook | an (GitHub-Webhook auf die dockhand-URL zeigen lassen) |
| Environment variable | `TIME_ZONE=Europe/Berlin` |

> ⚠️ **„Context directory" auf `.` setzen** — sonst nimmt dockhand das Verzeichnis der
> Compose-Datei (`docker/`) als Build-Context und findet die App-Dateien im Repo-Root
> (`requirements.txt`, `*.py`) nicht → Build bricht mit
> `lstat .../docker: no such file or directory` ab. Mit `.` ist das gesamte Repo der
> Build-Context und `build.context: ..` in `docker/compose.yaml` löst korrekt auf.

### Variante B — reines Docker Compose

```bash
git clone https://github.com/SirRenix/FritzDect2MQTT.git
cd FritzDect2MQTT
TIME_ZONE=Europe/Berlin docker compose -f docker/compose.yaml up -d --build
```

Logs gehen nach stdout und werden von Docker rotiert (`json-file`, 10 MB × 3):

```bash
docker compose -f docker/compose.yaml logs -f
# oder:  docker logs -f fritzdect2mqtt
```

---

## 🧪 Manuelle Installation (ohne Docker, optional)

Läuft auf jedem Linux-Rechner mit Python 3.10+:

```bash
sudo apt-get install python3-venv
cd FritzDect2MQTT
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp _secrets.yaml secrets.yaml   # danach Zugangsdaten eintragen
python FritzDect2MQTT.py
```

Für Dauerbetrieb das Ganze in einen systemd-Dienst (oder einen Supervisor deiner Wahl)
packen, der `python FritzDect2MQTT.py` aus dem Projektverzeichnis startet.

---

## ⚙️ Konfiguration (`configdata.cfg`)

| Schlüssel | Bedeutung |
|-----------|-----------|
| `QUERY.FB` | Name des FritzBox-Eintrags in `secrets.yaml` |
| `QUERY.AINS` | `ALL` oder eine Liste konkreter AINs |
| `QUERY.looptime` | Sekunden zwischen den Abfragezyklen (Default 30; Änderung erfordert Neustart) |
| `MQTT.broker` | Welcher `MQTT_BROKER`-Eintrag aus `secrets.yaml` genutzt wird (Default `RASPI`) |
| `MQTT.maintoken` | Basis-Topic für veröffentlichte Statusdaten |
| `MQTT.cmdtoken` | Basis-Topic für eingehende Schaltbefehle |
| `MQTT.clientId` | MQTT-Client-ID |
| `logging` | Standard-`logging.config.dictConfig`-Block von Python |
