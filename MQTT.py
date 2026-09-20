"""Thin paho-mqtt wrapper: connect, publish state, receive switch commands."""

import json
import logging.config

import paho.mqtt.client as mqttClient


class MQTT:
    def __init__(self, ConfigData: dict = None, SecretData: dict = None):
        if ConfigData is None:
            raise ValueError("No config data given")
        if SecretData is None:
            raise ValueError("No secret data given")

        self.mqttConfData = ConfigData["MQTT"]
        # Which broker entry under MQTT_BROKER in secrets.yaml to use.
        # Configurable via MQTT.broker, defaults to "RASPI" for compatibility.
        broker_key = self.mqttConfData.get("broker", "RASPI")
        self.mqttSecData = SecretData["MQTT_BROKER"][broker_key]
        self.fritzbox = ConfigData["QUERY"]["FB"]

        # Command topic for incoming switch commands. Kept separate from the
        # state/publish tree (maintoken) so the client does not receive its own
        # published messages back (which would be parsed as invalid commands).
        cmd_token = self.mqttConfData.get("cmdtoken", "cmd/FB")
        self.cmd_topic = f"{cmd_token}/{self.fritzbox}/#"

        self.logger = logging.getLogger(__name__)

        self.MQTTClient = mqttClient.Client(
            mqttClient.CallbackAPIVersion.VERSION2,
            client_id=self.mqttConfData["clientId"],
        )
        # paho's loop_forever() reconnects on its own with this back-off; no
        # manual reconnect logic in callbacks (that would block the network loop).
        self.MQTTClient.reconnect_delay_set(min_delay=1, max_delay=60)

        if self.mqttSecData["user"] and self.mqttSecData["password"]:
            self.MQTTClient.username_pw_set(self.mqttSecData["user"], self.mqttSecData["password"])

        self.MQTTClient.on_connect = self.on_connect
        self.MQTTClient.on_disconnect = self.on_disconnect
        self.MQTTClient.on_message = self.receiveData
        self.MQTTClient.enable_logger(self.logger)

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            self.logger.info("Connected to MQTT Broker")
            client.subscribe(self.cmd_topic)
            self.logger.info(f"Subscribed to command topic '{self.cmd_topic}'")
        else:
            self.logger.error(f"Failed to connect to MQTT Broker: {reason_code}")

    def on_disconnect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            self.logger.info("Disconnected from MQTT Broker")
        else:
            self.logger.warning(f"Disconnected from MQTT Broker ({reason_code}); paho will reconnect")

    def connect(self):
        try:
            retCode = self.MQTTClient.connect(str(self.mqttSecData["ip"]), int(self.mqttSecData["port"]))
            if retCode == 0:
                self.logger.info("Connection successful")
            else:
                self.logger.error(f"Failed to connect to broker {self.mqttSecData['ip']}:"
                                  f"{self.mqttSecData['port']} (retCode={retCode})")
        except Exception as err:
            self.logger.error(f"Connection error: {err} (will keep retrying in the background)")
        return self.MQTTClient

    def sendData(self, addTopic: str = "", sendData: dict = None):
        if sendData is None:
            raise ValueError("No data to send given")

        currentTopic = self.mqttConfData["maintoken"] + "/" + self.fritzbox + "/" + addTopic

        self.logger.debug(f"Current topic: '{currentTopic}'")

        sendString = json.dumps(sendData, ensure_ascii=False)
        result = self.MQTTClient.publish(currentTopic, sendString)

        if result.rc == mqttClient.MQTT_ERR_SUCCESS:
            self.logger.debug(f"Sent '{sendString}' to topic '{currentTopic}'")
        else:
            self.logger.error(f"Failed to send to topic '{currentTopic}': {mqttClient.error_string(result.rc)}")

    def receiveData(self, client, userdata, message):
        try:
            raw_payload = message.payload.decode("utf-8")
            self.logger.debug(f"Received on topic {message.topic}: {raw_payload}")

            payload = json.loads(raw_payload)
            action_type = payload.get("action", None)
            data = payload.get("data", None)

            if not action_type or data is None:
                self.logger.error(f"Invalid message received: {raw_payload}")
                return

            # The AIN in the topic and in the payload should agree.
            topic_ain = message.topic.rsplit("/", 1)[-1]
            if isinstance(data, dict) and data.get("AIN") and str(data["AIN"]) != topic_ain:
                self.logger.warning(f"AIN in payload ({data['AIN']}) differs from topic ({topic_ain}); using payload")

            if hasattr(self, "action_handler"):
                self.action_handler(action_type, data)
            else:
                self.logger.warning("No action handler defined in MQTT class.")

        except (UnicodeDecodeError, json.JSONDecodeError, AttributeError) as e:
            self.logger.error(f"Failed to decode message on {message.topic}: {e}")
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
