"""Smoke tests: modules import without side effects."""

import importlib


def test_import_mqtt_module():
    assert importlib.import_module("MQTT")


def test_import_main_module():
    mod = importlib.import_module("FritzDect2MQTT")
    assert callable(mod.main)
