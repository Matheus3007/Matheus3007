"""Builds the animated SVGs in assets/ used by the profile README.

    python3 tools/svgs.py

Fonts (Barlow, Barlow Condensed, JetBrains Mono; OFL) are fetched from Google Fonts on
first run into tools/.fonts, subset to the glyphs each SVG uses and embedded as woff2,
since an SVG shown through <img> can't load external fonts. Needs `pip install fonttools brotli`.
Every animation ends on the static final frame, and prefers-reduced-motion skips straight to it.
"""

import base64, io, math, re, urllib.request
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"
FONT_DIR = Path(__file__).resolve().parent / ".fonts"

FONTS = {
    "cond": "Barlow+Condensed:wght@700",
    "condm": "Barlow+Condensed:wght@500",
    "body": "Barlow:wght@400",
    "mono": "JetBrains+Mono:wght@400",
}
FAMILY = {"cond": "RCond", "condm": "RCondM", "body": "RBody", "mono": "RMono"}

BG, RED, INK, DIM, LINE = "#07080a", "#e60000", "#eeeeee", "#8a9099", "#1c1f24"


def font_path(key):
    p = FONT_DIR / f"{key}.ttf"
    if not p.exists():
        FONT_DIR.mkdir(exist_ok=True)
        req = urllib.request.Request(
            f"https://fonts.googleapis.com/css2?family={FONTS[key]}",
            headers={"User-Agent": "Mozilla/5.0"},
        )
        css = urllib.request.urlopen(req).read().decode()
        url = re.search(r"https://[^)]+\.ttf", css).group(0)
        p.write_bytes(urllib.request.urlopen(url).read())
    return p


def font_face(key, text):
    f = TTFont(font_path(key))
    s = subset.Subsetter()
    s.populate(text=text + " ")
    s.subset(f)
    f.flavor = "woff2"
    buf = io.BytesIO()
    f.save(buf)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"@font-face{{font-family:{FAMILY[key]};src:url(data:font/woff2;base64,{b64}) format('woff2');}}"


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def svg(name, w, h, body, css, text_by_font):
    faces = "".join(font_face(k, t) for k, t in text_by_font.items() if t)
    reduce = "@media (prefers-reduced-motion: reduce){*{animation:none!important}}"
    doc = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
        f'font-family="RBody, Barlow, sans-serif">\n<style>{faces}\n'
        f".cond{{font-family:RCond,'Barlow Condensed',sans-serif;font-weight:700}}"
        f".condm{{font-family:RCondM,'Barlow Condensed',sans-serif;font-weight:500}}"
        f".mono{{font-family:RMono,'JetBrains Mono',monospace}}"
        f"{css}{reduce}</style>\n{body}\n</svg>\n"
    )
    (OUT / name).write_text(doc)
    print(f"{name}: {len(doc) // 1024} KB")


class T:
    """Collects text per font while building, so each SVG embeds only its glyphs."""

    def __init__(self):
        self.used = {k: "" for k in FONTS}

    def __call__(self, x, y, s, font="body", size=16, fill=INK, cls="", extra=""):
        self.used[font] += s
        fc = {"body": "", "cond": "cond", "condm": "condm", "mono": "mono"}[font]
        c = " ".join(v for v in (fc, cls) if v)
        return f'<text x="{x}" y="{y}" class="{c}" font-size="{size}" fill="{fill}" {extra}>{esc(s)}</text>'


def grid_floor(w, h, horizon, vx, n_v=34, n_h=14, period=3.2, op=0.55):
    """Perspective floor: radial lines to a vanishing point, horizontal lines rushing toward the viewer."""
    out = [f'<g clip-path="url(#floor)" opacity="{op}">']
    spread = w * 2.6
    for i in range(n_v + 1):
        xb = vx - spread / 2 + spread * i / n_v
        xt = vx + (xb - vx) * 0.02
        out.append(f'<line x1="{xt:.1f}" y1="{horizon}" x2="{xb:.1f}" y2="{h}" stroke="{RED}" stroke-opacity=".38" stroke-width="1"/>')
    for i in range(n_h):
        out.append(
            f'<line class="hl" x1="0" x2="{w}" y1="{horizon}" y2="{horizon}" stroke="{RED}" stroke-width="1.2" '
            f'style="animation-delay:{-period * i / n_h:.2f}s"/>'
        )
    out.append("</g>")
    css = (
        f".hl{{animation:rush {period}s cubic-bezier(.55,0,1,.45) infinite}}"
        f"@keyframes rush{{0%{{transform:translateY(0);stroke-opacity:0}}15%{{stroke-opacity:.35}}"
        f"100%{{transform:translateY({h - horizon}px);stroke-opacity:.6}}}}"
    )
    defs = (
        f'<clipPath id="floor"><rect x="0" y="{horizon}" width="{w}" height="{h - horizon}"/></clipPath>'
        f'<linearGradient id="haze" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{RED}" stop-opacity="0"/><stop offset=".5" stop-color="{RED}" stop-opacity=".22"/>'
        f'<stop offset="1" stop-color="{RED}" stop-opacity="0"/></linearGradient>'
        f'<linearGradient id="fadeTop" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{BG}" stop-opacity="1"/><stop offset="1" stop-color="{BG}" stop-opacity="0"/></linearGradient>'
    )
    overlay = (
        f'<rect x="0" y="{horizon}" width="{w}" height="{(h - horizon) * 0.35:.0f}" fill="url(#fadeTop)"/>'
        f'<rect x="0" y="{horizon - 18}" width="{w}" height="36" fill="url(#haze)"/>'
    )
    return defs, "".join(out) + overlay, css


