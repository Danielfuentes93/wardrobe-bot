"""Fashionista (public class-demo edition): per-visitor state, LLM limits, optional passcode.
Run:  streamlit run app.py"""
import base64
import html

import streamlit as st

import guards
import ui_style
import wardrobe_core as core

st.set_page_config(page_title="Fashionista", page_icon="👗", layout="wide", initial_sidebar_state="collapsed")

# ---------------------------------------------------------------- styling (soft monochrome dashboard look; CSS lives in ui_style.py)
st.markdown(ui_style.CSS, unsafe_allow_html=True)

esc = html.escape
IC = ui_style.ICONS


# ---------------------------------------------------------------- per-visitor state (nothing is written to disk)
def init_session(force=False):
    """Seed this visitor's closet/profile/photos/chat.  `force` is used by Reset (keeps the LLM counter)."""
    ss = st.session_state
    if force or "wardrobe" not in ss:
        ss["wardrobe"] = core.sample_closet()
        ss["profile"] = core.StyleProfile()
        ss["photos"] = {}  # item id -> {"full": jpeg bytes <=800px, "thumb": jpeg bytes}
        ss["chat"] = []
    ss.setdefault("llm_used", 0)  # Grok messages used this session (deliberately NOT cleared by Reset)


def load():
    return st.session_state["wardrobe"], st.session_state["profile"]


def flash(msg):
    st.session_state["flash"] = msg


def choice(label, options, key, default):
    """Chip-style picker: st.pills if this Streamlit has it, else a horizontal radio."""
    if hasattr(st, "pills"):
        val = st.pills(label, options, default=default, key=key)
        return val if val is not None else default
    return st.radio(label, options, index=options.index(default), horizontal=True, key=key)


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


def garment_card(g, mini=False, solo=False):
    """Card markup. mini=True is the compact version used inside outfit suggestions."""
    sw = core.SWATCH[g.color_group]
    banned = " fx-banned" if g.banned else ""
    if mini:
        return (f'<div class="fx-card{banned}">{tile_html(g, True)}<div class="fx-body mini">'
                f'<div class="fx-name">{esc(g.name)}</div></div></div>')
    return (f'<div class="fx-card{banned}">{tile_html(g)}<div class="fx-body">'
            f'<div class="fx-top"><div class="fx-name" title="{esc(g.name)}">{esc(g.name)}</div>'
            f'<div class="fx-worn">{g.times_worn}x<small>worn</small></div></div>'
            f'<div class="fx-metaline"><span><i class="fx-dot" style="background:{sw}"></i>{esc(g.color_group)}</span>'
            f'<span>{esc(g.warmth)}</span><span>{esc(g.dressiness)}</span></div>'
            f'</div></div>')


def mini_cards(items, cols=4):
    """A responsive row of compact tiles (one markdown block; wraps nicely on phones)."""
    st.markdown('<div class="fx-minirow">' + "".join(garment_card(g, mini=True) for g in items) + '</div>',
                unsafe_allow_html=True)


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
    for k in ["show_outfits", "chat_feedback_done", "llm_notice"]:
        st.session_state.pop(k, None)
    flash("Demo data reset to the sample closet.")


# ---------------------------------------------------------------- page
def nav():
    """Top bar: logo + name on the left, round icon buttons on the right.  The st.tabs pills are pulled up into the
    centre of this bar by CSS (see ui_style.py), so the tabs ARE the nav.  The icon buttons are decorative."""
    st.markdown(f'<div class="fx-nav"><div class="fx-brand"><span class="fx-logo">{IC["hanger"]}</span>Fashionista</div>'
                f'<div class="fx-nav-icons" aria-hidden="true"><span class="fx-ic hide-m">{IC["search"]}</span>'
                f'<span class="fx-ic hide-m">{IC["bell"]}</span><span class="fx-ic">{IC["sliders"]}</span>'
                f'<span class="fx-ic avatar">{IC["user"]}</span></div></div>', unsafe_allow_html=True)


