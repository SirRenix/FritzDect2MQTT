# Changelog

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