def blade_path():
    # Rebot's real single-tooth hook (GanchoUnidente, Ø230 Hardox), mm, centred on the weapon axis.
    # Top-view outline of the part in rebot-site/public/models/rebot.glb, unioned and simplified.
    return "M-1.6,38.4 L-13.9,27.9 L-42.1,7.6 L-56.5,-3.6 L-66.7,-13.5 L-68.0,-15.1 L-69.8,-18.7 L-70.6,-22.6 L-70.3,-26.6 L-67.7,-35.6 L-63.8,-44.1 L-58.7,-52.0 L-52.6,-59.0 L-45.5,-65.1 L-37.6,-70.1 L-29.0,-73.8 L-20.0,-76.3 L-10.7,-77.5 L-1.4,-77.3 L7.8,-75.8 L16.7,-72.9 L25.1,-68.8 L32.8,-63.5 L28.7,-59.0 L25.4,-54.4 L22.9,-49.8 L21.0,-45.2 L19.8,-39.9 L19.2,-34.2 L19.3,-29.0 L20.3,-22.0 L23.0,-12.8 L28.1,-0.6 L46.9,33.5 L51.1,42.7 L53.5,49.7 L55.3,56.9 L56.1,64.3 L55.9,72.1 L54.5,80.2 L51.4,86.9 L47.5,93.3 L42.6,99.0 L37.1,104.0 L31.0,108.2 L24.3,111.6 L19.9,113.3 L21.0,80.2 L19.8,72.4 L17.6,65.1 L14.4,58.3 L10.4,52.0 L5.7,45.9 Z M8.0,29.7 L8.4,31.7 L9.3,33.5 L16.9,42.3 L22.3,50.1 L26.8,58.6 L29.9,67.4 L31.5,69.3 L35.4,72.4 L40.0,74.4 L42.7,75.0 L44.2,74.3 L44.6,73.4 L45.1,67.2 L44.8,61.1 L43.3,53.9 L39.5,43.5 L26.7,20.3 L23.2,18.2 L20.6,17.9 L17.5,19.1 L10.6,23.8 L8.9,25.8 L8.1,27.7 Z M15.2,6.1 L15.9,6.8 L17.5,7.5 L19.0,7.2 L20.1,5.6 L20.1,4.2 L19.4,3.0 L18.1,2.3 L16.7,2.4 L15.3,3.5 L15.0,4.8 Z M13.1,-12.7 L12.2,-11.4 L12.2,-10.2 L12.8,-9.0 L13.9,-8.2 L14.8,-8.1 L16.3,-8.6 L17.2,-9.6 L17.4,-10.8 L16.9,-12.2 L15.0,-13.3 Z M2.1,-13.1 L-0.2,-13.1 L-2.7,-14.2 L-6.4,-12.8 L-8.4,-11.7 L-9.8,-8.6 L-12.6,-6.8 L-13.7,-4.8 L-14.4,-1.1 L-12.8,2.3 L-13.1,6.1 L-11.2,9.2 L-9.6,10.8 L-6.9,11.1 L-5.5,11.9 L-3.5,14.1 L0.2,14.5 L2.5,14.1 L5.1,12.0 L8.6,11.6 L10.9,9.4 L12.6,7.1 L12.5,3.5 L14.4,0.6 L14.1,-2.7 L13.3,-5.4 L11.6,-6.5 L10.1,-8.3 L9.4,-11.0 L4.2,-13.9 Z M5.3,15.0 L4.5,17.3 L5.7,19.0 L6.9,19.4 L7.9,19.3 L9.3,18.3 L9.7,16.5 L8.7,14.7 L7.9,14.3 L6.5,14.2 Z M-24.1,-9.3 L-20.8,-15.3 L-16.0,-20.3 L-13.2,-22.2 L-10.1,-23.8 L-6.6,-25.0 L-3.0,-25.6 L1.8,-25.8 L4.2,-26.7 L6.3,-28.2 L7.5,-29.9 L8.0,-31.9 L8.7,-41.0 L8.2,-43.6 L6.4,-46.2 L-0.3,-50.8 L-5.2,-52.7 L-10.2,-53.2 L-13.8,-52.8 L-21.8,-50.3 L-34.3,-44.0 L-55.4,-32.4 L-57.0,-31.1 L-58.1,-29.4 L-59.2,-25.5 L-58.8,-22.4 L-57.4,-19.7 L-47.2,-10.2 L-35.5,-1.3 L-32.6,-0.5 L-30.1,-0.9 L-27.8,-1.9 L-26.4,-3.3 L-25.4,-5.1 Z M0.3,-20.8 L-1.3,-19.7 L-1.7,-17.9 L-0.7,-16.2 L0.9,-15.6 L2.2,-16.0 L3.0,-16.8 L3.4,-18.3 L2.6,-20.2 Z M-8.6,13.4 L-10.6,14.4 L-11.2,15.8 L-10.8,17.6 L-9.9,18.4 L-8.8,18.7 L-6.9,17.9 L-6.1,16.4 L-6.5,14.7 L-7.6,13.7 Z M-15.0,-14.3 L-16.3,-12.7 L-16.2,-11.2 L-15.1,-9.8 L-13.0,-9.5 L-11.6,-10.5 L-11.2,-11.5 L-11.2,-12.9 L-12.5,-14.4 L-13.6,-14.7 Z M-16.6,1.1 L-18.2,0.6 L-19.7,1.2 L-20.3,2.2 L-20.6,3.3 L-20.2,4.5 L-18.5,5.8 L-16.2,5.1 L-15.3,3.5 L-15.8,1.7 Z"


