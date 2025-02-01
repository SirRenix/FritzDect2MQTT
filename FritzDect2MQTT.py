# coding: utf8

"""
# https://fritzconnection.readthedocs.io/en/1.13.2/sources/getting_started.html

# chrome-extension://gphandlahdpffmccakmbngmbjnjiiahp/https://avm.de/fileadmin/user_upload/Global/Service/Schnittstellen/AHA
# -HTTP-Interface.pdf
powershellcommand:
 .\mosquitto_pub.exe -h 192.168.xxx.xxx -p 1883 -t "home/devices/MyFritzBox/123456789" -m '{\"action\": \"set_switch\", \"data\": {\"AIN\": \"123456789\",\"switchstate\": \"True\"}}'
  .\mosquitto_sub.exe -h 192.168.xxx.xxx -p 1883 -t "#" -v
"""


import os
import time

import yaml
import logging.config
from logging import Logger
import xml.etree.ElementTree as ET
import threading

# from fritzconnection import FritzConnection                        # TR-064
from fritzconnection.core.fritzconnection import FritzConnection  # HTML
from fritzconnection.lib.fritzhomeauto import FritzHomeAutomation
from fritzconnection.core.exceptions import FritzServiceError, FritzHttpInterfaceError, FritzAuthorizationError

import MQTT

CONFIG_FILE_NAME_YAML = "configdata.cfg"
SECRETS_FILE_NAME_YAML = "secrets.yaml"

# --- Globals ---
configuration: dict
secrets: dict
logger: Logger

#load yaml file
def load_config_file(file_name):
    if not os.path.exists(file_name):
        raise NameError(f"File '{file_name}' is not accessible.")
    with open(file_name, 'rt', encoding="utf-8") as f:
        return yaml.safe_load(f.read())

def init_logging(config: str) -> Logger:
    """Initialize logging from configuration."""
    if "logging" not in config:
        raise Exception(f"No logging configuration in configuration file '{CONFIG_FILE_NAME_YAML}' available.")
    logging.config.dictConfig(config["logging"])
    return logging.getLogger("__main__")

def connect_to_fritzbox(fb_config: dict, max_tries: int = 10) -> FritzConnection:
    """Attempt to connect to the FritzBox, retrying on authorization errors."""
    connection_attempts = 0
    while connection_attempts < max_tries:
        try:
            return FritzConnection(
                address=fb_config["ip"],
                user=fb_config["user"],
                password=fb_config["password"],
                use_cache=True
            )
        except FritzAuthorizationError as fae:
            connection_attempts += 1
            logger.debug(f"Connection attempt {connection_attempts} failed: {fae}")
    raise FritzAuthorizationError("Max connection attempts reached.")

def parse_switch_list(fc: FritzConnection) -> list:
    """Retrieve and parse the list of switch identifiers from FritzBox."""
    result = fc.call_http("getswitchlist")
    switch_identifiers = result["content"].split(",")
    return [identifier.strip("\n") for identifier in switch_identifiers]

def get_selected_ains(config: dict, switch_identifiers: list) -> list:
    """Get the AINs to query from the configuration."""
    if configuration["QUERY"]["AINS"] == "ALL":
        return switch_identifiers
    else:
        return config["QUERY"]["AINS"]
    
def query_switch_data(fc: FritzConnection, ain: str)-> dict:
    """Query data for a specific switch identified by."""
    data = {"AIN": ain}

    result = fc.call_http("getswitchname", ain)
    data["name"] = result["content"].strip("\n")

    result = fc.call_http("gettemperature", ain)
    temp = result["content"].strip("\n")
    data["temp"] = float(temp) / 10 if temp.isdigit() else "NA"

    result = fc.call_http("getswitchpower", ain)
    power = result["content"].strip("\n")  
    data["power"] = float(power) / 1000 if power.isdigit() else "NA"

    result = fc.call_http("getswitchenergy", ain)
    energy = result["content"].strip("\n")
    data["allpower"] = float(energy) / 1000 if energy.isdigit() else "NA"

    result = fc.call_http("getbasicdevicestats", ain)
    parse_device_stats(result["content"], data)

    return data

def parse_device_stats(xml_data: str, data: dict):
    """Parse XML data from 'getbasicdevicestats' and update the data dictionary."""
    root = ET.fromstring(xml_data)
    voltage_element = root.find('voltage')
    if voltage_element is not None:
        stats = voltage_element.find('stats')
        if stats is not None:
            raw_voltage = stats.text.split(',')[0]
            try:
                voltage = float(raw_voltage[:-3] + '.' + raw_voltage[-1:])
                data["voltage"] = voltage
                if "power" in data and data["power"] != "NA":
                    data["current"] = round(data["power"] / voltage, 2)
            except ValueError:
                data["voltage_err"] = "NA"
    else:
        data["voltage_err"] = "NA"

