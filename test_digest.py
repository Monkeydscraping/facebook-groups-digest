"""Offline tests: no Apify, Anthropic or Slack calls. Run with `python -m pytest -q`."""

import sys
import types

import digest


def post(group, text, reactions=0, comments=0, shares=0, n=0):
    return {"groupName": group, "text": text, "postUrl": f"https://www.facebook.com/groups/g/posts/{n}/",
            "reactionCount": reactions, "commentCount": comments, "shareCount": shares}


def test_engagement_weights_comments_and_shares():
    assert digest.engagement(post("g", "x", reactions=10, comments=5, shares=1)) == 23
    assert digest.engagement({"reactionCount": None}) == 0


def test_digest_orders_groups_and_posts():
    posts = [
        post("Small group", "only one", reactions=1, n=1),
        post("Big group", "quiet post", reactions=2, n=2),
        post("Big group", "loud post", reactions=50, comments=10, n=3),
    ]
    text = digest.build_digest(posts, top=1, days=7, model=None)
    assert text.index("## Big group") < text.index("## Small group")
    assert "2 new posts, 52 reactions, 10 comments." in text
    assert "loud post" in text and "quiet post" not in text


def test_empty_week():
    assert "No new public posts" in digest.build_digest([], top=5, days=7, model=None)


def test_recap_is_added_and_refusal_is_skipped():
    responses = []

    class Messages:
        def create(self, **kwargs):
            return responses.pop(0)

    module = types.ModuleType("anthropic")
    module.Anthropic = lambda: types.SimpleNamespace(beta=types.SimpleNamespace(messages=Messages()))
    sys.modules["anthropic"] = module

    ok = types.SimpleNamespace(stop_reason="end_turn",
                               content=[types.SimpleNamespace(type="text", text="- people asked about starters")])
    refused = types.SimpleNamespace(stop_reason="refusal", content=[])
    responses += [ok, refused]
    posts = [post("A", "hello", n=1), post("B", "hi", n=2)]
    text = digest.build_digest(posts, top=1, days=7, model="claude-opus-5-5")
    assert text.count("people asked about starters") == 1
