import json
import subprocess
from datetime import date
from pathlib import Path

USER = "theomilll"
OUT = Path(__file__).resolve().parent.parent / "assets"
VENDOR_DIRS = {"venv", ".venv", "env", "node_modules"}
SKIP_LANGS = {"Makefile", "Dockerfile", "Mako", "PowerShell", "Batchfile", "Procfile", "Shell"}
PER_REPO_CAP = 3_500_000
GENERATED_HTML = 1_000_000
NOTEBOOK_WEIGHT = 0.1
TOP = 7

LANG_COLORS = {
    "Python": ("#3572A5", "#5b9bd5"),
    "TypeScript": ("#3178c6", "#4f9cf0"),
    "JavaScript": ("#c9b200", "#f1e05a"),
    "HTML": ("#e34c26", "#f0693f"),
    "CSS": ("#563d7c", "#9a7ad1"),
    "Rust": ("#b7410e", "#dea584"),
    "Lua": ("#000080", "#7b86ff"),
    "C": ("#555555", "#a0a8b0"),
    "C++": ("#f34b7d", "#f34b7d"),
    "Java": ("#b07219", "#d89a3e"),
    "Swift": ("#F05138", "#F05138"),
    "HCL": ("#844FBA", "#a77ae0"),
    "PHP": ("#4F5D95", "#8892c6"),
}

THEMES = {
    "light": {
        "bg": "#ffffff", "line": "#d0d7de", "fg": "#1f2328", "muted": "#59636e", "accent": "#e2700f",
        "ramp": ["#ebeef1", "#ffe1c2", "#ffb871", "#f27d1f", "#b5530a"], "other": "#c4cbd2",
    },
    "dark": {
        "bg": "#0d1117", "line": "#30363d", "fg": "#e6edf3", "muted": "#8b949e", "accent": "#ff9a3c",
        "ramp": ["#161b22", "#3d2410", "#7a3d0c", "#d26a12", "#ffaa4d"], "other": "#484f58",
    },
}

SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI','Helvetica Neue',Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,monospace"
W = 840


def gh(*args):
    return json.loads(subprocess.run(["gh", *args], capture_output=True, text=True, check=True).stdout)


def language_shares():
    repos = gh("repo", "list", USER, "--limit", "500", "--source", "--json", "name")
    totals = {}
    for repo in repos:
        name = repo["name"]
        try:
            root = gh("api", f"repos/{USER}/{name}/contents/")
        except subprocess.CalledProcessError:
            continue
        if any(e["type"] == "dir" and e["name"] in VENDOR_DIRS for e in root):
            continue
        for lang, size in gh("api", f"repos/{USER}/{name}/languages").items():
            if lang in SKIP_LANGS or (lang == "HTML" and size > GENERATED_HTML):
                continue
            if lang == "Jupyter Notebook":
                lang, size = "Python", size * NOTEBOOK_WEIGHT
            totals[lang] = totals.get(lang, 0) + min(size, PER_REPO_CAP)
    ranked = sorted(totals.items(), key=lambda kv: -kv[1])
    whole = sum(totals.values())
    shares = [(lang, size / whole) for lang, size in ranked[:TOP]]
    rest = 1 - sum(s for _, s in shares)
    return shares + ([("Other", rest)] if rest > 0.005 else []), len(repos)


