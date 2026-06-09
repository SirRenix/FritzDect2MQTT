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

## 🚀 Funktionen

- 📡 **MQTT-Veröffentlichung** je Steckdose: Name, Temperatur, Leistung, Energie, Spannung, Strom
- 🔀 **Schalten per MQTT** (`set_switch`) über das AHA-HTTP-Interface
- 🔁 **Reconnection-Handling** der MQTT-Verbindung
- 🔧 **Threading**: Abfrage und Befehls-Empfang laufen parallel
- 📊 **Gerätestatistik** via `getbasicdevicestats` (Spannung / abgeleiteter Strom)
- 🧹 **Logrotation** (app-seitig `TimedRotatingFileHandler` + Docker-`json-file`-Limits)

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

**Voraussetzungen:** Docker + Docker Compose v2 und ein externes Docker-Netzwerk
(standardmäßig `web_net` — siehe `docker/.env.example`).

```bash
# 1) Code auf den Docker-Host holen. Die compose.yaml mountet genau diesen Pfad,
#    also dorthin klonen (oder den Volume-Pfad in docker/compose.yaml anpassen).
sudo git clone https://github.com/SirRenix/FritzDect2MQTT.git /opt/docker-data/fritzdect2mqtt
cd /opt/docker-data/fritzdect2mqtt

# 2) Zugangsdaten: FritzBox- und MQTT-Broker-Daten eintragen, dann umbenennen.
cp _secrets.yaml secrets.yaml
$EDITOR secrets.yaml

# 3) Laufzeitkonfiguration: FritzBox-Name, AINs, looptime, MQTT-Topics/Broker-Key.
$EDITOR configdata.cfg

# 4) Umgebung: Zeitzone setzen (und ggf. das Netzwerk anlegen).
cp docker/.env.example docker/.env
$EDITOR docker/.env
docker network create web_net   # nur falls noch nicht vorhanden

# 5) Starten.
docker compose -f docker/compose.yaml --env-file docker/.env up -d
```

Die Abhängigkeiten werden beim Containerstart aus `requirements.txt` installiert
(es wird kein eigenes Image gebaut). Logs:

```bash
docker compose -f docker/compose.yaml logs -f      # Container-stdout
tail -f FritzDectMQTT.log                           # Anwendungs-Log
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
