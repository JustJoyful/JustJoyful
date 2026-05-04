#!/usr/bin/env python3
"""today.py — Generates a neofetch-style GitHub Profile SVG + README.md"""

import os, sys, xml.sax.saxutils as sax
import requests
from datetime import datetime, timezone, date
from dateutil.relativedelta import relativedelta

# ── Config ──────────────────────────────────────────────────────────────
GH_USER        = "JustJoyful"
DOB            = date(2007, 5, 2)
GH_TOKEN       = os.environ.get("GH_TOKEN", "")
PERSONAL_EMAIL = "joydeepdas217@gmail.com"
STUDENT_EMAIL  = "joydeepdas.cse2025@nsec.ac.in"
LINKEDIN_SHORT = "linkedin.com/in/joydeep-das-a2016a388"
GITHUB_SHORT   = f"github.com/{GH_USER}"

ROOT     = os.path.dirname(__file__)
ART_FILE = os.path.join(ROOT, "ascii-art.txt")
SVG_FILE = os.path.join(ROOT, "profile.svg")
MD_FILE  = os.path.join(ROOT, "README.md")

HEADERS = {"Authorization": f"token {GH_TOKEN}"} if GH_TOKEN else {}
GQL_URL = "https://api.github.com/graphql"

# ── Helpers ──────────────────────────────────────────────────────────────
xe = sax.escape   # XML-escape a string

