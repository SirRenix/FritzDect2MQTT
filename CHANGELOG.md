# Changelog

## Version 1.5.0 – 2026-09-20
Pre-public audit release: bug fixes, hardening, payload completion. Project is now
feature-complete (maintenance mode).

### Added
- `state` (`on`/`off`) in the state payload via `getswitchstate` → enables Moonraker
  `[power type: mqtt]` (on/off toggle in Mainsail).
- `energy` (kWh) in the state payload; `allpower` is kept as a **deprecated alias**.
- Availability topic `<maintoken>/<FB>/status` (`online` retained / `offline` as last will and on
  clean shutdown).
- `MQTT.qos` and `MQTT.retain` options (defaults 0 / false = previous behaviour).
- Clean shutdown on SIGTERM/SIGINT (publishes `offline`, disconnects).
- Docker `HEALTHCHECK` (heartbeat file written after every successful query cycle).
- Unit tests (`tests/`), CI (ruff, pytest, Docker build) replacing the failing pylint workflow.
- README: Moonraker/Mainsail example config, scope, license/attribution.

### Fixed
- Negative temperatures were reported as `"NA"` (`isdigit()`); signed values are now parsed.
- Voltage from `getbasicdevicestats` was mis-parsed (233412 mV → 233.2 V instead of 233.412 V).
- One unreachable/faulty socket no longer aborts the whole cycle with a 60 s reconnect; per-AIN
  errors are logged and skipped.
- No more login storm on wrong FritzBox credentials (10 immediate retries triggered the
  FritzBox lock-out); now fail fast + 300 s back-off.
- FritzBox HTTP calls have a 10 s timeout (previously none).
- `MQTT not connected` was logged every 5 s (176 k lines in a broker outage); now only on state change.
- Non-UTF-8 command payloads no longer escape the message handler and force a reconnect.

### Changed
- Unavailable values are JSON `null` instead of the string `"NA"`; `voltage`/`current` keys are
  always present (`voltage_err` removed).
- paho-mqtt `CallbackAPIVersion.VERSION2` (VERSION1 is deprecated); reconnect handled by paho
  (`reconnect_delay_set`) instead of a blocking loop in `on_disconnect`.
- Docker: container runs as UID 1000 (`secrets.yaml` must be `chown 1000:1000`); `.dockerignore`;
  compose no longer needs an external network or `/etc/localtime` mounts; `TIME_ZONE` defaults to UTC.
- Dead code removed (`handle_log_message`, `MQTT.py` test block).

### Deprecated
- `allpower` → use `energy`. Will be removed in 2.0.

## Version 1.4.1 – 2026-06-09
### Changed
- **Dependency maintenance** (verified against the live FritzBox before release):
  - Base image pinned to `python:3.14-slim` (floats to the latest 3.14 patch on rebuild;
    currently 3.14.5, was 3.14.2).
  - `fritzconnection` bumped `~=1.14.0` → `~=1.15.1`.
  - `paho-mqtt` (2.1.0) and `PyYAML` (6.0.3) already current.

## Version 1.4.0 – 2026-06-09
### Changed
- **Image-based deployment instead of runtime `pip`**: a minimal `docker/Dockerfile`
  bakes in the code, dependencies and `configdata.cfg`. `docker/compose.yaml` now uses
  `build:` instead of a base image + code bind-mount. No more `pip install` on every restart.
- **Git-based deployment (dockhand) set up and tested**: delivered via *Deploy from Git*
  (build on deploy + webhook) — `git push` is the only deploy action needed.
- **`secrets.yaml`** is the only file bind-mounted from the host (read-only); it is never
  committed to Git and never baked into the image. `TIME_ZONE` is passed as an env var.
- **Container-native logging to stdout** (rotated by Docker `json-file`); file handler removed.
### Docs
- READMEs (de/en) updated for the image/Git-deploy model, including the dockhand field values.

## Version 1.3.2 – 2026-06-09
### Changed
- **Docs & deployment aligned with reality** (no more QNAP): READMEs (de/en) rewritten —
  real Docker Compose setup, MQTT data model (state and command topics incl. `set_switch`),
  configuration reference. Removed references to no-longer-existing `cli/` files and the
  `dockerqnap` branch.
- Added the real `docker/compose.yaml` to the repository; reduced `.env.example` to
  `TIME_ZONE` + external network.
### Removed
- QNAP/Supervisor build artifacts: `docker/Dockerfile`, `docker/supervisor/*`,
  `docker/logrotate/*`, `docker/docker-compose.yml`, `scripts/run.sh`.

## Version 1.3.1 – 2026-06-09
### Fixed
- **set_switch now actually switches**: the implementation via
  `FritzHomeAutomation.set_switch` (TR-064/SOAP) failed with `UPnPError 402 Invalid Args`.
  Switched to the AHA HTTP interface (`setswitchon`/`setswitchoff`), consistent with the
  rest of the data polling. Verified end-to-end over MQTT (off/on toggle).

## Version 1.3.0 – 2026-06-09
### Fixed
- **FritzConnection reuse**: the connection is no longer rebuilt on every query cycle but
  created once and reused (rebuilt only after an error). Reduces HTTP/XML churn and thus the
  container's memory footprint.
- **MQTT switch commands (`set_switch`) made functional**: subscribe and publish topics were
  inconsistent (`home/devices/...` vs. `sensor/FB/...`), so commands never arrived. Added a
  dedicated command topic (`cmdtoken`, default `cmd/FB`) separate from the state tree.
  `switchstate` now accepts JSON booleans and strings; turning off (`false`/`off`) is no
  longer wrongly rejected.

### Changed
- `looptime` default changed from 10 to 30 seconds.
- MQTT broker entry in `secrets.yaml` selectable via `MQTT.broker` (default `RASPI`).
- Routine logs (every query / every send) moved from INFO to DEBUG → no needless log growth.
- `.gitattributes` (`text=auto eol=lf`) to stop recurring CRLF diffs.

### Ops
- Container RAM: added `MALLOC_ARENA_MAX=2`, `MALLOC_TRIM_THRESHOLD_=100000` and `mem_limit`
  to the Compose configuration.

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