def hero():
    t = T()
    W, H, HOR = 1200, 440, 250
    cx, cy = 905, 205
    gd, gfloor, gcss = grid_floor(W, H, HOR, cx)
    ticks = []
    for i in range(60):
        a = math.radians(i * 6 - 90)
        r1, r2 = (176, 188) if i % 5 == 0 else (181, 186)
        ticks.append(
            f'<line x1="{cx + r1 * math.cos(a):.1f}" y1="{cy + r1 * math.sin(a):.1f}" '
            f'x2="{cx + r2 * math.cos(a):.1f}" y2="{cy + r2 * math.sin(a):.1f}" stroke="{DIM}" stroke-opacity=".7" stroke-width="{1.6 if i % 5 == 0 else 1}"/>'
        )
    arc_r = 196
    arc_len = 2 * math.pi * arc_r * 0.75
    bp = blade_path()
    trails = "".join(
        f'<path d="{bp}" fill="#c9ced6" fill-rule="evenodd" opacity="{o}" transform="rotate({-a})"/>' for a, o in ((10, 0.22), (20, 0.12), (30, 0.06))
    )
    body = f"""<defs>{gd}
<radialGradient id="glow" cx="{cx}" cy="{cy}" r="260" gradientUnits="userSpaceOnUse">
  <stop offset="0" stop-color="{RED}" stop-opacity=".28"/><stop offset="1" stop-color="{RED}" stop-opacity="0"/></radialGradient>
<linearGradient id="steel" x1="-70" y1="-80" x2="60" y2="115" gradientUnits="userSpaceOnUse">
  <stop offset="0" stop-color="#5b6068"/><stop offset=".55" stop-color="#b9bfc7"/><stop offset="1" stop-color="#e9ecef"/></linearGradient>
<clipPath id="wipe"><rect class="wipe" x="60" y="80" width="560" height="170"/></clipPath>
</defs>
<rect width="{W}" height="{H}" fill="{BG}"/>
{gfloor}
<circle cx="{cx}" cy="{cy}" r="260" fill="url(#glow)"/>
<g transform="translate({cx} {cy}) scale(.86) translate({-cx} {-cy})">
<g class="fade" style="animation-delay:.2s">{"".join(ticks)}</g>
<circle cx="{cx}" cy="{cy}" r="{arc_r}" fill="none" stroke="{LINE}" stroke-width="4"
  stroke-dasharray="{arc_len:.1f} 9999" transform="rotate(135 {cx} {cy})"/>
<circle class="tach" cx="{cx}" cy="{cy}" r="{arc_r}" fill="none" stroke="{RED}" stroke-width="4" stroke-linecap="round"
  stroke-dasharray="{arc_len:.1f} 9999" transform="rotate(135 {cx} {cy})"/>
<circle class="blur" cx="{cx}" cy="{cy}" r="150" fill="#c9ced6"/>
<circle class="ring" cx="{cx}" cy="{cy}" r="160" fill="none" stroke="{RED}" stroke-opacity=".55" stroke-width="1.2" stroke-dasharray="3 11"/>
<g transform="translate({cx} {cy})">
  <g class="spinup"><g class="spin">
    <g transform="scale(1.3)">{trails}
    <path d="{bp}" fill="url(#steel)" fill-rule="evenodd" stroke="#2a2d33" stroke-width="1"/>
    <circle r="7" fill="{RED}"/><circle r="2.6" fill="{BG}"/></g>
  </g></g>
</g>
</g>
{t(cx, cy + 210, "0 → 6,800 RPM · ~0.5 S · 351 J", "mono", 13, DIM, "fade", 'text-anchor="middle" style="animation-delay:2.4s" letter-spacing="1.5"')}
<g class="fade">
  <line x1="62" y1="96" x2="92" y2="96" stroke="{RED}" stroke-width="2"/>
  {t(104, 101, "SOFTWARE ENGINEER @ ENTER · SÃO PAULO, BR", "mono", 14, RED, "", 'letter-spacing="2.5"')}
</g>
<g clip-path="url(#wipe)">
  {t(58, 228, "MATHEUS", "cond", 156, RED, "ghost", 'letter-spacing="2" opacity="0"')}
  {t(58, 228, "MATHEUS", "cond", 156, INK, "", 'letter-spacing="2"')}
</g>
<rect class="scan" x="58" y="96" width="4" height="140" fill="{RED}"/>
{t(62, 284, "Writes software for a living.", "body", 23, INK, "rise", 'style="animation-delay:1.1s"')}
{t(62, 316, "Builds a 3 lb robot that tries to delete other robots on weekends.", "body", 23, DIM, "rise", 'style="animation-delay:1.35s"')}
{t(62, 372, "POLI-USP '24  /  ex-AMAZON  /  ENTER  /  REBOT", "mono", 13, DIM, "rise", 'style="animation-delay:1.6s" letter-spacing="2"')}
"""
    css = gcss + f"""
.fade{{animation:fade 1s ease-out both}}
@keyframes fade{{from{{opacity:0}}}}
.rise{{animation:rise .9s cubic-bezier(.2,.7,.2,1) both}}
@keyframes rise{{from{{opacity:0;transform:translateY(14px)}}}}
.wipe{{animation:wipe 1.1s cubic-bezier(.7,0,.2,1) .25s both}}
@keyframes wipe{{from{{transform:scaleX(0)}}}}
.wipe{{transform-origin:60px 0}}
.scan{{opacity:0;animation:scan 1.1s cubic-bezier(.7,0,.2,1) .25s}}
@keyframes scan{{0%{{opacity:1;transform:translateX(0)}}95%{{opacity:1}}100%{{opacity:0;transform:translateX(540px)}}}}
.ghost{{animation:ghost 6s steps(1) 2s infinite}}
@keyframes ghost{{0%,100%{{opacity:0}}91%{{opacity:.9;transform:translate(-5px,2px)}}93%{{opacity:.9;transform:translate(4px,-1px)}}95%{{opacity:0}}}}
.spin{{animation:spin .42s linear infinite}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
.spinup{{animation:spinup 2.6s cubic-bezier(.6,0,1,1) both}}
@keyframes spinup{{from{{transform:rotate(-1080deg)}}}}
.blur{{opacity:.06;animation:blur 2.6s ease-in both}}
@keyframes blur{{from{{opacity:0}}}}
.ring{{transform-origin:{cx}px {cy}px;animation:spin 14s linear infinite reverse}}
.tach{{stroke-dashoffset:0;animation:tach 2.6s cubic-bezier(.2,.8,.3,1) both}}
@keyframes tach{{from{{stroke-dashoffset:{arc_len:.1f}}}}}
"""
    svg("hero.svg", W, H, body, css, t.used)


