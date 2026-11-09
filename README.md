# facebook-groups-digest

The posts that mattered in your Facebook groups this week, in one message. Give it a few public groups, get the numbers, the busiest posts and (with Claude) a three-line recap of what people talked about. It can land in Slack every Monday morning, so you don't have to scroll anything.

Good for community managers, brands that live in niche groups, researchers, or anyone who joined 14 groups "to keep an eye on things" and never opened them again.

Real output, Sourdough Geeks, last 3 days:

```
## Sourdough Geeks
15 new posts, 1110 reactions, 863 comments.

- Panettone season and lievito madre: several bakers shared their panettone projects, including
  lievito madre feeding and temperature schedules, and whether a KitchenAid can handle stiff doughs.
- Starter care questions: feeding ratios and timing, which flours work, reverse osmosis water.
- Troubleshooting oven spring and crumb: flat or dense loaves, bulk fermentation in warm climates,
  cold proofs, lamination, baking with steam.

Busiest posts:
- Lievito madre. That time of the year when all the panettone bakers start training... · 313 reactions, 68 comments
- When I do laminations, the breads seem to be taller. Who else laminate? · 277 reactions, 95 comments
- Is this normal? Should my KitchenAid be able to handle this amount? · 40 reactions, 198 comments
```

## How it works

1. Posts come from [Facebook Groups Scraper](https://apify.com/monkey.d.scraping/facebook-groups-scraper) on Apify. Public groups only, no login, newest first.
2. Posts are ranked by engagement (reactions + 2 × comments + 3 × shares).
3. With an Anthropic key, Claude writes the recap. Without one you still get numbers and busiest posts.
4. The digest is saved to `digest.md` and, if you set a webhook, posted to Slack.

## Run it once

```bash
git clone https://github.com/Monkeydscraping/facebook-groups-digest
cd facebook-groups-digest
pip install -r requirements.txt

export APIFY_TOKEN=...            # apify.com > Settings > API & Integrations
export ANTHROPIC_API_KEY=...      # optional, for the recap
export SLACK_WEBHOOK_URL=...      # optional

python digest.py https://www.facebook.com/groups/sourdoughgeeks/ --days 7
```

| Flag | Default | What it does |
| --- | --- | --- |
| `--days` | 7 | how far back to look |
| `--max-posts` | 50 | posts per group |
| `--keywords` | none | comma-separated, keep only posts that mention them |
| `--top` | 5 | busiest posts listed per group |
| `--no-recap` | off | skip Claude even if a key is set |
| `--out` | `digest.md` | where to save it |

## Run it every Monday, for free

The repo ships with a GitHub Actions workflow (`.github/workflows/weekly-digest.yml`).

1. Fork this repo, open the Actions tab of your fork and enable workflows (GitHub turns them off in forks).
2. In your fork: Settings > Secrets and variables > Actions.
3. Add the secret `APIFY_TOKEN`, and optionally `ANTHROPIC_API_KEY` and `SLACK_WEBHOOK_URL`.
4. Add the variable `GROUPS` with your group links, comma-separated.
5. Done. It runs Mondays at 07:00 UTC; you can also start it from the Actions tab. Without Slack, the digest is attached to each run.

## What it costs

- **Posts:** $0.69 per 1,000 on the Apify Free plan, less on paid plans. Five groups × 50 posts a week ≈ 17 cents. New Apify accounts get free monthly credits.
- **Recap:** a few cents per group with the default Claude model.
- **GitHub Actions:** free for public repos.

## FAQ

**Private groups?** No. Only groups anyone can read without logging in.

**Does it show who posted?** The digest doesn't include names. The Actor's dataset has more fields if you need them.

**Only posts about my brand?** Use `--keywords "yourbrand,your product"`.

---

Made by [Monkey.D.Scraping](https://github.com/Monkeydscraping). More examples: [social-comments-sentiment](https://github.com/Monkeydscraping/social-comments-sentiment). Something broke? Open an issue.