def gql(query, variables=None):
    r = requests.post(GQL_URL, json={"query": query, "variables": variables or {}},
                      headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.json()

def calc_uptime():
    d = relativedelta(date.today(), DOB)
    return f"{d.years}y {d.months}m {d.days}d  (since {DOB.strftime('%d %b %Y')})"

# ── GitHub data ───────────────────────────────────────────────────────────
def fetch_github_data():
    q = """query($l:String!){user(login:$l){
      repositories(ownerAffiliations:OWNER,isFork:false,first:100,orderBy:{field:PUSHED_AT,direction:DESC}){
        totalCount
        nodes{
          name description url primaryLanguage{name}
          defaultBranchRef{target{...on Commit{history{totalCount}}}}
          languages(first:10){edges{size}}
        }
      }
    }}"""
    try:
        data = gql(q, {"l": GH_USER})["data"]["user"]
        repos = data["repositories"]["nodes"]
        
        commits = 0
        bytes_of_code = 0
        
        for r in repos:
            ref = r.get("defaultBranchRef")
            if ref and ref.get("target"):
                commits += ref["target"].get("history", {}).get("totalCount", 0)
            for edge in r.get("languages", {}).get("edges", []):
                bytes_of_code += edge.get("size", 0)
                
        # Estimate LOC (approx 30 bytes per line of code)
        loc = bytes_of_code // 30
        
        active = []
        for r in repos[:5]:
            lang = r.get("primaryLanguage")
            active.append({
                "name": r.get("name", ""),
                "desc": (r.get("description") or "")[:40],
                "lang": lang.get("name", "") if lang else "",
                "url": r.get("url", "")
            })
            
        return {
            "repos": data["repositories"]["totalCount"],
            "commits": commits,
            "loc": loc,
            "active": active
        }
    except Exception as e:
        print(f"[WARN] github data: {e}", file=sys.stderr)
        return {"repos":"?","commits":"?","loc":"?","active":[]}

def fetch_weeks():
    q = """query($l:String!){user(login:$l){contributionsCollection{
      contributionCalendar{weeks{contributionDays{date contributionCount weekday}}}}}}"""
    try:
        return (gql(q, {"l": GH_USER})["data"]["user"]
                ["contributionsCollection"]["contributionCalendar"]["weeks"])
    except Exception as e:
        print(f"[WARN] contrib: {e}", file=sys.stderr)
        return []

# ── ASCII art ─────────────────────────────────────────────────────────────
def load_art():
    with open(ART_FILE, encoding="utf-8") as f:
        lines = [l.rstrip("\n") for l in f]
    while lines and not lines[-1].strip():
        lines.pop()
    return lines

# ── SVG builder ──────────────────────────────────────────────────────────
# Colours (Catppuccin Mocha Theme)
BG      = "#1e1e2e"
BORDER  = "#313244"
C_ART   = "#cdd6f4"
C_TITLE = "#cba6f7"
C_KEY   = "#89b4fa"
C_SEP   = "#585b70"
C_VAL   = "#cdd6f4"
C_DIM   = "#6c7086"
C_SEC   = "#6c7086"
C_ACNT  = "#f38ba8"
C_LINK  = "#89dceb"
C_PROJ  = "#f9e2af"

PALETTE = ["#f38ba8", "#fab387", "#f9e2af", "#a6e3a1", "#89dceb", "#cba6f7", "#f5c2e7", "#b4befe"]
CGREEN  = ["#181825", "#453a5c", "#6e558a", "#9b76bd", "#cba6f7"]

def clvl(n):
    if n==0: return 0
    if n<=2: return 1
    if n<=5: return 2
    if n<=10:return 3
    return 4

def build_svg(art, gh_data, weeks, uptime):
    out = []
    W   = 900   # total SVG width
    PAD = 18

    # Art metrics
    AF  = 9        # art font-size px
    ALH = 11       # art line-height px
    N   = len(art)
    art_h = N * ALH

    # Info panel
    IX    = 418    # info x-start
    IF    = 11     # info font-size
    ILH   = 18     # info line-height

    # Panel height (driven by art + padding)
    panel_h = art_h + PAD * 2 + 8

    # Contribution graph geometry
    CELL  = 10; GAP = 2; STR = CELL + GAP
    DLBW  = 26   # day-label width
    cg_hdr_y   = panel_h + 14
    month_y    = cg_hdr_y + 18
    grid_y     = month_y + 14
    grid_x     = PAD + DLBW
    grid_w     = 52 * STR
    grid_h     = 7 * STR
    legend_y   = grid_y + grid_h + 12
    footer_y   = legend_y + 26
    SVG_H      = footer_y + 10

    # ── open svg ──
    out.append(f'<svg width="{W}" height="{SVG_H}" viewBox="0 0 {W} {SVG_H}" '
               f'xmlns="http://www.w3.org/2000/svg">')

    # Background + border
    out.append(f'<rect width="{W}" height="{SVG_H}" rx="10" fill="{BG}"/>')
    out.append(f'<rect width="{W}" height="{SVG_H}" rx="10" fill="none" '
               f'stroke="{BORDER}" stroke-width="1"/>')

    # Vertical divider between art and info
    out.append(f'<line x1="{IX-8}" y1="{PAD}" x2="{IX-8}" y2="{panel_h-PAD}" '
               f'stroke="{BORDER}" stroke-width="1"/>')

    # Horizontal divider below main panel
    out.append(f'<line x1="{PAD}" y1="{panel_h}" x2="{W-PAD}" y2="{panel_h}" '
               f'stroke="{BORDER}" stroke-width="1"/>')

    # ── ASCII art ──
    out.append(f'<text font-family="\'Courier New\',Courier,monospace" '
               f'font-size="{AF}" fill="{C_ART}">')
    for i, ln in enumerate(art):
        y = PAD + (i + 1) * ALH
        out.append(f'  <tspan x="{PAD}" y="{y}">{xe(ln)}</tspan>')
    out.append('</text>')

    # ── Info panel helpers ──
    iy = PAD  # current y cursor for info

    def raw(tag): out.append(tag)

    def title_row():
        nonlocal iy
        iy += 14
        out.append(
            f'<text x="{IX}" y="{iy}" font-family="\'Courier New\',monospace" '
            f'font-size="14" font-weight="bold">'
            f'<tspan fill="{C_TITLE}">joydeep</tspan>'
            f'<tspan fill="{C_SEP}">@</tspan>'
            f'<tspan fill="{C_TITLE}">foss</tspan>'
            f'</text>'
        )
        iy += 5
        out.append(f'<line x1="{IX}" y1="{iy}" x2="{W-PAD}" y2="{iy}" '
                   f'stroke="{BORDER}" stroke-width="1"/>')
        iy += 12

    def kv(key, val, vc=None):
        nonlocal iy
        vc = vc or C_VAL
        out.append(
            f'<text x="{IX}" y="{iy}" font-family="\'Courier New\',monospace" '
            f'font-size="{IF}">'
            f'<tspan fill="{C_KEY}">{xe(key)}</tspan>'
            f'<tspan fill="{C_SEP}"> &gt; </tspan>'
            f'<tspan fill="{vc}">{xe(val)}</tspan>'
            f'</text>'
        )
        iy += ILH

    def sec(label):
        nonlocal iy
        iy += 4
        out.append(
            f'<text x="{IX}" y="{iy}" font-family="\'Courier New\',monospace" '
            f'font-size="10" fill="{C_SEC}">─── {xe(label)} ──────────────────────────</text>'
        )
        iy += ILH - 4

    def linkrow(key, val, href_val):
        nonlocal iy
        out.append(
            f'<text x="{IX}" y="{iy}" font-family="\'Courier New\',monospace" '
            f'font-size="{IF}">'
            f'<tspan fill="{C_KEY}">{xe(key)}</tspan>'
            f'<tspan fill="{C_SEP}"> &gt; </tspan>'
            f'<tspan fill="{C_LINK}">{xe(href_val)}</tspan>'
            f'</text>'
        )
        iy += ILH

    # ── Build info rows ──
    title_row()
    kv("OS     ", "Cachy OS  │  Windows 11")
    kv("Uptime ", uptime, C_ACNT)
    kv("Kernel ", "CSE Student @ NSEC  ·  2025–29")
    kv("IDE    ", "VSCode  │  Vim")
    kv("Theme  ", "Catppuccin Mocha")
    kv("Hobbies", "Gaming · Projects · Hardware · Electronics")

    sec("Languages")
    kv("Programming ", "Python · C · C++")
    kv("Markup/Data ", "HTML · CSS · JSON · YAML")
    kv("Spoken      ", "English · Hindi · Bengali")

    sec("Contact")
    linkrow("Email.Personal", PERSONAL_EMAIL,  PERSONAL_EMAIL)
    linkrow("Email.Student ", STUDENT_EMAIL,   STUDENT_EMAIL)
    linkrow("LinkedIn      ", LINKEDIN_SHORT,  LINKEDIN_SHORT)
    linkrow("GitHub        ", GITHUB_SHORT,    GITHUB_SHORT)

    sec("GitHub Stats")
    kv("Repos  ", f"{gh_data.get('repos', '?'):,}" if isinstance(gh_data.get('repos'), int) else str(gh_data.get('repos', '?')))
    kv("Commits", f"{gh_data.get('commits', '?'):,}  (all time)" if isinstance(gh_data.get('commits'), int) else "?  (all time)")
    kv("Lines  ", f"{gh_data.get('loc', '?'):,}  (est.)" if isinstance(gh_data.get('loc'), int) else "?  (est.)")

    active = gh_data.get("active", [])
    if active:
        sec("Active Projects")
        for p in active:
            lang = f"[{p['lang']}]" if p.get('lang') else ""
            name = p.get("name","")
            out.append(
                f'<text x="{IX}" y="{iy}" font-family="\'Courier New\',monospace" '
                f'font-size="{IF}">'
                f'<tspan fill="{C_ACNT}">→ </tspan>'
                f'<tspan fill="{C_PROJ}">{xe(name)}</tspan>'
                f'<tspan fill="{C_DIM}">  {xe(lang)}</tspan>'
                f'</text>'
            )
            iy += ILH

    # Colour palette (neofetch style)
    iy += 10
    px = IX
    for col in PALETTE:
        out.append(f'<rect x="{px}" y="{iy-9}" width="14" height="10" rx="2" fill="{col}"/>')
        px += 18

    # ── Contribution graph ──
    out.append(
        f'<text x="{PAD}" y="{cg_hdr_y}" font-family="\'Courier New\',monospace" '
        f'font-size="11" fill="{C_TITLE}">~/contrib  ──  Contribution Graph</text>'
    )

    if weeks:
        # Month labels
        prev_m = None
        for wi, week in enumerate(weeks):
            days = week["contributionDays"]
            m = datetime.strptime(days[0]["date"], "%Y-%m-%d").strftime("%b")
            if m != prev_m:
                mx = grid_x + wi * STR
                out.append(
                    f'<text x="{mx}" y="{month_y}" font-family="\'Courier New\',monospace" '
                    f'font-size="8" fill="{C_DIM}">{xe(m)}</text>'
                )
                prev_m = m

        # Day labels
        day_names = ["","Mon","","Wed","","Fri",""]
        for di, dlbl in enumerate(day_names):
            if dlbl:
                out.append(
                    f'<text x="{PAD}" y="{grid_y + di*STR + CELL}" '
                    f'font-family="\'Courier New\',monospace" font-size="8" '
                    f'fill="{C_DIM}">{dlbl}</text>'
                )

        # Cells
        for wi, week in enumerate(weeks):
            for day in week["contributionDays"]:
                col  = CGREEN[clvl(day["contributionCount"])]
                cx   = grid_x + wi * STR
                cy   = grid_y + day["weekday"] * STR
                out.append(
                    f'<rect x="{cx}" y="{cy}" width="{CELL}" height="{CELL}" '
                    f'rx="2" fill="{col}"/>'
                )

        # Legend
        out.append(
            f'<text x="{grid_x}" y="{legend_y}" font-family="\'Courier New\',monospace" '
            f'font-size="8" fill="{C_DIM}">Less</text>'
        )
        lx = grid_x + 26
        for col in CGREEN:
            out.append(f'<rect x="{lx}" y="{legend_y-8}" width="{CELL}" height="{CELL}" '
                       f'rx="2" fill="{col}"/>')
            lx += STR
        out.append(
            f'<text x="{lx+2}" y="{legend_y}" font-family="\'Courier New\',monospace" '
            f'font-size="8" fill="{C_DIM}">More</text>'
        )
    else:
        out.append(
            f'<text x="{grid_x}" y="{grid_y+20}" font-family="\'Courier New\',monospace" '
            f'font-size="10" fill="{C_DIM}">No contribution data (GH_TOKEN not set)</text>'
        )

    # Footer
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    out.append(
        f'<text x="{W//2}" y="{footer_y}" text-anchor="middle" '
        f'font-family="\'Courier New\',monospace" font-size="9" fill="{C_SEP}">'
        f'Auto-updated daily via GitHub Actions · {xe(now)}</text>'
    )

    out.append('</svg>')
    return "\n".join(out)

# ── README ────────────────────────────────────────────────────────────────
README_TMPL = """\
<!-- Auto-generated by today.py — do not edit manually -->

<div align="center">
  <img src="profile.svg" alt="joydeep@foss — GitHub Profile" width="900"/>
</div>
"""

# ── Main ──────────────────────────────────────────────────────────────────
def main():
    print("🟢  Fetching GitHub data …")
    gh_data = fetch_github_data()
    weeks   = fetch_weeks()
    uptime  = calc_uptime()
    print(f"   repos={gh_data.get('repos')}  commits={gh_data.get('commits')}  loc={gh_data.get('loc')}")
    print(f"   uptime={uptime}")

    print("🖼️  Loading ASCII art …")
    art = load_art()
    print(f"   {len(art)} lines")

    print("🎨  Building SVG …")
    svg = build_svg(art, gh_data, weeks, uptime)

    with open(SVG_FILE, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"✅  profile.svg written ({len(svg)} bytes)")

    with open(MD_FILE, "w", encoding="utf-8") as f:
        f.write(README_TMPL)
    print(f"✅  README.md written")

if __name__ == "__main__":
    main()
