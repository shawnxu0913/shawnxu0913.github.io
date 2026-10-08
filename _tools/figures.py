#!/usr/bin/env python3
"""Generate the static SVG figures for the Milestone 1 post (no dependencies).

Writes assets/img/winrate.svg and assets/img/architecture.svg. Same data and design as the
Claude Docs draft of the write-up. Run from the repo root: python _tools/figures.py
"""
import os

INK, QUIET, GRID, MUTED, ACCENT, EDGE, TINT = ("#1f2328", "#59636e", "#e6e6e6", "#b9b9b0",
                                              "#2f6fd6", "#9a9a92", "#f3f3f1")
FONT = "font-family='-apple-system, Segoe UI, Helvetica, Arial, sans-serif'"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "img")

# Promoted arm's win rate in each fleet A/B test (Ironclad, Ascension 0).
# (day since Aug 28 2026, win rate %, label or "", label dy, label anchor, date, change shipped)
WINRATE = [
    (0, 9.6, "Start", 4, "end", "Aug 28", "Baseline before survival-based route planning"),
    (1, 13.6, "", 0, "", "Aug 29", "Per-floor replanning + engine-forked route enumeration"),
    (1.5, 15.8, "", 0, "", "Aug 29", "Joint deck-value scorer"),
    (2, 18.5, "", 0, "", "Aug 30", "Future-boss survival in route value"),
    (13, 24.4, "", 0, "", "Sep 10", "Potion-aware leaf evaluation"),
    (19, 27.7, "", 0, "", "Sep 16", "Forkrank card picks"),
    (25, 33.6, "", 0, "", "Sep 22", "Forkrank retrained on its own runs"),
    (26, 52.5, "Event table", -12, "end", "Sep 23", "Causal event table"),
    (27, 49.7, "", 0, "", "Sep 24", "Planner uses the same pick model"),
    (31, 46.6, "", 0, "", "Sep 28", "Relics over cards in shops"),
    (32, 66.4, "Playout gate", -12, "end", "Sep 29", "Playout gate"),
    (33, 70.0, "", 0, "", "Sep 30", "Potion and racing fallback rungs"),
    (37, 77.7, "", 0, "", "Oct 4", "Strict defensive potions"),
    (40, 82.4, "Turn beam", 12, "start", "Oct 7", "Turn beam"),
    (40.6, 87.0, "Beam variants", -4, "start", "Oct 7", "Turn-beam variants"),
]


def winrate_svg():
    x = lambda d: 70 + d / 41 * 560
    y = lambda v: 330 - v / 100 * 250
    o = [f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 760 370' {FONT} font-size='12' role='img' "
         "style='width:100%;height:auto;display:block' "
         f"aria-label='Win rate rose from 10% to 87% in six weeks'>",
         "<rect width='760' height='370' fill='white'/>",
         f"<text x='20' y='26' font-size='16' font-weight='600' fill='{INK}'>Win rate rose from 10% to 87% in six weeks</text>",
         f"<text x='20' y='46' fill='{QUIET}'>Promoted agent's win rate in each A/B test (Ironclad, Ascension 0). "
         "Each test used its own seed pool, so small dips are noise.</text>"]
    for t in (0, 25, 50, 75, 100):
        o.append(f"<line x1='70' x2='650' y1='{y(t)}' y2='{y(t)}' stroke='{GRID}'/>")
        o.append(f"<text x='60' y='{y(t) + 4}' text-anchor='end' fill='{QUIET}'>{t}%</text>")
    for d, t in ((4, "Sep 1"), (18, "Sep 15"), (34, "Oct 1")):
        o.append(f"<text x='{x(d)}' y='352' text-anchor='middle' fill='{QUIET}'>{t}</text>")
    path = " ".join(("M" if i == 0 else "L") + f"{x(d):.1f} {y(v):.1f}" for i, (d, v, *_) in enumerate(WINRATE))
    o.append(f"<path d='{path}' fill='none' stroke='{MUTED}' stroke-width='2'/>")
    for d, v, key, ly, an, date, idea in WINRATE:
        fill = ACCENT if key and key != "Start" else MUTED
        # Hover/tap: data-tip is shown by the tooltip script in _includes/head.html; r=9 transparent hit area.
        o.append(f"<g data-tip='{date}: {idea} — {v}% win rate' style='cursor:pointer'>"
                 f"<circle cx='{x(d):.1f}' cy='{y(v):.1f}' r='{5 if key else 3}' fill='{fill}'/>"
                 f"<circle cx='{x(d):.1f}' cy='{y(v):.1f}' r='9' fill='transparent'/></g>")
        if key:
            lx = x(d) + (-10 if an == "end" else 12)
            col = QUIET if key == "Start" else ACCENT
            o.append(f"<text x='{lx:.1f}' y='{y(v) + ly:.1f}' text-anchor='{an}' font-weight='600' fill='{col}'>"
                     f"{key} {round(v)}%</text>")
    o.append("</svg>")
    return "\n".join(o)


