"""Fashionista (public class-demo edition): per-visitor state, LLM limits, optional passcode.
Run:  streamlit run app.py"""
import base64
import hashlib
import html
import json
from pathlib import Path
from urllib.parse import quote_plus

import streamlit as st

import guards
import storage
import tagging
import ui_style
import wardrobe_core as core

ASSETS = Path(__file__).parent / "assets"
_MARK = ASSETS / "logo-mark.png"
st.set_page_config(page_title="Fashionista", page_icon=str(_MARK) if _MARK.exists() else "👗", layout="wide", initial_sidebar_state="collapsed")

# ---------------------------------------------------------------- styling (soft monochrome dashboard look; CSS lives in ui_style.py)
st.markdown(ui_style.CSS, unsafe_allow_html=True)

esc = html.escape
IC = ui_style.ICONS


# ---------------------------------------------------------------- per-visitor state (+ saved closet, see storage.py)
def _restore(data):
    ss = st.session_state
    ss["wardrobe"] = core.wardrobe_from_list(data.get("wardrobe"))
    ss["profile"] = core.profile_from_dict(data.get("profile"))
    photos = {}
    for k, b64 in (data.get("photos") or {}).items():
        try:
            thumb = base64.b64decode(b64)
            photos[int(k)] = {"full": thumb, "thumb": thumb}
        except (ValueError, TypeError):
            pass
    ss["photos"] = photos
    ss["shop_list"] = [x for x in data.get("shop_list") or [] if isinstance(x, dict) and x.get("name")][:40]
    ss["closet_mode"] = data.get("mode", "demo")


def seed(mode="demo"):
    """Fresh closet: the sample one ('demo') or an empty personal one ('personal')."""
    ss = st.session_state
    ss["wardrobe"] = core.sample_closet() if mode == "demo" else core.Wardrobe()
    ss["profile"] = core.StyleProfile()
    ss["photos"] = {}  # item id -> {"full": jpeg bytes <=800px, "thumb": jpeg bytes}
    ss["chat"] = []
    ss["shop_list"] = []
    ss["closet_mode"] = mode


def init_session(force=False):
    """Load this visitor's saved closet (?c=<id> in the URL), or seed the sample one.  `force` is used by Reset."""
    ss = st.session_state
    token = ss.get("closet_token") or st.query_params.get("c")
    if not storage.valid_token(token):
        token = None
    if force:
        seed("demo")
    elif "wardrobe" not in ss:
        data = storage.load(token) if token else None
        if data:
            _restore(data)
            ss["chat"] = []
            ss["flash"] = f"Welcome back. Your closet ({len(ss['wardrobe'].items)} pieces) was restored."
        else:
            seed("demo")
            storage.prune()
    ss.setdefault("shop_list", [])
    ss.setdefault("closet_mode", "demo")
    if not token:
        token = storage.new_token()
    ss["closet_token"] = token
    if st.query_params.get("c") != token:
        st.query_params["c"] = token  # the id lives in the URL, so a refresh (or a bookmark) finds the closet again
    ss.setdefault("llm_used", 0)  # Grok messages used this session (deliberately NOT cleared by Reset)


def snapshot() -> dict:
    ss = st.session_state
    return {"v": 1, "mode": ss.get("closet_mode", "demo"),
            "wardrobe": core.wardrobe_to_list(ss["wardrobe"]), "profile": core.profile_to_dict(ss["profile"]),
            "photos": {str(k): base64.b64encode(v["thumb"]).decode() for k, v in ss.get("photos", {}).items()
                       if k in ss["wardrobe"].items},
            "shop_list": ss.get("shop_list", [])}


