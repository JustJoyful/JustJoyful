#!/usr/bin/env python3
"""Draw every SVG on the profile page from the GitHub GraphQL API. Needs GH_TOKEN."""
import os, sys
from datetime import date, timedelta
from xml.sax.saxutils import escape as xe
import requests

USER = "JustJoyful"
ROOT = os.path.join(os.path.dirname(__file__), "..")
W = 620
FONT = "JetBrains Mono,SFMono-Regular,Menlo,Consolas,monospace"
CSS = (".bg{fill:#0d1117}.f{fill:#e6edf3}.d{fill:#7d8590}.s{stroke:#7d8590}"
       "@media(prefers-color-scheme:light){.bg{fill:#f6f8fa}.f{fill:#1f2328}.d{fill:#656d76}.s{stroke:#656d76}}")
RAMP = " :+#@"  # quiet to loud, one character per day

def gql(query, **variables):
    r = requests.post("https://api.github.com/graphql", json={"query": query, "variables": variables},
                      headers={"Authorization": f"bearer {os.environ['GH_TOKEN']}"}, timeout=30)
    r.raise_for_status()
    body = r.json()
    if "errors" in body:
        sys.exit(f"GraphQL error: {body['errors']}")
    return body["data"]["user"]

def svg(name, h, body):
    s = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" role="img" '
         f'aria-label="{xe(name)}"><style>{CSS}</style><rect class="bg" width="{W}" height="{h}" rx="6"/>'
         f'<g class="f" font-family="{FONT}" xml:space="preserve">{body}</g></svg>')
    with open(os.path.join(ROOT, name + ".svg"), "w") as f:
        f.write(s)

def heading(title):
    n = len(title)
    svg(f"hd-{title}", 36,
        f'<text x="16" y="24" font-size="15" font-weight="700">## {xe(title)}</text>'
        f'<line class="s" x1="{16 + (n + 4) * 9}" x2="{W - 16}" y1="19" y2="19" stroke-dasharray="2 4">'
        f'<animate attributeName="x2" from="{16 + (n + 4) * 9}" to="{W - 16}" dur="1s" fill="freeze"/></line>')

def stat(x, y, value, label, i=0):
    # rise 8px and fade in, staggered by tile
    return (f'<g opacity="0"><animate attributeName="opacity" from="0" to="1" begin="{i * 0.15}s" dur="0.6s" fill="freeze"/>'
            f'<animateTransform attributeName="transform" type="translate" from="0 8" to="0 0" begin="{i * 0.15}s" dur="0.6s" fill="freeze"/>'
            f'<text x="{x}" y="{y}" font-size="26" font-weight="700">{xe(str(value))}</text>'
            f'<text class="d" x="{x}" y="{y + 22}" font-size="11">{xe(label)}</text></g>')

Q = """query($l:String!){user(login:$l){
  repositories(ownerAffiliations:OWNER,isFork:false,first:100){totalCount nodes{languages(first:10){edges{size node{name}}}}}
  contributionsCollection{totalCommitContributions totalPullRequestContributions totalIssueContributions
    contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}}}"""

def main():
    u = gql(Q, l=USER)
    cc = u["contributionsCollection"]
    days = [(date.fromisoformat(d["date"]), d["contributionCount"])
            for w in cc["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
    today = date.today()
    days = [d for d in days if d[0] <= today]

    for t in ("about", "stack", "projects", "stats"):
        heading(t)

    # stats.svg
    svg("stats", 90, "".join(stat(16 + i * 150, 38, v, l, i) for i, (v, l) in enumerate([
        (cc["contributionCalendar"]["totalContributions"], "contributions, 1y"),
        (cc["totalCommitContributions"], "commits"),
        (cc["totalPullRequestContributions"], "pull requests"),
        (u["repositories"]["totalCount"], "owned repos")])))

    # streak.svg: a zero-count today doesn't break the current streak yet
    longest = run = 0
    for _, c in days:
        run = run + 1 if c else 0
        longest = max(longest, run)
    cur, i = 0, len(days) - 1
    if i >= 0 and not days[i][1]:
        i -= 1
    while i >= 0 and days[i][1]:
        cur, i = cur + 1, i - 1
    svg("streak", 90, "".join(stat(16 + i * 200, 38, v, l, i) for i, (v, l) in enumerate([
        (f"{cur}d", "current streak"), (f"{longest}d", "longest streak"),
        (f"{sum(1 for _, c in days if c)}d", "active days, 1y")])))

    # langs.svg: top 6 by bytes
    totals = {}
    for r in u["repositories"]["nodes"]:
        for e in r["languages"]["edges"]:
            totals[e["node"]["name"]] = totals.get(e["node"]["name"], 0) + e["size"]
    top = sorted(totals.items(), key=lambda kv: -kv[1])[:6]
    whole = sum(totals.values()) or 1
    rows = ""
    for i, (name, size) in enumerate(top):
        y, pct = 28 + i * 24, size / whole * 100
        rows += (f'<text x="16" y="{y}" font-size="12">{xe(name)}</text>'
                 f'<rect class="f" x="150" y="{y - 10}" width="{size / top[0][1] * 380:.0f}" height="10" opacity="0.85">'
                 f'<animate attributeName="width" from="0" to="{size / top[0][1] * 380:.0f}" begin="{i * 0.1}s" dur="0.8s"/></rect>'
                 f'<text class="d" x="{W - 16}" y="{y}" font-size="12" text-anchor="end">{pct:.1f}%</text>')
    svg("langs", 28 + len(top) * 24, rows)

    # year.svg: one character per day, weeks as columns
    peak = max((c for _, c in days), default=1) or 1
    cells = ""
    first = days[0][0].weekday() + 1 if days else 0   # GitHub weeks start Sunday
    first %= 7
    for n, (_, c) in enumerate(days):
        col, row = (n + first) // 7, (n + first) % 7
        ch = RAMP[0] if not c else RAMP[min(4, 1 + int(c / peak * 3.99))]
        cls = ' class="d"' if not c else ""
        cells += (f'<text{cls} x="{16 + col * 11}" y="{26 + row * 14}" font-size="12" opacity="0">{xe(ch) if ch != " " else "·"}'
                  f'<animate attributeName="opacity" from="0" to="1" begin="{col * 0.03:.2f}s" dur="0.3s" fill="freeze"/></text>')
    svg("year", 126, cells)

if __name__ == "__main__":
    main()