def section(name, idx, title, kicker):
    t = T()
    W, H = 1200, 96
    body = f"""<clipPath id="card"><rect width="{W}" height="{H}" rx="6"/></clipPath>
<g clip-path="url(#card)"><rect width="{W}" height="{H}" fill="{BG}"/>
<rect class="bar" x="0" y="0" width="{W}" height="3" fill="{RED}"/></g>
{t(32, 62, idx, "mono", 18, RED, "", 'letter-spacing="2"')}
<rect class="blink" x="68" y="44" width="10" height="20" fill="{RED}"/>
{t(94, 66, title, "cond", 40, INK, "slide", 'letter-spacing="1.5"')}
{t(W - 32, 62, kicker, "mono", 13, DIM, "slide2", 'text-anchor="end" letter-spacing="2"')}"""
    css = """
.bar{transform-origin:0 0;animation:bar 1.2s cubic-bezier(.7,0,.2,1) both}
@keyframes bar{from{transform:scaleX(0)}}
.blink{animation:blink 1.1s steps(1) infinite}
@keyframes blink{50%{opacity:0}}
.slide{animation:slide .8s cubic-bezier(.2,.7,.2,1) .3s both}
@keyframes slide{from{opacity:0;transform:translateX(-18px)}}
.slide2{animation:fade 1s ease-out .8s both}
@keyframes fade{from{opacity:0}}
"""
    svg(name, W, H, body, css, t.used)


