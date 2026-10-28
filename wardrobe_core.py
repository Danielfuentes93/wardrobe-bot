"""Fashionista core logic (extracted from wardrobe_app.ipynb).

Public (multi-user) edition: pure standard library, no file I/O at all.  Every visitor's closet, style
profile and chat live in memory (the Streamlit session); the LLM client is created by guards.py, which
also enforces the message limits, so this module never reads API keys or environment variables.
"""
from __future__ import annotations

import json
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


def today() -> date:
    return date.today()


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
    temp_f: int = 58
    condition: str = "dry"  # "dry" or "rain"
    no_repeat_yesterday: bool = True
    color_theme: str | None = None
    min_days_unworn: int = 0

    def target_dressiness(self):
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
    by_type = {t: [g for g in items if g.type == t] for t in TYPES}
    mids = [g for g in items if g.layer == "mid-layer"]
    outers = [g for g in items if g.layer == "outer"]
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
    reason = f"{worn} {'Light enough' if warmth <= 1.7 else 'Warm enough'} for {req.temp_f}°."
    if req.condition == "rain" and any(g.layer == "outer" for g in outfit):
        reason += " Covered for rain."
    return name, reason


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
    req = OutfitRequest(temp_f=temp_f, condition=condition)
    if any(w in m for w in ["meeting", "work", "office", "business", "interview"]):
        req.plans = "work"
    if any(w in m for w in ["weekend", "casual", "off duty", "brunch", "relax"]):
        req.plans = "off duty"
    for color in COLORS[:-1]:
        if color in m or (color == "blue" and "navy" in m):
            req.color_theme = color
    if "rain" in m:
        req.condition = "rain"
    t = re.search(r"(\d+)\s*(?:°|degrees|f\b)", m)
    if t:
        req.temp_f = int(t.group(1))
    d = re.search(r"(?:last|past)\s+(\d+)\s+days", m)
    if d:
        req.min_days_unworn = int(d.group(1))
    return req


SYSTEM_PROMPT = """You are Wardrobe Bot, a friendly personal stylist inside the Fashionista app.
Pick ONE outfit using ONLY garment ids from the user's closet JSON. Never invent items.
A valid outfit is top+bottom+shoes or dress+shoes, optionally with a mid-layer and/or outer layer.
Respect the weather, plans and the learned style profile (positive weights = liked, negative = disliked).
Avoid items in banned_ids. Prefer items not worn recently.
Reply with JSON only: {"reply": "<short friendly message>", "outfit": [<ids>], "reasoning": "<one sentence>"}"""


def closet_context(wardrobe, profile, req):
    recent = sorted((g for g in wardrobe.items.values() if g.last_worn), key=lambda g: g.last_worn, reverse=True)[:5]
    return {
        "closet": [{"id": g.id, "name": g.name, "type": g.type, "layer": g.layer, "color": g.color_group,
                    "warmth": g.warmth, "dressiness": g.dressiness, "days_since_worn": g.days_since_worn()}
                   for g in wardrobe.available()],
        "style_profile": {"weights": {k: round(v, 2) for k, v in profile.weights.items()},
                          "banned_ids": sorted(profile.banned_ids)},
        "today": {"date": today().isoformat(), "plans": req.plans, "temp_f": req.temp_f, "condition": req.condition},
        "recent_wear": [{"id": g.id, "name": g.name, "last_worn": g.last_worn.isoformat()} for g in recent],
    }


def build_messages(message, history, wardrobe, profile, req):
    ctx = json.dumps(closet_context(wardrobe, profile, req), separators=(",", ":"))
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "system", "content": "CONTEXT " + ctx}]
    msgs += [{"role": h["role"], "content": h["content"]} for h in history[-6:]]
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


def rules_answer(message, wardrobe, profile, note):
    req = parse_chat(message)
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
    return {"reply": f"How about {o['name']}?", "items": o["items"], "reasoning": o["reason"], "source": note}


def stylist_chat(message, history, wardrobe, profile, req=None, client=None, model="gpt-4o-mini", max_tokens=600):
    """Answer one chat message.  `client` None means the free offline rules.

    The result has `llm_error` (None, or {"type", "status"}) so the app can show a banner and stop calling
    the API after auth/credit errors.  Only the exception class and HTTP status are kept (never its text,
    which could echo part of a key).
    """
    req = req or parse_chat(message)
    llm_error = None
    if client is None:
        ans = rules_answer(message, wardrobe, profile, "offline rules")
    else:
        try:
            resp = client.chat.completions.create(
                model=model, messages=build_messages(message, history, wardrobe, profile, req),
                response_format={"type": "json_object"}, temperature=0.7, max_tokens=max_tokens)
            data = json.loads(resp.choices[0].message.content)
            pieces = validate_outfit(data.get("outfit"), wardrobe, profile)
            if pieces is None:
                ans = rules_answer(message, wardrobe, profile, "rules (LLM picked invalid items)")
            else:
                ans = {"reply": str(data.get("reply", ""))[:600], "items": pieces,
                       "reasoning": str(data.get("reasoning", ""))[:300], "source": f"llm ({model})"}
        except Exception as e:
            llm_error = {"type": type(e).__name__, "status": getattr(e, "status_code", None)}
            ans = rules_answer(message, wardrobe, profile, f"rules (LLM error: {type(e).__name__})")
    ans["llm_error"] = llm_error
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": ans["reply"], "item_ids": [g.id for g in ans["items"]],
                    "reasoning": ans["reasoning"], "source": ans["source"]})
    return ans
