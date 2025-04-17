# FritzDectMQTT

> ⚠️ **Project under active development**  
> This project – especially the Docker/QNAP integration – is actively evolving.  
> Documentation and folder structures may change.  


[![en](https://img.shields.io/badge/lang-en-red.svg)](README.md) | [![de](https://img.shields.io/badge/lang-de-green.svg)](README.de.md)

## 📦 Overview

This project reads data from **Fritz!DECT smart sockets** connected to a Fritzbox using the **fritzconnection HTTP API** and publishes it to an MQTT broker.  

Originally designed for Raspberry Pi, this project now also supports **Docker-based environments**, including QNAP NAS.

---

## Changelog

You can find the full changelog of this project [here](CHANGELOG.md).

---

This script reads data from DECT sockets connected to a Fritzbox via the HTTP API fritzconnection and sends it to an **MQTT Broker**. The project is primarily designed for use on a Raspberry Pi but can be run on any Linux machine with Python 3.10 or higher. Also it is possible to run the script in an Docker Container.

---

## 🚀 Features

- 📡 **MQTT Protocol**: Sends DECT socket data via MQTT
- 🔁 **Reconnection Handling**: Automatically retries MQTT if connection is lost
- 📦 **Docker Support**: Works with Docker on QNAP NAS or other systems
- ⚙️ **Supervisor Integration**: Auto-start & auto-restart of the script
- 🔍 **Healthcheck**: Detects whether the script is running
- 🧹 **Logrotate**: Prevents logs from growing endlessly
- 🔧 **Threading**: Background process support
- 📊 **Device Statistics**: `GetDeviceStats` included

---

## 📦 Docker-based Installation (Recommended)

### 🔧 Requirements

- Docker & Docker Compose (pre-installed on QNAP via Container Station)
- Git or manually downloaded repository

---

### 🚀 Quick Start (Docker)

1. Clone the repository:
   shell or bash
   git clone --branch dockerqnap https://github.com/SirRenix/FritzDect2MQTT.git
   cd FritzDect2MQTT
   
2. Adjust configdata.cfg and _secrets:
   Fill in **_secrets.yaml** with Fritzbox credentials and rename to `secrets.yaml`.

3. Build and run:
   ./scripts/run.sh	
   
---
## 🔎 Logs & Configs
Mounted folders inside the container:

- /fritzdect2mqtt/logs – All log output

- /fritzdect2mqtt/config – Optional configs, secrets

Logs are rotated daily using logrotate. Docker's internal log size is also limited (10 MB × 5 files).

## Planned Changes

- Documentation of Docker functionality with an MQTT server.
- Expand code documentation.
- Improve error handling to cover more cases.
- Docker install docu (QNAP NAS)

---

## Setup Instructions

1. 
2. [Set up a Python virtual environment](#python-virtual-environment-setup).
3. [Configure log rotation](#log-rotation).
4. [Set up as a systemd service for auto-start](#systemd-service-setup).

---

### 🧪 Manual (non-Docker) Installation (Optional)
If you prefer running this manually on a Linux machine (e.g. Raspberry Pi), follow these steps:

To create an isolated Python environment for the project:

```bash
#python virtual environment install
sudo apt-get install python3-venv

#move to project directory
cd ~/FritzDectMQTT

# virtual environment init
python -m venv ~/FritzDectMQTT/venv

# activate env
source ~/FritzDectMQTT/venv/bin/activate

# install dependencies
pip install -r requirements.txt

# modify service
The path in `fritzdectmqtt.service` - service file must be changed or modified with your username of the system.

---

### Logfile-Rotation
to avoid the computer system being full of log files or large files.
It is recommended to use logrotate under linux.

install:

    sudo apt install logrotate

copy file ``fritzdectmqtt.logrotate``:

    sudo cp cli/fritzdectmqtt.logrotate /etc/logrotate.d/fritzdectmqtt 

---

### Service (systemctl)
run script as a background service:

# System service copy
sudo cp cli/fritzdectmqtt.service /etc/systemd/system

# activate
sudo systemctl enable fritzdectmqtt.service

# start
sudo systemctl start fritzdectmqtt.service

# check status 
sudo systemctl status fritzdectmqtt.service

# stop
sudo systemctl stop fritzdectmqtt.service

---

*The project is in an early phase, the error detection is still of a basic quality.*
