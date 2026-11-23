"""Tests for the outfit rules and the LLM request/fallback.  Run: python tests/test_core.py  (or pytest)"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import wardrobe_core as core  # noqa: E402


def rainy_office(wardrobe=None):
    w = wardrobe or core.sample_closet()
    return w, core.rules_answer("rainy day at the office", w, core.StyleProfile(), "offline rules")


def test_rain_needs_outer_layer_and_no_sneakers():
    w, ans = rainy_office()
    names = [g.name for g in ans["items"]]
    assert any(g.layer == "outer" for g in ans["items"]), names
    assert "White Sneakers" not in names, names


def test_rain_claim_only_when_true():
    # the sample closet only has a wool coat: no "Covered for rain" claim
    _, ans = rainy_office()
    assert "Covered for rain" not in ans["reasoning"], ans["reasoning"]
    assert "umbrella" in ans["reasoning"]
    # add a trench coat: now it's used and the claim is true
    w = core.sample_closet()
    w.add_item(core.Garment(w.next_id(), "Beige Trench Coat", "outer", "outer", "brown", "mid", "office"))
    _, ans = rainy_office(w)
    assert "Beige Trench Coat" in [g.name for g in ans["items"]]
    assert "Covered for rain" in ans["reasoning"]


def test_sneakers_allowed_when_only_shoes():
    w = core.sample_closet()
    for gid in [g.id for g in w.items.values() if g.type == "shoes" and g.name != "White Sneakers"]:
        w.remove(gid)
    _, ans = rainy_office(w)
    assert "White Sneakers" in [g.name for g in ans["items"]]
    assert "aren't great in the wet" in ans["reasoning"]


def test_no_invented_temperature():
    _, ans = rainy_office()
    assert "°" not in ans["reasoning"], ans["reasoning"]
    req = core.parse_chat("rainy day at the office")
    assert req.temp_given is False
    assert core.closet_context(core.sample_closet(), core.StyleProfile(), req)["today"]["temp_f"] is None
    req = core.parse_chat("casual brunch, 72 degrees")
    assert req.temp_given and req.temp_f == 72
    ans = core.rules_answer("casual brunch, 72 degrees", core.sample_closet(), core.StyleProfile(), "x")
    assert "72°" in ans["reasoning"]


def test_today_tab_still_shows_slider_temperature():
    res = core.smart_suggest(core.sample_closet(), core.OutfitRequest(temp_f=40), core.StyleProfile(), n=1)
    assert "40°" in res[0]["reason"]


def test_build_chat_request():
    msgs = [{"role": "user", "content": "hi"}]
    kw = core.build_chat_request("grok-4.3", msgs, 1200, "low")
    assert kw["model"] == "grok-4.3" and kw["max_tokens"] == 1200
    assert kw["extra_body"] == {"reasoning_effort": "low"}
    for bad in ("presence_penalty", "frequency_penalty", "stop", "reasoning_effort"):
        assert bad not in kw
    assert "extra_body" not in core.build_chat_request("m", msgs, 600, None)


def test_build_messages_skips_empty_history():
    hist = [{"role": "user", "content": "a"}, {"role": "assistant", "content": ""}]
    msgs = core.build_messages("b", hist, core.sample_closet(), core.StyleProfile(), core.parse_chat("b"))
    assert all(m["content"] for m in msgs)


class _FakeError(Exception):
    status_code = 400
    body = {"error": {"message": "Model not found: grok-3-mini (key xai-abcdef123456)"}}


class _FakeClient:
    def __init__(self, exc=None, content=None):
        self.exc, self.content = exc, content
        self.chat = self
        self.completions = self

    def create(self, **kw):
        if self.exc:
            raise self.exc
        msg = type("M", (), {"content": self.content})()
        return type("R", (), {"choices": [type("C", (), {"message": msg, "finish_reason": "stop"})()]})()


def test_api_error_is_reported_and_masked():
    ans = core.stylist_chat("rainy day at the office", [], core.sample_closet(), core.StyleProfile(),
                            client=_FakeClient(_FakeError()), model="grok-3-mini")
    err = ans["llm_error"]
    assert err["status"] == 400 and "Model not found" in err["message"]
    assert "abcdef123456" not in err["message"]
    assert ans["items"]  # offline rules still answered


def test_unreadable_reply_is_not_an_api_error():
    ans = core.stylist_chat("hi", [], core.sample_closet(), core.StyleProfile(), client=_FakeClient(content=""),
                            model="m")
    assert ans["llm_error"] is None and "unreadable" in ans["source"]


def test_llm_happy_path():
    ans = core.stylist_chat("hi", [], core.sample_closet(), core.StyleProfile(), model="m",
                            client=_FakeClient(content='{"reply": "ok", "outfit": [10, 12, 13], "reasoning": "r"}'))
    assert ans["llm_error"] is None and [g.id for g in ans["items"]] == [10, 12, 13]


def test_budget_refund():
    import guards
    b = guards.DailyBudget()
    assert b.try_consume(1)
    assert not b.try_consume(1)
    b.refund()
    assert b.try_consume(1)


# ---------------------------------------------------------------- occasions (bug: "work out" got jeans/tailored pants)
WORKOUT_BAD = ("Dark Jeans", "Tailored Pants", "Wide Trousers", "Loafers", "Ankle Boots", "Linen Blazer",
               "Classic Silk Blouse", "Silk Camisole", "Ribbed Knit Dress", "Wool Coat")


def gym_closet():
    w = core.sample_closet()
    for name, t in (("Black Leggings", "bottom"), ("Running Shoes", "shoes"), ("Gym Tank", "top")):
        w.add_item(core.Garment(w.next_id(), name, t, core.default_layer(t), "black", "light", "casual"))
    return w


def test_work_out_is_not_work():
    for msg in ("I want to work out", "going to the gym", "workout later", "leg day at the gym, then a run",
                "yoga class", "training session tonight"):
        req = core.parse_chat(msg)
        assert req.occasion == "workout" and req.plans == "off duty", (msg, req)
    assert core.parse_chat("training session tonight").condition == "dry"  # "training" is not rain
    assert core.parse_chat("rainy day at the office").occasion == "office"


def test_workout_never_jeans_or_tailored_pants():
    w = gym_closet()
    for msg in ("I want to work out", "gym", "going for a run"):
        ans = core.rules_answer(msg, w, core.StyleProfile(), "offline rules")
        names = [g.name for g in ans["items"]]
        assert names, ans
        assert not set(names) & set(WORKOUT_BAD), names
        assert "Black Leggings" in names and "Running Shoes" in names, names


def test_workout_without_activewear_says_whats_missing():
    ans = core.rules_answer("I want to work out", core.sample_closet(), core.StyleProfile(), "offline rules")
    assert ans["items"] == [], [g.name for g in ans["items"]]
    assert "missing" in ans["reply"] and "leggings" in ans["reply"], ans["reply"]
    assert "Dark Jeans" not in ans["reply"] and "Tailored Pants" not in ans["reply"]
    # with nothing athletic at all, every slot is listed
    w = core.sample_closet()
    w.remove(10); w.remove(13)  # Navy Tee, White Sneakers
    assert len(core.occasion_gaps(w, "workout")) == 3


def test_office_still_works():
    ans = core.rules_answer("business meeting, blue theme", core.sample_closet(), core.StyleProfile(), "x")
    names = [g.name for g in ans["items"]]
    assert names and not ans.get("missing")
    assert any(g.dressiness == "office" for g in ans["items"]), names
    assert core.parse_chat("business meeting").plans == "work"


def test_interview_and_wedding_skip_casual_pieces():
    for msg in ("job interview tomorrow", "wedding on saturday"):
        names = [g.name for g in core.rules_answer(msg, core.sample_closet(), core.StyleProfile(), "x")["items"]]
        assert names and not {"Dark Jeans", "White Sneakers", "Navy Tee"} & set(names), (msg, names)


def test_llm_gets_occasion_and_rules():
    req = core.parse_chat("I want to work out")
    ctx = core.closet_context(core.sample_closet(), core.StyleProfile(), req)
    assert ctx["today"]["occasion"] == "workout" and ctx["today"]["plans"] == "off duty"
    assert "jeans" in ctx["today"]["occasion_rules"].lower()
    assert ctx["today"]["missing_for_occasion"]
    assert '"outfit": []' in core.SYSTEM_PROMPT


def test_llm_wrong_occasion_picks_are_rejected():
    # Grok picks Navy Tee + Dark Jeans + White Sneakers for a workout: replaced by the occasion-aware rules
    w = gym_closet()
    ans = core.stylist_chat("I want to work out", [], w, core.StyleProfile(), model="m",
                            client=_FakeClient(content='{"reply": "ok", "outfit": [10, 12, 13], "reasoning": "r"}'))
    names = [g.name for g in ans["items"]]
    assert "Dark Jeans" not in names and "Black Leggings" in names, names
    assert "didn't suit" in ans["source"]


def test_llm_honest_missing_reply_is_kept():
    ans = core.stylist_chat("I want to work out", [], core.sample_closet(), core.StyleProfile(), model="m",
                            client=_FakeClient(content='{"reply": "You need leggings or gym shorts.", "outfit": [], '
                                                       '"reasoning": "no workout bottoms"}'))
    assert ans["items"] == [] and ans["source"] == "llm (m)" and "leggings" in ans["reply"]


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print("ok ", t.__name__)
    print(f"{len(tests)} tests passed")