def timeline():
    t = T()
    W, H = 1200, 230
    xs = [110, 520, 930]
    stops = [
        ("POLI-USP", "Computer Engineering", "graduated end of 2024", "thesis: Micras, a micromouse"),
        ("AMAZON", "Software Engineer", "first job out of uni", "learned the LPs by heart"),
        ("ENTER", "Software Engineer · now", "enterprise AI, made in Brazil", "getenter.ai"),
    ]
    nodes = []
    for i, (x, (name, role, l1, l2)) in enumerate(zip(xs, stops)):
        d = 0.4 + i * 0.7
        now = i == len(xs) - 1
        col = RED if now else INK
        pulse = (
            f'<circle class="pulse" cx="{x}" cy="70" r="9" fill="none" stroke="{RED}" stroke-width="2"/>' if now else ""
        )
        nodes.append(
            f'<g class="pop" style="animation-delay:{d:.2f}s;transform-origin:{x}px 70px">{pulse}'
            f'<circle cx="{x}" cy="70" r="9" fill="{BG}" stroke="{col}" stroke-width="3"/>'
            f'<circle cx="{x}" cy="70" r="3.5" fill="{col}"/></g>'
            f'<g class="rise" style="animation-delay:{d + 0.15:.2f}s">'
            + t(x - 10, 128, name, "cond", 34, col, "", 'letter-spacing="1.5"')
            + t(x - 10, 154, role, "body", 17, INK)
            + t(x - 10, 180, l1, "body", 15, DIM)
            + t(x - 10, 202, l2, "mono", 12, DIM, "", 'letter-spacing="1"')
            + "</g>"
        )
    body = f"""<rect width="{W}" height="{H}" fill="{BG}" rx="6"/>
<line x1="40" y1="70" x2="{W - 40}" y2="70" stroke="{LINE}" stroke-width="2"/>
<line class="track" x1="40" y1="70" x2="{xs[-1]}" y2="70" stroke="{RED}" stroke-width="2"/>
<line class="ahead" x1="{xs[-1] + 16}" y1="70" x2="{W - 40}" y2="70" stroke="{RED}" stroke-width="2" stroke-dasharray="4 8"/>
{t(W - 40, 50, "→ NEXT: WIN A FIGHT", "mono", 12, DIM, "fade", 'text-anchor="end" letter-spacing="2" style="animation-delay:2.4s"')}
{"".join(nodes)}"""
    css = """
.track{transform-origin:40px 70px;animation:bar 2s cubic-bezier(.5,0,.3,1) both}
@keyframes bar{from{transform:scaleX(0)}}
.ahead{animation:march .8s linear infinite}
@keyframes march{to{stroke-dashoffset:-12}}
.pop{animation:pop .5s cubic-bezier(.3,1.6,.5,1) both}
@keyframes pop{from{transform:scale(0)}}
.pulse{transform-box:fill-box;transform-origin:center;animation:pulse 1.8s ease-out 2s infinite}
@keyframes pulse{from{transform:scale(1);opacity:.9}to{transform:scale(3.2);opacity:0}}
.rise{animation:rise .8s cubic-bezier(.2,.7,.2,1) both}
@keyframes rise{from{opacity:0;transform:translateY(10px)}}
.fade{animation:fade 1s ease-out both}
@keyframes fade{from{opacity:0}}
"""
    svg("timeline.svg", W, H, body, css, t.used)


def wordmark_paths():
    src = (OUT / "rebot-wordmark.svg").read_text()
    out = []
    for cls, d in re.findall(r'<path class="(cls-\d)" d="([^"]+)"', src):
        out.append((cls, d))
    return out


