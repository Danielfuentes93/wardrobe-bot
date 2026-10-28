"""Fashionista: Streamlit GUI for the wardrobe app.  Run:  streamlit run app.py"""
import base64
import html
import mimetypes

import streamlit as st

import wardrobe_core as core

st.set_page_config(page_title="Fashionista", page_icon="👗", layout="wide")

# ---------------------------------------------------------------- styling (Figma look)
st.markdown("""
<style>
.stApp { background:#f8f5f0; }
h1, h2, h3, .serif { font-family: Georgia, 'Times New Roman', serif !important; font-weight: normal !important; color:#3b302b; }
.fx-card { background:#fff; border-radius:16px; box-shadow:0 2px 8px rgba(0,0,0,.06); overflow:hidden; margin-bottom:6px; }
.fx-tile { height:120px; display:flex; align-items:center; justify-content:center; font-size:46px; }
.fx-tile img { width:100%; height:120px; object-fit:cover; }
.fx-body { padding:10px 12px; font-size:13px; }
.fx-name { font-family:Georgia,serif; font-size:16px; }
.fx-muted { color:#8b7f76; font-size:12px; }
.fx-chip { display:inline-block; padding:2px 9px; margin:4px 4px 0 0; border-radius:999px; background:#f1e6e2; color:#c47a6c; font-size:11px; }
.fx-dot { display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:4px; vertical-align:middle; border:1px solid #ccc; }
.fx-row { background:#fff; border-radius:14px; padding:12px 16px; margin-bottom:8px; }
.fx-count { float:right; color:#c47a6c; }
.fx-banned { opacity:.45; }
.fx-banner { border-radius:12px; padding:8px 14px; margin-bottom:10px; font-size:14px; }
.stButton button { border-radius:999px; }
.stTabs [data-baseweb="tab"] { font-family:Georgia,serif; font-size:17px; }
</style>
""", unsafe_allow_html=True)

esc = html.escape


# ---------------------------------------------------------------- state helpers
def load():
    return core.load_state()


def save(w, p):
    core.save_state(w, p)


def flash(msg):
    st.session_state["flash"] = msg


def choice(label, options, key, default):
    """Chip-style picker: st.pills if this Streamlit has it, else a horizontal radio."""
    if hasattr(st, "pills"):
        val = st.pills(label, options, default=default, key=key)
        return val if val is not None else default
    return st.radio(label, options, index=options.index(default), horizontal=True, key=key)


def tile_html(g):
    p = g.photo_path()
    if p:
        mime = mimetypes.guess_type(p.name)[0] or "image/jpeg"
        data = base64.b64encode(p.read_bytes()).decode()
        return f'<div class="fx-tile"><img src="data:{mime};base64,{data}"></div>'
    return f'<div class="fx-tile" style="background:{core.SWATCH[g.color_group]}22">{core.ICON[g.type]}</div>'


def garment_card(g):
    return (f'<div class="fx-card{" fx-banned" if g.banned else ""}">{tile_html(g)}<div class="fx-body">'
            f'<div class="fx-name">{esc(g.name)}</div>'
            f'<div class="fx-muted">Worn {g.times_worn}x{" · banned" if g.banned else ""}</div>'
            f'<span class="fx-chip"><span class="fx-dot" style="background:{core.SWATCH[g.color_group]}"></span>{g.color_group}</span>'
            f'<span class="fx-chip">{g.warmth}</span><span class="fx-chip">{g.dressiness}</span></div></div>')


def mini_cards(items, cols=4):
    columns = st.columns(cols)
    for i, g in enumerate(items):
        columns[i % cols].markdown(garment_card(g), unsafe_allow_html=True)


# ---------------------------------------------------------------- callbacks (run before the page redraws)
def cb_ban(gid):
    w, p = load()
    if gid in w.items:
        w.ban_item(gid, not w.items[gid].banned)
        p.banned_ids.discard(gid) if not w.items[gid].banned else p.banned_ids.add(gid)
        save(w, p); flash(f"{'Banned' if w.items[gid].banned else 'Unbanned'} {w.items[gid].name}.")


def cb_remove(gid):
    w, p = load()
    g = w.remove(gid)
    if g:
        save(w, p); flash(f"Removed {g.name}.")


def cb_feedback(item_ids, action, reason_key=None, source="today", reason=None):
    w, p = load()
    items = [w.items[i] for i in item_ids if i in w.items]
    reason = st.session_state.get(reason_key) if reason_key else reason
    msg = core.feedback(w, p, items, action, reason)
    save(w, p)
    flash(msg)
    if source == "chat":
        st.session_state["chat_feedback_done"] = True


