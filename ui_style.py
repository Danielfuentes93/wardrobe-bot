"""Visual layer for Fashionista (v3 "soft monochrome dashboard" look): one CSS block injected once by app.py.

Fonts: Inter is loaded from Google Fonts.  If the visitor's browser cannot reach Google, the fallbacks
(system-ui / Segoe UI / Roboto) keep the same clean geometric-sans feel.

Design tokens: a large light-grey floating panel on a slightly darker grey page, white bento cards, near-black ink,
and ONE warm accent (soft peach/sand) used only for progress, highlights and the demo strip.
"""

# Inline icons (stroke = currentColor).  Decorative, so they are aria-hidden where used.
ICONS = {
    "search": '<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="6.5"/><path d="m20 20-3.6-3.6"/></svg>',
    "bell": '<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M6 16.5V11a6 6 0 1 1 12 0v5.5l1.5 1.5h-15z"/><path d="M10 20.5a2 2 0 0 0 4 0"/></svg>',
    "sliders": '<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 7h9M17 7h3M4 17h3M11 17h9"/><circle cx="15" cy="7" r="2"/><circle cx="9" cy="17" r="2"/></svg>',
    "user": '<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8.5" r="3.6"/><path d="M5 20c.8-3.6 3.6-5.4 7-5.4s6.2 1.8 7 5.4"/></svg>',
    "arrow": '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17 17 7M9 7h8v8"/></svg>',
    "heart": '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.4A4 4 0 0 1 19 10c0 5.6-7 10-7 10z"/></svg>',
    "hanger": '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8.2a2.2 2.2 0 1 0-2.2-2.2"/><path d="M12 8.2v1.6l8.4 5.6a1.4 1.4 0 0 1-.8 2.6H4.4a1.4 1.4 0 0 1-.8-2.6z"/></svg>',
    "lock": '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="10.5" width="14" height="9.5" rx="3"/><path d="M8.5 10.5V8a3.5 3.5 0 0 1 7 0v2.5"/></svg>',
    "check": '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="m5 12.5 4.5 4.5L19 7.5"/></svg>',
    "alert": '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8v5M12 16.6v.1"/><circle cx="12" cy="12" r="9"/></svg>',
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
  --page:#dcdcda; --panel:#f1f1f0; --card:#ffffff; --soft:#f6f6f5; --chip:#ebebea; --line:#e4e4e2; --line-2:#d6d6d3;
  --ink:#0e0e10; --ink-2:#34343a; --muted:#7b7b82; --faint:#a8a8ad;
  --peach:#ecc9a4; --peach-deep:#c98f58; --peach-tint:#f8ebdd; --ok:#2f7a4d; --ok-tint:#e3f1e8;
  --sans:'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  --shadow:0 1px 2px rgba(20,20,24,.04), 0 8px 24px rgba(20,20,24,.05);
  --shadow-lg:0 2px 4px rgba(20,20,24,.05), 0 16px 36px rgba(20,20,24,.10);
  --hatch:repeating-linear-gradient(115deg, #cfcfcc 0 1px, transparent 1px 5px);
  --navh:56px;
}

/* ---------- page + floating panel ---------- */
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
  background:radial-gradient(1200px 600px at 50% -10%, #e7e7e5 0%, var(--page) 70%) fixed !important; }
.stApp, .stApp p, .stApp label, .stApp li, .stApp input, .stApp textarea, .stApp button, .stApp select,
[data-testid="stWidgetLabel"], [data-baseweb], [data-testid="stMarkdownContainer"], [data-testid="stCaptionContainer"] {
  font-family:var(--sans) !important; color:var(--ink); }
.stApp { -webkit-font-smoothing:antialiased; text-rendering:optimizeLegibility; }
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"],
[data-testid="stHeader"], [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"],
[data-testid="stHeaderActionElements"], .stMarkdown a.anchor { display:none !important; visibility:hidden !important; }
.block-container, [data-testid="stMainBlockContainer"] {
  max-width:1180px !important; width:calc(100% - 48px) !important; margin:28px auto 40px !important;
  padding:22px 30px 30px !important; background:var(--panel); border-radius:32px;
  border:1px solid rgba(255,255,255,.75);
  box-shadow:0 40px 90px -20px rgba(24,24,28,.22), 0 6px 18px rgba(24,24,28,.06), inset 0 1px 0 rgba(255,255,255,.9); }
[data-testid="stVerticalBlock"] { gap:1rem !important; }
h1, h2, h3, h4 { font-family:var(--sans) !important; font-weight:700 !important; color:var(--ink) !important; letter-spacing:-.02em; padding:0 !important; }
[data-testid="stMarkdown"], [data-testid="stMarkdownContainer"] { margin-bottom:0 !important; }
[data-testid="stMarkdownContainer"] > p:last-child { margin-bottom:0 !important; }
.stApp ::selection { background:var(--peach); color:var(--ink); }
[data-testid="stToast"], [data-testid="stNotification"] { border-radius:999px !important; background:var(--ink) !important; box-shadow:var(--shadow-lg); }
[data-testid="stToast"] *, [data-testid="stNotification"] * { color:#fff !important; }

/* ---------- top nav: brand left, tabs (pills) centre, round icon buttons right ---------- */
.fx-nav { display:flex; align-items:center; justify-content:space-between; height:var(--navh); }
.fx-brand { display:flex; align-items:center; gap:12px; font:600 17px/1 var(--sans); letter-spacing:-.01em; color:var(--ink); }
.fx-logo { width:44px; height:44px; border-radius:50%; background:#fff; display:flex; align-items:center; justify-content:center;
  box-shadow:var(--shadow); color:var(--ink); }
.fx-nav-icons { display:flex; gap:10px; align-items:center; }
.fx-ic { width:40px; height:40px; border-radius:50%; background:#f7f7f6; border:1px solid var(--line); display:flex; align-items:center;
  justify-content:center; color:var(--ink); }
.fx-ic.avatar { background:linear-gradient(145deg,#3a3a40,#0e0e10); color:#fff; border:0; box-shadow:0 0 0 3px #fff; }
[data-testid="stTabs"] { margin-top:calc(-1 * var(--navh) - 1rem) !important; }
[data-baseweb="tab-list"], [role="tablist"] { gap:8px !important; background:transparent !important; padding:0 !important; border:0 !important; box-shadow:none !important;
  width:fit-content; max-width:100%; overflow:visible; scrollbar-width:none; margin:0 auto; height:var(--navh); align-items:center; }
[data-baseweb="tab-list"]::-webkit-scrollbar { display:none; }
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"], .react-aria-SelectionIndicator { display:none !important; }
button[data-baseweb="tab"], [data-testid="stTab"] { border-radius:999px !important; padding:0 22px !important; height:42px !important; border:0 !important; box-shadow:none;
  background:var(--chip) !important; transition:background .15s, color .15s, transform .15s; cursor:pointer; margin:0 !important; }
button[data-baseweb="tab"] p, [data-testid="stTab"] p { font:500 13.5px/1 var(--sans) !important; color:var(--ink-2) !important; margin:0; }
button[data-baseweb="tab"]:hover, [data-testid="stTab"]:hover { background:#e1e1df !important; }
button[data-baseweb="tab"][aria-selected="true"], [data-testid="stTab"][aria-selected="true"] { background:var(--ink) !important; box-shadow:0 6px 16px rgba(14,14,16,.22) !important; }
button[data-baseweb="tab"][aria-selected="true"] p, [data-testid="stTab"][aria-selected="true"] p { color:#fff !important; font-weight:600 !important; }
[role="tablist"]::after, [role="tablist"]::before { display:none !important; content:none !important; }
[data-baseweb="tab-panel"], [role="tabpanel"] { padding-top:1.1rem !important; }

/* ---------- class-demo strip ---------- */
.fx-demo { display:flex; align-items:flex-start; gap:10px; margin:0 0 6px; padding:8px 14px; background:var(--peach-tint);
  border-radius:999px; font-size:12px; color:var(--ink-2); line-height:1.5; border-radius:18px; }
.fx-demo .fx-pill { flex:none; background:var(--ink); color:#fff; font-weight:600; font-size:10px;
  letter-spacing:.1em; text-transform:uppercase; padding:3px 10px; border-radius:999px; margin-top:1px; }
.fx-demo details summary { cursor:pointer; list-style:none; }
.fx-demo details summary::-webkit-details-marker { display:none; }
.fx-demo details summary u { color:var(--ink); font-weight:600; text-decoration:none; border-bottom:1px solid var(--peach-deep); margin-left:6px; white-space:nowrap; }
.fx-demo details[open] summary u { display:none; }
.fx-demo details p { margin:6px 0 0; }

/* ---------- section headings ---------- */
.fx-sec { margin:2px 0 0; }
.fx-sec h2 { font-size:1.45rem !important; margin:0 !important; line-height:1.2 !important; }
.fx-sec h3 { font-size:1.15rem !important; margin:0 !important; }
.fx-sec p { margin:4px 0 0; font-size:13px; color:var(--muted); }
.fx-sec.sub { margin-top:10px; }

/* ---------- hero strip: stats with bars (left) + visual (right) ---------- */
.fx-hero { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1.05fr); gap:28px; align-items:center; padding:6px 4px 0; }
.fx-hero-stats { display:grid; grid-template-columns:1fr 1fr; gap:22px; }
.fx-hs .l { font-size:12.5px; color:var(--ink-2); font-weight:500; }
.fx-hs .v { display:flex; align-items:baseline; gap:6px; margin:8px 0 14px; font:700 30px/1 var(--sans); letter-spacing:-.03em; color:var(--ink); }
.fx-hs .v small { font:500 14px var(--sans); color:var(--faint); letter-spacing:0; }
.fx-bar { height:16px; border-radius:999px; background:var(--hatch); position:relative; overflow:hidden; }
.fx-bar i { position:absolute; inset:0 auto 0 0; border-radius:999px; background:var(--ink); }
.fx-bar.peach i { background:var(--peach); }
.fx-hero-vis { position:relative; height:224px; border-radius:26px; overflow:hidden;
  background:radial-gradient(120% 140% at 80% 0%, #ffffff 0%, #ececea 55%, #e1e1df 100%); box-shadow:inset 0 0 0 1px rgba(255,255,255,.9), var(--shadow); }
.fx-hero-vis::after { content:""; position:absolute; left:6%; right:6%; bottom:14px; height:14px; background:radial-gradient(closest-side, rgba(14,14,16,.16), transparent); filter:blur(3px); }
.fx-float { position:absolute; bottom:30px; width:21%; aspect-ratio:3/4; border-radius:20px; background:#fff; box-shadow:0 14px 30px rgba(20,20,24,.16), 0 2px 4px rgba(20,20,24,.06);
  overflow:hidden; display:flex; flex-direction:column; }
.fx-float .fx-tile { flex:1; min-height:0; height:auto; border-radius:0; font-size:44px; }
.fx-float .fx-cat { display:none; }
.fx-float b { font:600 11px/1 var(--sans); padding:9px 10px 10px; color:var(--ink); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.fx-float:nth-of-type(1) { left:5%; transform:rotate(-5deg) translateY(6px); }
.fx-float:nth-of-type(2) { left:28%; transform:translateY(-8px); z-index:2; width:23%; }
.fx-float:nth-of-type(3) { left:53%; transform:rotate(4deg) translateY(2px); z-index:1; }
.fx-float:nth-of-type(4) { left:74%; transform:rotate(8deg) translateY(12px); }
.fx-hero-vis .tag { position:absolute; top:14px; left:16px; z-index:3; background:rgba(255,255,255,.9); backdrop-filter:blur(6px); border-radius:999px;
  padding:6px 12px; font:600 11px/1 var(--sans); color:var(--ink); box-shadow:var(--shadow); }

/* ---------- bento cards ---------- */
.fx-bento { display:grid; grid-template-columns:1fr 1fr 1.45fr; grid-auto-rows:minmax(0,auto); gap:14px; }
.fx-b { background:var(--card); border-radius:26px; padding:20px 22px; box-shadow:var(--shadow); min-width:0; position:relative; display:flex; flex-direction:column; }
.fx-b .top { display:flex; align-items:center; justify-content:space-between; gap:10px; }
.fx-b .t { font:500 14px/1.2 var(--sans); color:var(--ink); }
.fx-rb { width:30px; height:30px; flex:none; border-radius:50%; background:#fff; border:1px solid var(--line); display:inline-flex; align-items:center; justify-content:center; color:var(--ink);
  box-shadow:0 1px 2px rgba(20,20,24,.05); }
.fx-rb.dark { background:var(--ink); border-color:var(--ink); color:#fff; }
.fx-rb.on { color:#fff; background:var(--ink); border-color:var(--ink); }
.fx-rb.on svg { fill:currentColor; }
.fx-b .num { font:700 clamp(34px,4.2vw,46px)/1 var(--sans); letter-spacing:-.04em; margin-top:auto; padding-top:22px; color:var(--ink); }
.fx-b .num small { font:500 13px var(--sans); letter-spacing:0; color:var(--muted); margin-left:2px; }
.fx-b .sub { font-size:12px; color:var(--muted); margin-top:6px; }
.fx-b .foot { display:flex; align-items:flex-end; justify-content:space-between; gap:10px; margin-top:auto; padding-top:16px; }
.fx-b .foot .num { padding-top:0; margin-top:0; }
.fx-bars { display:flex; align-items:flex-end; gap:2.5px; height:44px; }
.fx-bars i { display:block; width:3px; border-radius:2px; background:#c9c9c6; }
.fx-bars i.k { background:var(--ink); }
.fx-bento.three { grid-template-columns:repeat(3, minmax(0,1fr)); }
.fx-bento .span-rows { grid-row:span 2; }
.fx-bento .span-cols { grid-column:span 2; }
.fx-layers { display:flex; flex-direction:column; gap:12px; margin-top:16px; }
.fx-layer .r { display:flex; align-items:center; gap:10px; }
.fx-layer .n { width:78px; flex:none; font-size:12px; color:var(--muted); text-transform:capitalize; }
.fx-layer .trk { flex:1; min-width:0; height:26px; border-radius:999px; background:#f3f3f2; position:relative; }
.fx-layer .trk i { position:absolute; inset:0 auto 0 0; background:var(--ink); border-radius:999px; min-width:42px; color:#fff; font:600 11px/26px var(--sans);
  text-align:right; padding-right:11px; box-sizing:border-box; }
.fx-layer .trk i.zero { background:#e9e9e8; color:var(--muted); min-width:30px; text-align:center; padding:0; }
.fx-layer .its { font-size:11px; color:var(--faint); margin:3px 0 0 88px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }

/* ---------- buttons ---------- */
.stButton > button, [data-testid="stFormSubmitButton"] > button, [data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-secondaryFormSubmit"] {
  border-radius:999px !important; border:1px solid var(--line-2) !important; background:transparent !important; color:var(--ink) !important;
  font:500 13px/1.2 var(--sans) !important; padding:.45rem 1.15rem !important; min-height:2.4rem; box-shadow:none !important; transition:all .15s ease; }
.stButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover { border-color:var(--ink) !important; background:#fff !important; color:var(--ink) !important; }
.stButton > button:active { transform:scale(.98); }
button[kind="primary"], [data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"],
.stButton > button[kind="primary"], [data-testid="stFormSubmitButton"] > button[kind="primaryFormSubmit"], [data-testid="stFormSubmitButton"] > button[kind="primary"] {
  background:var(--ink) !important; border-color:var(--ink) !important; color:#fff !important; font-weight:600 !important; box-shadow:0 8px 18px rgba(14,14,16,.20) !important; }
button[kind="primary"]:hover, [data-testid="stBaseButton-primary"]:hover, [data-testid="stBaseButton-primaryFormSubmit"]:hover,
.stButton > button[kind="primary"]:hover, [data-testid="stFormSubmitButton"] > button[kind="primaryFormSubmit"]:hover {
  background:#2a2a30 !important; border-color:#2a2a30 !important; color:#fff !important; }
button[kind="primary"] p, [data-testid="stBaseButton-primary"] p, [data-testid="stBaseButton-primaryFormSubmit"] p { color:#fff !important; }
.stButton > button p { font-size:13px !important; font-weight:500 !important; }
button:focus-visible { outline:2px solid var(--ink) !important; outline-offset:2px; }

/* ---------- inputs: pill dropdowns + search ---------- */
[data-testid="stWidgetLabel"] p, label p { font-size:12px !important; font-weight:600 !important; color:var(--muted) !important; letter-spacing:.01em; }
[data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="textarea"], [data-baseweb="base-input"],
[data-testid="stSelectbox"] [role="group"], [data-testid="stMultiSelect"] [role="group"], [data-testid="stTextInputRootElement"] {
  border-radius:999px !important; background:#fff !important; border:1px solid var(--line) !important; box-shadow:none !important; min-height:2.6rem; }
[data-testid="stTextInputRootElement"] input, [data-testid="stSelectbox"] input, [data-testid="stMultiSelect"] input { background:transparent !important; font-size:13.5px; padding-left:.9rem; }
[data-baseweb="input"]:focus-within, [data-baseweb="select"] > div:focus-within, [data-testid="stSelectbox"] [role="group"]:focus-within,
[data-testid="stMultiSelect"] [role="group"]:focus-within, [data-testid="stTextInputRootElement"]:focus-within { border-color:var(--ink) !important; box-shadow:0 0 0 3px rgba(14,14,16,.08) !important; }
[data-baseweb="select"] svg, [data-testid="stMultiSelect"] svg { color:var(--ink-2); }
[data-baseweb="tag"], [data-testid="stMultiSelect"] [data-testid="stTag"] { background:var(--ink) !important; border-radius:999px !important; }
[data-baseweb="tag"] span, [data-baseweb="tag"] svg { color:#fff !important; fill:#fff; }
[data-baseweb="popover"] [role="listbox"], [data-baseweb="menu"] { border-radius:18px !important; box-shadow:var(--shadow-lg); }
[data-testid="stFileUploaderDropzone"] { background:#fafafa; border:1.5px dashed var(--line-2); border-radius:20px; }
[data-testid="stCameraInput"] > div, [data-testid="stCameraInput"] img { border-radius:20px; }
[data-testid="stForm"] { border:0 !important; border-radius:22px !important; background:var(--soft); padding:1.1rem !important; }
[data-testid="stExpander"] { border:0 !important; border-radius:22px !important; background:var(--soft); overflow:hidden; }
[data-testid="stExpander"] details { border:0 !important; }
[data-testid="stExpander"] [data-testid="stForm"] { background:transparent; padding:.2rem .4rem !important; }
[data-testid="stExpander"] details summary { padding:.75rem 1.1rem; }
[data-testid="stExpander"] summary p { font:600 13.5px var(--sans) !important; color:var(--ink) !important; }
[data-testid="stSlider"] [role="slider"] { background:var(--ink) !important; box-shadow:0 0 0 5px rgba(14,14,16,.10); }
[data-testid="stSlider"] [data-testid="stSliderThumbValue"], [data-testid="stSlider"] [data-testid="stSliderTickBarMin"], [data-testid="stSlider"] [data-testid="stSliderTickBarMax"] { color:var(--ink-2) !important; font-weight:600; }
[data-testid="stTickBar"] { display:none; }
[data-testid="stCheckbox"] label p, [data-testid="stToggle"] label p { font-size:13.5px !important; color:var(--ink) !important; font-weight:500 !important; }

/* pills (st.pills): inactive light grey, active solid black */
[data-testid="stPills"] button, button[data-variant="pills"], [data-testid="stBaseButton-pills"], [data-testid="stBaseButton-pillsActive"] {
  border-radius:999px !important; padding:.3rem .95rem !important; min-height:2.1rem; border:0 !important;
  background:var(--chip) !important; color:var(--ink-2) !important; box-shadow:none !important; transition:all .15s; }
button[data-variant="pills"]:hover { background:#e0e0de !important; }
button[data-variant="pills"] p { font:500 13px var(--sans) !important; color:inherit !important; }
button[data-variant="pills"][data-selected="true"], [data-testid="stBaseButton-pillsActive"] { background:var(--ink) !important; color:#fff !important; }
button[data-variant="pills"][data-selected="true"] p, [data-testid="stBaseButton-pillsActive"] p { color:#fff !important; font-weight:600 !important; }

/* alerts */
[data-testid="stAlert"], [data-testid="stAlertContainer"] { border-radius:18px !important; border:0 !important; background:#fff !important; box-shadow:var(--shadow); font-size:13.5px; }
[data-testid="stAlert"] [data-testid="stAlertContainer"] { box-shadow:none; }
[data-testid="InputInstructions"] { display:none !important; }
[data-testid="stAlertContainer"] p { color:var(--ink) !important; }

/* ---------- closet card: header, filter bar, grid ---------- */
.st-key-closet_card, .st-key-controls, .st-key-chat_card, .st-key-gate_wrap, .st-key-style_card, [class*="st-key-outfit_"] {
  background:var(--card); border-radius:28px; box-shadow:var(--shadow); padding:22px 24px !important; }
.fx-cardhead { display:flex; align-items:flex-start; justify-content:space-between; gap:12px; }
.fx-cardhead + .fx-bento { margin-top:14px; }
.fx-cardhead h2, .fx-cardhead h3 { font-size:1.15rem !important; margin:0 !important; font-weight:700 !important; }
.fx-cardhead p { margin:3px 0 0; font-size:12.5px; color:var(--muted); }
.fx-count-pill { background:var(--ink); color:#fff; border-radius:999px; padding:7px 14px; font:600 12px/1 var(--sans); white-space:nowrap; }
.st-key-filters { margin:2px 0 4px; }
.st-key-filters [data-testid="stHorizontalBlock"] { gap:10px !important; align-items:center; }
.st-key-filters [data-testid="stTextInputRootElement"] { background:#fff !important; }
.st-key-filters [data-baseweb="select"] > div { background:var(--soft) !important; }

.st-key-closet_grid { display:grid !important; grid-template-columns:repeat(4, minmax(0,1fr)); gap:16px !important; }
@media (max-width:1000px) { .st-key-closet_grid { grid-template-columns:repeat(3, minmax(0,1fr)); } }
@media (max-width:700px) { .st-key-closet_grid { grid-template-columns:repeat(2, minmax(0,1fr)); gap:10px !important; } }
[class*="st-key-card_"] { background:var(--soft); border-radius:24px; padding:8px !important; gap:0 !important; overflow:hidden;
  transition:box-shadow .2s, transform .2s, background .2s; }
[class*="st-key-card_"]:hover { background:#f0f0ee; box-shadow:var(--shadow-lg); transform:translateY(-2px); }
[class*="st-key-card_"] [data-testid="stHorizontalBlock"] { padding:0 6px 6px; gap:8px !important; flex-wrap:nowrap !important; flex-direction:row !important; }
[class*="st-key-card_"] [data-testid="stColumn"] > *, [class*="st-key-card_"] [data-testid="stColumn"] [data-testid="stElementContainer"] { width:100% !important; }
[class*="st-key-card_"] [data-testid="stColumn"] { min-width:0 !important; flex:1 1 0 !important; width:auto !important; }
[class*="st-key-card_"] .stButton, [class*="st-key-card_"] [data-testid="stButton"] { width:100% !important; }
[class*="st-key-card_"] .stButton button { width:100% !important; min-height:2rem; padding:.3rem .5rem !important; font-size:12px !important; border-color:var(--line-2) !important; }
[class*="st-key-card_"] .stButton button p { font-size:12px !important; }

/* item tile + meta */
.fx-card { overflow:hidden; }
.fx-tile { position:relative; height:176px; border-radius:20px; display:flex; align-items:center; justify-content:center; font-size:62px; overflow:hidden;
  background:radial-gradient(90% 80% at 50% 38%, #fff 0%, transparent 70%), linear-gradient(160deg, color-mix(in srgb, var(--sw) 9%, #f4f4f3) 0%, color-mix(in srgb, var(--sw) 22%, #e9e9e7) 100%); }
.fx-tile.mini { height:84px; font-size:34px; border-radius:16px; }
.fx-tile img { width:100%; height:100%; object-fit:cover; display:block; }
.fx-tile .fx-emoji { filter:saturate(.8) drop-shadow(0 10px 10px rgba(20,20,24,.20)); }
.fx-cat { position:absolute; top:10px; left:10px; background:rgba(255,255,255,.92); color:var(--ink); font:600 10px/1 var(--sans);
  letter-spacing:.06em; text-transform:capitalize; padding:6px 10px; border-radius:999px; }
.fx-fab { position:absolute; top:8px; right:8px; display:flex; gap:6px; }
.fx-body { padding:12px 8px 12px; }
.fx-body.mini { padding:8px 6px 4px; }
.fx-top { display:flex; align-items:baseline; justify-content:space-between; gap:8px; }
.fx-name { font:600 14.5px/1.25 var(--sans); color:var(--ink); letter-spacing:-.01em; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.fx-body.mini .fx-name { font-size:12.5px; }
.fx-worn { font:700 13px/1 var(--sans); color:var(--ink); white-space:nowrap; letter-spacing:-.02em; }
.fx-worn small { font:500 10.5px var(--sans); color:var(--muted); margin-left:2px; letter-spacing:0; }
.fx-metaline { display:flex; flex-wrap:wrap; gap:3px 12px; margin-top:8px; font-size:11px; color:var(--muted); }
.fx-metaline span { display:inline-flex; align-items:center; gap:5px; }
.fx-dot { width:8px; height:8px; border-radius:50%; display:inline-block; box-shadow:0 0 0 1px rgba(0,0,0,.15); }
.fx-banned { opacity:.55; filter:grayscale(.7); }
.fx-banned .fx-worn::after { content:" · banned"; font-weight:500; color:var(--muted); }
.fx-muted { color:var(--muted); font-size:13px; }
.fx-chip { display:inline-flex; align-items:center; gap:5px; padding:4px 11px; border-radius:999px; background:var(--chip); color:var(--ink-2); font-size:11.5px; font-weight:500; line-height:1.4; }
.fx-chip.dark { background:var(--ink); color:#fff; }
.fx-chip.warn { background:var(--peach-tint); color:#8a5a26; font-weight:600; letter-spacing:.04em; }
.fx-chips { display:flex; flex-wrap:wrap; gap:6px; margin-top:8px; }

/* outfit cards on Today */
[class*="st-key-outfit_"] [data-testid="stHorizontalBlock"] { align-items:center; }
[class*="st-key-outfit_"] [data-testid="stColumn"] > *, [class*="st-key-outfit_"] [data-testid="stColumn"] [data-testid="stElementContainer"], [class*="st-key-outfit_"] .stButton { width:100% !important; }
[class*="st-key-outfit_"] .stButton button { width:100% !important; }
.fx-look-eyebrow { display:inline-block; font:600 10.5px/1 var(--sans); letter-spacing:.08em; text-transform:uppercase; color:#fff; background:var(--ink); padding:6px 11px; border-radius:999px; margin-bottom:12px; }
.fx-look-title { font:700 1.45rem/1.15 var(--sans); letter-spacing:-.025em; color:var(--ink); }
.fx-look-pieces { font-size:13.5px; color:var(--ink-2); margin-top:6px; }
.fx-look-why { font-size:12.5px; color:var(--muted); margin-top:4px; }
.fx-minirow { display:grid; grid-template-columns:repeat(auto-fill, minmax(118px, 148px)); gap:10px; margin:12px 0 10px; }
.fx-minirow .fx-card { background:var(--soft); border-radius:20px; padding:6px; }

/* today: two-up bento (right card stretches to the height of the controls card) */
.st-key-today_row [data-testid="stColumn"]:last-child [data-testid="stLayoutWrapper"], .st-key-today_row .st-key-style_card { flex:1 1 auto; }
.st-key-controls .fx-cardhead { margin-bottom:6px; }
.fx-style-grid { display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:12px; }
.fx-mini { background:var(--soft); border-radius:18px; padding:12px 14px; font-size:13px; line-height:1.45; min-width:0; }
.fx-mini .fx-label { font:600 11px/1 var(--sans); color:var(--muted); margin-bottom:8px; }

/* info rows (shop) */
.fx-grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(260px, 1fr)); gap:14px; }
.fx-row { background:var(--card); border-radius:26px; padding:18px 20px; box-shadow:var(--shadow); font-size:14px; line-height:1.5; }
.fx-gap { display:flex; gap:14px; align-items:flex-start; }
.fx-gap .ico { flex:none; width:40px; height:40px; border-radius:50%; display:flex; align-items:center; justify-content:center; background:var(--peach-tint); color:#8a5a26; }
.fx-gap.ok { align-items:center; }
.fx-gap.ok .ico { background:var(--ink); color:#fff; }
.fx-gap .t { font-size:14px; color:var(--ink); line-height:1.4; font-weight:500; }
.fx-gap .t b { font-weight:700; }
.fx-gap .s { font-size:12.5px; color:var(--muted); margin-top:4px; }
.fx-prod { display:flex; align-items:center; justify-content:space-between; gap:10px; margin-top:12px; padding:10px 12px; background:var(--soft); border-radius:16px; font-size:12.5px; }
.fx-prod b { font-weight:600; color:var(--ink); } .fx-prod span { color:var(--muted); }
.fx-prod .pr { font:700 14px var(--sans); color:var(--ink); letter-spacing:-.02em; }
.fx-empty { text-align:center; border-radius:26px; padding:36px 20px; background:var(--card); box-shadow:var(--shadow); color:var(--muted); font-size:13.5px; }
.fx-empty .big { width:54px; height:54px; margin:0 auto 12px; border-radius:50%; background:var(--soft); display:flex; align-items:center; justify-content:center; font-size:24px; }
.fx-empty b { display:block; font:700 1.05rem var(--sans); color:var(--ink); margin-bottom:4px; letter-spacing:-.01em; }

/* ---------- stylist ---------- */
.fx-status { display:inline-flex; align-items:center; gap:8px; background:var(--soft); border-radius:999px; padding:8px 14px; font-size:12px; color:var(--muted); line-height:1.4; }
.fx-status .led { flex:none; width:8px; height:8px; border-radius:50%; background:var(--faint); }
.fx-status.on .led { background:var(--ok); box-shadow:0 0 0 3px var(--ok-tint); }
.fx-status.on { color:var(--ink-2); }
.st-key-chat_meta { flex-direction:row !important; flex-wrap:wrap; align-items:center; gap:10px !important; }
.st-key-chat_meta > * { width:auto !important; flex:0 0 auto; }
.st-key-counter { background:var(--ink); border-radius:999px; padding:0 14px 0 4px !important; flex-direction:row !important; align-items:center; gap:10px !important; }
.st-key-counter > * { width:auto !important; flex:0 0 auto; }
.st-key-counter [data-testid="stCaptionContainer"], .st-key-counter [data-testid="stCaptionContainer"] p { opacity:1 !important;
  font:600 12px/1 var(--sans) !important; color:#fff !important; padding:9px 0 9px 10px; margin:0; }
.st-key-counter .fx-track { width:56px; height:5px; border-radius:999px; background:rgba(255,255,255,.22); overflow:hidden; }
.st-key-counter .fx-track i { display:block; height:100%; background:var(--peach); border-radius:999px; }
.st-key-counter [data-testid="stMarkdownContainer"] { line-height:0; }
.fx-privacy { font-size:11.5px; color:var(--muted); margin:2px 0 2px; }
.st-key-chat_card { display:flex; flex-direction:column; gap:14px !important; }
.fx-chatscroll { height:1px; }

[data-testid="stChatMessage"] { background:var(--soft); border-radius:22px 22px 22px 8px; padding:12px 16px; box-shadow:none; gap:0; width:fit-content; max-width:min(88%, 640px); border:0; }
[data-testid="stChatMessage"]:not(:has([data-testid="stChatMessageAvatarUser"])):not(:has([aria-label="Chat message from user"])) { width:100%; max-width:640px; }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]), [data-testid="stChatMessage"]:has([aria-label="Chat message from user"]) {
  background:var(--ink); border-radius:22px 22px 8px 22px; margin-left:auto; }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) *, [data-testid="stChatMessage"]:has([aria-label="Chat message from user"]) * { color:#fff !important; }
[data-testid="stChatMessageAvatarUser"], [data-testid="stChatMessageAvatarAssistant"], [data-testid="stChatMessage"] > div:first-child:not([data-testid="stChatMessageContent"]) { display:none !important; }
[data-testid="stChatMessage"] p { font-size:14px; line-height:1.55; }
[data-testid="stChatMessage"] [data-testid="stCaptionContainer"] p { font-size:11.5px !important; color:var(--muted) !important; }
[data-testid="stChatMessage"] .fx-minirow .fx-card { background:#fff; }
[data-testid="stChatMessage"] [data-testid="stHorizontalBlock"] { flex-wrap:wrap !important; gap:8px !important; }
[data-testid="stChatMessage"] [data-testid="stColumn"] { flex:0 0 auto !important; width:auto !important; min-width:0 !important; }
[data-testid="stChatMessage"] .stButton button { white-space:nowrap; }
[data-testid="stChatInput"], [data-testid="stChatInput"] > div { border-radius:999px !important; border:1px solid var(--line) !important; background:var(--soft) !important; box-shadow:none !important; }
[data-testid="stChatInput"] > div { border:0 !important; }
[data-testid="stChatInput"] textarea { font-family:var(--sans) !important; font-size:14px; background:transparent !important; }
[data-testid="stChatInput"] button { border-radius:50% !important; }
[data-testid="stChatInput"] button:not(:disabled) { background:var(--ink) !important; color:#fff !important; }
[data-testid="stChatInput"] button:disabled { background:var(--chip) !important; }
[data-testid="stBottom"] > div, [data-testid="stBottomBlockContainer"] { background:transparent !important; }
.fx-examples { display:flex; flex-wrap:wrap; gap:8px; justify-content:center; margin-top:14px; }
.fx-examples span { background:var(--chip); border-radius:999px; padding:7px 14px; font-size:12px; color:var(--ink-2); font-weight:500; }
.st-key-chat_card .fx-empty { box-shadow:none; background:var(--soft); }

/* ---------- passcode gate ---------- */
.st-key-gate_wrap { max-width:440px; margin:26px auto 4px; }
.fx-gate-head { text-align:center; margin-bottom:6px; }
.fx-gate-head .lock { width:56px; height:56px; margin:0 auto 14px; border-radius:50%; background:var(--ink); color:#fff; display:flex; align-items:center; justify-content:center; box-shadow:0 10px 22px rgba(14,14,16,.25); }
.fx-gate-head h3 { font-size:1.4rem !important; margin:0 !important; }
.fx-gate-head p { color:var(--muted); font-size:13px; margin:6px 0 0; }
.st-key-gate_wrap [data-testid="stForm"] { background:transparent; padding:.2rem 0 0 !important; }

/* ---------- footer ---------- */
.st-key-footer > * { width:auto !important; flex:0 0 auto; }
.st-key-footer { margin-top:10px; padding-top:18px; border-top:1px solid var(--line-2); flex-direction:row !important; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:12px !important; }
.fx-foot-note { font-size:12px; color:var(--muted); }
[data-testid="stCaptionContainer"] { opacity:1 !important; }
[data-testid="stCaptionContainer"] p { color:var(--muted) !important; }

/* ---------- tablets + phones ---------- */
@media (max-width:900px) {
  .fx-hero { grid-template-columns:1fr; gap:18px; }
  .fx-bento, .fx-bento.three { grid-template-columns:1fr 1fr; }
  .fx-bento.three > :last-child { grid-column:1 / -1; }
  .fx-bento .span-rows { grid-row:auto; }
  .fx-bento .span-cols, .fx-bento .full { grid-column:1 / -1; }
  [data-testid="stTabs"] { margin-top:2px !important; }
  [data-baseweb="tab-list"], [role="tablist"] { width:100%; justify-content:center; height:auto; overflow-x:auto; padding:4px 0 8px !important; }
  .fx-nav { height:auto; padding-bottom:2px; }
}
@media (max-width:640px) {
  html, body, .stApp { overflow-x:hidden; }
  .block-container, [data-testid="stMainBlockContainer"] { width:calc(100% - 16px) !important; margin:8px auto 16px !important; padding:14px 12px 20px !important; border-radius:26px; }
  .fx-logo { width:38px; height:38px; } .fx-brand { font-size:16px; gap:10px; }
  .fx-ic { width:36px; height:36px; } .fx-nav-icons { gap:8px; } .fx-ic.hide-m { display:none; }
  button[data-baseweb="tab"], [data-testid="stTab"] { padding:0 4px !important; flex:1 1 auto; justify-content:center; height:40px !important; }
  [data-baseweb="tab-list"], [role="tablist"] { gap:6px !important; justify-content:space-between; }
  .fx-demo { border-radius:16px; }
  .fx-hero-stats { gap:14px; }
  .fx-hs .v { font-size:26px; }
  .fx-hero-vis { height:168px; border-radius:22px; }
  .fx-float .fx-tile { font-size:30px; } .fx-float b { font-size:9.5px; padding:7px 7px 8px; } .fx-float { border-radius:14px; bottom:22px; }
  .fx-b { padding:16px 16px; border-radius:22px; }
  .st-key-closet_card, .st-key-controls, .st-key-chat_card, .st-key-gate_wrap, .st-key-style_card, [class*="st-key-outfit_"] { padding:16px !important; border-radius:24px; }
  .fx-tile { height:128px; font-size:46px; border-radius:18px; }
  .fx-tile.mini { height:68px; font-size:28px; }
  .fx-minirow { grid-template-columns:repeat(3, minmax(0,1fr)); gap:8px; }
  .fx-style-grid { grid-template-columns:1fr; }
  .fx-grid { grid-template-columns:1fr; }
  [data-testid="stChatMessage"] { padding:11px 14px; max-width:92%; }
  [class*="st-key-outfit_"] > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"], [class*="st-key-outfit_"] [data-testid="stHorizontalBlock"]:has(button) { flex-wrap:wrap !important; gap:8px !important; }
  [class*="st-key-outfit_"] [data-testid="stHorizontalBlock"]:has(button) > [data-testid="stColumn"] { min-width:0 !important; width:auto !important; }
  [class*="st-key-outfit_"] [data-testid="stHorizontalBlock"]:has(button) > [data-testid="stColumn"]:nth-child(-n+2) { flex:1 1 calc(50% - 8px) !important; }
  [class*="st-key-outfit_"] [data-testid="stHorizontalBlock"]:has(button) > [data-testid="stColumn"]:nth-child(3) { flex:1 1 calc(66% - 8px) !important; }
  [class*="st-key-outfit_"] [data-testid="stHorizontalBlock"]:has(button) > [data-testid="stColumn"]:nth-child(4) { flex:1 1 calc(24% - 8px) !important; }
  [class*="st-key-outfit_"] .stButton, [class*="st-key-outfit_"] .stButton button { width:100% !important; }
  [class*="st-key-card_"] .stButton button { min-height:1.9rem; padding:.3rem .1rem !important; white-space:nowrap; }
  [class*="st-key-card_"] .stButton button p { font-size:11.5px !important; }
  [class*="st-key-card_"] [data-testid="stHorizontalBlock"] { padding:0 2px 4px; gap:6px !important; }
  .fx-top { flex-wrap:wrap; row-gap:4px; } .fx-name { white-space:normal; flex:1 1 100%; min-height:2.5em; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; }
  .fx-body.mini .fx-name { min-height:0; }
  .fx-body { padding:10px 4px 10px; }
  .fx-fab .fx-rb.dark { display:none; } .fx-cat { top:8px; left:8px; padding:5px 8px; font-size:9.5px; } .fx-fab { top:6px; right:6px; }
  button[data-baseweb="tab"][aria-selected="true"], [data-testid="stTab"][aria-selected="true"] { box-shadow:none !important; }
  .fx-bars { gap:2px; height:34px; } .fx-bars i { width:2px; } .fx-b .sub { font-size:11px; }
  .st-key-filters [data-testid="stHorizontalBlock"] { flex-wrap:wrap !important; }
  .st-key-filters [data-testid="stColumn"] { min-width:calc(50% - 10px) !important; flex:1 1 calc(50% - 10px) !important; }
  .st-key-filters [data-testid="stColumn"]:last-child { min-width:100% !important; }
}
</style>
"""

# Markdown ends an HTML block at a blank line, so the CSS must contain none.
CSS = "\n".join(line for line in CSS.splitlines() if line.strip())
