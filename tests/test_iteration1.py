"""Iteration 1: full looks with shop-this cards, Today occasion picker, photo tagging, saved closets."""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

import storage  # noqa: E402
import tagging  # noqa: E402
import wardrobe_core as core  # noqa: E402
from test_core import WORKOUT_BAD, _FakeClient, _FakeError, gym_closet  # noqa: E402

ATHLETIC_SHOES = ("White Sneakers", "Running Shoes")


# ---------------------------------------------------------------- 1. Stylist always builds a full look
def test_workout_full_look_marks_missing_pieces():
    ans = core.rules_answer("I want to work out today", core.sample_closet(), core.StyleProfile(), "offline rules")
    names = [g.name for g in ans["items"]]
    assert names == ["Navy Tee", "White Sneakers"] and not set(names) & set(WORKOUT_BAD)
    (m,) = ans["missing_items"]
    assert m["slot"] == "bottom" and m["name"] == "Black leggings" and m["occasion"] == "workout"
    assert "Gym look" in ans["reply"] and "not in your closet" in ans["reply"]
    assert ans["reasoning"]  # the short "why" line


def test_empty_closet_still_gets_a_full_look():
    ans = core.rules_answer("what should I wear to work", core.Wardrobe(), core.StyleProfile(), "x")
    assert ans["items"] == [] and [m["slot"] for m in ans["missing_items"]] == ["top", "bottom", "shoes"]


def test_complete_closet_has_no_missing_items():
    ans = core.rules_answer("I want to work out", gym_closet(), core.StyleProfile(), "x")
    assert ans["missing_items"] == [] and ans["items"]


def test_llm_partial_look_is_completed_with_its_shop_names():
    ans = core.stylist_chat("I want to work out", [], core.sample_closet(), core.StyleProfile(), model="m",
                            client=_FakeClient(content='{"reply": "Tee and sneakers, plus leggings.", "outfit": [10, 13], '
                                                       '"missing": [{"slot": "bottom", "name": "Grey joggers"}], "reasoning": "r"}'))
    assert ans["source"] == "llm (m)" and [g.id for g in ans["items"]] == [10, 13]
    assert [m["name"] for m in ans["missing_items"]] == ["Grey joggers"]


def test_llm_unsuitable_partial_falls_back_to_rules():
    # Grok picks Dark Jeans for a workout: swapped for the offline answer (PR #2 logic), still a full look
    ans = core.stylist_chat("I want to work out", [], core.sample_closet(), core.StyleProfile(), model="m",
                            client=_FakeClient(content='{"reply": "ok", "outfit": [10, 12, 13], "reasoning": "r"}'))
    assert "Dark Jeans" not in [g.name for g in ans["items"]] and "didn't suit" in ans["source"]
    assert [m["slot"] for m in ans["missing_items"]] == ["bottom"]


def test_api_error_falls_back_to_full_offline_look():
    ans = core.stylist_chat("I want to work out", [], core.sample_closet(), core.StyleProfile(), model="m",
                            client=_FakeClient(_FakeError()))
    assert ans["llm_error"] and ans["missing_items"] and ans["items"]


def test_shop_list_dedupes():
    lst = []
    miss = [core.missing_item("bottom", "workout")]
    assert core.add_to_shop_list(lst, miss) == 1
    assert core.add_to_shop_list(lst, miss) == 0 and len(lst) == 1 and lst[0]["name"] == "Black leggings"


# ---------------------------------------------------------------- 3. Today occasion picker
def test_interview_never_running_shoes_or_sneakers():
    w = gym_closet()  # has Running Shoes + White Sneakers
    for norepeat in (True, False):
        req = core.OutfitRequest(plans="work", occasion="interview", no_repeat_yesterday=norepeat)
        looks = core.smart_suggest(w, req, core.StyleProfile(), n=5)
        assert looks
        for o in looks:
            names = [g.name for g in o["items"]]
            assert not set(names) & set(ATHLETIC_SHOES + ("Gym Tank", "Black Leggings", "Navy Tee")), names
    assert not core.suits_occasion(w.items[15], "interview")  # Running Shoes
    ans = core.rules_answer("job interview", w, core.StyleProfile(), "x")
    assert not set(g.name for g in ans["items"]) & set(ATHLETIC_SHOES)


def test_today_chips_map_to_occasions():
    assert core.TODAY_OCCASIONS == {"Work": "office", "Interview": "interview", "Date": "date", "Workout": "workout",
                                    "Weekend": "casual"}
    assert "Sneakers and running shoes" in core.OCCASION_NOTES["interview"]
    req = core.OutfitRequest(occasion="workout", plans="off duty")
    assert core.smart_suggest(core.sample_closet(), req, core.StyleProfile()) == []
    items, missing = core.complete_look(core.sample_closet(), core.StyleProfile(), req)
    assert [m["slot"] for m in missing] == ["bottom"]