def cb_reset():
    core.reset_demo()
    for k in ["chat", "show_outfits", "chat_feedback_done"]:
        st.session_state.pop(k, None)
    flash("Demo data reset to the sample closet.")


# ---------------------------------------------------------------- page
wardrobe, profile = load()
st.markdown("<h1>Fashionista</h1>", unsafe_allow_html=True)
if "flash" in st.session_state:
    st.toast(st.session_state.pop("flash"))

with st.sidebar:
    st.markdown("### Fashionista")
    st.caption(f"{len(wardrobe.items)} pieces · {profile.events} feedback events learned")
    st.button("Reset demo data", on_click=cb_reset, key="reset_btn")

tab_closet, tab_today, tab_shop, tab_chat = st.tabs(["👚 Closet", "☀️ Today", "🛍️ Shop", "💬 Stylist"])

# ================================================================ CLOSET
with tab_closet:
    st.markdown("## My Wardrobe")
    n_avail = len(wardrobe.available())
    st.progress(min(n_avail / core.MIN_ITEMS, 1.0),
                text=f"Enough to suggest: {min(n_avail, core.MIN_ITEMS)}/{core.MIN_ITEMS} items"
                     + (" ✅" if n_avail >= core.MIN_ITEMS else " (add more clothes)"))

    with st.expander("➕ Add clothes", expanded=False):
        with st.form("add_form", clear_on_submit=True):
            name = st.text_input("Name", placeholder="e.g. Trench Coat", key="add_name")
            c1, c2 = st.columns(2)
            upload = c1.file_uploader("Upload a photo", type=["png", "jpg", "jpeg", "webp"], key="add_upload")
            camera = c2.camera_input("…or take one", key="add_camera")
            gtype = choice("Type", core.TYPES, "add_type", "top")
            color = choice("Color", core.COLORS, "add_color", "blue")
            warmth = choice("Warmth", list(core.WARMTH), "add_warmth", "mid")
            dress = choice("Dressiness", list(core.DRESSINESS), "add_dress", "casual")
            layer = st.selectbox("Layer", ["auto"] + core.LAYERS, key="add_layer")
            submitted = st.form_submit_button("Save")
        if submitted:
            if not name.strip():
                st.error("Please give the item a name.")
            else:
                gid = wardrobe.next_id()
                photo_file = upload or camera
                photo_name = None
                if photo_file is not None:
                    ext = (photo_file.name.rsplit(".", 1)[-1] if "." in (photo_file.name or "") else "jpg").lower()
                    photo_name = f"{gid}.{ext}"
                    _, _, photos = core.paths()
                    (photos / photo_name).write_bytes(photo_file.getvalue())
                lay = core.default_layer(gtype) if layer == "auto" else layer
                wardrobe.add_item(core.Garment(gid, name.strip(), gtype, lay, color, warmth, dress, photo=photo_name))
                save(wardrobe, profile)
                st.success(f"Added {name.strip()}.")

    f1, f2 = st.columns(2)
    ftype = f1.multiselect("Filter by type", core.TYPES, key="filter_type")
    fcolor = f2.multiselect("Filter by color", core.COLORS, key="filter_color")
    shown = [g for g in wardrobe.items.values()
             if (not ftype or g.type in ftype) and (not fcolor or g.color_group in fcolor)]
    cols = st.columns(4)
    for i, g in enumerate(shown):
        with cols[i % 4]:
            st.markdown(garment_card(g), unsafe_allow_html=True)
            b1, b2 = st.columns(2)
            b1.button("Unban" if g.banned else "Ban", key=f"ban_{g.id}", on_click=cb_ban, args=(g.id,))
            b2.button("Remove", key=f"rm_{g.id}", on_click=cb_remove, args=(g.id,))
    if not shown:
        st.info("No items match these filters.")

    st.markdown("### By layer")
    for layer, items in wardrobe.grouped_by_layer().items():
        names = ", ".join(esc(g.name) for g in items) or '<span class="fx-muted">None logged.</span>'
        st.markdown(f'<div class="fx-row"><b>{layer.capitalize()}</b><span class="fx-count">{len(items)}</span><br>{names}</div>',
                    unsafe_allow_html=True)

