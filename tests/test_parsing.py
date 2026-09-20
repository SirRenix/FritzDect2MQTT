"""Unit tests for the pure parsing / conversion helpers (no FritzBox, no broker)."""

import json

import pytest

import FritzDect2MQTT as app


# --- _to_number -------------------------------------------------------------

@pytest.mark.parametrize(
    "raw, divisor, expected",
    [
        ("215", 10, 21.5),
        ("-35\n", 10, -3.5),  # negative temperatures are valid (regression: isdigit() rejected them)
        ("7460", 1000, 7.46),
        ("0", 1000, 0.0),
        ("inval", 10, None),
        ("", 10, None),
        (None, 10, None),
    ],
)
def test_to_number(raw, divisor, expected):
    assert app._to_number(raw, divisor) == expected


# --- parse_device_stats -----------------------------------------------------

STATS_XML = """<devicestats>
  <temperature><stats count="96" grid="900">210,215,220</stats></temperature>
  <voltage><stats count="360" grid="10">233412,233500,233100</stats></voltage>
  <power><stats count="360" grid="10">7460,7500</stats></power>
</devicestats>"""


def test_parse_device_stats_voltage_and_current():
    data = {"power": 7.46}
    app.parse_device_stats(STATS_XML, data)
    # 233412 mV -> 233.412 V (regression: old code produced 233.2)
    assert data["voltage"] == pytest.approx(233.412)
    assert data["current"] == pytest.approx(round(7.46 / 233.412, 3))


def test_parse_device_stats_without_voltage_block():
    data = {"power": 7.46}
    app.parse_device_stats("<devicestats><temperature/></devicestats>", data)
    assert data["voltage"] is None
    assert data["current"] is None


def test_parse_device_stats_empty_stats_text():
    data = {"power": 7.46}
    app.parse_device_stats("<devicestats><voltage><stats/></voltage></devicestats>", data)
    assert data["voltage"] is None
    assert data["current"] is None


def test_parse_device_stats_power_unavailable():
    data = {"power": None}
    app.parse_device_stats(STATS_XML, data)
    assert data["voltage"] == pytest.approx(233.412)
    assert data["current"] is None


def test_parse_device_stats_invalid_xml_raises_parse_error():
    import xml.etree.ElementTree as ET

    with pytest.raises(ET.ParseError):
        app.parse_device_stats("<not xml", {})


# --- _parse_switchstate -----------------------------------------------------

@pytest.mark.parametrize("value", [True, "true", "True", "on", "ON", "1", " on "])
def test_parse_switchstate_on(value):
    assert app._parse_switchstate(value) is True


@pytest.mark.parametrize("value", [False, "false", "off", "0"])
def test_parse_switchstate_off(value):
    assert app._parse_switchstate(value) is False


def test_parse_switchstate_invalid():
    with pytest.raises(ValueError):
        app._parse_switchstate("maybe")


# --- get_selected_ains / parse_switch_list -----------------------------------

def test_get_selected_ains_all_and_list():
    assert app.get_selected_ains({"QUERY": {"AINS": "ALL"}}, ["1", "2"]) == ["1", "2"]
    assert app.get_selected_ains({"QUERY": {"AINS": [116570123456]}}, ["1"]) == ["116570123456"]


class _FakeFC:
    def __init__(self, responses):
        self.responses = responses

    def call_http(self, command, identifier=None):
        return {"content": self.responses[command]}


def test_parse_switch_list_strips_and_drops_empty():
    fc = _FakeFC({"getswitchlist": "116570123456,116570654321\n"})
    assert app.parse_switch_list(fc) == ["116570123456", "116570654321"]


def test_query_switch_data_payload_is_json_serialisable():
    fc = _FakeFC(
        {
            "getswitchname": "Printer\n",
            "gettemperature": "-15\n",
            "getswitchpower": "inval\n",
            "getswitchenergy": "29400\n",
            "getbasicdevicestats": STATS_XML,
        }
    )
    data = app.query_switch_data(fc, "116570123456")
    assert data["name"] == "Printer"
    assert data["temp"] == -1.5
    assert data["power"] is None
    assert data["allpower"] == 29.4
    assert data["voltage"] == pytest.approx(233.412)
    assert data["current"] is None
    assert json.loads(json.dumps(data))["power"] is None  # "NA" strings are gone
