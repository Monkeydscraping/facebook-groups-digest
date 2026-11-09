"""Weekly digest of what happened in public Facebook groups: busiest posts, numbers, and (with Claude) a short recap.

Usage:
    python digest.py https://www.facebook.com/groups/sourdoughgeeks/ --days 7

Needs APIFY_TOKEN. ANTHROPIC_API_KEY adds a three-line recap per group. SLACK_WEBHOOK_URL posts the digest to Slack.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone

from apify_client import ApifyClient

GROUPS_ACTOR = "monkey.d.scraping/facebook-groups-scraper"


def fetch_posts(groups: list[str], days: int, max_posts: int, keywords: list[str]) -> list[dict]:
    apify = ApifyClient(os.environ["APIFY_TOKEN"])
    run_input = {
        "startUrls": [{"url": g} for g in groups],
        "maxPostsPerGroup": max_posts,
        "onlyPostsNewerThan": f"{days} days",
        "sortBy": "newest",
    }
    if keywords:
        run_input["keywords"] = keywords
    print(f"reading posts from {len(groups)} group(s), last {days} days...", file=sys.stderr)
    run = apify.actor(GROUPS_ACTOR).call(run_input=run_input, logger=None)
    if run is None:
        sys.exit("The Apify run did not start.")
    return list(apify.dataset(run.default_dataset_id).iterate_items())


def engagement(post: dict) -> int:
    return int(post.get("reactionCount") or 0) + 2 * int(post.get("commentCount") or 0) + 3 * int(post.get("shareCount") or 0)


def recap_with_claude(group_name: str, posts: list[dict], model: str) -> str | None:
    """Three short bullets on what the group talked about. Returns None if Claude declines."""
    import anthropic

    texts = "\n".join(f"- {(p.get('text') or '').strip()[:400]}" for p in posts[:80] if p.get("text"))
    if not texts:
        return None
    response = anthropic.Anthropic().beta.messages.create(
        model=model,
        max_tokens=4000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "low"},
        messages=[{
            "role": "user",
            "content": (
                f"These are this week's posts from the public Facebook group \"{group_name}\". "
                "Write exactly three short bullet points in English on what people talked about most: "
                "recurring questions, complaints, products or events. No intro, no names of people.\n\n" + texts
            ),
        }],
    )
    if response.stop_reason == "refusal":
        return None
    return next((b.text.strip() for b in response.content if b.type == "text"), None)


def build_digest(posts: list[dict], top: int, days: int, model: str | None) -> str:
    by_group: dict[str, list[dict]] = defaultdict(list)
    for p in posts:
        by_group[p.get("groupName") or p.get("groupUrl") or "Unknown group"].append(p)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [f"# Facebook groups digest, last {days} days (to {today})", ""]
    if not by_group:
        lines.append("No new public posts in these groups.")
    for name, group_posts in sorted(by_group.items(), key=lambda kv: -len(kv[1])):
        reactions = sum(int(p.get("reactionCount") or 0) for p in group_posts)
        comments = sum(int(p.get("commentCount") or 0) for p in group_posts)
        lines.append(f"## {name}")
        lines.append(f"{len(group_posts)} new posts, {reactions} reactions, {comments} comments.")
        if model:
            recap = recap_with_claude(name, group_posts, model)
            if recap:
                lines += ["", recap]
        lines += ["", "Busiest posts:"]
        for p in sorted(group_posts, key=engagement, reverse=True)[:top]:
            text = " ".join((p.get("text") or "(no text)").split())[:160]
            lines.append(
                f"- [{text}]({p.get('postUrl')}) · {p.get('reactionCount') or 0} reactions, "
                f"{p.get('commentCount') or 0} comments"
            )
        lines.append("")
    return "\n".join(lines)


def post_to_slack(webhook: str, text: str) -> None:
    body = json.dumps({"text": text}).encode()
    request = urllib.request.Request(webhook, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status != 200:
            print(f"Slack answered {response.status}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("groups", nargs="*", help="public Facebook group links (or set GROUPS, comma-separated)")
    parser.add_argument("--days", type=int, default=7, help="look back this many days (default 7)")
    parser.add_argument("--max-posts", type=int, default=50, help="posts per group (default 50)")
    parser.add_argument("--keywords", default="", help="comma-separated: keep only posts mentioning these")
    parser.add_argument("--top", type=int, default=5, help="busiest posts to list per group (default 5)")
    parser.add_argument("--model", default="claude-opus-5-5", help="Claude model for the recap")
    parser.add_argument("--no-recap", action="store_true", help="skip the Claude recap even if a key is set")
    parser.add_argument("--out", default="digest.md", help="where to save the digest")
    args = parser.parse_args()

    groups = args.groups or [g.strip() for g in os.environ.get("GROUPS", "").split(",") if g.strip()]
    if not groups:
        sys.exit("Give at least one group link, or set GROUPS.")
    if not os.environ.get("APIFY_TOKEN"):
        sys.exit("Set APIFY_TOKEN first (Apify console > Settings > API & Integrations).")

    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    posts = fetch_posts(groups, args.days, args.max_posts, keywords)
    use_claude = bool(os.environ.get("ANTHROPIC_API_KEY")) and not args.no_recap
    digest = build_digest(posts, args.top, args.days, args.model if use_claude else None)

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(digest)
    print(digest)
    if os.environ.get("SLACK_WEBHOOK_URL"):
        post_to_slack(os.environ["SLACK_WEBHOOK_URL"], digest)
        print("sent to Slack", file=sys.stderr)


if __name__ == "__main__":
    main()