def contributions():
    query = """query($u:String!){user(login:$u){contributionsCollection{contributionCalendar{totalContributions
      weeks{contributionDays{date contributionCount}}}}}}"""
    cal = gh("api", "graphql", "-f", f"query={query}", "-f", f"u={USER}")["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    prs = gh("search", "prs", "--author", USER, "--merged", "--limit", "1000", "--json", "repository")
    outside = sum(1 for p in prs if not p["repository"]["nameWithOwner"].startswith(f"{USER}/"))
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    best = run = 0
    for d in days:
        run = run + 1 if d["contributionCount"] else 0
        best = max(best, run)
    return cal["weeks"], cal["totalContributions"], best, outside


def frame(t, height, body, extra_style=""):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{height}" viewBox="0 0 {W} {height}" role="img">
<style>
.sans{{font-family:{SANS}}} .mono{{font-family:{MONO}}}
.fade{{animation:fade .6s ease-out both}}
@keyframes fade{{from{{opacity:0;transform:translateY(4px)}}to{{opacity:1;transform:none}}}}
{extra_style}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}
</style>
<rect x="0.5" y="0.5" width="{W - 1}" height="{height - 1}" rx="14" fill="{t['bg']}" stroke="{t['line']}"/>
{body}
</svg>"""


def smooth(pts):
    out = []
    for i in range(len(pts) - 1):
        p0, p1, p2 = pts[max(i - 1, 0)], pts[i], pts[i + 1]
        p3 = pts[min(i + 2, len(pts) - 1)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        out.append(f"C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}")
    return " ".join(out)


def header(t, weeks):
    totals = [sum(d["contributionCount"] for d in w["contributionDays"]) for w in weeks][-30:]
    peak = max(totals) or 1
    x0, x1, base, top = 610, 800, 150, 50
    step = (x1 - x0) / (len(totals) - 1)
    pts = [(x0 + i * step, base - (v / peak) * (base - top)) for i, v in enumerate(totals)]
    curve = smooth(pts)
    area = f"M{x0},{base} L{pts[0][0]:.1f},{pts[0][1]:.1f} {curve} L{x1},{base} Z"
    body = f"""<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="{t['accent']}" stop-opacity=".45"/><stop offset="1" stop-color="{t['accent']}" stop-opacity="0"/></linearGradient>
<clipPath id="reveal"><rect x="{x0}" y="0" width="0" height="200"><animate attributeName="width" from="0" to="{x1 - x0 + 4}" dur="1.6s" fill="freeze" calcMode="spline" keySplines=".2 .7 .2 1" keyTimes="0;1"/></rect></clipPath></defs>
<text class="mono fade" x="40" y="58" font-size="12" letter-spacing="1.6" fill="{t['muted']}">SOFTWARE ENGINEER · RECIFE, BRAZIL</text>
<text class="sans fade" x="38" y="112" font-size="50" font-weight="800" letter-spacing="-1.5" fill="{t['fg']}" style="animation-delay:.1s">Théo Moura</text>
<text class="sans fade" x="40" y="148" font-size="16" fill="{t['muted']}" style="animation-delay:.25s">I build AI products and the tooling that makes coding agents better.<tspan class="caret" fill="{t['accent']}">▍</tspan></text>
<g clip-path="url(#reveal)"><path d="{area}" fill="url(#g)"/><path d="M{pts[0][0]:.1f},{pts[0][1]:.1f} {curve}" fill="none" stroke="{t['accent']}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>
<circle cx="{pts[-1][0]:.1f}" cy="{pts[-1][1]:.1f}" r="4" fill="{t['accent']}"/></g>
<line x1="{x0}" y1="{base + 0.5}" x2="{x1}" y2="{base + 0.5}" stroke="{t['line']}"/>
<text class="mono" x="{x1}" y="{base + 22}" font-size="11" text-anchor="end" fill="{t['muted']}">weekly activity, last 30 weeks</text>"""
    return frame(t, 200, body, ".caret{animation:blink 1.1s steps(1) infinite}@keyframes blink{50%{opacity:0}}")


def stat(x, value, label, t, delay):
    return f"""<g class="fade" style="animation-delay:{delay}s"><text class="sans" x="{x}" y="78" font-size="30" font-weight="750" letter-spacing="-.8" fill="{t['fg']}">{value}</text>