def architecture_svg():
    lx, rx, bw, bh = 40, 416, 304, 56
    rows = (96, 176, 256, 336)
    left = [("Act path planner", "Searches map routes; replans every floor"),
            ("Forkrank card picks", "Learned from forked runs; floor 17 on"),
            ("Causal event table", "Picks options by measured effect on winning"),
            ("Shop, potions, rest", "Relics over cards; potions on lethal hits")]
    right = [("Playout gate", "Simulates the whole fight before turn one"),
             ("Combat search (default)", "3-turn lookahead, learned leaf evaluation"),
             ("Fallback strategies", "Deeper, racing and potion-drinking arms"),
             ("Turn beam", "Keeps 40 to 80 end-of-turn states; 4 variants")]
    o = [f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 760 488' {FONT} font-size='13' role='img' "
         "aria-label='Learned models plan the run; search plays each fight'>",
         "<rect width='760' height='488' fill='white'/>",
         "<defs><marker id='a' viewBox='0 0 10 10' refX='9' refY='5' markerWidth='6' markerHeight='6' "
         f"orient='auto-start-reverse'><path d='M0 0L10 5L0 10z' fill='{EDGE}'/></marker></defs>",
         f"<text x='24' y='32' font-size='15' font-weight='600' fill='{INK}'>Learned models plan the run; search plays each fight</text>"]
    for cx, name in ((24, "Between fights"), (400, "In each fight")):
        o.append(f"<rect x='{cx}' y='56' width='336' height='352' rx='8' fill='{TINT}' stroke='{EDGE}'/>")
        o.append(f"<text x='{cx + 16}' y='80' font-weight='600' fill='{QUIET}'>{name}</text>")
    for bx, items in ((lx, left), (rx, right)):
        for (name, body), ry in zip(items, rows):
            o.append(f"<rect x='{bx}' y='{ry}' width='{bw}' height='{bh}' rx='8' fill='white' stroke='{EDGE}' stroke-width='1.25'/>")
            o.append(f"<text x='{bx + 16}' y='{ry + 24}' font-weight='600' fill='{INK}'>{name}</text>")
            o.append(f"<text x='{bx + 16}' y='{ry + 42}' font-size='11.5' fill='{QUIET}'>{body}</text>")
    mid = rx + bw // 2
    conns = [f"M{lx + bw} {rows[0] + bh // 2}H{rx}"] + [f"M{mid} {rows[i] + bh}V{rows[i + 1]}" for i in range(3)]
    for d in conns:
        o.append(f"<path d='{d}' fill='none' stroke='{EDGE}' stroke-width='1.25' marker-end='url(#a)'/>")
    o.append(f"<path d='M192 408V424M568 408V424' stroke='{EDGE}' stroke-width='1.25'/>")
    o.append(f"<text x='380' y='{rows[0] + bh // 2 - 8}' text-anchor='middle' font-size='11.5' fill='{QUIET}'>fight</text>")
    for i, label in enumerate(("tries first", "if it dies", "if all of them die")):
        o.append(f"<text x='{mid + 10}' y='{rows[i] + bh + 16}' font-size='11.5' fill='{QUIET}'>{label}</text>")
    o.append(f"<rect x='24' y='424' width='712' height='40' rx='8' fill='white' stroke='{EDGE}' stroke-width='1.25'/>")
    o.append(f"<text x='380' y='449' text-anchor='middle' font-weight='600' fill='{INK}'>"
             "Simulator built from the game&#8217;s own code: fork, simulate, rewind</text>")
    o.append("</svg>")
    return "\n".join(o)


INC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_includes", "figures")

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(INC, exist_ok=True)
    # Inlined into the post (hover tooltips only work on inline SVG, not through <img>).
    with open(os.path.join(INC, "winrate.svg"), "w", encoding="utf-8") as f:
        f.write(winrate_svg())
    print("wrote", os.path.normpath(os.path.join(INC, "winrate.svg")))
    for name, svg in (("winrate.svg", winrate_svg()), ("architecture.svg", architecture_svg())):
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            f.write(svg)
        print("wrote", os.path.normpath(os.path.join(OUT, name)))
