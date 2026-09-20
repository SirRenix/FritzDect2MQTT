r"""
FritzDect2MQTT - poll Fritz!DECT smart sockets via the AHA HTTP interface and publish to MQTT.

https://fritzconnection.readthedocs.io/en/latest/sources/getting_started.html
AHA-HTTP-Interface: https://avm.de/fileadmin/user_upload/Global/Service/Schnittstellen/AHA-HTTP-Interface.pdf

State data is published to:   <maintoken>/<FB>/<AIN>   e.g. sensor/FB/MyFritzbox/123456789
Switch commands are read on:  <cmdtoken>/<FB>/<AIN>   e.g. cmd/FB/MyFritzbox/123456789

Example (PowerShell, mosquitto clients):
  .\mosquitto_pub.exe -h 192.168.xxx.xxx -p 1883 -t "cmd/FB/MyFritzbox/123456789" `
      -m '{\"action\": \"set_switch\", \"data\": {\"AIN\": \"123456789\", \"switchstate\": \"on\"}}'
  .\mosquitto_sub.exe -h 192.168.xxx.xxx -p 1883 -t "#" -v
"""

import logging.config
import os
import threading
import time
import xml.etree.ElementTree as ET
from logging import Logger

import requests
import yaml
from fritzconnection.core.exceptions import (
    FritzAuthorizationError,
    FritzConnectionException,
    FritzHttpInterfaceError,
)
from fritzconnection.core.fritzconnection import FritzConnection

import MQTT

CONFIG_FILE_NAME_YAML = "configdata.cfg"
SECRETS_FILE_NAME_YAML = "secrets.yaml"

# HTTP timeout (seconds) for every call to the FritzBox. Without it a hanging
# box would block the poll thread forever.
FRITZBOX_TIMEOUT = 10
# Back-off after a connection/service error resp. after an authorization
# error (the latter is long on purpose: the FritzBox locks the login after
# repeated failures, and a wrong password does not fix itself).
RETRY_DELAY_ERROR = 60
RETRY_DELAY_AUTH = 300
MQTT_WAIT_DELAY = 5

# Errors that concern a single device / response and must not abort the
# whole query cycle (the other AINs are still queried).
PER_AIN_ERRORS = (FritzHttpInterfaceError, ET.ParseError, ValueError, AttributeError, KeyError)

# --- Globals (set once in main(), read-only afterwards -> safe for both threads) ---
configuration: dict
secrets: dict
logger: Logger


def load_config_file(file_name: str) -> dict:
    """Load a YAML file."""
    if not os.path.exists(file_name):
        raise FileNotFoundError(f"File '{file_name}' is not accessible.")
    with open(file_name, encoding="utf-8") as f:
        return yaml.safe_load(f.read())


def init_logging(config: dict) -> Logger:
    """Initialize logging from configuration."""
    if "logging" not in config:
        raise ValueError(f"No logging configuration in configuration file '{CONFIG_FILE_NAME_YAML}' available.")
    logging.config.dictConfig(config["logging"])
    return logging.getLogger("__main__")


def connect_to_fritzbox(fb_config: dict) -> FritzConnection:
    """Create a FritzConnection.

    Authorization errors are *not* retried here: a wrong password does not
    fix itself and repeated attempts trigger the FritzBox login lock-out.
    The caller decides how long to wait before trying again.
    """
    return FritzConnection(
        address=fb_config["ip"],
        user=fb_config["user"],
        password=fb_config["password"],
        use_cache=True,
        timeout=FRITZBOX_TIMEOUT,
    )


def parse_switch_list(fc: FritzConnection) -> list:
    """Retrieve and parse the list of switch identifiers from FritzBox."""
    result = fc.call_http("getswitchlist")
    return [ain.strip() for ain in result["content"].split(",") if ain.strip()]


def get_selected_ains(config: dict, switch_identifiers: list) -> list:
    """Get the AINs to query from the configuration."""
    if config["QUERY"]["AINS"] == "ALL":
        return switch_identifiers
    return [str(ain) for ain in config["QUERY"]["AINS"]]


