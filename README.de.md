# FritzDectMQTT

> ⚠️ **Achtung: Dieses Projekt befindet sich in aktiver Entwicklung.**  
> Vor allem die Docker/QNAP-Integration wird aktuell strukturell angepasst.  
> Dokumentation und Ordnerstrukturen können sich kurzfristig ändern.

[![en](https://img.shields.io/badge/lang-en-red.svg)](README.md) | [![de](https://img.shields.io/badge/lang-de-green.svg)](README.de.md)

---

## 📦 Überblick

Dieses Projekt liest Daten von **Fritz!DECT Steckdosen** über die **fritzconnection HTTP-API** aus und veröffentlicht diese über MQTT.  
Ursprünglich für den Raspberry Pi entwickelt, wird es nun auch offiziell unter **Docker** (z. B. auf einem QNAP NAS) unterstützt.

---

## 📋 Changelog

Das vollständige Änderungsprotokoll befindet sich [hier](CHANGELOG.md).

---

## 🚀 Funktionen

- 📡 **MQTT-Unterstützung**: Überträgt die DECT-Daten an einen MQTT-Broker
- 🔁 **Reconnection-Handling**: Erkennt MQTT-Verbindungsabbrüche und stellt automatisch wieder her
- 📦 **Docker-Unterstützung**: Kompatibel mit QNAP NAS / Container Station
- ⚙️ **Supervisor-Integration**: Automatischer Start und Neustart des Scripts
- 🔍 **Healthcheck**: Erkennt, ob das Script noch aktiv läuft
- 🧹 **Logrotate**: Begrenzt und rotiert Logdateien
- 🔧 **Threading**: Unterstützt parallele Abläufe
- 📊 **Gerätestatus**: `GetDeviceStats` integriert

---
## 🐳 Docker-basierte Installation (empfohlen)

### 🔧 Voraussetzungen

- Docker & Docker Compose (z.B. über QNAP Container Station)
- Git (alternativ manuell ZIP herunterladen)

---

### 🚀 Schnellstart (Docker)

1. Repository klonen:
   bash oder shell
   git clone --branch dockerqnap https://github.com/SirRenix/FritzDect2MQTT.git
   cd FritzDect2MQTT
   
2. Bearbeite configdata.cfg und _secrets.yml:
   bearbeite **_secrets.yaml** mit Fritzbox  login daten, sowie dem MQTT Broker und nenne die datei in `secrets.yaml` um.
   
3. Erstellen und Ausführen:
   "sudo sh" oder "bash" ./scripts/run.sh	
   
4. optional
   eigenständiger build mit docker compose up -d --build

##🔎 Logs & Konfiguration
Die folgenden Verzeichnisse sind im Container verfügbar:

- /fritzdect2mqtt/logs – Logdateien

- /fritzdect2mqtt/config – Konfigurationen & Zugangsdaten

Docker-Logs sind zusätzlich auf 10 MB × 5 Dateien begrenzt. Die internen Logfiles werden täglich rotiert (logrotate). 
   
## Geplante Änderungen

- Dokumentation der Docker-Funktionalität in Verbindung mit einem MQTT-Server.
- Erweiterung der Code-Dokumentation.
- Verbesserung der Fehlerbehandlung, um alle möglichen Fehlerfälle abzudecken.
- Docker installations Anleitung (QNAP NAS)

---

## 🧪 Manuelle Installation 

1. **_secrets.yaml**: Datei mit den Fritzbox-Zugangsdaten ausfüllen und in `secrets.yaml` umbenennen.
2. **Virtuelles Python-Environment**: [Anleitung weiter unten](#python-virtuelles-environment-venv-einrichten).
3. **Logfile-Rotation**: [Anleitung zur Einrichtung](#logfile-rotation).
4. **Systemdienst einrichten**: Automatischer Start des Scripts über `systemctl`. [Details](#service-systemctl).

---

### Python Virtuelles Environment (venv) einrichten

Um eine isolierte Python-Umgebung für das Projekt zu erstellen:

```bash
# Python virtual environment installieren
sudo apt-get install python3-venv

# In das Projektverzeichnis wechseln
cd ~/FritzDectMQTT

# Virtuelles environment initialisieren
python -m venv ~/FritzDectMQTT/venv

# Environment aktivieren
source ~/FritzDectMQTT/venv/bin/activate

# Abhängigkeiten installieren
pip install -r requirements.txt

# Service anpassen
Der Pfad in der `fritzdectmqtt.service` - Datei muss entsprechend dem Usernamen angepasst werden.

---

### Logfile-Rotation
Um zu vermeiden, dass das Filesystem des Rechners durch die Logfiles voll läuft, wird die Logrotate Funktionalität des 
Linux-OS verwendet.

Falls ``logrotate`` noch nicht installiert ist, installiere es:

    sudo apt install logrotate

Kopiere das File ``fritzdectmqtt.logrotate``:

    sudo cp cli/fritzdectmqtt.logrotate /etc/logrotate.d/fritzdectmqtt 

---
### Service (systemctl)
Um das Script als Hintergrunddienst laufen zu lassen:


# Systemdienst umkopieren
sudo cp cli/fritzdectmqtt.service /etc/systemd/system

# Aktivieren
sudo systemctl enable fritzdectmqtt.service

# Starten
sudo systemctl start fritzdectmqtt.service

# Status prüfen
sudo systemctl status fritzdectmqtt.service

# Stoppen
sudo systemctl stop fritzdectmqtt.service


---

*Das Projekt ist in einer frühen Phase, die Fehlererkennung ist noch in einer relativ rudimentären Qualität.*