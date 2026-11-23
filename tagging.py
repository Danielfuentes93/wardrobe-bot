"""Photo auto-tagging for the Add-a-piece form: suggest Type and Color from a garment photo.

Two paths, same output:
  1. vision model (the app's OpenAI-compatible client, image sent as a base64 data URL).  The model may not accept
     images (grok-4.3 vision support is unconfirmed), so ANY failure falls back silently to path 2.
  2. offline: dominant colour of the garment (background removed via the photo's border colour) mapped to a named
     palette, plus a type guess from the file name / item name and the garment's shape.
Pure functions apart from the optional client call; nothing is written to disk.
"""
from __future__ import annotations

import base64
import io
import json
import logging
import re

import wardrobe_core as core

log = logging.getLogger("fashionista")

# named shade -> (RGB, colour group used by the outfit engine)
PALETTE = {
    "Black": ((22, 22, 24), "black"), "Charcoal": ((58, 58, 62), "grey"), "Grey": ((128, 128, 132), "grey"),
    "Light Grey": ((196, 196, 198), "grey"), "White": ((244, 244, 242), "white"), "Ivory": ((238, 232, 214), "white"),
    "Cream": ((236, 224, 196), "beige"), "Beige": ((214, 196, 164), "beige"), "Khaki": ((190, 176, 130), "beige"),
    "Tan": ((196, 160, 116), "brown"), "Camel": ((193, 142, 86), "brown"), "Brown": ((112, 72, 44), "brown"),
    "Chocolate": ((70, 44, 30), "brown"), "Navy": ((28, 38, 72), "blue"), "Blue": ((44, 92, 180), "blue"),
    "Royal Blue": ((40, 70, 200), "blue"), "Light Blue": ((156, 192, 228), "blue"), "Denim": ((78, 104, 140), "blue"),
    "Teal": ((20, 120, 124), "green"), "Olive": ((108, 108, 52), "green"), "Green": ((44, 132, 64), "green"),
    "Forest Green": ((34, 78, 48), "green"), "Sage": ((156, 172, 140), "green"), "Red": ((196, 34, 44), "red"),
    "Burgundy": ((112, 26, 44), "red"), "Rust": ((166, 76, 40), "orange"), "Orange": ((236, 122, 40), "orange"),
    "Pink": ((240, 156, 184), "pink"), "Hot Pink": ((222, 54, 130), "pink"), "Lavender": ((186, 166, 214), "purple"),
    "Purple": ((108, 58, 140), "purple"), "Yellow": ((242, 212, 64), "yellow"), "Mustard": ((202, 160, 44), "yellow"),
}

TYPE_WORDS = {  # checked in order; first hit wins
    "dress": ("dress", "gown", "jumpsuit", "romper"),
    "shoes": ("shoe", "sneaker", "trainer", "boot", "loafer", "heel", "pump", "sandal", "oxford", "derby", "mule",
              "flat", "slipper", "runner"),
    "outer": ("coat", "jacket", "blazer", "parka", "trench", "puffer", "cardigan", "vest", "anorak", "windbreaker"),
    "bottom": ("jean", "pant", "trouser", "short", "skirt", "legging", "jogger", "chino", "slack", "sweatpant"),
    "top": ("shirt", "tee", "top", "blouse", "sweater", "hoodie", "tank", "polo", "knit", "camisole", "sweatshirt"),
}


