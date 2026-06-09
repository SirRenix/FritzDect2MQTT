# Changelog

## Version 1.3.2 – 2026-06-09
### Changed
- **Doku & Deployment an die Realität angepasst** (kein QNAP mehr): READMEs (de/en)
  neu geschrieben — reales Docker-Compose-Setup, MQTT-Datenmodell (State- und
  Befehls-Topics inkl. `set_switch`), Konfigurationsreferenz. Verweise auf nicht mehr
  vorhandene `cli/`-Dateien und den `dockerqnap`-Branch entfernt.
- `docker/compose.yaml` (reales Deployment) ins Repo aufgenommen; `.env.example` auf
  `TIME_ZONE` + externes Netz reduziert.
### Removed
- QNAP-/Supervisor-Build-Artefakte: `docker/Dockerfile`, `docker/supervisor/*`,
  `docker/logrotate/*`, `docker/docker-compose.yml`, `scripts/run.sh`.

## Version 1.3.1 – 2026-06-09
### Fixed
- **set_switch schaltet jetzt tatsächlich**: Die Umsetzung über
  `FritzHomeAutomation.set_switch` (TR-064/SOAP) scheiterte mit
  `UPnPError 402 Invalid Args`. Umgestellt auf das AHA-HTTP-Interface
  (`setswitchon`/`setswitchoff`), konsistent mit der übrigen Abfrage.
  End-to-end über MQTT verifiziert (off/on-Toggle).

## Version 1.3.0 – 2026-06-09
### Fixed
- **FritzConnection-Wiederverwendung**: Die Verbindung wird nicht mehr in jedem
  Abfragezyklus neu aufgebaut, sondern einmal angelegt und wiederverwendet (Neuaufbau
  nur nach Fehler). Reduziert HTTP-/XML-Churn und damit den Speicherbedarf des Containers.
- **MQTT-Schaltbefehle (`set_switch`) funktionsfähig**: Subscribe- und Publish-Topics
  waren inkonsistent (`home/devices/...` vs. `sensor/FB/...`), Befehle kamen nie an.
  Neues, vom State-Baum getrenntes Kommando-Topic (`cmdtoken`, Default `cmd/FB`).
  `switchstate` akzeptiert nun JSON-Booleans und Strings; Ausschalten (`false`/`off`)
  wird nicht mehr fälschlich verworfen.

### Changed
- `looptime` Default von 10 auf 30 Sekunden.
- MQTT-Broker-Eintrag aus `secrets.yaml` über `MQTT.broker` konfigurierbar (Default `RASPI`).
- Routine-Logs (jede Abfrage / jeder Send) von INFO auf DEBUG → kein unnötiges Logwachstum.
- `.gitattributes` (`text=auto eol=lf`) gegen wiederkehrende CRLF-Diffs.

### Ops
- Container-RAM: `MALLOC_ARENA_MAX=2`, `MALLOC_TRIM_THRESHOLD_=100000` und `mem_limit`
  in der Compose-Konfiguration ergänzt.

## Version 1.2.0 (dockerqnap branch) – 2025-04-16
### Added
- **Docker Support for QNAP**:
  - Created a complete Docker environment for QNAP NAS systems
  - New `dockerqnap` branch with fully integrated Docker build, compose, and run structure
  - Added structured project layout with clear separation of app code, Docker configs, supervisor, logrotate, and scripts

- **Supervision and Restart**:
  - Added Supervisor to auto-start, restart, and monitor `FritzDectMQTT.py`
  - Added `healthcheck` in `docker-compose.yml` for process monitoring
  - Auto-restarts on crash or failure within container

- **Logrotate Integration**:
  - Daily log rotation and compression via logrotate config
  - Prevents overgrowth of logfiles for long-term use
  - Docker logging limited to 10 MB per file (max 5 files)

- **Helper Files**:
  - Added `run.sh` shell script for one-command setup
  - Added `Makefile` for convenient dev/test commands

### Changed
- **Dockerfile**:
  - Updated Python base image from `3.9-slim` → `3.13-slim`
  - Removed SSH (security & simplicity)
  - Refactored Dockerfile structure for clarity and reproducibility
  - Reduced COPY usage to essentials only (`supervisor` & `logrotate`)
  - Made GitHub clone optional via comment
  - add network settings add build process
  - add internal network name (`dockernet`) in docker-compose.yaml
  - External QNAP network is now fully configurable via `.env` using `NETWORK_NAME` and optional `STATIC_IP`

### Fixed
- Improved compatibility with QNAP’s limited BusyBox shell
- Ensured proper line endings (`LF`) in shell scripts to prevent `^M` errors
- Adjusted mount points to avoid duplicated host volumes (`Fritz2MQTT-container` vs `FritzDect2MQTT-container`)

---

## Version 1.1.02a – 2024-10-24
### Fixes
- **Requirements**:  
  Updated to new versions  
  - `PyYAML~=6.0.2`  
  - `paho-mqtt~=2.1.0`  
  - `fritzconnection~=1.14.0`

- **Dockerfile**:  
  - Some changes for testing – not ready to use (deprecated in favor of `dockerqnap`)  
  - Switched Python from 3.9slim to 3.13slim  
  - Added logrotate  
  - Added supervisor incl. SSH (now removed)

---

## Version 1.1.01 – 2024-10-24
### Fixes
- **MQTT Reconnection Fix**:  
  Added reconnection check to handle MQTT disconnects more reliably  
  Retry every 5 seconds until successful

---

## Version 1.1 – 2024-10-23
### Fixes
- Improved automatic reconnection after MQTT loss
- Improved exception handling

### Changes
- Enhanced logging during reconnection attempts
- Code refactoring for clarity and maintainability

---

## Version 1.0 – Initial Release
- Initial release with support for:
  - Reading DECT socket data from FritzBox
  - Sending data to MQTT broker
  - Basic home automation commands
  - Threading & message handling
