#!/usr/bin/env python3
#
# Run with pytest

from typing import Optional, List
from pathlib import Path
from dataclasses import dataclass
import xml.etree

import os
import logging
import string
import pytest

from . import WacomDatabase, WacomDevice
from .conftest import load_test_db

logger = logging.getLogger(__name__)


def datadir():
    return Path(os.getenv("MESON_SOURCE_ROOT") or ".") / "data"


def layoutsdir():
    return datadir() / "layouts"


def load_svg(layoutfile: Path) -> xml.etree.ElementTree:
    try:
        f = layoutsdir() / layoutfile
        assert f.exists()
        tree = xml.etree.ElementTree.parse(f)
        assert tree is not None
        return tree
    except KeyError:
        pass
    return None


@dataclass
class SvgDevice:
    _db: WacomDatabase
    device: WacomDevice
    svg: xml.etree.ElementTree
    is_autogenerated: bool

    def has_item(self, id: str, classes: Optional[List[str]] = None):
        root = self.svg.getroot()
        nodes = root.findall(f".//*[@id='{id}']")
        assert nodes, f"Failed to find required element with id {id}"
        assert len(nodes) == 1, f"Expected one element with id {id}, have {len(nodes)}"
        node = nodes[0]
        for klass in classes or []:
            assert klass in node.get("class").split(
                " "
            ), f"Missing class '{klass}' for {id}. Have: {node.get('class')}"

    @property
    def name(self):
        return self.device.name


def is_autogenerated(svg_filename: Path):
    tabletfile = datadir() / svg_filename.name.replace(".svg", ".tablet")
    return (
        any("autogenerated" in t for t in open(tabletfile))
        if tabletfile.exists()
        else False
    )


def pytest_generate_tests(metafunc):
    # We need to keep the db inside each SvgDevice, otherwise python may clean it up
    # and thus invalidate all our devices from db.list_devices()
    db = load_test_db()
    devices = db.list_devices()
    devices = [
        SvgDevice(
            db,
            d,
            load_svg(d.layout_filename),
            is_autogenerated(Path(d.layout_filename)),
        )
        for d in devices
        if d.layout_filename
    ]
    devices = sorted(devices, key=lambda d: d.name)

    def filenames(devices: List[SvgDevice]) -> List[str]:
        return [Path(d.device.layout_filename).name for d in devices]

    if "svgdevice" in metafunc.fixturenames:
        metafunc.parametrize("svgdevice", devices, ids=filenames(devices))

    if "ringdevice" in metafunc.fixturenames:
        devices = list(filter(lambda d: d.device.num_rings > 0, devices))
        metafunc.parametrize("ringdevice", devices, ids=filenames(devices))

    if "stripdevice" in metafunc.fixturenames:
        devices = list(filter(lambda d: d.device.num_strips > 0, devices))
        metafunc.parametrize("stripdevice", devices, ids=filenames(devices))

    if "dialdevice" in metafunc.fixturenames:
        devices = list(filter(lambda d: d.device.num_dials > 0, devices))
        metafunc.parametrize("dialdevice", devices, ids=filenames(devices))

    if "buttondevice" in metafunc.fixturenames:
        devices = list(filter(lambda d: d.device.num_buttons > 0, devices))
        metafunc.parametrize("buttondevice", devices, ids=filenames(devices))


def test_svg(svgdevice):
    root = svgdevice.svg.getroot()
    assert root.tag in ["svg", "{http://www.w3.org/2000/svg}svg"]
    assert root.get("width") is not None
    assert root.get("height") is not None


def test_svg_maybe_not_needed(svgdevice):
    device = svgdevice.device
    features = [
        device.num_buttons,
        device.num_rings,
        device.num_strips,
        device.num_dials,
    ]
    assert any(
        x > 0 for x in features
    ), f"Device {device.name} has no buttons/rings/strips/dials and should not have an SVG"


def has_item(root, id: str, classes: Optional[List[str]] = None):
    nodes = root.findall(f".//*[@id='{id}']")
    assert nodes, f"Failed to find required element with id {id}"
    assert len(nodes) == 1, f"Expected on element with id {id}, have {len(nodes)}"
    node = nodes[0]
    for klass in classes or []:
        assert klass in node.get("class").split(
            " "
        ), f"Missing class '{klass}' for {id}. Have: {node.get('class')}"


