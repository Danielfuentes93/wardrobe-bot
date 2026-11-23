"""Fashionista core logic (extracted from wardrobe_app.ipynb).

Public (multi-user) edition: pure standard library, no file I/O at all.  Every visitor's closet, style
profile and chat live in memory (the Streamlit session); the LLM client is created by guards.py, which
also enforces the message limits, so this module never reads API keys or environment variables.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import date, timedelta
from itertools import product

# ---------------------------------------------------------------- vocab
TYPES = ["top", "bottom", "outer", "shoes", "dress"]
LAYERS = ["base", "mid-layer", "outer", "bottom", "shoes"]
COLORS = ["blue", "black", "white", "brown", "other"]
WARMTH = {"light": 1, "mid": 2, "heavy": 3}
DRESSINESS = {"casual": 1, "office": 2, "formal": 3}
ICON = {"top": "👚", "bottom": "👖", "outer": "🧥", "shoes": "👢", "dress": "👗"}
SWATCH = {"blue": "#2f4a6d", "black": "#2b2b2b", "white": "#ece7df", "brown": "#8a5a3c", "other": "#a99f94"}
COLOR_NAMES = {"blue": "navy", "black": "noir", "white": "crisp", "brown": "earthy", "other": "mixed"}
STYLE_WORDS = ["balance", "edit", "classic", "uniform", "mix"]
MIN_ITEMS = 8
NO_REASONS = ["too hot", "too formal", "wrong pieces", "don't own it", "ban this item"]
# rain gear is recognised from the garment name (there is no "waterproof" field yet)
RAIN_OUTER_WORDS = ("rain", "trench", "mac", "parka", "shell", "waterproof", "anorak", "slicker", "poncho")
RAIN_BAD_SHOE_WORDS = ("sneaker", "trainer", "canvas", "suede", "sandal", "espadrille", "slipper", "satin", "heel")

log = logging.getLogger("fashionista")


def today() -> date:
    return date.today()


def _name_has(g, words) -> bool:
    return any(re.search(rf"\b{w}", g.name.lower()) for w in words)


def is_rain_outer(g) -> bool:
    """An outer layer that keeps you dry (raincoat, trench, mac, parka...)."""
    return g.layer == "outer" and _name_has(g, RAIN_OUTER_WORDS)


def is_rain_bad_shoe(g) -> bool:
    """Shoes that get ruined or soaked in the rain (sneakers, suede, sandals...)."""
    return g.type == "shoes" and _name_has(g, RAIN_BAD_SHOE_WORDS)


# ---------------------------------------------------------------- occasions
# What the user says they're doing ("I want to work out", "job interview", "wedding").  Garments have no tags
# yet, so suitability is read from the garment name + type + dressiness, the same way rain gear is.
# Patterns are regexes matched on the lowercased message; the FIRST occasion that matches wins, so
# "workout" is checked before "office" (otherwise "work out" reads as "work").
OCCASIONS = {
    "workout": {
        "label": "a workout",
        "patterns": [r"\bwork(?:ing)?[\s-]?outs?\b", r"\bgym\b", r"\bexercis", r"\brun(?:s|ning)?\b", r"\bjog",
                     r"\byoga\b", r"\bpilates\b", r"\bspin class", r"\bcardio\b", r"\bcrossfit\b",
                     r"\blift(?:ing)? weights\b", r"\bweightlifting\b", r"\btraining\b", r"\bhik(?:e|ing)\b",
                     r"\btennis\b", r"\bbasketball\b", r"\bsoccer\b", r"\bbike ride\b", r"\bcycling\b",
                     r"\bsweat(?:y)?\b", r"\bfitness\b", r"\bboxing\b", r"\bclimbing\b"],
        "plans": "off duty", "dressiness": 1,
        # every piece must look athletic; a plain tee/tank is fine on top
        "require": {
            "top": ("tee", "t-shirt", "tshirt", "tank", "sports bra", "bra", "hoodie", "sweatshirt", "athletic",
                    "gym", "running", "performance", "dri", "workout", "training", "jersey", "active",
                    "compression", "quarter-zip", "crop"),
            "bottom": ("legging", "jogger", "sweatpant", "sweats", "track", "short", "athletic", "gym", "running",
                       "yoga", "compression", "tights", "active", "workout", "training", "bike short"),
            "shoes": ("sneaker", "trainer", "running", "athletic", "gym", "cross", "tennis", "basketball",
                      "workout", "training", "hiking", "trail"),
            "mid-layer": ("hoodie", "sweatshirt", "fleece", "quarter-zip", "track", "athletic", "running", "zip"),
            "outer": ("windbreaker", "track", "running", "shell", "rain", "anorak", "athletic", "hoodie", "fleece"),
        },
        "exclude": ("jean", "denim", "tailored", "trouser", "slack", "chino", "blazer", "suit", "silk", "satin",
                    "blouse", "camisole", "loafer", "oxford", "heel", "pump", "derby", "wool", "cashmere",
                    "leather", "ankle boot", "dress", "button", "pencil", "cardigan"),
        "no_dresses": True, "no_formal": True,
        "add": {"top": "a workout top (athletic tee, tank or sports bra)",
                "bottom": "workout bottoms (leggings, gym shorts or joggers)",
                "shoes": "athletic shoes (running shoes or trainers)"},
        "note": "The user is going to WORK OUT / exercise. Only athletic pieces: sneakers or trainers, leggings, "
                "gym shorts, joggers or sweatpants, tees, tanks, sports bras, hoodies. NEVER jeans, tailored pants, "
                "trousers, chinos, blazers, silk, dresses, boots, loafers or other dress shoes.",
    },
    "interview": {
        "label": "an interview",
        "patterns": [r"\binterview"],
        "plans": "work", "dressiness": 2.6,
        "exclude": ("sneaker", "trainer", "jean", "denim", "tee", "t-shirt", "tank", "hoodie", "sweat", "legging",
                    "jogger", "short", "athletic", "gym", "flip", "sandal", "crop"),
        "add": {"top": "a crisp shirt or blouse", "bottom": "tailored trousers or a skirt",
                "shoes": "polished shoes (loafers, oxfords or low heels)"},
        "note": "Job interview: polished, office-to-formal pieces. No sneakers, jeans, tees, hoodies or athletic wear.",
    },
    "wedding": {
        "label": "a wedding or formal event",
        "patterns": [r"\bwedding", r"\bgala\b", r"\bblack[\s-]tie", r"\bformal\b", r"\bcocktail", r"\bfuneral",
                     r"\bceremony\b"],
        "plans": "work", "dressiness": 3,
        "exclude": ("sneaker", "trainer", "jean", "denim", "tee", "t-shirt", "tank", "hoodie", "sweat", "legging",
                    "jogger", "short", "athletic", "gym", "flip", "sandal", "parka", "puffer"),
        "no_casual": True,
        "add": {"top": "a dressy top or shirt", "bottom": "dress trousers or a skirt", "dress": "a formal dress",
                "shoes": "dress shoes or heels"},
        "note": "Wedding / formal event: the dressiest pieces in the closet. No casual or athletic wear.",
    },
    "office": {
        "label": "work",
        "patterns": [r"\boffice\b", r"\bmeeting", r"\bbusiness\b", r"\bwork(?:ing|day)?\b", r"\bpresentation",
                     r"\bconference\b", r"\bclient"],
        "plans": "work", "dressiness": 2,
        "exclude": ("athletic", "gym", "legging", "jogger", "sweatpant", "sweats", "running", "workout", "hoodie",
                    "flip", "sports bra"),
        "add": {"top": "an office top (shirt or blouse)", "bottom": "trousers or a skirt",
                "shoes": "office shoes (loafers or boots)"},
        "note": "Work / office: office-appropriate pieces. No athletic wear or hoodies.",
    },
    "date": {
        "label": "a date",
        "patterns": [r"\bdate\b", r"\bdate night", r"\bromantic", r"\banniversary"],
        "plans": "off duty", "dressiness": 1.8,
        "exclude": ("athletic", "gym", "legging", "jogger", "sweatpant", "sweats", "running", "workout", "hoodie",
                    "flip", "sports bra"),
        "add": {"top": "a nice top", "bottom": "dark jeans or trousers", "shoes": "clean shoes or boots"},
        "note": "Date: put-together, a step above casual. No gym wear or hoodies.",
    },
    "party": {
        "label": "a night out",
        "patterns": [r"\bpart(?:y|ies)\b", r"\bhappy hour", r"\bdrinks\b", r"\bbar\b", r"\bclub", r"\bnight out",
                     r"\bconcert"],
        "plans": "off duty", "dressiness": 1.7,
        "exclude": ("athletic", "gym", "legging", "jogger", "sweatpant", "sweats", "running", "workout",
                    "flip", "sports bra"),
        "add": {"top": "a going-out top", "bottom": "dark jeans or trousers", "shoes": "boots or clean sneakers"},
        "note": "Party / happy hour / night out: social and a bit dressed up. No gym wear.",
    },
    "travel": {
        "label": "travel",
        "patterns": [r"\btravel", r"\bflight\b", r"\bflying\b", r"\bairport", r"\bplane\b", r"\broad trip",
                     r"\btrain ride"],
        "plans": "off duty", "dressiness": 1,
        "exclude": ("heel", "pump", "silk", "satin", "tailored", "blazer", "camisole"),
        "add": {"top": "a comfy layer-friendly top", "bottom": "comfortable pants or joggers",
                "shoes": "comfortable walking shoes"},
        "note": "Travel: comfortable, easy to layer and walk in. No heels, silk or stiff tailoring.",
    },
    "lounge": {
        "label": "lounging at home",
        "patterns": [r"\blounge", r"\blounging", r"\bstay(?:ing)? (?:in|home)", r"\bat home\b", r"\bchill",
                     r"\bcouch", r"\bnetflix", r"\bcozy"],
        "plans": "off duty", "dressiness": 1,
        "exclude": ("heel", "pump", "silk", "satin", "tailored", "blazer", "camisole", "loafer", "oxford", "wool coat",
                    "trouser"),
        "no_formal": True,
        "add": {"top": "a soft tee or sweatshirt", "bottom": "sweatpants, joggers or leggings",
                "shoes": "slippers or easy sneakers"},
        "note": "Lounging / staying in: comfy and relaxed. No tailoring, silk or dress shoes.",
    },
    "casual": {
        "label": "a casual day",
        "patterns": [r"\bweekend", r"\bcasual", r"\boff[\s-]duty", r"\bbrunch", r"\berrands?\b", r"\brelax"],
        "plans": "off duty", "dressiness": 1,
        "exclude": (),
        "add": {"top": "a casual top", "bottom": "jeans or casual pants", "shoes": "sneakers"},
        "note": "Casual day: relaxed everyday pieces.",
    },
}
RAIN_RE = re.compile(r"\b(?:rain\w*|storm\w*|drizzl\w*|downpour|wet weather)\b")


def detect_occasion(message) -> str | None:
    m = str(message).lower()
    for key, o in OCCASIONS.items():
        if any(re.search(p, m) for p in o["patterns"]):
            return key
    return None


def suits_occasion(g, occasion) -> bool:
    """Can this garment be worn for the occasion?  None/unknown occasion allows everything."""
    o = OCCASIONS.get(occasion)
    if o is None:
        return True
    if _name_has(g, o.get("exclude", ())):
        return False
    if o.get("no_dresses") and g.type == "dress":
        return False
    if o.get("no_formal") and g.dressiness == "formal":
        return False
    if o.get("no_casual") and g.dressiness == "casual":
        return False
    req = o.get("require")
    if req:
        words = req.get(g.layer if g.layer in ("mid-layer", "outer") else g.type)
        if words is None or not _name_has(g, words):
            return False
    return True


def occasion_gaps(wardrobe, occasion) -> list[str]:
    """What's missing to dress for the occasion at all (empty list = the closet can do it)."""
    o = OCCASIONS.get(occasion)
    if o is None:
        return []
    ok = [g for g in wardrobe.available() if suits_occasion(g, occasion)]
    has = {t: any(g.type == t and (t != "top" or g.layer == "base") for g in ok) for t in TYPES}
    missing = []
    if not has["dress"] or o.get("no_dresses"):
        missing += [t for t in ("top", "bottom") if not has[t]]
    if not has["shoes"]:
        missing.append("shoes")
    return [o["add"].get(t, t) for t in missing]