def demo_strip():
    st.markdown(
        '<div class="fx-demo"><span class="fx-pill">Class demo</span><div><details><summary>'
        'Fashionista is a student prototype. Nothing you do is saved between visits.<u>More</u></summary>'
        '<p>Closing or refreshing the page starts you over with a sample closet, and you do not need to upload '
        'real personal photos: the sample closet works fine. The stylist chat is limited to '
        f'{guards.SESSION_LLM_LIMIT} AI messages per visit; when Grok is on, your message and a summary of your '
        'closet are sent to xAI.</p></details></div></div>', unsafe_allow_html=True)


if guards.passcode_required() and not st.session_state.get("authed"):
    demo_strip()
    nav()
    with st.container(key="gate_wrap"):
        st.markdown(f'<div class="fx-gate-head"><div class="lock">{IC["lock"]}</div><h3>Class access</h3>'
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


with tab_closet:
    closet_dashboard(wardrobe, profile)

    with st.container(key="closet_card"):
        st.markdown(f'<div class="fx-cardhead"><div><h2>My Wardrobe</h2><p>Everything you own, in one place.</p></div>'
                    f'<span class="fx-count-pill">{len(wardrobe.items)} pieces</span></div>', unsafe_allow_html=True)

        with st.expander("Add clothes", expanded=False):
            with st.form("add_form", clear_on_submit=True):
                name = st.text_input("Name", placeholder="e.g. Trench Coat", key="add_name")
                c1, c2 = st.columns(2)
                upload = c1.file_uploader("Upload a photo (max 5 MB)", type=["png", "jpg", "jpeg", "webp"], key="add_upload")
                camera = c2.camera_input("…or take one", key="add_camera")
                gtype = choice("Type", core.TYPES, "add_type", "top")
                color = choice("Color", core.COLORS, "add_color", "blue")
                warmth = choice("Warmth", list(core.WARMTH), "add_warmth", "mid")
                dress = choice("Dressiness", list(core.DRESSINESS), "add_dress", "casual")
                layer = st.selectbox("Layer", ["auto"] + core.LAYERS, key="add_layer")
                submitted = st.form_submit_button("Save", type="primary")
            if submitted:
                clean_name = name.strip()[:guards.MAX_NAME_CHARS]
                photo_file = upload or camera
                if not clean_name:
                    st.error("Please give the item a name.")
                elif len(wardrobe.items) >= guards.MAX_ITEMS:
                    st.error(f"Demo closets are limited to {guards.MAX_ITEMS} items. Remove one first.")
                else:
                    photo = None
                    if photo_file is not None:
                        try:
                            photo = guards.process_photo(photo_file.getvalue())
                        except guards.PhotoError as e:
                            st.error(str(e))
                    if photo_file is None or photo is not None:
                        gid = wardrobe.next_id()
                        lay = core.default_layer(gtype) if layer == "auto" else layer
                        wardrobe.add_item(core.Garment(gid, clean_name, gtype, lay, color, warmth, dress,
                                                       has_photo=photo is not None))
                        if photo is not None:
                            st.session_state["photos"][gid] = {"full": photo[0], "thumb": photo[1]}
                        st.success(f"Added {clean_name}.")

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
with tab_today:
    with st.container(key="today_row"):
        t_left, t_right = st.columns([1.1, 1], gap="medium")
    with t_left:
        with st.container(key="controls"):
            st.markdown('<div class="fx-cardhead"><div><h2>What\'s today like?</h2>'
                        '<p>Tell us the plan and the weather. We\'ll do the styling.</p></div></div>', unsafe_allow_html=True)
            plans = choice("Plans", ["Work", "Off duty"], "today_plans", "Work")
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
        req = core.OutfitRequest(plans=plans.lower(), temp_f=temp, condition=cond.lower(), no_repeat_yesterday=norepeat)
        outfits = core.smart_suggest(wardrobe, req, profile)
        section("Your outfits", level=3, extra="sub")
        if not outfits:
            st.warning("No outfits fit these rules. Try turning off 'Don't repeat yesterday' or add more clothes.")
        for i, o in enumerate(outfits):
            ids = [g.id for g in o["items"]]
            with st.container(key=f"outfit_{i}"):
                st.markdown(f'<div class="fx-look-eyebrow">Look {i + 1}</div>'
                            f'<div class="fx-look-title">{esc(o["name"])}</div>'
                            f'<div class="fx-look-pieces">{" + ".join(esc(g.name) for g in o["items"])}</div>'
                            f'<div class="fx-look-why">{esc(o["reason"])}</div>'
                            + chip_html([esc(req.plans), f"{req.temp_f}°F", esc(req.condition)]), unsafe_allow_html=True)
                mini_cards(o["items"], cols=5)
                b1, b2, b3, b4 = st.columns([1, 1, 2, 1])
                b1.button("Wear", type="primary", key=f"wear_{i}", on_click=cb_feedback, args=(ids, "wear"))
                b2.button("Skip", key=f"skip_{i}", on_click=cb_feedback, args=(ids, "skip"))
                b3.selectbox("Why not?", core.NO_REASONS, key=f"reason_{i}", label_visibility="collapsed")
                b4.button("No", key=f"no_{i}", on_click=cb_feedback, args=(ids, "no", f"reason_{i}"))
    else:
        st.markdown('<div class="fx-empty"><div class="big">☀️</div><b>Ready when you are</b>'
                    'Pick your plans and the weather, then tap Show outfits.</div>', unsafe_allow_html=True)

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
    st.markdown('<div class="fx-foot-note">Fashionista · class demo prototype · nothing is saved between visits</div>', unsafe_allow_html=True)
    st.button("Reset demo data", on_click=cb_reset, key="reset_btn")

# ================================================================ STYLIST
LIMIT = guards.SESSION_LLM_LIMIT


def banner(text, on=False):
    """Slim status pill (green dot = Grok online, grey dot = offline/notice)."""
    st.markdown(f'<div class="fx-status{" on" if on else ""}"><span class="led"></span><span>{text}</span></div>',
                unsafe_allow_html=True)


with tab_chat:
    with st.container(key="chat_card"):
        st.markdown('<div class="fx-cardhead"><div><h2>Wardrobe Bot</h2><p>Describe the occasion. Get a look from your own closet.</p></div></div>',
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
        if client is not None:
            st.markdown('<div class="fx-privacy">When Grok is on, your message and a summary of your closet are sent to xAI.</div>',
                        unsafe_allow_html=True)

        history = st.session_state.setdefault("chat", [])
        if not history:
            st.markdown('<div class="fx-empty"><div class="big">💬</div><b>Ask for a look</b>'
                        'Try one of these in the box below:'
                        '<div class="fx-examples"><span>business meeting, blue theme</span><span>casual brunch, 72 degrees</span>'
                        '<span>rainy day at the office</span></div></div>', unsafe_allow_html=True)
        for idx, h in enumerate(history):
            with st.chat_message("user" if h["role"] == "user" else "assistant",
                                 avatar="🧑" if h["role"] == "user" else "👗"):
                st.markdown(h["content"])
                if h["role"] == "assistant":
                    items = [wardrobe.items[i] for i in h.get("item_ids", []) if i in wardrobe.items]
                    if items:
                        mini_cards(items, cols=4)
                    st.caption(f"{h.get('reasoning', '')} · via {h.get('source', '')}")
                    if items and idx == len(history) - 1 and not st.session_state.get("chat_feedback_done"):
                        c1, c2, _ = st.columns([1, 1, 4])
                        c1.button("Wear this", key="chat_wear", on_click=cb_feedback,
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
                        st.session_state["llm_used"] += 1  # every attempt counts, even if the API then errors
                ans = core.stylist_chat(prompt, history, wardrobe, profile, client=client if use_llm else None,
                                        model=guards.llm_model(),
                                        max_tokens=guards.int_secret("LLM_MAX_TOKENS", guards.DEFAULT_MAX_TOKENS))
                err = ans["llm_error"]
                if err:
                    code = f" (HTTP {err['status']})" if err["status"] else ""
                    notice = f"The Grok API returned an error [{err['type']}{code}] for your last message, so the free offline stylist answered."
                    if err["status"] in guards.PERSISTENT_ERROR_STATUS:
                        budget.mark_down()  # bad key / no credits / rate limit: stop calling for everyone for a few minutes
                st.session_state["llm_notice"] = notice
                st.rerun()