def test_color_words_match_whole_words():
    assert core.parse_chat("tailored look for the office").color_theme is None  # "tailored" contains "red"
    assert core.parse_chat("something red for a date").color_theme == "red"
    assert core.parse_chat("gray outfit").color_theme == "grey"


# ---------------------------------------------------------------- 2. photo tagging
def _photo(rgb, box=(80, 90, 320, 330), bg=(236, 232, 226)):
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (400, 400), bg)
    ImageDraw.Draw(im).rectangle(box, fill=rgb)
    b = io.BytesIO()
    im.save(b, "JPEG")
    return b.getvalue()


@pytest.mark.parametrize("rgb,shade,group", [((28, 40, 75), "Navy", "blue"), ((20, 20, 20), "Black", "black"),
                                             ((110, 110, 55), "Olive", "green"), ((200, 30, 40), "Red", "red"),
                                             ((193, 142, 86), "Camel", "brown")])
def test_dominant_color(rgb, shade, group):
    assert tagging.dominant_color(_photo(rgb)) == (shade, group)


def test_offline_type_guess():
    assert tagging.offline_tags(_photo((20, 20, 20)), "IMG_white_sneakers.jpg")["type"] == "shoes"
    assert tagging.offline_tags(_photo((20, 20, 20), box=(160, 30, 240, 390)), "IMG_1234.jpg")["type"] == "bottom"
    assert tagging.offline_tags(_photo((20, 20, 20), box=(40, 170, 360, 260)), "")["type"] == "shoes"


def test_vision_request_and_reply():
    kw = tagging.build_vision_request("grok-4.3", b"\xff\xd8abc")
    url = kw["messages"][1]["content"][1]["image_url"]["url"]
    assert url.startswith("data:image/jpeg;base64,")
    tags = tagging.parse_vision_reply('{"type": "Top", "subtype": "tee", "color": "Navy", "name": "Navy Tee", '
                                      '"warmth": "light", "dressiness": "casual"}', _photo((28, 40, 75)))
    assert tags["type"] == "top" and tags["color"] == "blue" and tags["color_name"] == "Navy" and tags["source"] == "vision"
    assert tagging.parse_vision_reply('{"type": "hat"}', _photo((0, 0, 0))) is None
    assert tagging.parse_vision_reply("not json", _photo((0, 0, 0))) is None


def test_vision_failure_falls_back_to_offline():
    tags = tagging.suggest_tags(_photo((28, 40, 75)), "", client=_FakeClient(_FakeError()), model="grok-4.3")
    assert tags["source"] == "offline" and tags["color"] == "blue"
    assert tags["vision_error"]["status"] == 400 and "abcdef123456" not in tags["vision_error"]["message"]
    ok = tagging.suggest_tags(_photo((28, 40, 75)), "", model="m",
                              client=_FakeClient(content='{"type": "shoes", "color": "brown", "subtype": "Loafers"}'))
    assert ok["source"] == "vision" and ok["type"] == "shoes" and ok["vision_error"] is None


# ---------------------------------------------------------------- 4. persistence
def test_closet_roundtrip_and_corrupt_rows():
    w = core.sample_closet()
    w.ban_item(3)
    rows = core.wardrobe_to_list(w)
    back = core.wardrobe_from_list(rows + [{"id": 99, "name": "bad", "type": "hat"}, {"nope": 1}])
    assert core.wardrobe_to_list(back) == rows
    p = core.StyleProfile()
    p.update([w.items[1]], "wear")
    q = core.profile_from_dict(core.profile_to_dict(p))
    assert q.weights == p.weights and q.events == 1


def test_storage(tmp_path, monkeypatch):
    monkeypatch.setenv("FASHIONISTA_DATA_DIR", str(tmp_path))
    t = storage.new_token()
    assert storage.valid_token(t) and not storage.valid_token("../etc/passwd") and not storage.valid_token(None)
    assert storage.load(t) is None and not storage.exists(t)
    assert storage.save(t, {"v": 1, "wardrobe": []})
    assert storage.exists(t) and storage.load(t) == {"v": 1, "wardrobe": []}
    (tmp_path / f"{t}.json").write_text("{corrupt")
    assert storage.load(t) is None
    with pytest.raises(ValueError):
        storage._path("../x")
    os.utime(tmp_path / f"{t}.json", (0, 0))
    assert storage.prune() == 1 and not storage.exists(t)
