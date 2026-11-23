"""Streamlit AppTest smoke tests (offline: no secrets, so no passcode and no Grok)."""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from streamlit.testing.v1 import AppTest  # noqa: E402

APP = os.path.join(ROOT, "app.py")


def html(at):
    return "".join(m.value for m in at.markdown)


def new_app(tmp_path, monkeypatch, token=None):
    monkeypatch.setenv("FASHIONISTA_DATA_DIR", str(tmp_path))
    for k in ("OPENAI_API_KEY", "APP_PASSCODE"):
        monkeypatch.delenv(k, raising=False)
    at = AppTest.from_file(APP, default_timeout=30)
    if token:
        at.query_params["c"] = token
    return at.run()


def token_of(at):
    t = at.query_params["c"]
    return t[0] if isinstance(t, list) else t


def test_today_interview_and_workout(tmp_path, monkeypatch):
    at = new_app(tmp_path, monkeypatch)
    assert not at.exception
    assert "✓ Closet saved · 13 pieces" in html(at)
    at.session_state["today_occ"] = "Interview"
    at.button(key="show_btn").click().run()
    page = html(at)
    assert "Sneakers and running shoes are hidden for interviews." in page
    looks = re.findall(r'fx-look-pieces">([^<]*)', page)
    assert looks and not any("Sneakers" in x or "Navy Tee" in x for x in looks), looks
    at.session_state["today_occ"] = "Workout"
    at.button(key="show_btn").click().run()
    assert "Not in closet" in html(at) and "Black leggings" in html(at)
    at.button(key="today_addshop").click().run()
    assert [x["name"] for x in at.session_state["shop_list"]] == ["Black leggings"]
    assert "Your Shop list" in html(at)


def test_stylist_workout_full_look(tmp_path, monkeypatch):
    at = new_app(tmp_path, monkeypatch)
    at.chat_input(key="chat_input").set_value("I want to work out today").run()
    assert not at.exception
    assert "Gym look" in at.chat_message[-1].markdown[0].value
    assert "Occasion detected" in html(at) and "Shop this" in html(at)
    at.button(key="chat_addshop_1").click().run()
    assert at.session_state["shop_list"][0]["name"] == "Black leggings"


def test_closet_survives_refresh_and_own_closet(tmp_path, monkeypatch):
    at = new_app(tmp_path, monkeypatch)
    tok = token_of(at)
    at.button(key="rm_1").click().run()  # remove a piece
    assert len(at.session_state["wardrobe"].items) == 12
    again = new_app(tmp_path, monkeypatch, tok)  # "refresh": new session, same ?c= link
    assert len(again.session_state["wardrobe"].items) == 12
    again.button(key="own_today").click().run()
    assert any("starts an empty closet" in w.value for w in again.warning)
    assert len(again.session_state["wardrobe"].items) == 12  # nothing cleared before confirming
    again.button(key="own_yes_today").click().run()
    assert len(again.session_state["wardrobe"].items) == 0 and not again.exception
    assert "✓ Closet saved · 0 pieces" in html(again)
    third = new_app(tmp_path, monkeypatch, tok)
    assert len(third.session_state["wardrobe"].items) == 0 and third.session_state["closet_mode"] == "personal"
    third.button(key="demo_today").click().run()
    assert len(third.session_state["wardrobe"].items) == 13
