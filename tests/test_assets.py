"""The logo files the passcode screen and browser tab rely on."""
import os
import xml.etree.ElementTree as ET

ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")


def test_logo_svg_is_valid_and_self_contained():
    root = ET.parse(os.path.join(ASSETS, "logo.svg")).getroot()
    assert root.tag.endswith("svg")
    assert "viewBox" in root.attrib
    svg = open(os.path.join(ASSETS, "logo.svg")).read()
    assert "<text" not in svg and "<image" not in svg  # outlined text, no external fonts or images


def test_logo_pngs_exist():
    for name in ("logo.png", "logo-mark.png"):
        with open(os.path.join(ASSETS, name), "rb") as f:
            assert f.read(8) == b"\x89PNG\r\n\x1a\n", name