def default_layer(gtype: str) -> str:
    return {"top": "base", "dress": "base", "bottom": "bottom", "shoes": "shoes", "outer": "outer"}[gtype]


# ---------------------------------------------------------------- data model
@dataclass
class Garment:
    id: int
    name: str
    type: str
    layer: str
    color_group: str
    warmth: str = "mid"
    dressiness: str = "casual"
    banned: bool = False
    times_worn: int = 0
    last_worn: date | None = None
    has_photo: bool = False  # the photo bytes live in the visitor's session (st.session_state), never on disk

    def __post_init__(self):
        assert self.type in TYPES, f"bad type {self.type}"
        assert self.layer in LAYERS, f"bad layer {self.layer}"
        assert self.color_group in COLORS, f"bad color {self.color_group}"
        assert self.warmth in WARMTH and self.dressiness in DRESSINESS

    def days_since_worn(self) -> int:
        return 999 if self.last_worn is None else (today() - self.last_worn).days



class Wardrobe:
    def __init__(self):
        self.items: dict[int, Garment] = {}

    def next_id(self) -> int:
        return max(self.items, default=0) + 1

    def add_item(self, g: Garment):
        self.items[g.id] = g

    def remove(self, item_id: int):
        return self.items.pop(item_id, None)

    def ban_item(self, item_id: int, banned: bool = True):
        self.items[item_id].banned = banned

    def available(self):
        return [g for g in self.items.values() if not g.banned]

    def grouped_by_layer(self):
        groups = {layer: [] for layer in LAYERS}
        for g in self.items.values():
            groups[g.layer].append(g)
        return groups



