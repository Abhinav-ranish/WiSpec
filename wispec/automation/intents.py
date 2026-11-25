"""Turn "play that" / "turn the lamp off" + a pointing resolution into a Home Assistant service call.

Deliberately rule-based: the voice front-end (e.g. Home Assistant Assist)
does speech-to-text; this module only handles the deictic part ("that",
"this", "it") by substituting whatever the user is pointing at.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from wispec.room.room_map import Anchor, Resolution, RoomMap

DEICTIC = {"that", "this", "it", "there", "those", "these"}

# (pattern, action) — first match wins.
_ACTIONS = [
    (r"\b(play|resume)\b", "play"),
    (r"\b(pause|stop playing)\b", "pause"),
    (r"\b(turn|switch)\b.*\boff\b|\boff\b", "off"),
    (r"\b(turn|switch)\b.*\bon\b|\bon\b", "on"),
    (r"\b(start|run|clean)\b", "start"),
    (r"\b(stop|dock)\b", "stop"),
    (r"\btoggle\b", "toggle"),
]

# action -> domain -> (service domain, service)
_SERVICES = {
    "play":   {"media_player": ("media_player", "media_play")},
    "pause":  {"media_player": ("media_player", "media_pause")},
    "on":     {"*": ("homeassistant", "turn_on")},
    "off":    {"*": ("homeassistant", "turn_off")},
    "toggle": {"*": ("homeassistant", "toggle")},
    "start":  {"vacuum": ("vacuum", "start"), "media_player": ("media_player", "media_play"),
               "*": ("homeassistant", "turn_on")},
    "stop":   {"vacuum": ("vacuum", "return_to_base"), "media_player": ("media_player", "media_stop"),
               "*": ("homeassistant", "turn_off")},
}


@dataclass
class ServiceCall:
    domain: str
    service: str
    entity_id: str
    data: dict = field(default_factory=dict)


@dataclass
class IntentResult:
    call: ServiceCall | None
    action: str | None
    target: Anchor | None
    clarify: str | None = None    # question to ask back when ambiguous


def parse_action(text: str) -> str | None:
    t = text.lower()
    for pat, action in _ACTIONS:
        if re.search(pat, t):
            return action
    return None


def service_for(action: str, anchor: Anchor) -> ServiceCall | None:
    table = _SERVICES.get(action, {})
    svc = table.get(anchor.domain) or table.get("*")
    if not svc:
        return None
    return ServiceCall(svc[0], svc[1], anchor.entity_id)


def resolve_intent(text: str, room: RoomMap, pointing: Resolution | None) -> IntentResult:
    action = parse_action(text)
    if action is None:
        return IntentResult(None, None, None, clarify="Sorry, what should I do?")

    words = re.findall(r"[a-z]+", text.lower())
    named = next((a for w in words if (a := room.find(w)) is not None), None)
    target = named
    if target is None:   # "play that", or no object named at all -> use what they're pointing at
        if pointing is None or pointing.anchor is None:
            return IntentResult(None, action, None, clarify="What are you pointing at?")
        if pointing.ambiguous and len(pointing.candidates) > 1:
            a, b = pointing.candidates[0][0], pointing.candidates[1][0]
            return IntentResult(None, action, pointing.anchor, clarify=f"The {a} or the {b}?")
        target = pointing.anchor

    call = service_for(action, target)
    if call is None:
        return IntentResult(None, action, target, clarify=f"I can't {action} the {target.name}.")
    return IntentResult(call, action, target)