def rebot_banner():
    t = T()
    W, H = 1200, 320
    paths = wordmark_paths()
    letters = "".join(f'<path d="{d}" fill="{INK}"/>' for c, d in paths if c == "cls-2")
    mark = "".join(f'<path d="{d}" fill="{RED}"/>' for c, d in paths if c == "cls-1")
    # Mark sits around (1373.8, 213.9) in wordmark units; it spins down into place like a weapon.
    s = 0.46
    body = f"""<defs>
<linearGradient id="shine" x1="0" y1="0" x2="1" y2="0">
  <stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".85"/>
  <stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
<clipPath id="letters"><g transform="translate(70 66) scale({s})">{letters}</g></clipPath>
</defs>
<rect width="{W}" height="{H}" fill="{BG}" rx="6"/>
<g class="fade">
  <line x1="74" y1="56" x2="104" y2="56" stroke="{RED}" stroke-width="2"/>
  {t(116, 61, "02 · THE BATTLEBOT · 6S UNDERCUTTER · BEETLEWEIGHT (1.36 KG)", "mono", 14, RED, "", 'letter-spacing="2.5"')}
</g>
<g transform="translate(70 66) scale({s})">
  <g class="letters">{letters}</g>
  <g class="mark" style="transform-origin:1373.8px 213.9px">{mark}</g>
</g>
<rect class="sweep" x="-240" y="190" width="200" height="100" fill="url(#shine)" clip-path="url(#letters)"/>
{t(W - 70, 254, "rebot.spinup.fail ↗", "mono", 15, DIM, "fade", 'text-anchor="end" letter-spacing="1.5" style="animation-delay:1.4s"')}
{t(W - 70, 280, "built from the real CAD", "mono", 12, "#4b5058", "fade", 'text-anchor="end" letter-spacing="1.5" style="animation-delay:1.6s"')}"""
    css = """
.fade{animation:fade 1s ease-out both}
@keyframes fade{from{opacity:0}}
.letters{animation:fade 1.2s ease-out .2s both}
.mark{animation:spindown 2.2s cubic-bezier(.1,.6,.2,1) both}
@keyframes spindown{from{transform:rotate(-1440deg) scale(.6);opacity:0}20%{opacity:1}}
.sweep{animation:sweep 5s cubic-bezier(.6,0,.4,1) 1.8s infinite}
@keyframes sweep{0%{transform:translateX(0)}35%,100%{transform:translateX(900px)}}
"""
    svg("rebot-banner.svg", W, H, body, css, t.used)


def odometer(t, x, y, value, h, size, delay, font="cond", fill=INK):
    """Rolling digits: each digit column spins up past 0-9 once and lands on its value."""
    out, cw = [], size * 0.5
    cx = x
    for ch in value:
        if not ch.isdigit():
            out.append(t(cx, y, ch, font, size, fill))
            cx += cw * (0.45 if ch in ",." else 1)
            continue
        d = int(ch)
        col = "".join(t(0, i * h, str(i % 10), font, size, fill) for i in range(20))
        out.append(
            f'<g clip-path="url(#odo)" transform="translate({cx:.1f} {y})">'
            f'<g class="odo" style="--to:{-(10 + d) * h}px;transform:translateY({-(10 + d) * h}px);animation-delay:{delay:.2f}s">{col}</g></g>'
        )
        delay += 0.12
        cx += cw
    return "".join(out)