def abfrage_fb(mqtt_con):
    """Main function to query FritzBox and send data via MQTT."""
    while True:
        try:
            if not mqtt_con.MQTTClient.is_connected():  
                logger.warning("MQTT not connected. Reconnecting...")
                time.sleep(5) # wait 5 seconds and try again
                continue

            fb_config = secrets["Fritzbox"][configuration["QUERY"]["FB"]]
            fc = connect_to_fritzbox(fb_config)

            switch_identifiers = parse_switch_list(fc)
            selected_ains = get_selected_ains(configuration, switch_identifiers)

            for ain in selected_ains:
                logger.info(f"Querying data for AIN '{ain}'")
                try:
                    mqtt_data = query_switch_data(fc, ain)
                    mqtt_con.sendData(ain, mqtt_data)
                except FritzHttpInterfaceError as fbintexp:
                    logger.error(f"AIN '{ain}' not exists on this FritzBox? {fbintexp}")

        except FritzServiceError as fbexp:
            logger.error(f"FritzServiceError: {fbexp}")
            logger.info("Reconnecting to FritzBox in 60sec...")
            time.sleep(60)
            
        except Exception as e:
            logger.error(f"Error querying FritzBox: {e}")
            logger.info("Reconnecting to FritzBox in 60sec...")
            time.sleep(60)

        looptime = configuration.get("QUERY", {}).get("looptime", 10) 
        time.sleep(looptime)

def action_handler(action_type, data):
    if action_type == "set_switch":
        ain = data.get("AIN")
        switchstate = data.get("switchstate")

        if ain and switchstate:
            # Logik zum Schalten des Geräts mit AIN
            print(f"Setting switch for AIN {ain} to {switchstate}")
            handle_set_switch(ain, switchstate)
            # Hier die eigentliche Schaltlogik hinzufügen
        else:
            print("AIN or switchstate missing in the data.")
    else:
        print(f"Unknown action type '{action_type}' received.")
        
    # """Handle specific actions received from MQTT."""
    # print(f"Received action '{action_type}' with data: {data}")
    # if action_type == "set_switch":
    #     handle_set_switch(data)
    # elif action_type == "log_message":
    #     handle_log_message(data)
    # else:
    #     print(f"Unknown action type '{action_type}' received.")

def handle_set_switch(ain: str, switchstate: str):
    """Handle the 'set_switch' action."""
    logger.info(f"Handling 'set_switch' action.AIN: {ain} switchstate: {switchstate}")

    if not isinstance(ain, str) or not isinstance(switchstate, str):
        logger.error("Invalid AIN or switchstate type.")
        return

    try:
        logger.debug(f"Sending switchstate: {switchstate}")
       
        # Verbinde zur FritzBox und ändere den Schalterzustand
        fb_config = secrets["Fritzbox"][configuration["QUERY"]["FB"]]
        fc = connect_to_fritzbox(fb_config)
        fh = FritzHomeAutomation(fc)

        if switchstate== "True" or switchstate == "on":
            logger.info(f"Switching AIN {ain} on")
            fh.set_switch(ain, on=True)
        elif switchstate == "False" or switchstate == "off":
            logger.info(f"Switching AIN {ain} off")
            fh.set_switch(ain, on=False)

    except Exception as e:
        logger.error(f"Error setting switch: {e}")

def handle_log_message(data):
    """Handle the 'log_message' action."""
    log_message = data.get("message", "No message provided")
    log_level = data.get("level", "info").lower()

    if log_level == "info":
        print(log_message)
    elif log_level == "warning":
        print(f"WARNING: {log_message}")
    elif log_level == "error":
        print(f"ERROR: {log_message}")
    else:
        print(f"DEBUG: {log_message}")

def listen_mqtt_forever(mqtt_client):
    """Endlessly listen for MQTT messages."""
    while True:
        try:
            mqtt_client.MQTTClient.loop_forever()
        except Exception as e:
            logger.error(f"Error in MQTT loop: {e}")
            try:
                mqtt_client.MQTTClient.reconnect()
                logger.info("Reconnected to MQTT broker.")
            except Exception as e:
                logger.error(f"Error reconnecting to MQTT broker: {e}")
                time.sleep(5)

# ---------------
def main():
    global configuration , secrets, logger

    configuration = load_config_file(CONFIG_FILE_NAME_YAML)
    secrets = load_config_file(SECRETS_FILE_NAME_YAML)

    logger = init_logging(configuration)
    
    logger.info("------------Start program ------------")
    logger.info(f"Used Configfile: '{CONFIG_FILE_NAME_YAML}'")

    # MQTT setup
    mqtt_client = MQTT.MQTT(configuration, secrets)
    mqtt_client.action_handler = action_handler
    mqtt_client.connect()

    # Starte den Thread für die FritzBox-Abfragen
    fb_thread = threading.Thread(target=abfrage_fb, args=(mqtt_client,))
    fb_thread.daemon = True

    # Starte den Thread für das MQTT-Listening
    mqtt_thread = threading.Thread(target=listen_mqtt_forever, args=(mqtt_client,))
    mqtt_thread.daemon = True

    #starte die Threads
    fb_thread.start()
    mqtt_thread.start()

    fb_thread.join()
    mqtt_thread.join()

# ===================================
if __name__ == '__main__':
    main()