def sample_closet() -> Wardrobe:
    ago = lambda n: today() - timedelta(days=n)
    w = Wardrobe()
    for g in [
        Garment(1, "Classic Silk Blouse", "top", "base", "blue", "light", "office", times_worn=6, last_worn=ago(9)),
        Garment(2, "Linen Blazer", "outer", "mid-layer", "white", "light", "office", times_worn=4, last_worn=ago(12)),
        Garment(3, "Wide Trousers", "bottom", "bottom", "black", "mid", "office", times_worn=8, last_worn=ago(1)),
        Garment(4, "Ankle Boots", "shoes", "shoes", "brown", "mid", "office", times_worn=10, last_worn=ago(3)),
        Garment(5, "Silk Camisole", "top", "base", "black", "light", "formal", times_worn=2, last_worn=ago(35)),
        Garment(6, "Knit Sweater", "top", "mid-layer", "brown", "heavy", "casual", times_worn=5, last_worn=ago(6)),
        Garment(7, "Tailored Pants", "bottom", "bottom", "blue", "mid", "office", times_worn=3, last_worn=ago(32)),
        Garment(8, "Ribbed Knit Dress", "dress", "base", "black", "mid", "office", times_worn=2, last_worn=ago(30)),
        Garment(9, "Loafers", "shoes", "shoes", "black", "light", "office", times_worn=7, last_worn=ago(1)),
        Garment(10, "Navy Tee", "top", "base", "blue", "light", "casual", times_worn=12, last_worn=ago(1)),
        Garment(11, "Wool Coat", "outer", "outer", "blue", "heavy", "office", times_worn=1, last_worn=ago(200)),
        Garment(12, "Dark Jeans", "bottom", "bottom", "blue", "mid", "casual", times_worn=9, last_worn=ago(4)),
        Garment(13, "White Sneakers", "shoes", "shoes", "white", "light", "casual", times_worn=5, last_worn=ago(40)),
    ]:
        w.add_item(g)
    return w