<text class="sans" x="{x}" y="100" font-size="13" fill="{t['muted']}">{label}</text></g>"""


def calendar(t, weeks, total, streak, outside):
    days = [d["contributionCount"] for w in weeks for d in w["contributionDays"] if d["contributionCount"]]
    cuts = sorted(days)
    q = [cuts[int(len(cuts) * f)] for f in (0.25, 0.5, 0.75)] if cuts else [1, 2, 3]
    level = lambda n: 0 if n == 0 else 1 + sum(n > c for c in q)
    cell, gap, x0, y0 = 11, 3, 49, 156
    cells, months, last = [], [], None
    for i, w in enumerate(weeks):
        for d in w["contributionDays"]:
            dt = date.fromisoformat(d["date"])
            if dt.month != last and dt.day <= 7 and i < len(weeks) - 2:
                months.append(f'<text class="mono" x="{x0 + i * (cell + gap)}" y="{y0 - 10}" font-size="10.5" fill="{t["muted"]}">{dt.strftime("%b")}</text>')
                last = dt.month
            cells.append(f'<rect class="c" x="{x0 + i * (cell + gap)}" y="{y0 + dt.isoweekday() % 7 * (cell + gap)}" width="{cell}" height="{cell}" rx="2.5" fill="{t["ramp"][level(d["contributionCount"])]}" style="animation-delay:{i * 18}ms"/>')
    legend_x = W - 49 - 5 * (cell + gap) - 64
    legend = "".join(f'<rect x="{legend_x + 34 + k * (cell + gap)}" y="{y0 + 7 * (cell + gap) + 12}" width="{cell}" height="{cell}" rx="2.5" fill="{c}"/>' for k, c in enumerate(t["ramp"]))
    ly = y0 + 7 * (cell + gap) + 21
    body = f"""<text class="mono" x="49" y="40" font-size="12" letter-spacing="1.6" fill="{t['muted']}">CONTRIBUTIONS</text>
{stat(49, f"{total:,}", "contributions in the last year", t, 0)}
{stat(309, f"{streak} days", "longest streak", t, .1)}
{stat(569, f"{outside}", "PRs merged into repos I don't own", t, .2)}
{''.join(months)}{''.join(cells)}
<text class="mono" x="{legend_x}" y="{ly}" font-size="10.5" fill="{t['muted']}">Less</text>{legend}
<text class="mono" x="{legend_x + 34 + 5 * (cell + gap) + 4}" y="{ly}" font-size="10.5" fill="{t['muted']}">More</text>"""
    return frame(t, y0 + 7 * (cell + gap) + 40, body, ".c{animation:pop .45s ease-out both}@keyframes pop{from{opacity:0}to{opacity:1}}")


def languages(t, shares, repo_count, theme):
    x0, bw, y = 49, W - 98, 92
    segs, legend, x = [], [], x0
    for i, (lang, share) in enumerate(shares):
        color = t["other"] if lang == "Other" else LANG_COLORS.get(lang, (t["other"], t["other"]))[theme == "dark"]
        width = share * bw
        segs.append(f'<rect x="{x:.2f}" y="{y}" width="{max(width - 2, 1):.2f}" height="16" fill="{color}"/>')
        col, row = i % 4, i // 4
        lx, ly = x0 + col * (bw / 4), y + 56 + row * 30
        legend.append(f"""<g class="fade" style="animation-delay:{.5 + i * .06:.2f}s"><circle cx="{lx + 5}" cy="{ly - 4}" r="5" fill="{color}"/>
<text class="sans" x="{lx + 18}" y="{ly}" font-size="14" font-weight="600" fill="{t['fg']}">{lang}</text>
<text class="mono" x="{lx + bw / 4 - 28:.1f}" y="{ly}" font-size="12.5" text-anchor="end" fill="{t['muted']}">{share * 100:.1f}%</text></g>""")
        x += width
    rows = (len(shares) + 3) // 4
    height = y + 56 + rows * 30 + 10
    body = f"""<defs><clipPath id="bar"><rect x="{x0}" y="{y}" width="{bw}" height="16" rx="8"/></clipPath>
<clipPath id="grow"><rect x="{x0}" y="{y - 2}" width="0" height="20"><animate attributeName="width" from="0" to="{bw}" dur="1.2s" fill="freeze" calcMode="spline" keySplines=".2 .7 .2 1" keyTimes="0;1"/></rect></clipPath></defs>
<text class="mono" x="49" y="40" font-size="12" letter-spacing="1.6" fill="{t['muted']}">LANGUAGES</text>
<text class="sans" x="49" y="66" font-size="14" fill="{t['muted']}">By code size across {repo_count} repos I wrote</text>
<g clip-path="url(#grow)"><g clip-path="url(#bar)"><rect x="{x0}" y="{y}" width="{bw}" height="16" fill="{t['line']}"/>{''.join(segs)}</g></g>
{''.join(legend)}"""
    return frame(t, height, body)


def main():
    OUT.mkdir(exist_ok=True)
    weeks, total, streak, outside = contributions()
    shares, repo_count = language_shares()
    for theme, t in THEMES.items():
        (OUT / f"header-{theme}.svg").write_text(header(t, weeks))
        (OUT / f"contributions-{theme}.svg").write_text(calendar(t, weeks, total, streak, outside))
        (OUT / f"languages-{theme}.svg").write_text(languages(t, shares, repo_count, theme))
    print(json.dumps({"total": total, "streak": streak, "outside_prs": outside, "repos": repo_count, "languages": [(l, round(s * 100, 1)) for l, s in shares]}))


if __name__ == "__main__":
    main()