# ================================================================ TODAY
with tab_today:
    st.markdown("## What's today like?")
    c1, c2 = st.columns(2)
    with c1:
        plans = choice("Plans", ["Work", "Off duty"], "today_plans", "Work")
        cond = choice("Weather", ["Dry", "Rain"], "today_cond", "Dry")
    with c2:
        temp = st.slider("Temperature (°F)", 20, 100, 58, key="today_temp")
        norepeat = st.toggle("Don't repeat yesterday", value=True, key="today_norepeat")
    if st.button("Show outfits", type="primary", key="show_btn"):
        st.session_state["show_outfits"] = True

    if st.session_state.get("show_outfits"):
        req = core.OutfitRequest(plans=plans.lower(), temp_f=temp, condition=cond.lower(), no_repeat_yesterday=norepeat)
        outfits = core.smart_suggest(wardrobe, req, profile)
        st.markdown("### Your outfits")
        if not outfits:
            st.warning("No outfits fit these rules. Try turning off 'Don't repeat yesterday' or add more clothes.")
        for i, o in enumerate(outfits):
            ids = [g.id for g in o["items"]]
            with st.container(border=True):
                st.markdown(f'<h3 style="margin:0">{esc(o["name"])}</h3>'
                            f'<div>{" + ".join(esc(g.name) for g in o["items"])}</div>'
                            f'<div class="fx-muted">{esc(o["reason"])}</div>'
                            f'<span class="fx-chip">{req.plans}</span><span class="fx-chip">{req.temp_f}°F</span>'
                            f'<span class="fx-chip">{req.condition}</span>', unsafe_allow_html=True)
                mini_cards(o["items"], cols=5)
                b1, b2, b3, b4 = st.columns([1, 1, 2, 1])
                b1.button("Wear", type="primary", key=f"wear_{i}", on_click=cb_feedback, args=(ids, "wear"))
                b2.button("Skip", key=f"skip_{i}", on_click=cb_feedback, args=(ids, "skip"))
                b3.selectbox("Why not?", core.NO_REASONS, key=f"reason_{i}", label_visibility="collapsed")
                b4.button("No", key=f"no_{i}", on_click=cb_feedback, args=(ids, "no", f"reason_{i}"))

    st.markdown("### Your style so far")
    def chips(prefix):
        c = "".join(f'<span class="fx-chip">{esc(k)} {v:+.1f}</span>' for k, v in profile.top(prefix) if v > 0)
        return c or '<span class="fx-muted">Not enough feedback yet.</span>'
    fav = [int(k) for k, v in profile.top("id") if v > 0]
    favs = ", ".join(esc(wardrobe.items[i].name) for i in fav if i in wardrobe.items) or "-"
    st.markdown(f'<div class="fx-row"><span class="fx-muted">Learned from {profile.events} feedback events</span></div>'
                f'<div class="fx-row"><b>Top colors</b><br>{chips("color")}</div>'
                f'<div class="fx-row"><b>Dressiness</b><br>{chips("dress")}</div>'
                f'<div class="fx-row"><b>Warmth</b><br>{chips("warmth")}</div>'
                f'<div class="fx-row"><b>Most-loved pieces</b><br>{favs}</div>', unsafe_allow_html=True)

# ================================================================ SHOP
with tab_shop:
    st.markdown("## Closet Analysis")
    gaps = core.gap_analysis(wardrobe)
    st.caption(f"Season: {gaps[0]['season'] if gaps else core.season(core.today())}")
    missing = [g for g in gaps if not g["ok"]]
    for g in missing:
        p = g["product"]
        st.markdown(f'<div class="fx-row">⚠️ You\'re missing a <b>{esc(g["label"])}</b> for {g["season"]}.<br>'
                    f'<span class="fx-muted">Try: {esc(p["name"])} · {esc(p["store"])} · {esc(p["price"])}</span> '
                    f'<span class="fx-chip">EXAMPLE DATA</span></div>', unsafe_allow_html=True)
    for g in gaps:
        if g["ok"]:
            st.markdown(f'<div class="fx-row">✅ You have a {esc(g["label"])}.</div>', unsafe_allow_html=True)
    if not missing:
        st.success("No gaps found. Nice closet!")
    st.caption("Products shown are example data. A real marketplace API would plug in here later.")

# ================================================================ STYLIST
with tab_chat:
    st.markdown("## 💬 Wardrobe Bot")
    if core.get_llm_client() is not None:
        st.markdown(f'<div class="fx-banner" style="background:#e3efe3">🟢 Online · model <b>{esc(core.llm_model())}</b></div>',
                    unsafe_allow_html=True)
    else:
        st.markdown('<div class="fx-banner" style="background:#f1e6e2">⚪ Offline mode: set OPENAI_API_KEY '
                    '(and OPENAI_BASE_URL for Grok) to use the LLM stylist. Using the built-in rules.</div>',
                    unsafe_allow_html=True)

    history = st.session_state.setdefault("chat", [])
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

    prompt = st.chat_input("Ask for an outfit, e.g. 'business meeting, blue theme'", key="chat_input")
    if prompt:
        st.session_state["chat_feedback_done"] = False
        core.stylist_chat(prompt, history, wardrobe, profile)
        st.rerun()