def test_svg_rings(ringdevice):
    if ringdevice.device.num_rings >= 1:
        ringdevice.has_item(id="Ring", classes=["Ring", "TouchRing"])
        ringdevice.has_item(id="LabelRingCW", classes=["RingCW", "Ring", "Label"])
        ringdevice.has_item(id="LabelRingCCW", classes=["RingCCW", "Ring", "Label"])
        ringdevice.has_item(id="LeaderRingCW", classes=["RingCW", "Ring", "Leader"])
        ringdevice.has_item(id="LeaderRingCCW", classes=["RingCCW", "Ring", "Leader"])

    if ringdevice.device.num_rings >= 2:
        ringdevice.has_item(id="Ring2", classes=["Ring2", "TouchRing"])
        ringdevice.has_item(id="LabelRing2CW", classes=["Ring2CW", "Ring2", "Label"])
        ringdevice.has_item(id="LabelRing2CCW", classes=["Ring2CCW", "Ring2", "Label"])
        ringdevice.has_item(id="LeaderRing2CW", classes=["Ring2CW", "Ring2", "Leader"])
        ringdevice.has_item(
            id="LeaderRing2CCW", classes=["Ring2CCW", "Ring2", "Leader"]
        )


def test_svg_strips(stripdevice):
    try:
        if stripdevice.device.num_strips >= 1:
            stripdevice.has_item(id="Strip", classes=["Strip", "TouchStrip"])
            stripdevice.has_item(
                id="LabelStripUp", classes=["StripUp", "Strip", "Label"]
            )
            stripdevice.has_item(
                id="LabelStripDown", classes=["StripDown", "Strip", "Label"]
            )
            stripdevice.has_item(
                id="LeaderStripUp", classes=["StripUp", "Strip", "Leader"]
            )
            stripdevice.has_item(
                id="LeaderStripDown", classes=["StripDown", "Strip", "Leader"]
            )

        if stripdevice.device.num_strips >= 2:
            stripdevice.has_item(id="Strip2", classes=["Strip2", "TouchStrip"])
            stripdevice.has_item(
                id="LabelStrip2Up", classes=["Strip2Up", "Strip2", "Label"]
            )
            stripdevice.has_item(
                id="LabelStrip2Down", classes=["Strip2Down", "Strip2", "Label"]
            )
            stripdevice.has_item(
                id="LeaderStrip2Up", classes=["Strip2Up", "Strip2", "Leader"]
            )
            stripdevice.has_item(
                id="LeaderStrip2Down", classes=["Strip2Down", "Strip2", "Leader"]
            )
    except AssertionError as e:
        if stripdevice.is_autogenerated:
            pytest.skip(f"Autogenerated device has errors in SVG: {e}")
        raise e


def test_svg_dials(dialdevice):
    try:
        if dialdevice.device.num_dials >= 1:
            dialdevice.has_item(id="Dial", classes=["Dial", "TouchDial"])
            dialdevice.has_item(id="LabelDialCW", classes=["DialCW", "Dial", "Label"])
            dialdevice.has_item(id="LabelDialCCW", classes=["DialCCW", "Dial", "Label"])
            dialdevice.has_item(id="LeaderDialCW", classes=["DialCW", "Dial", "Leader"])
            dialdevice.has_item(
                id="LeaderDialCCW", classes=["DialCCW", "Dial", "Leader"]
            )

        if dialdevice.device.num_dials >= 2:
            dialdevice.has_item(id="Dial2", classes=["Dial2", "TouchDial"])
            dialdevice.has_item(
                id="LabelDial2CW", classes=["Dial2CW", "Dial2", "Label"]
            )
            dialdevice.has_item(
                id="LabelDial2CCW", classes=["Dial2CCW", "Dial2", "Label"]
            )
            dialdevice.has_item(
                id="LeaderDial2CW", classes=["Dial2CW", "Dial2", "Leader"]
            )
            dialdevice.has_item(
                id="LeaderDial2CCW", classes=["Dial2CCW", "Dial2", "Leader"]
            )
    except AssertionError as e:
        if dialdevice.is_autogenerated:
            pytest.skip(f"Autogenerated device has errors in SVG: {e}")
        raise e


def test_svg_button(buttondevice):
    for button in list(string.ascii_uppercase)[: buttondevice.device.num_buttons]:
        modeswitch_label = []
        flags = buttondevice.device.button_flags(button)
        if any(f in flags for f in WacomDevice.ButtonFlags.modeswitch_flags()):
            modeswitch_label = ["ModeSwitch"]
        buttondevice.has_item(
            id=f"Button{button}", classes=["Button", button] + modeswitch_label
        )
        buttondevice.has_item(
            id=f"Label{button}", classes=["Label", button] + modeswitch_label
        )
        buttondevice.has_item(
            id=f"Leader{button}", classes=["Leader", button] + modeswitch_label
        )