@dataclass
class OutfitRequest:
    plans: str = "work"  # "work" or "off duty"
    temp_f: int = 58  # used for scoring; only shown to the user when temp_given is True
    condition: str = "dry"  # "dry" or "rain"
    temp_given: bool = True  # False when the chat message gave no temperature (58 is then just an assumption)
    no_repeat_yesterday: bool = True
    color_theme: str | None = None
    min_days_unworn: int = 0
    occasion: str | None = None  # a key of OCCASIONS (set by the chat parser); None = plain Work/Off duty

    def target_dressiness(self):
        if self.occasion in OCCASIONS:
            return OCCASIONS[self.occasion]["dressiness"]
        return DRESSINESS["office"] if self.plans == "work" else DRESSINESS["casual"]

    def target_warmth(self):
        return 1 if self.temp_f >= 70 else 2 if self.temp_f >= 50 else 3


# ---------------------------------------------------------------- style profile
class StyleProfile:
    LEARNING_RATE = 0.5
    DECAY = 0.9

    def __init__(self):
        self.weights: dict[str, float] = {}
        self.banned_ids: set[int] = set()
        self.events = 0

    @staticmethod
    def attributes(g: Garment):
        return [f"color:{g.color_group}", f"warmth:{g.warmth}", f"dress:{g.dressiness}", f"type:{g.type}", f"id:{g.id}"]

    def _nudge(self, key, amount):
        self.weights[key] = self.weights.get(key, 0.0) + self.LEARNING_RATE * amount

    def update(self, items, action, reason=None):
        for k in self.weights:
            self.weights[k] *= self.DECAY
        self.events += 1
        if action == "wear":
            for g in items:
                for a in self.attributes(g):
                    self._nudge(a, +1)
        elif action == "skip":
            for g in items:
                for a in self.attributes(g):
                    self._nudge(a, -0.3)
        elif action == "no":
            if reason == "too formal":
                self._nudge("dress:formal", -1.5); self._nudge("dress:office", -1); self._nudge("dress:casual", +0.5)
                for g in items:
                    self._nudge(f"id:{g.id}", -0.5)
            elif reason == "too hot":
                self._nudge("warmth:heavy", -1.5); self._nudge("warmth:mid", -0.7); self._nudge("warmth:light", +0.5)
            elif reason == "wrong pieces":
                for g in items:
                    self._nudge(f"id:{g.id}", -1.5)
            elif reason in ("ban this item", "don't own it") and items:
                self.banned_ids.add(items[0].id)

    def bonus(self, items):
        if not items:
            return 0.0
        return sum(self.weights.get(a, 0.0) for g in items for a in self.attributes(g)) / len(items)

    def allows(self, items):
        return not any(g.id in self.banned_ids for g in items)

    def top(self, prefix, n=3):
        kv = [(k.split(":", 1)[1], v) for k, v in self.weights.items() if k.startswith(prefix + ":")]
        return sorted(kv, key=lambda x: -x[1])[:n]