def _to_number(raw: str, divisor: float = 1.0) -> float | None:
    """Convert a raw AHA value ("215", "-35", "inval", "") to a float.

    The AHA interface reports unavailable values as "inval"; those become
    None (JSON null). Negative values (e.g. outdoor temperatures) are valid.
    """
    raw = (raw or "").strip()
    try:
        return float(int(raw)) / divisor
    except ValueError:
        return None


def query_switch_data(fc: FritzConnection, ain: str) -> dict:
    """Query data for a specific switch identified by its AIN."""
    data = {"AIN": ain}

    data["name"] = fc.call_http("getswitchname", ain)["content"].strip()
    # gettemperature: 0.1 degC, getswitchpower: mW, getswitchenergy: Wh
    data["temp"] = _to_number(fc.call_http("gettemperature", ain)["content"], 10)
    data["power"] = _to_number(fc.call_http("getswitchpower", ain)["content"], 1000)
    data["allpower"] = _to_number(fc.call_http("getswitchenergy", ain)["content"], 1000)

    parse_device_stats(fc.call_http("getbasicdevicestats", ain)["content"], data)
    return data


def parse_device_stats(xml_data: str, data: dict) -> None:
    """Parse XML from 'getbasicdevicestats' and add voltage / derived current.

    The voltage stats are a comma separated list in mV, newest value first.
    Keys are always present; unavailable values are None (JSON null).
    """
    voltage = None
    root = ET.fromstring(xml_data)
    stats = root.find("voltage/stats")
    if stats is not None and stats.text:
        voltage = _to_number(stats.text.split(",")[0], 1000)

    data["voltage"] = voltage
    power = data.get("power")
    data["current"] = round(power / voltage, 3) if voltage and power is not None else None


def abfrage_fb(mqtt_con):
    """Poll loop: query the FritzBox and publish the data via MQTT.

    The FritzConnection is created once and reused across loop iterations.
    It is only rebuilt (fc = None -> reconnect) after a connection/service
    error. Errors that concern a single device are logged and skipped so
    that one broken socket does not block the others.
    """
    fc = None
    mqtt_was_connected = True
    while True:
        try:
            if not mqtt_con.MQTTClient.is_connected():
                if mqtt_was_connected:
                    logger.warning(f"MQTT not connected. Waiting for the broker (retrying every {MQTT_WAIT_DELAY}s)...")
                    mqtt_was_connected = False
                time.sleep(MQTT_WAIT_DELAY)
                continue
            if not mqtt_was_connected:
                logger.info("MQTT connection is back. Resuming queries.")
                mqtt_was_connected = True

            if fc is None:
                fb_config = secrets["Fritzbox"][configuration["QUERY"]["FB"]]
                fc = connect_to_fritzbox(fb_config)
                logger.info("FritzBox connection established")

            switch_identifiers = parse_switch_list(fc)
            selected_ains = get_selected_ains(configuration, switch_identifiers)

            for ain in selected_ains:
                logger.debug(f"Querying data for AIN '{ain}'")
                try:
                    mqtt_data = query_switch_data(fc, ain)
                    mqtt_con.sendData(ain, mqtt_data)
                except PER_AIN_ERRORS as per_ain_err:
                    logger.error(f"AIN '{ain}': skipped ({type(per_ain_err).__name__}: {per_ain_err})")

        except FritzAuthorizationError as auth_err:
            logger.error(f"FritzBox login failed: {auth_err} - check user/password in {SECRETS_FILE_NAME_YAML}")
            logger.info(f"Retrying in {RETRY_DELAY_AUTH}s (avoid triggering the FritzBox login lock-out)...")
            fc = None
            time.sleep(RETRY_DELAY_AUTH)

        except (FritzConnectionException, requests.exceptions.RequestException) as conn_err:
            logger.error(f"FritzBox connection error: {conn_err}")
            logger.info(f"Reconnecting to FritzBox in {RETRY_DELAY_ERROR}s...")
            fc = None  # force a fresh connection on the next cycle
            time.sleep(RETRY_DELAY_ERROR)

        except Exception as e:
            logger.exception(f"Unexpected error querying FritzBox: {e}")
            logger.info(f"Reconnecting to FritzBox in {RETRY_DELAY_ERROR}s...")
            fc = None
            time.sleep(RETRY_DELAY_ERROR)

        looptime = configuration.get("QUERY", {}).get("looptime", 10)
        time.sleep(looptime)