# ---------------------------------------------------------------- colour
def _lab(rgb):
    def lin(c):
        c /= 255
        return ((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92
    r, g, b = (lin(float(v)) for v in rgb)
    x = (r * 0.4124 + g * 0.3576 + b * 0.1805) / 0.95047
    y = r * 0.2126 + g * 0.7152 + b * 0.0722
    z = (r * 0.0193 + g * 0.1192 + b * 0.9505) / 1.08883
    f = lambda t: t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


_PAL_LAB = {name: _lab(rgb) for name, (rgb, _) in PALETTE.items()}


def nearest_color(rgb) -> tuple[str, str]:
    """(shade name, colour group) of the palette entry closest to `rgb` (CIELAB distance)."""
    L, a, b = _lab(rgb)
    name = min(_PAL_LAB, key=lambda n: (L - _PAL_LAB[n][0]) ** 2 + (a - _PAL_LAB[n][1]) ** 2 + (b - _PAL_LAB[n][2]) ** 2)
    return name, PALETTE[name][1]


def color_from_name(text) -> tuple[str, str] | None:
    """A colour word in free text ('navy', 'Light Blue', 'gray') -> (shade, group), or None."""
    t = str(text or "").lower().replace("gray", "grey")
    for name in sorted(PALETTE, key=len, reverse=True):  # "light blue" before "blue"
        if re.search(rf"\b{re.escape(name.lower())}\b", t):
            return name, PALETTE[name][1]
    for group in core.COLORS[:-1]:
        if re.search(rf"\b{group}\b", t):
            return group.title(), group
    return None


def _open_small(jpeg_bytes, px=96):
    from PIL import Image
    img = Image.open(io.BytesIO(jpeg_bytes)).convert("RGB")
    img.thumbnail((px, px))
    return img


def _foreground(img):
    """Pixels that differ from the photo's border colour (the background), plus the garment's bounding box."""
    w, h = img.size
    px = img.load()
    border = [px[x, y] for x in range(w) for y in (0, h - 1)] + [px[x, y] for y in range(h) for x in (0, w - 1)]
    bg = tuple(sorted(c[i] for c in border)[len(border) // 2] for i in range(3))  # per-channel median
    fg, xs, ys = [], [], []
    for y in range(h):
        for x in range(w):
            c = px[x, y]
            if sum((c[i] - bg[i]) ** 2 for i in range(3)) > 40 ** 2:
                fg.append(c); xs.append(x); ys.append(y)
    if len(fg) < 0.04 * w * h:  # no clear background: use the centre of the photo
        fg = [px[x, y] for y in range(h // 4, 3 * h // 4) for x in range(w // 4, 3 * w // 4)]
        return fg, None
    return fg, (min(xs), min(ys), max(xs) + 1, max(ys) + 1)


def dominant_color(jpeg_bytes) -> tuple[str, str]:
    """(shade name, colour group) of the garment in the photo."""
    from PIL import Image
    fg, _ = _foreground(_open_small(jpeg_bytes))
    if not fg:
        return "Other", "other"
    strip = Image.new("RGB", (len(fg), 1))
    strip.putdata(fg)
    q = strip.quantize(colors=5, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()
    counts = sorted(q.getcolors(), reverse=True)
    idx = counts[0][1]
    return nearest_color(tuple(pal[idx * 3: idx * 3 + 3]))


# ---------------------------------------------------------------- type
def type_from_text(text) -> tuple[str, str] | None:
    """('top', 'Tee') style guess from an item or file name."""
    t = re.sub(r"[^a-z]+", " ", str(text or "").lower())  # "IMG_white_sneakers.jpg" -> "img white sneakers jpg"
    for gtype, words in TYPE_WORDS.items():
        for w in words:
            if re.search(rf"\b{w}", t):
                return gtype, w.title()
    return None


def type_from_shape(jpeg_bytes) -> str:
    """Very rough: wide and flat = shoes, tall and narrow = bottoms, else top."""
    img = _open_small(jpeg_bytes)
    _, box = _foreground(img)
    if not box:
        return "top"
    ratio = (box[3] - box[1]) / max(box[2] - box[0], 1)
    return "shoes" if ratio < 0.62 else "bottom" if ratio > 1.55 else "top"


def offline_tags(jpeg_bytes, hint_text="") -> dict:
    shade, group = dominant_color(jpeg_bytes)  # the photo beats colour words in a file name
    t = type_from_text(hint_text)
    gtype, sub = t if t else (type_from_shape(jpeg_bytes), "")
    return {"type": gtype, "subtype": sub, "color": group, "color_name": shade, "name": "", "warmth": None,
            "dressiness": None, "source": "offline", "confidence": "guess" if not t else "from name"}


# ---------------------------------------------------------------- vision model
VISION_PROMPT = (
    "You tag clothing photos for a wardrobe app. Look at the single main garment and reply with JSON only: "
    '{"type": one of ["top","bottom","outer","shoes","dress"], "subtype": "<1-2 words, e.g. Tee, Jeans, Loafers>", '
    '"color": "<plain colour name, e.g. Navy, Black, Camel>", "name": "<short item name, max 4 words>", '
    '"warmth": one of ["light","mid","heavy"], "dressiness": one of ["casual","office","formal"]}. '
    "outer = coats, jackets and blazers.")


def build_vision_request(model, jpeg_bytes, max_tokens=300) -> dict:
    url = "data:image/jpeg;base64," + base64.b64encode(jpeg_bytes).decode()
    return {"model": model, "max_tokens": max_tokens, "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": VISION_PROMPT},
                         {"role": "user", "content": [{"type": "text", "text": "Tag this garment."},
                                                      {"type": "image_url", "image_url": {"url": url}}]}]}


def parse_vision_reply(content, jpeg_bytes) -> dict | None:
    """Validated tags from the model's JSON, or None if unusable."""
    try:
        m = re.search(r"\{.*\}", str(content or ""), re.S)
        data = json.loads(m.group(0) if m else "")
    except (ValueError, AttributeError):
        return None
    if not isinstance(data, dict):
        return None
    gtype = str(data.get("type", "")).strip().lower()
    gtype = {"outerwear": "outer", "jacket": "outer", "coat": "outer", "shoe": "shoes", "footwear": "shoes",
             "bottoms": "bottom", "pants": "bottom", "tops": "top"}.get(gtype, gtype)
    if gtype not in core.TYPES:
        return None
    col = color_from_name(data.get("color"))
    shade, group = col if col else dominant_color(jpeg_bytes)
    clean = lambda v, n: re.sub(r"[^\w\s\-'&/]", "", str(v or "")).strip()[:n]
    warmth = data.get("warmth") if data.get("warmth") in core.WARMTH else None
    dress = data.get("dressiness") if data.get("dressiness") in core.DRESSINESS else None
    return {"type": gtype, "subtype": clean(data.get("subtype"), 20).title(), "color": group, "color_name": shade,
            "name": clean(data.get("name"), 40), "warmth": warmth, "dressiness": dress, "source": "vision",
            "confidence": "ai"}


def suggest_tags(jpeg_bytes, hint_text="", client=None, model=None, timeout=15) -> dict:
    """Best available tags.  result["vision_error"] is set (masked) when the model call failed and we fell back."""
    err = None
    if client is not None and model:
        try:
            resp = client.with_options(timeout=timeout).chat.completions.create(**build_vision_request(model, jpeg_bytes)) \
                if hasattr(client, "with_options") else client.chat.completions.create(**build_vision_request(model, jpeg_bytes))
            tags = parse_vision_reply(resp.choices[0].message.content, jpeg_bytes)
            if tags:
                tags["vision_error"] = None
                return tags
            err = {"type": "UnreadableReply", "status": None, "message": "vision reply was not usable JSON"}
        except Exception as e:  # model without image input, auth, timeout... -> offline tags
            err = core.describe_api_error(e)
        log.warning("Photo tagging fell back to offline: model=%s type=%s status=%s", model, err["type"], err["status"])
    tags = offline_tags(jpeg_bytes, hint_text)
    tags["vision_error"] = err
    return tags