# ---------------------------------------------------------------- outfit engine
def eligible(wardrobe, req):
    out = []
    for g in wardrobe.available():
        d = g.days_since_worn()
        if req.no_repeat_yesterday and d <= 1:
            continue
        if d < req.min_days_unworn:
            continue
        out.append(g)
    return out


def build_combos(items, req):
    if req.occasion:
        items = [g for g in items if suits_occasion(g, req.occasion)]
    by_type = {t: [g for g in items if g.type == t] for t in TYPES}
    mids = [g for g in items if g.layer == "mid-layer"]
    outers = [g for g in items if g.layer == "outer"]
    if req.condition == "rain":
        # rain: use real rain gear when the closet has it, and skip sneakers/suede/sandals if other shoes exist
        outers = [g for g in outers if is_rain_outer(g)] or outers
        by_type["shoes"] = [g for g in by_type["shoes"] if not is_rain_bad_shoe(g)] or by_type["shoes"]
    bases = [g for g in by_type["top"] if g.layer == "base"]
    cores = [list(c) for c in product(bases, by_type["bottom"], by_type["shoes"])]
    cores += [[d, s] for d, s in product(by_type["dress"], by_type["shoes"])]
    combos = []
    for core in cores:
        options = [core]
        if req.temp_f < 65 and mids:
            options = [core + [m] for m in mids] + [core]
        if (req.temp_f < 50 or req.condition == "rain") and outers:
            options = [o + [x] for o in options for x in outers]
        combos.extend(options)
    return combos


def score(outfit, req):
    warmth = sum(WARMTH[g.warmth] for g in outfit) / len(outfit) + 0.3 * (len(outfit) - 3)
    dressy = sum(DRESSINESS[g.dressiness] for g in outfit) / len(outfit)
    s = 10 - 3 * abs(warmth - req.target_warmth()) - 3 * abs(dressy - req.target_dressiness())
    s += min(min(g.days_since_worn() for g in outfit), 60) / 10
    colors = [g.color_group for g in outfit]
    top_color = max(sorted(set(colors)), key=colors.count)
    s += 1.5 * (colors.count(top_color) - 1)
    if req.color_theme:
        s += 2 * colors.count(req.color_theme)
    return s, top_color


def describe(outfit, req, top_color, rank):
    name = f"The {COLOR_NAMES[top_color]} {STYLE_WORDS[rank % len(STYLE_WORDS)]}"
    d = outfit[0].days_since_worn()
    worn = "Never worn yet." if d >= 999 else f"Not worn in {d} day{'' if d == 1 else 's'}."
    warmth = sum(WARMTH[g.warmth] for g in outfit) / len(outfit)
    if req.temp_given:
        reason = f"{worn} {'Light enough' if warmth <= 1.7 else 'Warm enough'} for {req.temp_f}°."
    else:
        reason = f"{worn} Layered for mild weather (add a temperature for a better fit)."
    if req.condition == "rain":
        reason += " " + rain_note(outfit)
    return name, reason


def rain_note(outfit) -> str:
    """Only claim the look is covered for rain when it really has rain gear."""
    if any(is_rain_outer(g) for g in outfit):
        note = "Covered for rain."
    elif any(g.layer == "outer" for g in outfit):
        note = "Your coat isn't rainproof, so bring an umbrella."
    else:
        note = "No coat in your closet for rain, so bring an umbrella."
    if any(is_rain_bad_shoe(g) for g in outfit):
        note += " These shoes aren't great in the wet (you have no other pair)."
    return note


def suggest(wardrobe, req, n=3):
    combos = build_combos(eligible(wardrobe, req), req)
    scored = sorted(((*score(c, req), c) for c in combos), key=lambda x: -x[0])
    results, seen = [], set()
    for s, color, outfit in scored:
        key = frozenset(g.id for g in outfit if g.layer in ("base", "bottom"))
        if key in seen:
            continue
        seen.add(key)
        name, reason = describe(outfit, req, color, len(results))
        results.append({"name": name, "items": outfit, "score": round(s, 2), "reason": reason})
        if len(results) == n:
            break
    return results


