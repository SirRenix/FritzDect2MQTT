import logging.config
import json
import time
import paho.mqtt.client as mqttClient

class MQTT:
    def __init__(self, ConfigData: dict = None, SecretData: dict = None):
        assert (ConfigData is not None), "No config data given"
        assert (SecretData is not None), "No secret data given"

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

        self.MQTTClient = mqttClient.Client(client_id=self.mqttConfData["clientId"])

        if self.mqttSecData["user"] and self.mqttSecData["password"]:
            self.MQTTClient.username_pw_set(self.mqttSecData["user"], self.mqttSecData["password"])

        self.MQTTClient.on_connect = self.on_connect
        self.MQTTClient.on_disconnect = self.on_disconnect
        self.MQTTClient.on_message = self.receiveData
        self.MQTTClient.enable_logger(self.logger)

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.logger.info("Connected to MQTT Broker")
            client.subscribe(self.cmd_topic)
            self.logger.info(f"Subscribed to command topic '{self.cmd_topic}'")
        else:
            self.logger.error(f"Failed to connect to MQTT Broker, return code {rc}")

    def on_disconnect(self, client, userdata, rc):
        FIRST_RECONNECT_DELAY = 1
        RECONNECT_RATE = 2
        MAX_RECONNECT_COUNT = 12
        MAX_RECONNECT_DELAY = 60

        self.logger.warning("Disconnected with result code: %s", rc)
        reconnect_count, reconnect_delay = 0, FIRST_RECONNECT_DELAY
        while reconnect_count < MAX_RECONNECT_COUNT:
            self.logger.warning("Reconnecting in %d seconds...", reconnect_delay)
            time.sleep(reconnect_delay)

            try:
                client.reconnect()
                self.logger.info("Reconnected successfully!")
                return
            except Exception as myErr:
                self.logger.error(f"{myErr}. Reconnect failed. Retrying...")

            reconnect_delay *= RECONNECT_RATE
            reconnect_delay = min(reconnect_delay, MAX_RECONNECT_DELAY)
            reconnect_count += 1

        self.logger.warning("Reconnect failed after %s attempts. Exiting...", reconnect_count)

    def connect(self):
        try:
            retCode = self.MQTTClient.connect(str(self.mqttSecData["ip"]), int(self.mqttSecData["port"]))
            if retCode == 0:
                self.logger.info("Connection successful")
            else:
                self.logger.error(f"Failed to connect to broker {self.mqttSecData['ip']}:"
                                  f"{self.mqttSecData['port']} (retCode={retCode})")
        except Exception as err:
            self.logger.error(f"Connection error: {err}")
        return self.MQTTClient

    def sendData(self, addTopic: str = "", sendData: dict = None):
        assert (sendData is not None), "No data to send given"

        currentTopic = self.mqttConfData["maintoken"] + "/" + self.fritzbox + "/" + addTopic

        self.logger.debug(f"Current topic: '{currentTopic}'")

        sendString = json.dumps(sendData, ensure_ascii=False)
        result = self.MQTTClient.publish(currentTopic, sendString)

        if result[0] == 0:
            self.logger.debug(f"Sent '{sendString}' to topic '{currentTopic}'")
        else:
            self.logger.error(f"Failed to send message to topic '{currentTopic}'")

    def receiveData(self, client, userdata, message):
        raw_payload = message.payload.decode("utf-8")
        self.logger.debug(f"Received on topic {message.topic}: {raw_payload}")

        try:
            payload = json.loads(raw_payload)
            action_type = payload.get("action", None)
            data = payload.get("data", None)

            if not action_type or data is None:
                self.logger.error(f"Invalid message received: {message.payload}")
                return

            if hasattr(self, 'action_handler'):
                self.action_handler(action_type, data)
            else:
                self.logger.warning("No action handler defined in MQTT class.")

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to decode JSON: {e}")
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