def action_handler(action_type, data):
    """Dispatch an action received via MQTT."""
    if action_type == "set_switch":
        ain = data.get("AIN")
        switchstate = data.get("switchstate")

        # switchstate may legitimately be False/"off" -> check for presence,
        # not truthiness.
        if ain and switchstate is not None:
            logger.info(f"Setting switch for AIN {ain} to {switchstate}")
            handle_set_switch(str(ain), switchstate)
        else:
            logger.error("AIN or switchstate missing in the data.")
    else:
        logger.warning(f"Unknown action type '{action_type}' received.")


def _parse_switchstate(switchstate) -> bool:
    """Normalize a switchstate from MQTT into a bool.

    Accepts JSON booleans (true/false) as well as common strings
    ("True"/"on"/"1" -> on, "False"/"off"/"0" -> off). Raises ValueError
    for anything unrecognized.
    """
    if isinstance(switchstate, bool):
        return switchstate
    value = str(switchstate).strip().lower()
    if value in ("true", "on", "1"):
        return True
    if value in ("false", "off", "0"):
        return False
    raise ValueError(f"Unrecognized switchstate: {switchstate!r}")


def handle_set_switch(ain: str, switchstate):
    """Handle the 'set_switch' action."""
    logger.info(f"Handling 'set_switch' action. AIN: {ain} switchstate: {switchstate}")

    if not isinstance(ain, str) or not ain:
        logger.error("Invalid AIN.")
        return

    try:
        target = _parse_switchstate(switchstate)
    except ValueError as e:
        logger.error(str(e))
        return

    try:
        # Switch via the AHA HTTP interface (consistent with the polling).
        # The TR-064/SOAP variant (FritzHomeAutomation.set_switch) returns
        # 'UPnPError 402 Invalid Args' here. A dedicated connection is used
        # so the poll thread's connection is never shared between threads.
        fb_config = secrets["Fritzbox"][configuration["QUERY"]["FB"]]
        fc = connect_to_fritzbox(fb_config)

        command = "setswitchon" if target else "setswitchoff"
        logger.info(f"Switching AIN {ain} {'on' if target else 'off'}")
        result = fc.call_http(command, ain)
        logger.debug(f"FritzBox response: {result.get('content', '').strip()}")

    except Exception as e:
        logger.error(f"Error setting switch: {e}")


def listen_mqtt_forever(mqtt_client):
    """Run the paho network loop; paho reconnects by itself (reconnect_delay_set)."""
    while True:
        try:
            mqtt_client.MQTTClient.loop_forever(retry_first_connection=True)
        except Exception as e:
            logger.error(f"Error in MQTT loop: {e}")
        time.sleep(MQTT_WAIT_DELAY)


# ---------------
def main():
    global configuration, secrets, logger

    configuration = load_config_file(CONFIG_FILE_NAME_YAML)
    secrets = load_config_file(SECRETS_FILE_NAME_YAML)

    logger = init_logging(configuration)

    logger.info("------------Start program ------------")
    logger.info(f"Used Configfile: '{CONFIG_FILE_NAME_YAML}'")

    # MQTT setup
    mqtt_client = MQTT.MQTT(configuration, secrets)
    mqtt_client.action_handler = action_handler
    mqtt_client.connect()

    fb_thread = threading.Thread(target=abfrage_fb, args=(mqtt_client,), name="fritzbox-poll", daemon=True)
    mqtt_thread = threading.Thread(target=listen_mqtt_forever, args=(mqtt_client,), name="mqtt-loop", daemon=True)

    fb_thread.start()
    mqtt_thread.start()

    fb_thread.join()
    mqtt_thread.join()


# ===================================
if __name__ == "__main__":
    main()