def smart_suggest(wardrobe, req, profile, n=3, weight=2.0):
    ranked = []
    for o in suggest(wardrobe, req, n=20):
        if not profile.allows(o["items"]):
            continue
        o = dict(o, score=round(o["score"] + weight * profile.bonus(o["items"]), 2))
        ranked.append(o)
    ranked.sort(key=lambda o: -o["score"])
    for i, o in enumerate(ranked[:n]):  # rename after re-ranking
        o["name"] = f"The {o['name'].split()[1]} {STYLE_WORDS[i % len(STYLE_WORDS)]}"
    return ranked[:n]


def feedback(wardrobe, profile, items, action, reason=None) -> str:
    """Apply Wear/Skip/No to the closet and teach the profile. Returns a message."""
    target = items[0] if items else None
    msg = "Thanks, noted."
    if action == "wear":
        for g in items:
            if g.id in wardrobe.items:
                wardrobe.items[g.id].times_worn += 1
                wardrobe.items[g.id].last_worn = today()
        msg = "Logged as worn today."
    elif action == "skip":
        msg = "Skipped. I'll show it less."
    elif action == "no":
        if reason == "don't own it" and target:
            wardrobe.remove(target.id); msg = f"Removed {target.name} from your closet."
        elif reason == "ban this item" and target:
            wardrobe.ban_item(target.id); msg = f"Banned {target.name}."
        else:
            msg = {"too hot": "Got it, lighter outfits next.", "too formal": "Got it, more casual next.",
                   "wrong pieces": "Got it, fewer of those pieces."}.get(reason, msg)
    profile.update(items, action, reason)
    return msg


# ---------------------------------------------------------------- shop / gaps
def season(d):
    return {12: "winter", 1: "winter", 2: "winter", 3: "spring", 4: "spring", 5: "spring",
            6: "summer", 7: "summer", 8: "summer"}.get(d.month, "autumn")


def _has(pred):
    return lambda w: any(pred(g) for g in w.available())


GAP_RULES = {
    "autumn": [
        ("rain jacket", _has(lambda g: g.layer == "outer" and any(k in g.name.lower() for k in ("rain", "trench", "mac")))),
        ("warm mid-layer", _has(lambda g: g.layer == "mid-layer" and g.warmth != "light")),
        ("pair of boots", _has(lambda g: g.type == "shoes" and "boot" in g.name.lower())),
        ("white shirt", _has(lambda g: g.type == "top" and g.color_group == "white")),
    ],
    "winter": [
        ("heavy coat", _has(lambda g: g.layer == "outer" and g.warmth == "heavy")),
        ("warm mid-layer", _has(lambda g: g.layer == "mid-layer" and g.warmth == "heavy")),
    ],
    "spring": [
        ("light jacket", _has(lambda g: g.type == "outer" and g.warmth == "light")),
        ("rain jacket", _has(lambda g: g.layer == "outer" and "rain" in g.name.lower())),
    ],
    "summer": [
        ("light dress", _has(lambda g: g.type == "dress" and g.warmth == "light")),
        ("pair of sneakers", _has(lambda g: g.type == "shoes" and "sneaker" in g.name.lower())),
    ],
}


def find_products(query):
    """PLACEHOLDER: a real marketplace API would go here. Everything returned is EXAMPLE DATA."""
    return [{"name": f"Example {query.title()}", "price": "$--", "store": "Example Store", "example_data": True}]


def gap_analysis(wardrobe, when=None):
    when = when or today()
    s = season(when)
    out = []
    for label, has_it in GAP_RULES.get(s, []):
        out.append({"label": label, "season": s, "ok": has_it(wardrobe),
                    "product": None if has_it(wardrobe) else find_products(label)[0]})
    return out


# ---------------------------------------------------------------- chat stylist
def parse_chat(message, temp_f=58, condition="dry"):
    m = message.lower()
    req = OutfitRequest(temp_f=temp_f, condition=condition, temp_given=False)
    req.occasion = detect_occasion(m)
    if req.occasion:
        req.plans = OCCASIONS[req.occasion]["plans"]
    for color in COLORS[:-1]:
        if color in m or (color == "blue" and "navy" in m):
            req.color_theme = color
    if RAIN_RE.search(m):  # whole words only: "training" or "brain" is not rain
        req.condition = "rain"
    t = re.search(r"(\d+)\s*(?:°|degrees|f\b)", m)
    if t:
        req.temp_f, req.temp_given = int(t.group(1)), True
    d = re.search(r"(?:last|past)\s+(\d+)\s+days", m)
    if d:
        req.min_days_unworn = int(d.group(1))
    return req