def persist():
    """Save the closet if anything changed since the last save (cheap hash check on every run)."""
    ss = st.session_state
    if "wardrobe" not in ss or not ss.get("closet_token"):
        return
    data = snapshot()
    digest = hashlib.sha1(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()
    if digest != ss.get("_saved_digest"):
        ok = storage.save(ss["closet_token"], data)
        ss["save_ok"] = ok
        if ok:
            ss["_saved_digest"] = digest


def load():
    return st.session_state["wardrobe"], st.session_state["profile"]


def flash(msg):
    st.session_state["flash"] = msg


def choice(label, options, key, default, format_func=str):
    """Chip-style picker: st.pills if this Streamlit has it, else a horizontal radio.
    The value lives in session state (so photo tagging can pre-fill it); no default= is passed to avoid warnings."""
    if st.session_state.get(key) not in options:
        st.session_state[key] = default
    if hasattr(st, "pills"):
        val = st.pills(label, options, key=key, format_func=format_func)
        return val if val is not None else default
    return st.radio(label, options, horizontal=True, key=key, format_func=format_func)


def tile_html(g, mini=False, fab=True):
    photo = st.session_state.get("photos", {}).get(g.id)
    cls = "fx-tile mini" if mini else "fx-tile"
    cat = "" if mini else f'<span class="fx-cat">{esc(g.type)}</span>'
    if mini or not fab:
        buttons = ""
    else:
        loved = st.session_state["profile"].weights.get(f"id:{g.id}", 0) > 0 if "profile" in st.session_state else False
        buttons = (f'<span class="fx-fab" aria-hidden="true"><span class="fx-rb{" on" if loved else ""}">{IC["heart"]}</span>'
                   f'<span class="fx-rb dark">{IC["arrow"]}</span></span>')
    if photo:
        data = base64.b64encode(photo["thumb"]).decode()
        return f'<div class="{cls}">{cat}{buttons}<img src="data:image/jpeg;base64,{data}" alt=""></div>'
    return (f'<div class="{cls}" style="--sw:{core.SWATCH[g.color_group]}">{cat}{buttons}'
            f'<span class="fx-emoji">{core.ICON[g.type]}</span></div>')


def garment_card(g, mini=False, solo=False, owned_tag=False):
    """Card markup. mini=True is the compact version used inside outfit suggestions."""
    sw = core.SWATCH[g.color_group]
    banned = " fx-banned" if g.banned else ""
    if mini:
        tag = '<div class="fx-own">✓ In your closet</div>' if owned_tag else ""
        return (f'<div class="fx-card{banned}">{tile_html(g, True)}<div class="fx-body mini">'
                f'<div class="fx-name" title="{esc(g.name)}">{esc(g.name)}</div>{tag}</div></div>')
    return (f'<div class="fx-card{banned}">{tile_html(g)}<div class="fx-body">'
            f'<div class="fx-top"><div class="fx-name" title="{esc(g.name)}">{esc(g.name)}</div>'
            f'<div class="fx-worn">{g.times_worn}x<small>worn</small></div></div>'
            f'<div class="fx-metaline"><span><i class="fx-dot" style="background:{sw}"></i>{esc(g.color_group)}</span>'
            f'<span>{esc(g.warmth)}</span><span>{esc(g.dressiness)}</span></div>'
            f'</div></div>')


def shop_url(name):
    return "https://www.google.com/search?tbm=shop&q=" + quote_plus(str(name))


def missing_card(m):
    """'Not in closet, shop this' placeholder card (dashed, hatched tile)."""
    return (f'<div class="fx-card fx-missing"><div class="fx-tile mini fx-hatch"><span class="fx-emoji">{m.get("icon", "🛍️")}</span></div>'
            f'<div class="fx-body mini"><div class="fx-name" title="{esc(m["name"])}">{esc(m["name"])}</div>'
            f'<div class="fx-miss">Not in closet</div>'
            f'<a class="fx-shopbtn" href="{esc(shop_url(m["name"]))}" target="_blank" rel="noopener">Shop this</a></div></div>')


def mini_cards(items, cols=4, missing=None, owned_tag=False):
    """A responsive row of compact tiles (one markdown block; wraps nicely on phones), plus any shop-this cards."""
    html_ = "".join(garment_card(g, mini=True, owned_tag=owned_tag) for g in items)
    if missing:
        html_ += '<div class="fx-plus" aria-hidden="true">+</div>' + "".join(missing_card(m) for m in missing)
    st.markdown('<div class="fx-minirow">' + html_ + '</div>', unsafe_allow_html=True)


def section(title, sub="", level=2, extra=""):
    st.markdown(f'<div class="fx-sec {extra}"><h{level}>{esc(title)}</h{level}>' + (f'<p>{esc(sub)}</p>' if sub else "") + '</div>',
                unsafe_allow_html=True)


def chip_html(items, cls=""):
    return '<div class="fx-chips">' + "".join(f'<span class="fx-chip {cls}">{i}</span>' for i in items) + '</div>'


# ---------------------------------------------------------------- callbacks (run before the page redraws)
def cb_ban(gid):
    w, p = load()
    if gid in w.items:
        w.ban_item(gid, not w.items[gid].banned)
        p.banned_ids.discard(gid) if not w.items[gid].banned else p.banned_ids.add(gid)
        flash(f"{'Banned' if w.items[gid].banned else 'Unbanned'} {w.items[gid].name}.")


def cb_remove(gid):
    w, p = load()
    g = w.remove(gid)
    if g:
        st.session_state["photos"].pop(gid, None)
        flash(f"Removed {g.name}.")


def cb_feedback(item_ids, action, reason_key=None, source="today", reason=None):
    w, p = load()
    items = [w.items[i] for i in item_ids if i in w.items]
    reason = st.session_state.get(reason_key) if reason_key else reason
    msg = core.feedback(w, p, items, action, reason)
    flash(msg)
    if source == "chat":
        st.session_state["chat_feedback_done"] = True


def cb_reset():
    init_session(force=True)  # only THIS visitor's data
    for k in ["show_outfits", "chat_feedback_done", "llm_notice", "pending_tag", "confirm_own"]:
        st.session_state.pop(k, None)
    flash("Demo data reset to the sample closet.")


def cb_own_closet():
    """'Start my own closet' (after confirming): an empty personal closet, saved under the same link."""
    seed("personal")
    for k in ["show_outfits", "chat_feedback_done", "llm_notice", "pending_tag", "confirm_own"]:
        st.session_state.pop(k, None)
    flash("Your own closet is ready. Add your first piece in the Closet tab.")


def on_shop_list(missing_items) -> bool:
    have = {str(x.get("name", "")).lower() for x in st.session_state.get("shop_list", [])}
    return bool(missing_items) and all(m["name"].lower() in have for m in missing_items)


def cb_add_to_shop(missing_items, key):
    n = core.add_to_shop_list(st.session_state.setdefault("shop_list", []), missing_items)
    flash(f"Added {n} item{'' if n == 1 else 's'} to your Shop list." if n else "Already on your Shop list.")


def cb_shop_remove(i):
    lst = st.session_state.get("shop_list", [])
    if 0 <= i < len(lst):
        flash(f"Removed {lst.pop(i)['name']} from your Shop list.")


# ---------------------------------------------------------------- page
def saved_badge():
    ss = st.session_state
    if "wardrobe" not in ss:
        return ""
    n = len(ss["wardrobe"].items)
    if ss.get("save_ok") is False:
        return '<span class="fx-saved off">Not saved (server storage unavailable)</span>'
    return f'<span class="fx-saved">✓ Closet saved · {n} piece{"" if n == 1 else "s"}</span>'


def nav():
    """Top bar: logo + name on the left, round icon buttons on the right.  The st.tabs pills are pulled up into the
    centre of this bar by CSS (see ui_style.py), so the tabs ARE the nav.  The icon buttons are decorative."""
    st.markdown(f'<div class="fx-nav"><div class="fx-brand"><span class="fx-logo">{IC["hanger"]}</span>Fashionista{saved_badge()}</div>'
                f'<div class="fx-nav-icons" aria-hidden="true"><span class="fx-ic hide-m">{IC["search"]}</span>'
                f'<span class="fx-ic hide-m">{IC["bell"]}</span><span class="fx-ic">{IC["sliders"]}</span>'
                f'<span class="fx-ic avatar">{IC["user"]}</span></div></div>', unsafe_allow_html=True)


@st.cache_data
def logo_img() -> str:
    """The Fashionista logo (assets/logo.svg) as an inline <img>; falls back to the lock icon if the file is missing."""
    svg = ASSETS / "logo.svg"
    if not svg.exists():
        return f'<div class="lock">{IC["lock"]}</div>'
    b64 = base64.b64encode(svg.read_bytes()).decode()
    return f'<img class="fx-gate-logo" src="data:image/svg+xml;base64,{b64}" alt="Fashionista, your AI stylist">'


def demo_strip():
    st.markdown(
        '<div class="fx-demo"><span class="fx-pill">Class demo</span><div><details><summary>'
        'Fashionista is a student prototype. Your closet is saved to this page\'s link.<u>More</u></summary>'
        '<p>Refreshing keeps your closet (it is saved on the app server under the private id in this page\'s link; '
        'bookmark the link to come back). Anyone with the full link can open that closet, and a server restart or '
        'redeploy clears saved closets. You do not need to upload real personal photos: the sample closet works fine. '
        'The stylist chat is limited to '
        f'{guards.SESSION_LLM_LIMIT} AI messages per visit; when Grok is on, your message and a summary of your '
        'closet are sent to xAI.</p></details></div></div>', unsafe_allow_html=True)


if (guards.passcode_required() and not st.session_state.get("authed")
        and storage.exists(st.query_params.get("c"))):
    st.session_state["authed"] = True  # a saved-closet link was created after the passcode, so a refresh skips the gate

if guards.passcode_required() and not st.session_state.get("authed"):
    demo_strip()
    nav()
    with st.container(key="gate_wrap"):
        st.markdown(f'<div class="fx-gate-head">{logo_img()}<h3>Class access</h3>'
                    '<p>Enter the passcode your instructor shared to step inside.</p></div>', unsafe_allow_html=True)
        with st.form("gate"):
            code = st.text_input("Class passcode", type="password", key="passcode_input")
            entered = st.form_submit_button("Enter", type="primary", use_container_width=True)
        if entered:
            if guards.check_passcode(code):
                st.session_state["authed"] = True
                st.rerun()
            st.error("That passcode isn't right.")
    st.stop()

init_session()
persist()  # saves changes made by the previous run's callbacks / chat
wardrobe, profile = load()
if "flash" in st.session_state:
    st.toast(st.session_state.pop("flash"))

demo_strip()
nav()

tab_closet, tab_today, tab_shop, tab_chat = st.tabs(["Closet", "Today", "Shop", "Stylist"])

# ================================================================ CLOSET
def bars_html(values, hi=None):
    """Tiny decorative bar-code style chart (like the reference's mini sparkline)."""
    top = max(values, default=1) or 1
    hi = max(values, default=0) if hi is None else hi
    return ('<span class="fx-bars" aria-hidden="true">'
            + "".join(f'<i class="{"k" if v == hi else ""}" style="height:{max(14, int(100 * v / top))}%"></i>' for v in values) + '</span>')


def closet_dashboard(wardrobe, profile):
    """Hero strip (readiness bars + floating garment tiles) and the bento stat cards."""
    items = list(wardrobe.items.values())
    n_all, n_avail = len(items), len(wardrobe.available())
    ready_pct = int(min(n_avail / core.MIN_ITEMS, 1.0) * 100)
    ready = n_avail >= core.MIN_ITEMS
    learn_pct = int(min(profile.events / 10, 1.0) * 100)
    # four floating tiles: one of each type first, so the visual shows variety
    seen, pick = set(), []
    for g in items:
        if g.type not in seen and not g.banned:
            seen.add(g.type); pick.append(g)
    pick = pick[:4]
    floats = "".join(f'<div class="fx-float">{tile_html(g, fab=False)}<b>{esc(g.name)}</b></div>' for g in pick)
    st.markdown(
        '<div class="fx-hero"><div class="fx-hero-stats">'
        f'<div class="fx-hs"><div class="l">Closet readiness</div><div class="v">{min(n_avail, core.MIN_ITEMS)}<small>/ {core.MIN_ITEMS} items{" ✓" if ready else ""}</small></div>'
        f'<div class="fx-bar" role="img" aria-label="Closet readiness {ready_pct} percent"><i style="width:{ready_pct}%"></i></div></div>'
        f'<div class="fx-hs"><div class="l">Style learning</div><div class="v">{profile.events}<small>/ 10 signals</small></div>'
        f'<div class="fx-bar peach" role="img" aria-label="Style learning {learn_pct} percent"><i style="width:{learn_pct}%"></i></div></div>'
        '</div>'
        f'<div class="fx-hero-vis"><span class="tag">Your capsule</span>{floats}</div></div>', unsafe_allow_html=True)

    req = core.OutfitRequest()
    n_looks = len(core.build_combos(core.eligible(wardrobe, req), req))
    worn = [g.times_worn for g in items]
    rested = [min(g.days_since_worn(), 60) for g in items]
    layers = wardrobe.grouped_by_layer()
    mx = max((len(v) for v in layers.values()), default=1) or 1
    rows = ""
    for layer, its in layers.items():
        names = ", ".join(esc(g.name) for g in its) or "None logged"
        w = int(100 * len(its) / mx)
        rows += (f'<div class="fx-layer"><div class="r"><span class="n">{esc(layer)}</span><span class="trk">'
                 f'<i class="{"" if its else "zero"}" style="width:{max(w, 0) if its else 0}%">{len(its)}</i></span></div>'
                 f'<div class="its">{names}</div></div>')
    rows = rows.replace('style="width:0%">0</i>', 'style="position:static;display:inline-block;width:30px;margin:0">0</i>')
    sig = "".join(f'<span class="fx-chip">{esc(k)}</span>' for k, v in profile.top("color") if v > 0)
    sig = sig or '<span class="fx-muted">Tap Wear or No on a look to teach me.</span>'
    st.markdown(
        '<div class="fx-bento">'
        f'<div class="fx-b"><div class="top"><span class="t">Pieces in closet</span><span class="fx-rb" aria-hidden="true">{IC["arrow"]}</span></div>'
        f'<div class="foot"><div><div class="num">{n_all}</div><div class="sub">{n_avail} ready to wear</div></div>{bars_html(worn)}</div></div>'
        f'<div class="fx-b"><div class="top"><span class="t">Outfits ready</span><span class="fx-rb" aria-hidden="true">{IC["arrow"]}</span></div>'
        f'<div class="foot"><div><div class="num">{n_looks}</div><div class="sub">for a work day, 58°F</div></div>{bars_html(rested)}</div></div>'
        f'<div class="fx-b span-rows full"><div class="top"><span class="t">By layer</span><span class="fx-rb dark" aria-hidden="true">{IC["arrow"]}</span></div>'
        f'<div class="fx-layers">{rows}</div></div>'
        f'<div class="fx-b span-cols"><div class="top"><span class="t">Style signals</span><span class="fx-rb" aria-hidden="true">{IC["arrow"]}</span></div>'
        f'<div class="foot"><div><div class="num">{profile.events}</div><div class="sub">taps that taught your stylist</div></div>'
        f'<div class="fx-chips" style="margin:0;justify-content:flex-end">{sig}</div></div></div>'
        '</div>', unsafe_allow_html=True)


@st.cache_resource
def vision_state() -> dict:
    """Process-wide: set once the vision model has refused images, so we stop calling it (until a restart)."""
    return {"unsupported": False, "last_error": None}


def run_tagging(full_jpeg, hint):
    """Suggested tags for a new photo: the vision model when available (counts toward the daily Grok cap,
    refunded on failure), otherwise offline colour detection."""
    client = guards.make_llm_client()
    vs, budget = vision_state(), guards.get_budget()
    use = (client is not None and str(guards.get_secret("VISION_TAGGING", "on")).lower() != "off"
           and not vs["unsupported"] and budget.try_consume(guards.int_secret("DAILY_LLM_CAP", guards.DEFAULT_DAILY_CAP)))
    tags = tagging.suggest_tags(full_jpeg, hint, client=client if use else None, model=guards.vision_model())
    err = tags.get("vision_error")
    if use and err:
        budget.refund()
        vs["last_error"] = f"{err['type']} {err['status'] or ''}".strip()
        if err["status"] in (400, 404, 415, 422) or err["type"] == "UnreadableReply":
            vs["unsupported"] = True  # this model doesn't take images: offline tagging from now on
        elif err["status"] in guards.PERSISTENT_ERROR_STATUS:
            budget.mark_down()
    tags["vision_tried"] = bool(use)
    return tags


def _prefill(tags):
    ss = st.session_state
    ss["add_type"] = tags["type"]
    ss["add_color"] = tags["color"]
    if tags.get("warmth"):
        ss["add_warmth"] = tags["warmth"]
    if tags.get("dressiness"):
        ss["add_dress"] = tags["dressiness"]
    if tags["type"] == "outer":
        ss["add_layer"] = "auto"
    if not ss.get("add_name") or ss.get("_auto_name") == ss.get("add_name"):
        sub = tags.get("subtype") or {"top": "Top", "bottom": "Bottoms", "outer": "Jacket", "shoes": "Shoes",
                                      "dress": "Dress"}[tags["type"]]
        auto = (tags.get("name") or f"{tags['color_name']} {sub}")[:guards.MAX_NAME_CHARS]
        ss["add_name"] = ss["_auto_name"] = auto


def cb_add_item():
    ss = st.session_state
    w = ss["wardrobe"]
    clean_name = str(ss.get("add_name", "")).strip()[:guards.MAX_NAME_CHARS]
    if not clean_name:
        ss["add_error"] = "Please give the item a name."
        return
    if len(w.items) >= guards.MAX_ITEMS:
        ss["add_error"] = f"Closets are limited to {guards.MAX_ITEMS} items. Remove one first."
        return
    if ss.get("photo_bad"):
        ss["add_error"] = "That photo couldn't be used. Remove it or pick another one."
        return
    pend = ss.get("pending_tag")
    gtype = ss.get("add_type") if ss.get("add_type") in core.TYPES else "top"
    color = ss.get("add_color") if ss.get("add_color") in core.COLORS else "other"
    warmth = ss.get("add_warmth") if ss.get("add_warmth") in core.WARMTH else "mid"
    dress = ss.get("add_dress") if ss.get("add_dress") in core.DRESSINESS else "casual"
    layer = ss.get("add_layer", "auto")
    gid = w.next_id()
    lay = core.default_layer(gtype) if layer == "auto" else layer
    w.add_item(core.Garment(gid, clean_name, gtype, lay, color, warmth, dress, has_photo=pend is not None))
    if pend is not None:
        ss["photos"][gid] = {"full": pend["full"], "thumb": pend["thumb"]}
    for k in ("pending_tag", "add_error", "_auto_name", "photo_bad"):
        ss.pop(k, None)
    ss["add_name"] = ""
    ss["upload_nonce"] = ss.get("upload_nonce", 0) + 1  # clears the uploader
    flash(f"Added {clean_name} to your closet.")


def add_piece_panel(wardrobe):
    ss = st.session_state
    with st.expander("Add a piece · AI tagging", expanded=bool(ss.get("pending_tag") or ss.get("add_error"))):
        nonce = ss.setdefault("upload_nonce", 0)
        c1, c2 = st.columns(2)
        upload = c1.file_uploader(f"Upload a photo (max {guards.MAX_UPLOAD_MB} MB)", type=["png", "jpg", "jpeg", "webp"],
                                  key=f"add_upload_{nonce}")
        camera = (c2.camera_input("Take a photo", key=f"add_camera_{nonce}")
                  if c2.toggle("…or use the camera", key="add_use_camera") else None)
        photo_file = upload or camera
        if photo_file is None:
            ss.pop("pending_tag", None); ss.pop("photo_bad", None)
        else:
            raw = photo_file.getvalue()
            digest = hashlib.sha1(raw).hexdigest()
            pend = ss.get("pending_tag")
            if (not pend or pend["hash"] != digest) and ss.get("photo_bad") != digest:
                try:
                    full, thumb = guards.process_photo(raw)
                except guards.PhotoError as e:
                    ss.pop("pending_tag", None)
                    ss["photo_bad"] = digest
                    ss["photo_err"] = str(e)
                else:
                    ss.pop("photo_bad", None)
                    with st.spinner("Detecting type and color…"):
                        tags = run_tagging(full, f"{getattr(photo_file, 'name', '')} {ss.get('add_name', '')}")
                    ss["pending_tag"] = {"hash": digest, "full": full, "thumb": thumb, "tags": tags}
                    _prefill(tags)
            if ss.get("photo_bad"):
                st.error(ss.get("photo_err", "That file is not a readable image."))
        pend = ss.get("pending_tag")
        if pend:
            t = pend["tags"]
            how = ("AI vision" if t["source"] == "vision" else
                   "offline color detection" + (" (AI vision unavailable)" if t.get("vision_tried") else ""))
            typ = t["type"].title() + (f" · {esc(t['subtype'])}" if t.get("subtype") else "")
            img = base64.b64encode(pend["thumb"]).decode()
            st.markdown(
                f'<div class="fx-tagcard"><img src="data:image/jpeg;base64,{img}" alt="">'
                f'<div class="fx-tagrows"><div class="fx-tagrow"><span>Type</span><b>{typ}</b></div>'
                f'<div class="fx-tagrow"><span>Color</span><b><i class="fx-dot" style="background:{core.SWATCH[t["color"]]}"></i>'
                f'{esc(t["color_name"])}</b></div>'
                f'<div class="fx-tagok">✓ Auto-detected from your photo ({esc(how)})</div>'
                '<div class="fx-tagq"><b>Looks right?</b> Tap Save, or edit any field below.</div></div></div>',
                unsafe_allow_html=True)
        with st.form("add_form", clear_on_submit=False):
            st.text_input("Name", placeholder="e.g. Trench Coat", key="add_name")
            choice("Type", core.TYPES, "add_type", "top")
            choice("Color", core.COLORS, "add_color", "blue")
            choice("Warmth", list(core.WARMTH), "add_warmth", "mid")
            choice("Dressiness", list(core.DRESSINESS), "add_dress", "casual")
            st.selectbox("Layer", ["auto"] + core.LAYERS, key="add_layer")
            st.form_submit_button("Save", type="primary", on_click=cb_add_item)
        if ss.get("add_error"):
            st.error(ss.pop("add_error"))


def closet_card(where):
    """'Your closet' card: piece count, saved state, 'Start my own closet' (with confirmation) and 'Use demo'."""
    ss = st.session_state
    w = ss["wardrobe"]
    n = len(w.items)
    req = core.OutfitRequest()
    looks = len(core.build_combos(core.eligible(w, req), req))
    icons = "".join(f'<span class="fx-ico">{core.ICON[g.type]}</span>' for g in list(w.items.values())[:6])
    mode = "Sample closet" if ss.get("closet_mode") == "demo" else "Your own closet"
    with st.container(key=f"closetcard_{where}"):
        st.markdown(
            f'<div class="fx-cc"><div class="top"><span class="t">Your closet</span>'
            f'<span class="fx-savedpill">{"✓ Saved" if ss.get("save_ok") is not False else "Not saved"}</span></div>'
            f'<div class="num">{n}<small> piece{"" if n == 1 else "s"} · {looks} outfits</small></div>'
            f'<div class="sub">{mode}</div><div class="fx-icos">{icons}</div></div>', unsafe_allow_html=True)
        if ss.get(f"confirm_own_{where}"):
            st.warning(f"This clears the {n} piece{'' if n == 1 else 's'} here and starts an empty closet "
                       "that's yours. Continue?")
            c1, c2 = st.columns(2)
            c1.button("Yes, start empty", type="primary", key=f"own_yes_{where}", on_click=cb_own_closet)
            c2.button("Cancel", key=f"own_no_{where}", on_click=lambda: ss.pop(f"confirm_own_{where}", None))
        else:
            c1, c2 = st.columns([1.4, 1])
            c1.button("Start my own closet", type="primary", key=f"own_{where}",
                      on_click=lambda: ss.__setitem__(f"confirm_own_{where}", True))
            c2.button("Use demo", key=f"demo_{where}", on_click=cb_reset)


with tab_closet:
    closet_dashboard(wardrobe, profile)

    with st.container(key="closet_card"):
        st.markdown(f'<div class="fx-cardhead"><div><h2>My Wardrobe</h2><p>Everything you own, in one place.</p></div>'
                    f'<span class="fx-count-pill">{len(wardrobe.items)} pieces</span></div>', unsafe_allow_html=True)

        add_piece_panel(wardrobe)

        with st.container(key="filters"):
            f1, f2, f3 = st.columns([1, 1, 1.3])
            ftype = f1.multiselect("Filter by type", core.TYPES, key="filter_type", placeholder="Type",
                                   label_visibility="collapsed")
            fcolor = f2.multiselect("Filter by color", core.COLORS, key="filter_color", placeholder="Color",
                                    label_visibility="collapsed")
            fq = f3.text_input("Search pieces", key="filter_q", placeholder="Search", label_visibility="collapsed").strip().lower()
        shown = [g for g in wardrobe.items.values()
                 if (not ftype or g.type in ftype) and (not fcolor or g.color_group in fcolor)
                 and (not fq or fq in g.name.lower())]
        with st.container(key="closet_grid"):
            for g in shown:
                with st.container(key=f"card_{g.id}"):
                    st.markdown(garment_card(g), unsafe_allow_html=True)
                    b1, b2 = st.columns(2)
                    b1.button("Unban" if g.banned else "Ban", key=f"ban_{g.id}", on_click=cb_ban, args=(g.id,))
                    b2.button("Remove", key=f"rm_{g.id}", on_click=cb_remove, args=(g.id,))
        if not shown:
            st.markdown('<div class="fx-empty"><div class="big">🧺</div><b>No pieces match these filters</b>'
                        'No items match these filters. Clear a filter to see your whole closet.</div>', unsafe_allow_html=True)

# ================================================================ TODAY
OCC_EMOJI = {"Work": "💼", "Interview": "🤝", "Date": "🍷", "Workout": "🏋️", "Weekend": "☕"}

with tab_today:
    with st.container(key="today_row"):
        t_left, t_right = st.columns([1.1, 1], gap="medium")
    with t_left:
        with st.container(key="controls"):
            st.markdown('<div class="fx-cardhead"><div><h2>What\'s today like?</h2>'
                        '<p>Pick the occasion and the weather. We\'ll do the styling.</p></div></div>', unsafe_allow_html=True)
            occ_label = choice("Occasion", list(core.TODAY_OCCASIONS), "today_occ", "Work",
                               format_func=lambda o: f"{OCC_EMOJI.get(o, '')} {o}")
            occasion = core.TODAY_OCCASIONS[occ_label]
            cond = choice("Weather", ["Dry", "Rain"], "today_cond", "Dry")
            temp = st.slider("Temperature (°F)", 20, 100, 58, key="today_temp")
            norepeat = st.toggle("Don't repeat yesterday", value=True, key="today_norepeat")
            show = st.button("Show outfits", type="primary", key="show_btn")
    if show:
        st.session_state["show_outfits"] = True

    with t_right:
        def chips(prefix):
            c = "".join(f'<span class="fx-chip">{esc(k)} {v:+.1f}</span>' for k, v in profile.top(prefix) if v > 0)
            return f'<div class="fx-chips" style="margin:0">{c}</div>' if c else '<span class="fx-muted">Nothing yet.</span>'
        fav = [int(k) for k, v in profile.top("id") if v > 0]
        favs = ", ".join(esc(wardrobe.items[i].name) for i in fav if i in wardrobe.items) or '<span class="fx-muted">No favourites yet.</span>'
        closet_card("today")
        with st.container(key="style_card"):
            st.markdown(
                '<div class="fx-b" style="padding:0;box-shadow:none;background:none;border-radius:0"><div class="top"><span class="t">Your style so far</span>'
                f'<span class="fx-rb dark" aria-hidden="true">{IC["arrow"]}</span></div>'
                f'<div class="num" style="padding-top:14px">{profile.events}<small> feedback event{"" if profile.events == 1 else "s"}</small></div>'
                '<div class="sub">Tap Wear or No on an outfit to teach me.</div>'
                '<div class="fx-style-grid">'
                f'<div class="fx-mini"><div class="fx-label">Top colors</div>{chips("color")}</div>'
                f'<div class="fx-mini"><div class="fx-label">Dressiness</div>{chips("dress")}</div>'
                f'<div class="fx-mini"><div class="fx-label">Warmth</div>{chips("warmth")}</div>'
                f'<div class="fx-mini"><div class="fx-label">Most-loved pieces</div>{favs}</div></div></div>', unsafe_allow_html=True)

    if st.session_state.get("show_outfits"):
        req = core.OutfitRequest(plans=core.OCCASIONS[occasion]["plans"], temp_f=temp, condition=cond.lower(),
                                 no_repeat_yesterday=norepeat, occasion=occasion)
        outfits = core.smart_suggest(wardrobe, req, profile)
        section("Your outfits", level=3, extra="sub")
        note = core.OCCASION_NOTES.get(occasion)
        if note:
            st.markdown(f'<div class="fx-occnote">🛡️ {esc(note)}</div>', unsafe_allow_html=True)
        if not outfits:
            items, missing = core.complete_look(wardrobe, profile, req)
            if missing:
                with st.container(key="outfit_gap"):
                    st.markdown(f'<div class="fx-look-eyebrow">Look 1 · {esc(occ_label)}</div>'
                                f'<div class="fx-look-title">Almost there</div>'
                                f'<div class="fx-look-pieces">{esc(core.look_text(items, missing, occasion))}</div>'
                                f'<div class="fx-look-why">Your closet has no {esc(core._join([{"bottom": "bottoms"}.get(m["slot"], m["slot"]) for m in missing]))} '
                                f'for {esc(core.OCCASIONS[occasion]["label"])}, so the look is completed with {"a piece" if len(missing) == 1 else "pieces"} to shop for.</div>',
                                unsafe_allow_html=True)
                    mini_cards(items, missing=missing, owned_tag=True)
                    done = on_shop_list(missing)
                    st.button("✓ On your Shop list" if done else "Add missing to Shop list", key="today_addshop",
                              on_click=cb_add_to_shop, args=(missing, "today"), disabled=bool(done))
            else:
                st.warning("No outfits fit these rules. Try turning off 'Don't repeat yesterday' or add more clothes.")
        for i, o in enumerate(outfits):
            ids = [g.id for g in o["items"]]
            with st.container(key=f"outfit_{i}"):
                st.markdown(f'<div class="fx-look-eyebrow">Look {i + 1} · {esc(occ_label)}</div>'
                            f'<div class="fx-look-title">{esc(o["name"])}</div>'
                            f'<div class="fx-look-pieces">{" + ".join(esc(g.name) for g in o["items"])}</div>'
                            f'<div class="fx-look-why">{esc(o["reason"])}</div>'
                            + chip_html([esc(occ_label), f"{req.temp_f}°F", esc(req.condition)]), unsafe_allow_html=True)
                mini_cards(o["items"], cols=5)
                b1, b2, b3, b4 = st.columns([1, 1, 2, 1])
                b1.button("Wear", type="primary", key=f"wear_{i}", on_click=cb_feedback, args=(ids, "wear"))
                b2.button("Skip", key=f"skip_{i}", on_click=cb_feedback, args=(ids, "skip"))
                b3.selectbox("Why not?", core.NO_REASONS, key=f"reason_{i}", label_visibility="collapsed")
                b4.button("No", key=f"no_{i}", on_click=cb_feedback, args=(ids, "no", f"reason_{i}"))
    else:
        st.markdown('<div class="fx-empty"><div class="big">☀️</div><b>Ready when you are</b>'
                    'Pick the occasion and the weather, then tap Show outfits.</div>', unsafe_allow_html=True)

# ================================================================ SHOP
with tab_shop:
    gaps = core.gap_analysis(wardrobe)
    season_name = str(gaps[0]['season'] if gaps else core.season(core.today())).capitalize()
    missing = [g for g in gaps if not g["ok"]]
    covered = len(gaps) - len(missing)
    st.markdown(
        '<div class="fx-cardhead" style="padding:2px 4px 0"><div><h2>Closet Analysis</h2>'
        f'<p>Season: {esc(season_name)}</p></div></div>'
        '<div class="fx-bento three">'
        f'<div class="fx-b"><div class="top"><span class="t">Gaps found</span><span class="fx-rb" aria-hidden="true">{IC["arrow"]}</span></div>'
        f'<div class="num">{len(missing)}</div><div class="sub">things worth adding</div></div>'
        f'<div class="fx-b"><div class="top"><span class="t">Basics covered</span><span class="fx-rb" aria-hidden="true">{IC["arrow"]}</span></div>'
        f'<div class="num">{covered}<small> / {len(gaps)}</small></div><div class="sub">for {esc(season_name.lower())}</div></div>'
        f'<div class="fx-b"><div class="top"><span class="t">Season</span><span class="fx-rb dark" aria-hidden="true">{IC["arrow"]}</span></div>'
        f'<div class="num" style="font-size:clamp(26px,3.2vw,36px)">{esc(season_name)}</div><div class="sub">based on today\'s date</div></div>'
        '</div>', unsafe_allow_html=True)
    shop_list = st.session_state.get("shop_list", [])
    if shop_list:
        with st.container(key="shoplist"):
            st.markdown(f'<div class="fx-cardhead"><div><h2>Your Shop list</h2><p>Pieces the Stylist said would complete '
                        f'your looks.</p></div><span class="fx-count-pill">{len(shop_list)} item{"" if len(shop_list) == 1 else "s"}</span></div>',
                        unsafe_allow_html=True)
            for i, item in enumerate(shop_list):
                c1, c2 = st.columns([5, 1])
                occ = core.OCCASIONS.get(item.get("occasion") or "", {}).get("label")
                c1.markdown(f'<div class="fx-shoprow"><span class="fx-ico">{core.ICON.get(item.get("slot"), "🛍️")}</span>'
                            f'<div><b>{esc(item["name"])}</b><div class="s">{esc(item.get("hint", ""))}'
                            f'{" · for " + esc(occ) if occ else ""}</div></div>'
                            f'<a class="fx-shopbtn" href="{esc(shop_url(item["name"]))}" target="_blank" rel="noopener">Shop this</a></div>',
                            unsafe_allow_html=True)
                c2.button("Remove", key=f"shoprm_{i}", on_click=cb_shop_remove, args=(i,))
    cards = ""
    for g in missing:
        p = g["product"]
        cards += (f'<div class="fx-row"><div class="fx-gap"><div class="ico">{IC["alert"]}</div><div><div class="t">You\'re missing a <b>{esc(g["label"])}</b> for {esc(g["season"])}.</div>'
                  f'<div class="s">Try one of these</div></div></div>'
                  f'<div class="fx-prod"><div><b>{esc(p["name"])}</b><br><span>{esc(p["store"])}</span></div><div class="pr">{esc(p["price"])}</div></div>'
                  f'<div class="fx-chips"><span class="fx-chip warn">EXAMPLE DATA</span></div></div>')
    for g in gaps:
        if g["ok"]:
            cards += f'<div class="fx-row fx-gap ok"><div class="ico">{IC["check"]}</div><div><div class="t">You have a {esc(g["label"])}.</div></div></div>'
    if cards:
        st.markdown(f'<div class="fx-grid">{cards}</div>', unsafe_allow_html=True)
    if not missing:
        st.success("No gaps found. Nice closet!")
    st.caption("Products shown are example data. A real marketplace API would plug in here later.")

# ---------------------------------------------------------------- footer (Reset lives here now that there is no sidebar)
with st.container(key="footer"):
    st.markdown('<div class="fx-foot-note">Fashionista · class demo prototype · your closet is saved to this page\'s link '
                '(cleared if the app restarts)</div>', unsafe_allow_html=True)
    st.button("Reset demo data", on_click=cb_reset, key="reset_btn")

# ================================================================ STYLIST
LIMIT = guards.SESSION_LLM_LIMIT


def banner(text, on=False):
    """Slim status pill (green dot = Grok online, grey dot = offline/notice)."""
    st.markdown(f'<div class="fx-status{" on" if on else ""}"><span class="led"></span><span>{text}</span></div>',
                unsafe_allow_html=True)


with tab_chat:
    with st.container(key="chat_card"):
        st.markdown('<div class="fx-cardhead"><div><h2>Wardrobe Bot</h2><p>Describe the occasion. Get a full look from your closet, plus anything you\'re missing.</p></div></div>',
                    unsafe_allow_html=True)
        client = guards.make_llm_client()
        daily_cap = guards.int_secret("DAILY_LLM_CAP", guards.DEFAULT_DAILY_CAP)
        used = st.session_state["llm_used"]
        left = max(LIMIT - used, 0)
        notice = st.session_state.get("llm_notice")
        with st.container(key="chat_meta"):
            if client is None:
                banner("Offline mode: the Grok stylist is not switched on for this app. Using the free built-in rules.")
            elif notice:
                banner(esc(notice))
            elif left == 0:
                banner(f"You have used all {LIMIT} stylist messages for this visit. Using the free offline stylist.")
            else:
                banner(f"Online · model <b>{esc(guards.llm_model())}</b>", on=True)
            if client is not None:
                with st.container(key="counter"):
                    st.caption(f"{left} of {LIMIT} stylist messages left" if left else f"0 of {LIMIT} stylist messages left (offline stylist still works)")
                    st.markdown(f'<div class="fx-track"><i style="width:{int(100 * left / LIMIT)}%"></i></div>', unsafe_allow_html=True)
            last_occ = next((h.get("occasion") for h in reversed(st.session_state.get("chat", []))
                             if h["role"] == "assistant" and h.get("occasion")), None)
            if last_occ:
                st.markdown(f'<div class="fx-status">Occasion detected: <b>{esc(core.LOOK_LABEL.get(last_occ, last_occ).replace("Gym", "Workout"))}</b></div>',
                            unsafe_allow_html=True)
        if client is not None:
            st.markdown('<div class="fx-privacy">When Grok is on, your message and a summary of your closet are sent to xAI.</div>',
                        unsafe_allow_html=True)

        history = st.session_state.setdefault("chat", [])
        if not history:
            st.markdown('<div class="fx-empty"><div class="big">💬</div><b>Ask for a look</b>'
                        'Try one of these in the box below:'
                        '<div class="fx-examples"><span>I want to work out today</span><span>job interview, 50 degrees</span>'
                        '<span>rainy day at the office</span></div></div>', unsafe_allow_html=True)
        for idx, h in enumerate(history):
            with st.chat_message("user" if h["role"] == "user" else "assistant",
                                 avatar="🧑" if h["role"] == "user" else "👗"):
                st.markdown(h["content"])
                if h["role"] == "assistant":
                    items = [wardrobe.items[i] for i in h.get("item_ids", []) if i in wardrobe.items]
                    miss = h.get("missing_items") or []
                    if items or miss:
                        mini_cards(items, cols=4, missing=miss, owned_tag=bool(miss))
                    why = h.get("reasoning", "")
                    st.caption(f"{'Why: ' + why if why else ''} · via {h.get('source', '')}")
                    latest = idx == len(history) - 1
                    if miss:
                        done = on_shop_list(miss)
                        st.button("✓ On your Shop list" if done else "Add missing to Shop list", key=f"chat_addshop_{idx}",
                                  on_click=cb_add_to_shop, args=(miss, f"chat{idx}"), disabled=bool(done))
                    if items and latest and not st.session_state.get("chat_feedback_done"):
                        c1, c2, _ = st.columns([1, 1, 4])
                        c1.button("Wear this", key="chat_wear", type="primary", on_click=cb_feedback,
                                  args=([g.id for g in items], "wear"), kwargs={"source": "chat"})
                        c2.button("No", key="chat_no", on_click=cb_feedback,
                                  args=([g.id for g in items], "no"), kwargs={"source": "chat", "reason": "wrong pieces"})

        raw_prompt = st.chat_input(f"Ask for an outfit, e.g. 'business meeting, blue theme' (max {guards.MAX_MESSAGE_CHARS} characters)",
                                   key="chat_input", max_chars=guards.MAX_MESSAGE_CHARS)
        if raw_prompt:
            prompt, _ = guards.clean_message(raw_prompt)  # also enforced here, not only in the widget
            if prompt:
                st.session_state["chat_feedback_done"] = False
                budget = guards.get_budget()
                use_llm, notice = False, None
                if client is not None:
                    if st.session_state["llm_used"] >= LIMIT:
                        notice = f"You have used all {LIMIT} stylist messages for this visit. Using the free offline stylist."
                    elif not budget.try_consume(daily_cap):
                        if budget.status(daily_cap)["down"]:
                            notice = "The Grok stylist is paused for a few minutes after an API error. Using the free offline stylist."
                        else:
                            notice = "The class demo reached today's Grok limit. Using the free offline stylist until tomorrow (UTC)."
                    else:
                        use_llm = True
                        st.session_state["llm_used"] += 1  # refunded below if the API call fails
                model = guards.llm_model()
                ans = core.stylist_chat(prompt, history, wardrobe, profile, client=client if use_llm else None,
                                        model=model,
                                        max_tokens=guards.int_secret("LLM_MAX_TOKENS", guards.DEFAULT_MAX_TOKENS),
                                        reasoning_effort=guards.llm_reasoning_effort(model))
                err = ans["llm_error"]
                if err:
                    # a failed call isn't billed, so it shouldn't use up the visitor's messages or the daily cap
                    st.session_state["llm_used"] = max(st.session_state["llm_used"] - 1, 0)
                    budget.refund()
                    code = f" (HTTP {err['status']})" if err["status"] else ""
                    detail = f": {err['message'][:160]}" if err.get("message") else ""
                    notice = (f"The Grok API returned an error [{err['type']}{code}{detail}] for your last message, "
                              "so the free offline stylist answered. It didn't count against your messages.")
                    if err["status"] in guards.PERSISTENT_ERROR_STATUS:
                        budget.mark_down()  # bad key / no credits / rate limit: stop calling for everyone for a few minutes
                st.session_state["llm_notice"] = notice
                st.rerun()

persist()  # save anything changed in this run (the chat path saves on its rerun)
