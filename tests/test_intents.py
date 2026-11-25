from pathlib import Path

import numpy as np

from wispec.automation.home_assistant import HomeAssistant
from wispec.automation.intents import resolve_intent
from wispec.room.room_map import Resolution, RoomMap

ROOM = RoomMap.from_json(Path(__file__).parent.parent / "configs" / "room_example.json")


def pointing_at(name, ambiguous=False):
    a = ROOM.find(name)
    return Resolution(a, 2.0, ambiguous, [(name, 2.0), ("speaker", 6.0)])


def test_play_that_uses_pointed_device():
    r = resolve_intent("play that", ROOM, pointing_at("tv"))
    assert (r.call.domain, r.call.service, r.call.entity_id) == ("media_player", "media_play",
                                                                 "media_player.living_room_tv")


def test_named_device_overrides_pointing():
    r = resolve_intent("turn the lamp off", ROOM, pointing_at("tv"))
    assert (r.call.service, r.call.entity_id) == ("turn_off", "light.floor_lamp")


def test_start_that_on_vacuum():
    r = resolve_intent("start that", ROOM, pointing_at("vacuum"))
    assert (r.call.domain, r.call.service) == ("vacuum", "start")


def test_ambiguous_asks_back():
    r = resolve_intent("play that", ROOM, pointing_at("tv", ambiguous=True))
    assert r.call is None and "tv" in r.clarify and "speaker" in r.clarify


def test_not_pointing_asks_back():
    r = resolve_intent("turn that on", ROOM, None)
    assert r.call is None and r.clarify


def test_home_assistant_dry_run_without_token(monkeypatch):
    monkeypatch.delenv("HA_TOKEN", raising=False)
    r = resolve_intent("play that", ROOM, pointing_at("tv"))
    out = HomeAssistant().call(r.call)
    assert out["dry_run"] and out["endpoint"] == "/api/services/media_player/media_play"