SYSTEM_PROMPT = """You are Wardrobe Bot, a friendly personal stylist inside the Fashionista app.
Pick ONE outfit using ONLY garment ids from the user's closet JSON. Never invent items.
A valid outfit is top+bottom+shoes or dress+shoes, optionally with a mid-layer and/or outer layer.
The user's message says what they are doing (CONTEXT today.occasion and today.occasion_rules summarise it).
That activity comes FIRST: every piece must suit it. Example: for a workout only athletic pieces (sneakers,
leggings, gym shorts, joggers, tees, tanks, hoodies), never jeans, tailored pants, trousers, blazers or dress shoes.
Then respect the weather and the learned style profile (positive weights = liked, negative = disliked).
Avoid items in banned_ids. Prefer items not worn recently.
If the closet has no suitable pieces for the activity (see today.missing_for_occasion), do NOT substitute
unsuitable items: return "outfit": [] and say honestly which pieces are missing and suggest adding them.
Reply with JSON only: {"reply": "<short friendly message>", "outfit": [<ids>], "reasoning": "<one sentence>"}"""


def closet_context(wardrobe, profile, req):
    recent = sorted((g for g in wardrobe.items.values() if g.last_worn), key=lambda g: g.last_worn, reverse=True)[:5]
    return {
        "closet": [{"id": g.id, "name": g.name, "type": g.type, "layer": g.layer, "color": g.color_group,
                    "warmth": g.warmth, "dressiness": g.dressiness, "days_since_worn": g.days_since_worn()}
                   for g in wardrobe.available()],
        "style_profile": {"weights": {k: round(v, 2) for k, v in profile.weights.items()},
                          "banned_ids": sorted(profile.banned_ids)},
        "today": {"date": today().isoformat(), "plans": req.plans,
                  "occasion": req.occasion,
                  "occasion_rules": OCCASIONS[req.occasion]["note"] if req.occasion else None,
                  "missing_for_occasion": occasion_gaps(wardrobe, req.occasion),
                  "temp_f": req.temp_f if req.temp_given else None,  # None = not given; don't invent one
                  "condition": req.condition},
        "recent_wear": [{"id": g.id, "name": g.name, "last_worn": g.last_worn.isoformat()} for g in recent],
    }


def build_messages(message, history, wardrobe, profile, req):
    ctx = json.dumps(closet_context(wardrobe, profile, req), separators=(",", ":"))
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "system", "content": "CONTEXT " + ctx}]
    msgs += [{"role": h["role"], "content": h["content"]} for h in history[-6:] if str(h.get("content", "")).strip()]
    msgs.append({"role": "user", "content": message})
    return msgs


def validate_outfit(ids, wardrobe, profile):
    if not isinstance(ids, list) or not ids:
        return None
    owned = {g.id: g for g in wardrobe.available()}
    try:
        ids = [int(i) for i in ids]
    except (TypeError, ValueError):
        return None
    if any(i not in owned or i in profile.banned_ids for i in ids):
        return None
    pieces = [owned[i] for i in ids]
    types = [g.type for g in pieces]
    ok = "shoes" in types and ("dress" in types or ("top" in types and "bottom" in types))
    return pieces if ok else None


def missing_answer(wardrobe, occasion, missing, note):
    """Honest reply when the closet can't dress for the occasion: say what's missing instead of guessing."""
    label = OCCASIONS[occasion]["label"]
    usable = [g.name for g in wardrobe.available() if suits_occasion(g, occasion)]
    reply = (f"I can't put together a proper outfit for {label} from your closet yet. "
             f"You're missing {_join(missing)}.")
    if usable:
        reply += f" You do have {_join(usable)} that would work."
    reply += " Add the missing pieces in the Closet tab (the Shop tab has ideas)."
    return {"reply": reply, "items": [], "reasoning": f"Missing for {label}: {_join(missing)}.",
            "source": note, "missing": missing}


def _join(words):
    words = list(words)
    return words[0] if len(words) == 1 else ", ".join(words[:-1]) + " and " + words[-1]


def rules_answer(message, wardrobe, profile, note):
    req = parse_chat(message)
    missing = occasion_gaps(wardrobe, req.occasion)
    if missing:
        return missing_answer(wardrobe, req.occasion, missing, note)
    picks = smart_suggest(wardrobe, req, profile, n=1)
    if not picks:  # relax the rules once before giving up
        req.no_repeat_yesterday, req.min_days_unworn, req.color_theme = False, 0, req.color_theme
        picks = smart_suggest(wardrobe, req, profile, n=1)
        if picks:
            note += ", relaxed: allowed recently worn items"
    if not picks:
        return {"reply": "I couldn't build an outfit with those rules. Try relaxing one?", "items": [],
                "reasoning": "", "source": note}
    o = picks[0]
    label = f" for {OCCASIONS[req.occasion]['label']}" if req.occasion else ""
    return {"reply": f"How about {o['name']}{label}?", "items": o["items"], "reasoning": o["reason"], "source": note}