def telemetry():
    t = T()
    W, H = 1200, 360
    h, size = 64, 58
    # Spin-up curve: rpm(t) = 6800 (1 - e^(-t/tau)), ~0.5 s to ~95 %.
    gx, gy, gw, gh = 70, 92, 470, 200
    tau = 0.5 / 3
    pts = [(gx + gw * (i / 100), gy + gh - gh * (1 - math.exp(-(0.75 * i / 100) / tau)) * 0.92) for i in range(101)]
    curve = "M " + " L ".join(f"{px:.1f},{py:.1f}" for px, py in pts)
    area = curve + f" L {gx + gw},{gy + gh} L {gx},{gy + gh} Z"
    grid = "".join(
        f'<line x1="{gx}" y1="{gy + gh * k / 4:.1f}" x2="{gx + gw}" y2="{gy + gh * k / 4:.1f}" stroke="{LINE}"/>' for k in range(5)
    ) + "".join(
        f'<line x1="{gx + gw * k / 6:.1f}" y1="{gy}" x2="{gx + gw * k / 6:.1f}" y2="{gy + gh}" stroke="{LINE}"/>' for k in range(7)
    )
    x05 = gx + gw * (0.5 / 0.75)
    stats = [
        ("6,800", "RPM, TOP SPEED"),
        ("290", "KM/H AT THE TOOTH"),
        ("351", "JOULES STORED"),
        ("230", "MM HARDOX BAR"),
    ]
    tiles = []
    for i, (v, label) in enumerate(stats):
        tx = 600 + (i % 2) * 290
        ty = 130 + (i // 2) * 120
        tiles.append(
            f'<rect x="{tx - 18}" y="{ty - 58}" width="270" height="104" fill="#0c0e11" stroke="{LINE}" rx="4"/>'
            f'<rect x="{tx - 18}" y="{ty - 58}" width="3" height="104" fill="{RED}"/>'
            + odometer(t, tx, ty, v, h, size, 0.3 + i * 0.25)
            + t(tx, ty + 32, label, "mono", 12, DIM, "", 'letter-spacing="2"')
        )
    body = f"""<defs>
<clipPath id="odo"><rect x="0" y="{-size * 0.8:.0f}" width="40" height="{size * 0.94:.0f}"/></clipPath>
<linearGradient id="area" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="{RED}" stop-opacity=".35"/><stop offset="1" stop-color="{RED}" stop-opacity="0"/></linearGradient>
</defs>
<rect width="{W}" height="{H}" fill="{BG}" rx="6"/>
{t(70, 50, "WEAPON SPIN-UP · THEORETICAL", "mono", 13, RED, "", 'letter-spacing="2.5"')}
{t(582, 50, "BY THE NUMBERS", "mono", 13, RED, "", 'letter-spacing="2.5"')}
{grid}
<path class="area" d="{area}" fill="url(#area)"/>
<path class="curve" d="{curve}" fill="none" stroke="{RED}" stroke-width="3" pathLength="1" stroke-dasharray="1 1"/>
<line x1="{x05:.1f}" y1="{gy}" x2="{x05:.1f}" y2="{gy + gh}" stroke="{INK}" stroke-opacity=".5" stroke-dasharray="3 5"/>
{t(x05 + 8, gy + 18, "0.5 s: full send", "mono", 12, INK, "fade", 'style="animation-delay:2s"')}
<circle r="6" fill="{RED}" stroke="{BG}" stroke-width="2"><animateMotion dur="2s" begin="0.3s" fill="freeze" path="{curve}" calcMode="spline" keyTimes="0;1" keySplines=".3 .1 .3 1"/></circle>
{t(gx, gy + gh + 26, "0 s", "mono", 12, DIM)}
{t(gx + gw, gy + gh + 26, "0.75 s", "mono", 12, DIM, "", 'text-anchor="end"')}
{t(gx, gy + gh + 52, "2814 on 6S LiHV, wye-wound, 1.5:1 through a TPU ratchet wheel", "body", 14, DIM)}
{t(582, gy + gh + 52, "2× 2207 tangential drive · TPU unibody · 2 mm carbon sandwich", "body", 14, DIM)}
{"".join(tiles)}"""
    css = f"""
.odo{{animation:roll 1.8s cubic-bezier(.15,.7,.1,1) both}}
@keyframes roll{{from{{transform:translateY(0)}}to{{transform:translateY(var(--to))}}}}
.curve{{stroke-dashoffset:0;animation:draw 2s cubic-bezier(.3,.1,.3,1) .3s both}}
@keyframes draw{{from{{stroke-dashoffset:1}}}}
.area{{animation:fade 1.2s ease-out 1.4s both}}
.fade{{animation:fade 1s ease-out both}}
@keyframes fade{{from{{opacity:0}}}}
"""
    svg("rebot-telemetry.svg", W, H, body, css, t.used)


def eitri():
    t = T()
    W, H = 1200, 300
    bp = blade_path()
    lines = [
        ("$", "eitri optimize examples/hook230/spec.toml --trials 300"),
        (">", "B-rep mass + MOI ............ ok"),
        (">", "BLDC spin-up ................ ok"),
        (">", "impact bite + impulse ....... ok"),
        (">", "CalculiX FEA, spin + hit .... ok"),
        (">", "best trial → hook230.step"),
    ]
    rows = []
    for i, (p, s) in enumerate(lines):
        d = 0.3 + i * 0.45
        rows.append(
            f'<g class="type" style="animation-delay:{d:.2f}s">'
            + t(560, 110 + i * 28, p, "mono", 15, RED)
            + t(582, 110 + i * 28, s, "mono", 15, INK if i in (0, 5) else DIM)
            + "</g>"
        )
    body = f"""<defs>
<radialGradient id="stress" cx="0" cy="0" r="118" gradientUnits="userSpaceOnUse">
  <stop offset="0" stop-color="{RED}"/><stop offset=".18" stop-color="#f08a24"/><stop offset=".32" stop-color="#f2d34a"/>
  <stop offset=".5" stop-color="#5fd38a"/><stop offset=".72" stop-color="#2aa1c9"/><stop offset="1" stop-color="#1f3b8a"/>
</radialGradient>
<linearGradient id="legend" x1="0" x2="1">
  <stop offset="0" stop-color="#1f3b8a"/><stop offset=".28" stop-color="#2aa1c9"/><stop offset=".5" stop-color="#5fd38a"/>
  <stop offset=".68" stop-color="#f2d34a"/><stop offset=".82" stop-color="#f08a24"/><stop offset="1" stop-color="{RED}"/>
</linearGradient>
</defs>
<rect width="{W}" height="{H}" fill="{BG}" rx="6"/>
{t(70, 50, "EITRI · WEAPON DESIGN + SIMULATION", "mono", 13, RED, "", 'letter-spacing="2.5"')}
<g transform="translate(300 150) rotate(-90) scale(.95)">
  <g class="wobble">
    <path d="{bp}" fill="none" fill-rule="evenodd" stroke="{DIM}" stroke-opacity=".35" stroke-width="1" stroke-dasharray="2 4" transform="rotate(-6)"/>
    <path class="fea" d="{bp}" fill="url(#stress)" fill-rule="evenodd"/>
    <path class="mesh" d="{bp}" fill="none" stroke="{INK}" stroke-width="1" pathLength="1" stroke-dasharray="1 1"/>
  </g>
</g>
{t(90, 268, "von Mises · spin + hit", "mono", 12, DIM)}
<rect x="270" y="257" width="180" height="8" fill="url(#legend)" rx="2"/>
{"".join(rows)}
<rect class="cursor" x="582" y="{110 + 5 * 28 + 10}" width="10" height="3" fill="{RED}"/>"""
    css = """
.mesh{stroke-dashoffset:0;animation:draw 1.6s ease-in-out .2s both}
@keyframes draw{from{stroke-dashoffset:1}}
.fea{animation:fea 4s ease-in-out 1.8s infinite both}
@keyframes fea{0%{opacity:0}30%,70%{opacity:.95}100%{opacity:0}}
.wobble{animation:wob 4s ease-in-out 1.8s infinite}
@keyframes wob{0%,100%{transform:rotate(0)}50%{transform:rotate(-4deg)}}
.type{animation:type .35s steps(4) both}
@keyframes type{from{opacity:0;transform:translateX(-6px)}}
.cursor{animation:blink 1s steps(1) 3s infinite both}
@keyframes blink{50%{opacity:0}}
"""
    svg("eitri.svg", W, H, body, css, t.used)


def footer():
    t = T()
    W, H, HOR = 1200, 200, 70
    gd, gfloor, gcss = grid_floor(W, H, HOR, W / 2, n_h=8, period=2.6, op=0.7)
    src = (OUT / "rebot-mark.svg").read_text()
    mark = "".join(f'<path d="{d}" fill="{RED}"/>' for d in re.findall(r'<path class="cls-1" d="([^"]+)"', src))
    body = f"""<defs>{gd}</defs>
<rect width="{W}" height="{H}" fill="{BG}" rx="6"/>
{gfloor}
<g transform="translate({W / 2 - 45} 12) scale(.18)"><g class="mk" style="transform-origin:250px 250px">{mark}</g></g>
{t(W / 2, 150, "ENGINEERED TO MAXIMIZE ENTROPY.", "cond", 34, INK, "", 'text-anchor="middle" letter-spacing="3"')}
{t(W / 2, 178, "ours stays low.", "mono", 13, DIM, "", 'text-anchor="middle" letter-spacing="2"')}"""
    css = gcss + """
.mk{animation:breathe 3s ease-in-out infinite}
@keyframes breathe{50%{transform:scale(1.06)}}
"""
    svg("footer.svg", W, H, body, css, t.used)


if __name__ == "__main__":
    hero()
    section("h-now.svg", "01", "THE DAY JOB", "WHERE THE RENT COMES FROM")
    section("h-shop.svg", "03", "THE SHOP", "TOOLS I BUILT TO BUILD REBOT")
    section("h-blog.svg", "04", "SPINUP.FAIL", "THE BLOG · EN + PT")
    timeline()
    rebot_banner()
    telemetry()
    eitri()
    footer()