def build_chat_request(model, messages, max_tokens=600, reasoning_effort=None) -> dict:
    """Keyword arguments for client.chat.completions.create (pure, so it can be unit-tested).

    Only parameters every current xAI chat model accepts are sent: no presence/frequency penalties or `stop`
    (reasoning models reject those with HTTP 400).  `reasoning_effort` is optional and goes in extra_body so
    it works with any version of the openai package.
    """
    kw = {"model": model, "messages": messages, "response_format": {"type": "json_object"},
          "temperature": 0.7, "max_tokens": max_tokens}
    if reasoning_effort:
        kw["extra_body"] = {"reasoning_effort": reasoning_effort}
    return kw


_SECRET_RE = re.compile(r"(xai-|sk-)[A-Za-z0-9_\-]{4,}")


def describe_api_error(e) -> dict:
    """{"type", "status", "message"} for an API exception.  The message is the provider's error text with
    anything that looks like an API key masked, cut to 300 characters, so a 400 can actually be diagnosed."""
    body = getattr(e, "body", None)
    if isinstance(body, dict):
        inner = body.get("error", body)
        msg = (inner.get("message") or inner.get("error") or json.dumps(body)) if isinstance(inner, dict) else str(inner)
    elif body:
        msg = str(body)
    else:
        msg = str(e)
    msg = _SECRET_RE.sub(r"\1***", str(msg)).strip()[:300]
    return {"type": type(e).__name__, "status": getattr(e, "status_code", None), "message": msg}


def stylist_chat(message, history, wardrobe, profile, req=None, client=None, model="gpt-4o-mini", max_tokens=600,
                 reasoning_effort=None):
    """Answer one chat message.  `client` None means the free offline rules.

    The result has `llm_error` (None, or {"type", "status", "message"}) so the app can show a banner, refund
    the visitor's message, and stop calling the API after auth/credit errors.  The message is masked by
    describe_api_error and also written to the server log (Streamlit Cloud: Manage app > Logs).
    """
    req = req or parse_chat(message)
    llm_error = None
    if client is None:
        ans = rules_answer(message, wardrobe, profile, "offline rules")
    else:
        resp = None
        try:
            resp = client.chat.completions.create(**build_chat_request(
                model, build_messages(message, history, wardrobe, profile, req), max_tokens, reasoning_effort))
        except Exception as e:
            llm_error = describe_api_error(e)
            log.warning("LLM call failed: model=%s type=%s status=%s message=%s",
                        model, llm_error["type"], llm_error["status"], llm_error["message"])
            ans = rules_answer(message, wardrobe, profile, f"rules (LLM error: {llm_error['type']})")
        if resp is not None:
            try:
                data = json.loads(resp.choices[0].message.content or "")
                pieces = validate_outfit(data.get("outfit"), wardrobe, profile)
                if data.get("outfit") == [] and str(data.get("reply", "")).strip() and occasion_gaps(wardrobe, req.occasion):
                    pieces = []  # an honest "you're missing X" answer (only accepted when something IS missing)
            except (ValueError, AttributeError, IndexError, TypeError):
                data, pieces = None, None
                log.warning("LLM reply was not usable JSON (model=%s, finish_reason=%s)", model,
                            getattr(resp.choices[0], "finish_reason", "?") if getattr(resp, "choices", None) else "?")
            if data is None:
                ans = rules_answer(message, wardrobe, profile, "rules (LLM reply unreadable)")
            elif pieces is None:
                ans = rules_answer(message, wardrobe, profile, "rules (LLM picked invalid items)")
            elif req.occasion and not all(suits_occasion(g, req.occasion) for g in pieces):
                log.warning("LLM ignored the occasion %s: %s", req.occasion, [g.name for g in pieces])
                ans = rules_answer(message, wardrobe, profile, f"rules (LLM picks didn't suit {req.occasion})")
            else:
                ans = {"reply": str(data.get("reply", ""))[:600], "items": pieces,
                       "reasoning": str(data.get("reasoning", ""))[:300], "source": f"llm ({model})"}
    ans["llm_error"] = llm_error
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": ans["reply"], "item_ids": [g.id for g in ans["items"]],
                    "reasoning": ans["reasoning"], "source": ans["source"]})
    return ans
