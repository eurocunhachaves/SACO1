#!/usr/bin/env python3
"""Gera os diagramas SVG (fonte/svg/*.svg) usados nos PDFs e nos cards.

As cores vêm de classes CSS (base.css, seção "diagramas"), então o mesmo SVG
assume a cor de cada parte. Textos são medidos com a fonte Inter real para
quebrar linhas com precisão.

Uso: python3 fonte/diagramas.py [p1 p2 p3 p4]
"""
import html
import math
import re
import sys
from pathlib import Path

from PIL import ImageFont

FONTE = Path(__file__).resolve().parent
OUT = FONTE / "svg"
ICONES = FONTE / "estilo" / "icons"
LUCIDE = Path("/root/build/npm/package/icons")
TTF = Path("/root/build/ttf/inter-latin-standard-normal.ttf")

_fonts = {}


def font(size, weight):
    key = (round(size * 4), weight)
    if key not in _fonts:
        f = ImageFont.truetype(str(TTF), 200)
        f.set_variation_by_axes([14, weight])
        _fonts[key] = f
    return _fonts[key]


def tw(text, size=12, weight=400):
    """largura do texto em unidades do viewBox"""
    return font(size, weight).getlength(text) * size / 200


def wrap(text, width, size=12, weight=400):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if tw(t, size, weight) <= width or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def esc(s):
    return html.escape(s, quote=False)


class SVG:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.el = []

    def add(self, s):
        self.el.append(s)
        return self

    def rect(self, x, y, w, h, r=8, cls="cl", extra=""):
        return self.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{r}" class="{cls}" {extra}/>')

    def circle(self, cx, cy, r, cls="c", extra=""):
        return self.add(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" class="{cls}" {extra}/>')

    def line(self, x1, y1, x2, y2, cls="sm", w=1.5, extra=""):
        return self.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="{cls} nf" stroke-width="{w}" stroke-linecap="round" {extra}/>')

    def path(self, d, cls="sm nf", w=1.5, extra=""):
        return self.add(f'<path d="{d}" class="{cls}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round" {extra}/>')

    def head(self, x, y, ang, size=7, cls="c"):
        """ponta de seta (triângulo) apontando no ângulo ang (graus)"""
        a = math.radians(ang)
        p1 = (x, y)
        p2 = (x - size * math.cos(a) + size * 0.55 * math.sin(a), y - size * math.sin(a) - size * 0.55 * math.cos(a))
        p3 = (x - size * math.cos(a) - size * 0.55 * math.sin(a), y - size * math.sin(a) + size * 0.55 * math.cos(a))
        return self.add(f'<polygon points="{p1[0]:.1f},{p1[1]:.1f} {p2[0]:.1f},{p2[1]:.1f} {p3[0]:.1f},{p3[1]:.1f}" class="{cls}"/>')

    def arrow(self, x1, y1, x2, y2, cls="sm", fcls="mut", w=1.6, size=7, both=False):
        ang = math.degrees(math.atan2(y2 - y1, x2 - x1))
        d = size * 0.8
        sx = x1 + (d * math.cos(math.radians(ang)) if both else 0)
        sy = y1 + (d * math.sin(math.radians(ang)) if both else 0)
        ex = x2 - d * math.cos(math.radians(ang))
        ey = y2 - d * math.sin(math.radians(ang))
        self.line(sx, sy, ex, ey, cls, w)
        self.head(x2, y2, ang, size, fcls)
        if both:
            self.head(x1, y1, ang + 180, size, fcls)
        return self

    def text(self, x, y, txt, size=12, weight=400, cls="ink", anchor="start", lh=1.28, width=None, ls=0, upper=False, italic=False):
        """texto com quebra automática; y = linha de base da 1ª linha. Retorna altura usada."""
        if upper:
            txt = txt.upper()
        lines = txt if isinstance(txt, list) else (wrap(txt, width, size, weight) if width else [txt])
        st = f'font-size="{size}" font-weight="{weight}"'
        if ls:
            st += f' letter-spacing="{ls}"'
        if italic:
            st += ' font-style="italic"'
        ts = []
        for i, ln in enumerate(lines):
            dy = 0 if i == 0 else size * lh
            ts.append(f'<tspan x="{x:.1f}" dy="{dy:.1f}">{rich(ln)}</tspan>')
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" {st} class="{cls}" text-anchor="{anchor}">{"".join(ts)}</text>')
        return len(lines) * size * lh

    def icon(self, name, x, y, size=24, cls="sc", w=2):
        p = ICONES / f"{name}.svg"
        if not p.exists():
            ICONES.mkdir(parents=True, exist_ok=True)
            p.write_text((LUCIDE / f"{name}.svg").read_text())
        s = p.read_text()
        inner = re.search(r"<svg[^>]*>(.*)</svg>", s, re.S).group(1)
        inner = re.sub(r"<!--.*?-->", "", inner, flags=re.S)
        k = size / 24
        return self.add(f'<g transform="translate({x:.1f},{y:.1f}) scale({k:.4f})" class="{cls} nf" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round">{inner}</g>')

    def svg(self):
        return (f'<svg class="dg" viewBox="0 0 {self.w} {self.h}" xmlns="http://www.w3.org/2000/svg" '
                f'font-family="Inter, Arial, sans-serif">' + "".join(self.el) + "</svg>")

    def save(self, name):
        OUT.mkdir(exist_ok=True)
        (OUT / name).write_text(self.svg())
        print("ok", name)


def rich(s):
    """**negrito** dentro de tspans"""
    s = esc(s)
    return re.sub(r"\*\*(.+?)\*\*", r'<tspan font-weight="700">\1</tspan>', s)


def ctext(svg, cx, y, txt, size=12, weight=400, cls="ink", width=None, lh=1.28, **kw):
    return svg.text(cx, y, txt, size, weight, cls, "middle", lh, width, **kw)


def block_h(txt, width, size=12, weight=400, lh=1.28):
    n = len(wrap(txt, width, size, weight))
    return n * size * lh


# =========================================================================== P1
def p1_planos():
    s = SVG(680, 290)
    cols = [
        ("Subindividual", "microscope", "Nível biológico e orgânico",
         "Fisiologia e fisiopatologia. Saúde = equilíbrio; doença = desequilíbrio, disfunção.", 48),
        ("Individual", "user", "A pessoa: ser biológico e social",
         "Aspectos biológicos + condições gerais da existência do indivíduo.", 62),
        ("Coletivo", "users", "Expressão de um processo social",
         "Trama de fatores e relações; determinantes em vários níveis de análise.", 78),
    ]
    xs = [113, 340, 567]
    cy = 104
    # faixa de expansão
    s.rect(30, 252, 620, 30, 15, "ct")
    s.text(340, 272, "EXPANSÃO DO OLHAR: DO ÓRGÃO À SOCIEDADE", 10.5, 750, "cd", "middle", ls=1.6)
    s.arrow(60, 267, 132, 267, "sc", "c", 2, 8)
    s.arrow(548, 267, 620, 267, "sc", "c", 2, 8)
    for i, (t, ic, sub, desc, r) in enumerate(cols):
        x = xs[i]
        s.circle(x, cy, r + 14, "ct")
        s.circle(x, cy, r, ["cl", "cm", "cd"][i])
        icls = "scd" if i == 0 else "sw"
        isz = 30 + i * 8
        s.icon(ic, x - isz / 2, cy - isz / 2 - 6, isz, icls, 1.8)
        ctext(s, x, cy + isz / 2 + 10, t.upper(), 9.5 + i * 0.6, 800, "cd" if i == 0 else "w", ls=1.2)
        if i < 2:
            s.text((xs[i] + xs[i + 1]) / 2, cy + 8, "+", 26, 300, "c", "middle")
        ctext(s, x, 200, sub, 12.4, 750, "ink", width=210)
        ctext(s, x, 218, desc, 10.6, 400, "ink2", width=206, lh=1.3)
    s.save("p1-planos.svg")


def p1_linha_modelos():
    s = SVG(680, 274)
    items = [
        ("Antiguidade", "Mágico-religioso", "deuses: dádiva × castigo", "sparkles"),
        ("séc. V a.C.", "Hipócrates", "causas naturais, humores", "scroll"),
        ("séc. XVIII–XIX", "Miasmático", "ar corrompido, sujeira", "wind"),
        ("1890", "Microbiano", "uma causa, uma doença", "microscope"),
        ("séc. XX", "Biomédico", "linear, curativo, hospital", "stethoscope"),
        ("anos 1950–70", "Processual (HND)", "agente, hospedeiro, meio", "repeat-2"),
        ("fim do séc. XX", "Sistêmico", "níveis interligados", "network"),
        ("anos 1970–80", "Determinação social", "organização da sociedade", "landmark"),
    ]
    n = len(items)
    x0, x1, y = 80, 600, 135
    s.rect(x0 - 14, y - 4, x1 - x0 + 28, 8, 4, "cl")
    step = (x1 - x0) / (n - 1)
    for i, (when, name, idea, ic) in enumerate(items):
        x = x0 + i * step
        up = i % 2 == 0
        s.circle(x, y, 15, "c" if i not in (1,) else "cm")
        s.icon(ic, x - 9, y - 9, 18, "sw", 2)
        if up:
            s.line(x, y - 16, x, y - 34, "scl", 1.4)
            s.text(x, 34, when, 10.2, 700, "c", "middle")
            ctext(s, x, 52, name, 12.2, 800, "ink", width=150)
            ctext(s, x, 68 + (15 if tw(name, 12.2, 800) > 150 else 0), idea, 10.4, 400, "ink2", width=140)
        else:
            s.line(x, y + 16, x, y + 34, "scl", 1.4)
            s.text(x, 188, when, 10.2, 700, "c", "middle")
            ctext(s, x, 206, name, 12.2, 800, "ink", width=150)
            ctext(s, x, 222 + (15 if tw(name, 12.2, 800) > 150 else 0), idea, 10.4, 400, "ink2", width=140)
    s.text(640, 266, "Hipócrates não está nos slides; aparece aqui como ponte para as causas naturais.", 9.2, 400, "mut", "end", italic=True)
    s.save("p1-linha-modelos.svg")


def p1_biomedico():
    s = SVG(680, 330)
    cx, cy = 340, 160
    sats = [("Individual", "user", "o paciente isolado"), ("Curativo", "pill", "age depois da doença"),
            ("Centrado no médico", "stethoscope", "paciente passivo"), ("Fragmentado", "puzzle", "corpo em partes"),
            ("Especialista", "microscope", "alta tecnologia"), ("Hospitalocêntrico", "hospital", "o hospital no centro")]
    R = 128
    for i, (t, ic, d) in enumerate(sats):
        a = math.radians(-90 + i * 60)
        x, y = cx + R * 1.78 * math.cos(a), cy + R * 1.02 * math.sin(a)
        s.line(cx + 70 * math.cos(a), cy + 56 * math.sin(a), x - 46 * math.cos(a), y - 28 * math.sin(a), "scl", 2)
        s.rect(x - 92, y - 28, 184, 56, 28, "ct")
        s.circle(x - 64, y, 20, "c")
        s.icon(ic, x - 76, y - 12, 24, "sw", 2)
        s.text(x - 38, y - 3, t, 12.4, 800, "ink")
        s.text(x - 38, y + 13, d, 10.2, 400, "ink2")
    s.circle(cx, cy, 76, "cd")
    ctext(s, cx, cy - 26, "MODELO", 9.5, 700, "w", ls=2)
    ctext(s, cx, cy - 6, "BIOMÉDICO", 15, 850, "w", ls=1)
    s.rect(cx - 58, cy + 8, 116, 40, 8, "c")
    ctext(s, cx, cy + 23, "causa → lesão → doença", 9.2, 600, "w")
    ctext(s, cx, cy + 38, "lógica linear", 9.2, 400, "w", italic=True)
    s.save("p1-biomedico.svg")


def p1_hnd():
    s = SVG(680, 346)
    # cabeçalhos dos períodos
    xm = 236
    s.rect(14, 10, xm - 22, 34, 8, "cd")
    ctext(s, 14 + (xm - 22) / 2, 32, "PERÍODO PRÉ-PATOGÊNICO", 10.5, 800, "w", ls=1.2)
    s.rect(xm + 2, 10, 664 - xm, 34, 8, "c")
    ctext(s, xm + 2 + (664 - xm) / 2, 32, "PERÍODO PATOGÊNICO", 10.5, 800, "w", ls=1.2)
    s.text(14 + (xm - 22) / 2, 58, "(epidemiológico) · antes da doença", 9, 500, "mut", "middle")
    s.text(xm + 2 + (664 - xm) / 2, 58, "(patológico) · a doença no hospedeiro", 9, 500, "mut", "middle")
    # tríade
    tx, ty = 125, 132
    pts = [(tx, ty - 44, "Agente"), (tx - 66, ty + 36, "Hospedeiro"), (tx + 66, ty + 36, "Meio")]
    for (a, b) in ((0, 1), (1, 2), (2, 0)):
        s.line(pts[a][0], pts[a][1], pts[b][0], pts[b][1], "sc", 2)
    for (x, y, t) in pts:
        s.circle(x, y, 27, "cl")
        ctext(s, x, y + 4, t, 9.4 if len(t) > 6 else 10, 750, "cd")
    ctext(s, tx, ty + 6, "interação", 8.6, 500, "ink2", italic=True)
    ctext(s, tx, 204, "Estímulo: a tríade interage antes de qualquer lesão.", 9.8, 400, "ink2", width=200)
    # curva da doença
    gx0, gx1, base = xm + 22, 652, 190
    s.line(gx0, base, gx1, base, "sm", 1.2)
    s.line(gx0, 74, gx0, base, "sm", 1.2)
    # horizonte clínico
    hy = 142
    s.line(gx0, hy, gx1, hy, "s2", 1.4, 'stroke-dasharray="5 4"')
    s.text(gx1, hy - 5, "horizonte clínico", 8.8, 700, "c2", "end")
    d = f"M{gx0+4},{base-4} C{gx0+90},{base-6} {gx0+150},{base-30} {gx0+205},{hy} S{gx0+300},{98} {gx0+360},{96}"
    s.path(d, "scd nf", 3)
    steps = [(gx0 + 30, base - 12, "interação\nagente-hospedeiro"), (gx0 + 130, base - 30, "alterações\nprecoces"),
             (gx0 + 245, 118, "sinais e\nsintomas"), (gx0 + 345, 104, "cura, cronicidade,\ninvalidez ou morte")]
    for (x, y, t) in steps:
        s.circle(x, y + (0 if y < base - 20 else 0), 3.6, "cd")
    s.text(gx0 + 4, base + 16, ["interação", "agente-hospedeiro"], 9.2, 500, "ink2")
    s.text(gx0 + 108, base + 16, ["alterações precoces", "(subclínico)"], 9.2, 500, "ink2")
    s.text(gx0 + 236, 104, ["sinais e", "sintomas"], 9.2, 500, "ink2", "end")
    s.text(gx1, 78, ["desfecho: cura, cronicidade,", "invalidez ou morte"], 9.2, 500, "ink2", "end")
    # níveis de prevenção
    y0 = 262
    lv = [("Promoção da saúde", "medidas gerais", 14, 118), ("Proteção específica", "vacina, saneamento", 138, 108),
          ("Diagnóstico precoce e tratamento imediato", "rastreamento", 252, 166), ("Limitação da incapacidade", "evitar sequelas", 424, 110),
          ("Reabilitação", "reinserção social", 540, 126)]
    groups = [("PREVENÇÃO PRIMÁRIA", 14, 232, "cd"), ("PREVENÇÃO SECUNDÁRIA", 252, 282, "c"), ("PREVENÇÃO TERCIÁRIA", 540, 126, "cm")]
    for (t, x, w, c) in groups:
        s.rect(x, y0 - 34, w, 24, 6, c)
        ctext(s, x + w / 2, y0 - 18, t, 8.8, 800, "w", ls=0.7)
    for i, (t, sub, x, w) in enumerate(lv):
        s.rect(x, y0, w, 78, 8, "ct")
        s.circle(x + 16, y0 + 18, 10, ["cd", "cd", "c", "c", "cm"][i])
        ctext(s, x + 16, y0 + 22, str(i + 1), 10, 800, "w")
        s.text(x + 32, y0 + 22, t, 9.8, 750, "ink", width=w - 38)
        s.text(x + 10, y0 + 66, sub, 8.8, 500, "mut", width=w - 14)
    s.save("p1-hnd.svg")


def p1_sistemico_dengue():
    s = SVG(680, 345)
    lv = [("Fatores políticos e socioeconômicos", "planejamento urbano e condições de moradia", "landmark", "cd"),
          ("Fatores culturais", "armazenamento de água em local impróprio ou sem manutenção; descarte indevido do lixo", "house", "c"),
          ("Fatores ambientais", "proliferação de mosquitos do gênero Aedes aegypti", "droplets", "cm"),
          ("Agentes patogênicos", "vírus da dengue (DENV-1, DENV-2, DENV-3 ou DENV-4)", "virus", "c2")]
    x, w, h, gap = 20, 420, 58, 22
    for i, (t, d, ic, c) in enumerate(lv):
        y = 18 + i * (h + gap)
        s.rect(x, y, w, h, 10, "ct")
        s.rect(x, y, 62, h, 10, c)
        s.rect(x + 50, y, 14, h, 0, c)
        s.icon(ic, x + 17, y + h / 2 - 14, 28, "sw", 2)
        s.text(x + 78, y + 23, t, 12.4, 800, "ink")
        s.text(x + 78, y + 40, d, 10.3, 400, "ink2", width=w - 90)
        if i < 3:
            yy = y + h
            s.arrow(x + 210, yy + 2, x + 210, yy + gap - 2, "sc", "c", 2, 6.5, both=True)
    # lado direito: ciclo
    cx, cy = 560, 150
    s.circle(cx, cy - 62, 38, "cl")
    s.icon("user", cx - 16, cy - 80, 32, "scd", 2)
    ctext(s, cx, cy - 32 + 24, "pessoa infectada", 10.6, 700, "cd")
    s.circle(cx, cy + 82, 38, "cl")
    s.icon("bug", cx - 16, cy + 64, 32, "scd", 2)
    ctext(s, cx, cy + 82 + 54, "novos mosquitos", 10.6, 700, "cd")
    s.path(f"M{cx+44},{cy-44} C{cx+86},{cy-10} {cx+86},{cy+30} {cx+46},{cy+62}", "sc nf", 2)
    s.head(cx + 46, cy + 62, 130, 8, "c")
    s.path(f"M{cx-44},{cy+64} C{cx-86},{cy+30} {cx-86},{cy-10} {cx-46},{cy-42}", "sc nf", 2)
    s.head(cx - 46, cy - 42, -50, 8, "c")
    ctext(s, cx, cy + 14, "picada", 10, 600, "mut", italic=True)
    s.line(448, 150, 506, 150, "scl", 2, 'stroke-dasharray="3 4"')
    s.text(20, 338, "Setas duplas: cada nível influencia e é influenciado pelos demais (interdependência).", 10, 500, "mut")
    s.save("p1-sistemico-dengue.svg")


def p1_mapa():
    s = SVG(680, 380)
    cx, cy = 340, 190
    branches = [
        ("Definições", ["conceito negativo", "OMS 1948: completo bem-estar", "ampliado: 8ª CNS, CF88, Lei 8.080"], 122, 66, "cd"),
        ("Planos (Narvai)", ["subindividual: órgão", "individual: pessoa", "coletivo: processo social"], 558, 66, "c"),
        ("Modelos explicativos", ["mágico-religioso · miasmático", "microbiano · biomédico", "processual (HND) · sistêmico"], 122, 314, "cm"),
        ("Modelos de atenção", ["sanitarista (campanhas)", "médico-assistencial privatista", "alternativos: vigilância, ESF"], 558, 314, "c2"),
    ]
    for (t, items, x, y, c) in branches:
        s.path(f"M{cx},{cy} C{(cx+x)/2},{cy} {(cx+x)/2},{y} {x + (110 if x < cx else -110)},{y}", "scl nf", 3)
    s.circle(cx, cy, 62, "cd")
    ctext(s, cx, cy - 6, "CONCEITO", 11, 800, "w", ls=1.5)
    ctext(s, cx, cy + 12, "DE SAÚDE", 11, 800, "w", ls=1.5)
    for (t, items, x, y, c) in branches:
        bw = 236
        bx = x - bw / 2
        s.rect(bx, y - 56, bw, 112, 12, "ct")
        s.rect(bx, y - 56, bw, 30, 12, c)
        s.rect(bx, y - 38, bw, 12, 0, c)
        ctext(s, x, y - 36, t, 12.4, 800, "w")
        for k, it in enumerate(items):
            s.text(bx + 14, y - 4 + k * 19, "• " + it, 10.8, 500, "ink")
    s.save("p1-mapa.svg")


def build_p1():
    p1_planos(); p1_linha_modelos(); p1_biomedico(); p1_hnd(); p1_sistemico_dengue(); p1_mapa()



# =========================================================================== P2
def arc_path(cx, cy, r, a0, a1):
    """arco de a0 a a1 (graus, 0 = direita, 90 = topo), sentido anti-horário visual"""
    x0, y0 = cx + r * math.cos(math.radians(a0)), cy - r * math.sin(math.radians(a0))
    x1, y1 = cx + r * math.cos(math.radians(a1)), cy - r * math.sin(math.radians(a1))
    large = 1 if abs(a1 - a0) > 180 else 0
    sweep = 1 if a1 < a0 else 0
    return f"M{x0:.1f},{y0:.1f} A{r},{r} 0 {large} {sweep} {x1:.1f},{y1:.1f}"


def ring_sector(cx, cy, r0, r1, a0, a1):
    """setor de anel entre raios r0<r1 e ângulos a0>a1 (graus)"""
    p = lambda r, a: (cx + r * math.cos(math.radians(a)), cy - r * math.sin(math.radians(a)))
    (x0, y0), (x1, y1) = p(r1, a0), p(r1, a1)
    (x2, y2), (x3, y3) = p(r0, a1), p(r0, a0)
    large = 1 if abs(a0 - a1) > 180 else 0
    return (f"M{x0:.1f},{y0:.1f} A{r1},{r1} 0 {large} 1 {x1:.1f},{y1:.1f} "
            f"L{x2:.1f},{y2:.1f} A{r0},{r0} 0 {large} 0 {x3:.1f},{y3:.1f} Z")


def curved_text(s, pid, cx, cy, r, a0, a1, txt, size, weight, cls, ls=1.5):
    s.add(f'<path id="{pid}" d="{arc_path(cx, cy, r, a0, a1)}" fill="none"/>')
    s.add(f'<text font-size="{size}" font-weight="{weight}" class="{cls}" letter-spacing="{ls}">'
          f'<textPath href="#{pid}" startOffset="50%" text-anchor="middle">{esc(txt)}</textPath></text>')


DW_SETORES = ["Produção agrícola e de alimentos", "Educação", "Ambiente de trabalho", None, None, None,
              "Desemprego", "Água e esgoto", "Serviços sociais de saúde", "Habitação"]


def p2_dahlgren(hide=None, name="p2-dahlgren.svg", uid="dw"):
    """Modelo de Dahlgren e Whitehead redesenhado. hide = camada a ocultar (cards de oclusão)."""
    s = SVG(620, 352)
    cx, cy = 310, 334
    R = dict(core=80, estilo=114, redes=150, cond=254, macro=304)
    Q = lambda key: hide == key
    n = len(DW_SETORES)
    step = 180 / n
    s.path(ring_sector(cx, cy, R["cond"], R["macro"], 180, 0), "cd", 0)
    for i, lab in enumerate(DW_SETORES):
        if lab is None:
            continue
        a0, a1 = 180 - i * step, 180 - (i + 1) * step
        s.path(ring_sector(cx, cy, R["redes"] + 2, R["cond"] - 2, a0 - 0.6, a1 + 0.6), ("cm" if i % 2 == 0 else "c") + " sw", 1.2)
    s.path(ring_sector(cx, cy, R["redes"] + 2, R["cond"] - 2, 180 - 3 * step - 0.6, 180 - 6 * step + 0.6), "cl sw", 1.2)
    s.path(ring_sector(cx, cy, R["estilo"], R["redes"], 180, 0), "c2", 0)
    s.path(ring_sector(cx, cy, R["core"], R["estilo"], 180, 0), "cl", 0)
    semi = f'M{cx-R["core"]},{cy} A{R["core"]},{R["core"]} 0 0 1 {cx+R["core"]},{cy} Z'
    s.add(f'<path d="{semi}" class="w"/>')
    s.add(f'<path d="{semi}" class="sc nf" stroke-width="1.5"/>')
    if not Q("macro"):
        curved_text(s, uid + "m", cx, cy, (R["cond"] + R["macro"]) / 2 - 5, 176, 4, "CONDIÇÕES SOCIOECONÔMICAS, CULTURAIS E AMBIENTAIS GERAIS", 13.2, 800, "w", 1.6)
    if not Q("cond"):
        curved_text(s, uid + "c", cx, cy, R["cond"] - 34, 124, 56, "CONDIÇÕES DE VIDA", 11.8, 800, "cd", 1.2)
        curved_text(s, uid + "c2", cx, cy, R["cond"] - 52, 122, 58, "E DE TRABALHO", 11.8, 800, "cd", 1.2)
    if not Q("redes"):
        curved_text(s, uid + "r", cx, cy, (R["estilo"] + R["redes"]) / 2 - 4, 168, 12, "REDES SOCIAIS E COMUNITÁRIAS", 12.4, 800, "w", 2.2)
    if not Q("estilo"):
        curved_text(s, uid + "e", cx, cy, (R["core"] + R["estilo"]) / 2 - 4, 160, 20, "ESTILO DE VIDA DOS INDIVÍDUOS", 10.6, 800, "cd", 1.4)
    if not Q("core"):
        s.icon("users", cx - 18, cy - 72, 36, "scd", 1.6)
        ctext(s, cx, cy - 25, ["Idade, sexo e", "fatores hereditários"], 11, 750, "cd", lh=1.2)
    # setores: rótulos radiais (de fora para dentro à esquerda, de dentro para fora à direita)
    rm = (R["redes"] + R["cond"]) / 2 + 1
    for i, lab in enumerate(DW_SETORES):
        if lab is None or Q("setores") or Q(f"s{i}"):
            continue
        th = 180 - (i + 0.5) * step
        x, y = cx + rm * math.cos(math.radians(th)), cy - rm * math.sin(math.radians(th))
        rot = 180 - th if th > 90 else -th
        lines = wrap(lab, 86, 10.2, 700)
        y0 = -(len(lines) - 1) * 6.1 + 3.6
        s.add(f'<g transform="translate({x:.1f},{y:.1f}) rotate({rot:.1f})">')
        ctext(s, 0, y0, lines, 10.2, 700, "w", lh=1.2)
        s.add('</g>')
    # máscaras de oclusão: a própria faixa fica roxa, com "?"
    if hide:
        mk = {
            "macro": (ring_sector(cx, cy, R["cond"] + 3, R["macro"] - 3, 179, 1), cy - (R["cond"] + R["macro"]) / 2),
            "cond": (ring_sector(cx, cy, R["redes"] + 5, R["cond"] - 5, 180 - 3 * step - 1, 180 - 6 * step + 1), cy - (R["redes"] + R["cond"]) / 2),
            "redes": (ring_sector(cx, cy, R["estilo"] + 3, R["redes"] - 3, 179, 1), cy - (R["estilo"] + R["redes"]) / 2),
            "estilo": (ring_sector(cx, cy, R["core"] + 3, R["estilo"] - 3, 179, 1), cy - (R["core"] + R["estilo"]) / 2),
            "core": (f'M{cx-R["core"]+4},{cy} A{R["core"]-4},{R["core"]-4} 0 0 1 {cx+R["core"]-4},{cy} Z', cy - 34),
        }
        d, qy = mk[hide]
        s.add(f'<path d="{d}" class="pv"/>')
        ctext(s, cx, qy + 7, "?", 20, 800, "w")
    s.line(cx - R["macro"] - 4, cy, cx + R["macro"] + 4, cy, "sr", 1.5)
    s.save(name)


def p2_diderichsen():
    s = SVG(680, 330)
    # contexto
    s.rect(14, 16, 150, 298, 12, "cd")
    ctext(s, 89, 52, ["Contexto", "social"], 13.5, 800, "w", lh=1.15)
    ctext(s, 89, 268, ["Contexto", "das políticas"], 13.5, 800, "w", lh=1.15)
    s.arrow(44, 92, 44, 234, "sw", "w", 3, 10, both=True)
    ctext(s, 104, 158, ["mecanismos", "que geram", "estratificação", "social"], 10, 600, "w", lh=1.25, italic=True)
    bx, bw = 268, 244
    rows = [("Posição social", 26), ("Exposição específica", 108), ("Doença ou acidente", 180), ("Consequências sociais ou mau estado de saúde", 252)]
    for t, y in rows:
        h = 52 if y == 252 else 44
        s.rect(bx, y, bw, h, 10, "ct")
        s.rect(bx, y, 8, h, 4, "c")
        ctext(s, bx + bw / 2 + 4, y + (h / 2) + 5 - (7 if y == 252 else 0), wrap(t, 214, 12.4, 750), 12.4, 750, "ink", lh=1.15)
    mid = (166 + bx - 4) / 2
    # I: contexto -> posição
    s.arrow(166, 48, bx - 4, 48, "sc", "c", 2.4, 9)
    s.circle(mid, 48, 13, "c2"); ctext(s, mid, 53, "I", 12, 800, "w")
    # II: posição -> exposição
    s.arrow(bx + 60, 72, bx + 60, 106, "sc", "c", 2.4, 9)
    s.circle(bx + 60, 89, 13, "c2"); ctext(s, bx + 60, 94, "II", 11, 800, "w")
    s.arrow(bx + 60, 154, bx + 60, 178, "sc", "c", 2.4, 9)
    s.arrow(bx + 60, 226, bx + 60, 250, "sc", "c", 2.4, 9)
    # III e IV: da posição para baixo, pela direita
    rx = bx + bw + 36
    s.path(f"M{bx+bw},{48} L{rx},{48} L{rx},{240} L{bx+64},{240}", "sc nf", 2.4)
    s.path(f"M{rx},{166} L{bx+64},{166}", "sc nf", 2.4)
    s.head(bx + 62, 166, 180, 9, "c")
    s.head(bx + 62, 240, 180, 9, "c")
    s.circle(rx, 120, 14, "c2"); ctext(s, rx, 125, "III", 10.5, 800, "w")
    s.circle(rx, 205, 14, "c2"); ctext(s, rx, 210, "IV", 10.5, 800, "w")
    # volta: consequências -> contexto das políticas
    s.arrow(bx - 2, 286, 168, 286, "sc", "c", 2.4, 9)
    s.circle(mid, 286, 13, "c2"); ctext(s, mid, 291, "I", 12, 800, "w")
    s.text(rx + 20, 118, ["vulnerabilidade", "diferencial"], 10.2, 600, "ink2")
    s.text(rx + 20, 203, ["consequências", "diferenciais"], 10.2, 600, "ink2")
    s.text(bx + 76, 92, "exposição diferencial", 10.2, 600, "ink2")
    for lab in ("vulnerabilidade", "consequências"):
        if rx + 20 + tw(lab, 10.2, 600) > 676:
            print("  aviso: rótulo cortado no Diderichsen:", lab)
    s.save("p2-diderichsen.svg")


def p2_lalonde():
    s = SVG(680, 300)
    q = [("Biologia humana", "genética, envelhecimento, funcionamento do corpo", "dna", "cd"),
         ("Estilo de vida", "decisões individuais: fumo, dieta, sedentarismo", "bike", "c"),
         ("Ambiente", "físico e social, fora do controle do indivíduo", "tree-pine", "cm"),
         ("Organização da assistência", "quantidade, qualidade e acesso aos serviços de saúde", "hospital", "c2")]
    s.text(14, 22, "O CAMPO DA SAÚDE: 4 COMPONENTES", 10, 800, "c", ls=1.2)
    bw, bh = 170, 128
    for i, (t, d, ic, c) in enumerate(q):
        x = 14 + (i % 2) * (bw + 8)
        y = 34 + (i // 2) * (bh + 8)
        s.rect(x, y, bw, bh, 14, c)
        s.icon(ic, x + 14, y + 14, 26, "sw", 2)
        s.text(x + 14, y + 64, t, 12.4, 800, "w", width=bw - 26)
        nl = len(wrap(t, bw - 26, 12.4, 800))
        s.text(x + 14, y + 86 + (nl - 1) * 15, d, 9.8, 500, "w", width=bw - 26, lh=1.3)
    gx = 392
    s.text(gx, 22, "O DIAGNÓSTICO DE LALONDE (CANADÁ, 1974)", 10, 800, "c", ls=1.2)
    bars = [("Para onde ia o gasto", [("serviços de saúde", 0.9, "c2"), ("", 0.1, "cl")]),
            ("De onde vinham as principais causas", [("biologia, ambiente e estilo de vida", 0.8, "c"), ("", 0.2, "cl")])]
    y = 56
    for t, parts in bars:
        s.text(gx, y, t, 11.4, 750, "ink")
        x = gx
        for lab, frac, c in parts:
            w = 270 * frac - 2
            s.rect(x, y + 10, w, 30, 7, c)
            if lab:
                s.text(x + 10, y + 30, lab, 10.2, 700, "w")
            x += w + 4
        y += 72
    s.text(gx, 214, ["Esquema qualitativo, sem escala: quase todo", "o gasto ia para a assistência médica, mas as", "causas de doença e morte estavam sobretudo", "nos outros três componentes."], 10.2, 400, "ink2", lh=1.38)
    s.save("p2-lalonde.svg")


def p2_iceberg():
    s = SVG(680, 330)
    wl = 112  # linha d'água
    s.rect(0, wl, 680, 330 - wl, 0, "ct")
    s.path(f"M0,{wl} Q85,{wl-6} 170,{wl} T340,{wl} T510,{wl} T680,{wl}", "scm nf", 2)
    # ponta
    s.add(f'<polygon points="206,{wl} 256,40 286,58 308,30 366,{wl}" class="w"/>')
    s.add(f'<polygon points="206,{wl} 256,40 286,58 308,30 366,{wl}" class="scd nf" stroke-width="2"/>')
    # base
    s.add(f'<polygon points="206,{wl} 366,{wl} 468,200 424,300 170,312 86,236" class="cl"/>')
    s.add(f'<polygon points="206,{wl} 366,{wl} 468,200 424,300 170,312 86,236" class="scm nf" stroke-width="2"/>')
    ctext(s, 286, 92, "comportamentos", 11.4, 800, "cd")
    for i, t in enumerate(["renda e trabalho", "moradia e saneamento", "escolaridade", "redes de apoio", "cultura e propaganda", "políticas econômicas"]):
        ctext(s, 276, 150 + i * 25, t, 11.2, 700, "cd")
    s.text(400, 46, "ENFOQUE COMPORTAMENTAL", 10.4, 800, "c2", ls=1.2)
    s.text(400, 66, ["Vê só o que está acima da água:", "fumo, dieta, sedentarismo.", "Ação: educar o indivíduo."], 10.6, 500, "ink2", lh=1.32)
    s.text(500, 176, "ENFOQUE SOCIOAMBIENTAL", 10.4, 800, "cd", ls=1.2)
    s.text(500, 196, ["Mergulha nos determinantes", "que produzem os", "comportamentos.", "Ação: políticas públicas", "e intersetorialidade."], 10.6, 500, "ink2", lh=1.32)
    s.save("p2-iceberg.svg")


def p2_almaata():
    s = SVG(680, 250)
    it = [("Educação em saúde", "problemas prevalentes, prevenção e controle", "graduation-cap"),
          ("Alimentação e nutrição", "suprimento de alimentos e nutrição adequada", "apple"),
          ("Água e saneamento", "abastecimento de água e saneamento básico", "droplets"),
          ("Saúde materno-infantil", "inclusive planejamento familiar", "baby"),
          ("Imunização", "contra as principais doenças infecciosas", "syringe"),
          ("Doenças endêmicas", "prevenção e controle", "bug"),
          ("Tratamento", "de doenças e lesões comuns", "stethoscope"),
          ("Medicamentos essenciais", "fornecimento", "pill")]
    w, h = 158, 104
    for i, (t, d, ic) in enumerate(it):
        x = 14 + (i % 4) * (w + 8)
        y = 14 + (i // 4) * (h + 10)
        s.rect(x, y, w, h, 12, "ct")
        s.circle(x + 26, y + 28, 17, "c")
        s.icon(ic, x + 15, y + 17, 22, "sw", 2)
        ctext(s, x + 26, y + 33 - 22, "", 1, 400)
        s.text(x + 50, y + 25, str(i + 1), 11, 800, "c")
        s.text(x + 12, y + 64, t, 11.6, 800, "ink", width=w - 20)
        s.text(x + 12, y + 80 + (13 if tw(t, 11.6, 800) > w - 20 else 0), d, 9.6, 500, "ink2", width=w - 18)
    s.save("p2-almaata.svg")


def p2_ottawa():
    s = SVG(680, 400)
    cx, cy = 340, 206
    campos = [("Políticas públicas saudáveis", "legislação, impostos, saúde na agenda de todos os setores", "landmark"),
              ("Ambientes favoráveis", "condições de vida e trabalho seguras e agradáveis", "tree-pine"),
              ("Reforço da ação comunitária", "poder e controle das comunidades", "users"),
              ("Desenvolvimento de habilidades pessoais", "informação, educação para a saúde", "graduation-cap"),
              ("Reorientação dos serviços de saúde", "além do clínico: promover, respeitar a cultura", "hospital")]
    R = 150
    for i, (t, d, ic) in enumerate(campos):
        a = math.radians(90 - i * 72)
        x, y = cx + R * 1.42 * math.cos(a), cy - R * 0.98 * math.sin(a)
        s.line(cx, cy, x, y, "scl", 3)
        bw, bh = 196, 78
        bx, by = x - bw / 2, y - bh / 2
        s.rect(bx, by, bw, bh, 14, "ct")
        s.rect(bx, by, 6, bh, 3, "c")
        s.circle(bx + 28, by + 24, 15, "c")
        s.icon(ic, bx + 18, by + 14, 20, "sw", 2)
        s.text(bx + 50, by + 22, f"{i+1}. " + t, 11.2, 800, "ink", width=bw - 58)
        nl = len(wrap(f"{i+1}. " + t, bw - 58, 11.2, 800))
        s.text(bx + 14, by + 48 + (nl - 1) * 11, d, 9.4, 500, "ink2", width=bw - 24)
    s.circle(cx, cy, 64, "cd")
    ctext(s, cx, cy - 28, "3 ESTRATÉGIAS", 8.8, 800, "c2", ls=1)
    for k, t in enumerate(["defesa de causa", "capacitação", "mediação"]):
        ctext(s, cx, cy - 8 + k * 17, t, 11, 700, "w")
    s.text(14, 392, "Pré-requisitos: paz · habitação · educação · alimentação · renda · ecossistema estável · recursos sustentáveis · justiça social e equidade", 9.8, 600, "cd")
    s.save("p2-ottawa.svg")


def p2_conferencias():
    s = SVG(680, 300)
    items = [("1986", "Ottawa", "Canadá", "Carta de Ottawa: conceito e 5 campos"),
             ("1988", "Adelaide", "Austrália", "políticas públicas saudáveis"),
             ("1991", "Sundsvall", "Suécia", "ambientes favoráveis"),
             ("1997", "Jacarta", "Indonésia", "reforço da ação comunitária"),
             ("2000", "México", "Cidade do México", "reduzir a lacuna de equidade"),
             ("2005", "Bangkok", "Tailândia", "promoção num mundo globalizado"),
             ("2009", "Nairóbi", "Quênia", "fechar a lacuna de implementação"),
             ("2013", "Helsinque", "Finlândia", "Saúde em Todas as Políticas"),
             ("2016", "Xangai", "China", "desenvolvimento sustentável"),
             ("2021", "Genebra", "Suíça (virtual)", "bem-estar, equidade, sustentabilidade")]
    x0, x1, y = 58, 622, 150
    s.rect(x0 - 16, y - 5, x1 - x0 + 32, 10, 5, "cl")
    st = (x1 - x0) / (len(items) - 1)
    for i, (yr, city, country, theme) in enumerate(items):
        x = x0 + i * st
        up = i % 2 == 0
        s.circle(x, y, 13, "cd" if i == 0 else "c")
        ctext(s, x, y + 4, ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"][i], 9 if i < 7 else 8, 800, "w")
        if up:
            s.line(x, y - 14, x, y - 30, "scl", 1.4)
            ctext(s, x, 30, yr, 10.6, 800, "c")
            ctext(s, x, 46, city, 12, 800, "ink")
            ctext(s, x, 60, country, 9.4, 500, "mut")
            ctext(s, x, 76, theme, 9.8, 500, "ink2", width=104)
        else:
            s.line(x, y + 14, x, y + 30, "scl", 1.4)
            ctext(s, x, 200, yr, 10.6, 800, "c")
            ctext(s, x, 216, city, 12, 800, "ink")
            ctext(s, x, 230, country, 9.4, 500, "mut")
            ctext(s, x, 246, theme, 9.8, 500, "ink2", width=104)
    s.text(340, 292, "Conferências internacionais (globais) de promoção da saúde. Regionais: Santafé de Bogotá (1992) e Caribe (1993).", 9.4, 500, "mut", "middle")
    s.save("p2-conferencias.svg")


def p2_pnps_temas():
    s = SVG(680, 252)
    it = [("Formação e educação permanente", "graduation-cap"), ("Alimentação adequada e saudável", "apple"),
          ("Práticas corporais e atividades físicas", "bike"), ("Enfrentamento do uso do tabaco e derivados", "cigarette"),
          ("Enfrentamento do uso abusivo de álcool e outras drogas", "wine"), ("Promoção da mobilidade segura", "car"),
          ("Promoção da cultura da paz e dos direitos humanos", "hand-heart"), ("Promoção do desenvolvimento sustentável", "sprout")]
    grp = ["cd", "c", "c", "c2", "c2", "cm", "cm", "cm"]
    w, h = 158, 112
    for i, (t, ic) in enumerate(it):
        x = 14 + (i % 4) * (w + 8)
        y = 10 + (i // 4) * (h + 12)
        s.rect(x, y, w, h, 12, "ct")
        s.circle(x + 30, y + 32, 20, grp[i])
        s.icon(ic, x + 17, y + 19, 26, "sw", 2)
        s.text(x + w - 14, y + 30, f"{i+1}", 20, 300, "c", "end")
        s.text(x + 14, y + 76, t, 11, 750, "ink", width=w - 24)
    s.save("p2-pnps-temas.svg")


def p2_mapa():
    s = SVG(680, 410)
    cx, cy = 340, 205
    bw, bh = 238, 104
    branches = [
        ("Origens", ["• Sigerist: 4 tarefas da medicina", "• Lalonde 1974: campo da saúde", "• Alma-Ata 1978: cuidados primários"], "L", 62, "cd"),
        ("Dois enfoques", ["• comportamental: muda o indivíduo", "• socioambiental: muda os", "   determinantes (base da PNPS)"], "L", 205, "c2"),
        ("Determinantes sociais", ["• Dahlgren e Whitehead: 5 camadas", "• 4 níveis de intervenção", "• Diderichsen: estratificação"], "L", 348, "cm"),
        ("Ottawa 1986", ["• capacitar a comunidade", "• 5 campos de ação", "• 3 estratégias e pré-requisitos"], "R", 62, "c"),
        ("Conferências", ["• Adelaide: políticas públicas", "• Sundsvall: ambientes favoráveis", "• Jacarta: ação comunitária"], "R", 205, "cm"),
        ("PNPS 2006 · 2014 · 2017", ["• objetivo: promover a equidade", "• 9 princípios e 8 valores", "• 8 temas prioritários"], "R", 348, "c2"),
    ]
    for (t, items, side, y, c) in branches:
        x = 14 + bw if side == "L" else 680 - 14 - bw
        s.path(f"M{cx},{cy} C{(cx+x)/2},{cy} {(cx+x)/2},{y} {x},{y}", "scl nf", 3)
    s.circle(cx, cy, 66, "cd")
    ctext(s, cx, cy - 8, "PROMOÇÃO", 12.4, 800, "w", ls=1.4)
    ctext(s, cx, cy + 10, "DA SAÚDE", 12.4, 800, "w", ls=1.4)
    ctext(s, cx, cy + 30, "≠ prevenção", 10.4, 700, "c2", italic=True)
    for (t, items, side, y, c) in branches:
        bx = 14 if side == "L" else 680 - 14 - bw
        s.rect(bx, y - bh / 2, bw, bh, 12, "ct")
        s.rect(bx, y - bh / 2, bw, 28, 12, c)
        s.rect(bx, y - bh / 2 + 16, bw, 12, 0, c)
        ctext(s, bx + bw / 2, y - bh / 2 + 19, t, 12.4, 800, "w")
        for k, it in enumerate(items):
            if tw(it, 10.8, 500) > bw - 24:
                print("  aviso: linha longa no mapa:", it)
            s.text(bx + 14, y - 2 + k * 18, it, 10.8, 500, "ink")
    s.save("p2-mapa.svg")


def build_p2():
    p2_dahlgren()
    for k in ("macro", "cond", "redes", "estilo", "core"):
        p2_dahlgren(hide=k, name=f"p2-dahlgren-oculta-{k}.svg", uid=f"dw{k}")
    p2_diderichsen(); p2_lalonde(); p2_iceberg(); p2_almaata(); p2_ottawa(); p2_conferencias(); p2_pnps_temas(); p2_mapa()


# =========================================================================== P3
P3_PERIODOS = [
    ("Colônia e Império", "1500–1889", "cd", ["miasmas e quarentenas", "lazareto (alvará de 1810)", "Santas Casas, medicina liberal"]),
    ("República Velha", "1889–1930", "c", ["Oswaldo Cruz (1903)", "Revolta da Vacina (1904)", "DNSP (1920) · CAPs (1923)"]),
    ("Era Vargas", "1930–1945", "cm", ["MESP (1930)", "IAPs (1933)", "SESP (1942)"]),
    ("Período democrático", "1945–1963", "c", ["Ministério da Saúde (1953)", "IAPs ampliam a assistência", "LOPS (1960)"]),
    ("Regime Militar", "1964–1984", "cd", ["INPS (1966) · MPAS (1974)", "SINPAS/INAMPS (1977)", "PIASS (1976) · AIS (1983)"]),
    ("Nova República", "1985–1988", "c2", ["8ª CNS (1986)", "SUDS (1987)", "CF 1988: nasce o SUS"]),
]


def p3_linha():
    s = SVG(680, 262)
    n = len(P3_PERIODOS)
    x0, gap = 14, 5
    bw = (652 - gap * (n - 1)) / n
    xs = [x0 + i * (bw + gap) for i in range(n)]
    # modelos dominantes (faixas superiores)
    def faixa(xa, xb, y, txt, cls, tcls):
        s.rect(xa, y, xb - xa, 24, 12, cls)
        ctext(s, (xa + xb) / 2, y + 16, txt, 10.2, 800, tcls, ls=0.6)
    s.text(x0, 14, "MODELO DOMINANTE", 8.6, 800, "mut", ls=1.4)
    faixa(xs[1], xs[3] + bw * 0.62, 22, "SANITARISMO CAMPANHISTA", "cl", "cd")
    faixa(xs[3] + bw * 0.38, xs[5] + bw * 0.55, 52, "MÉDICO-ASSISTENCIAL PRIVATISTA", "c", "w")
    s.arrow(xs[5] + bw * 0.58, 64, xs[5] + bw - 4, 64, "sc", "c", 2, 7)
    s.text(xs[5] + bw - 2, 48, "SUS", 10, 850, "c2", "end", ls=0.8)
    # faixas dos períodos
    yb = 88
    for i, (nome, anos, cls, evs) in enumerate(P3_PERIODOS):
        x = xs[i]
        s.rect(x, yb, bw, 58, 10, cls)
        ctext(s, x + bw / 2, yb + 22, nome, 11.2, 800, "w", width=bw - 12, lh=1.15)
        nl = len(wrap(nome, bw - 12, 11.2, 800))
        ctext(s, x + bw / 2, yb + 22 + nl * 12.9 + 2, anos, 9.6, 600, "w")
        # eventos
        for k, ev in enumerate(evs):
            ctext(s, x + bw / 2, yb + 82 + k * 30, ev, 9.6, 600 if k == 0 else 500, "ink" if k == 0 else "ink2", width=bw - 6, lh=1.2)
        s.line(x + bw / 2, yb + 60, x + bw / 2, yb + 68, "scl", 1.6)
    s.text(666, 256, "Períodos fora de escala, com as datas usadas nos slides da Aula 3.", 8.8, 400, "mut", "end", italic=True)
    s.save("p3-linha.svg")


def p3_dicotomia():
    s = SVG(680, 364)
    L, R, cw = 14, 380, 286
    cols = [
        (L, "c2", "AÇÕES PREVENTIVAS E COLETIVAS", "Saúde pública", "shield-plus",
         [("1903", "Oswaldo Cruz na Saúde Pública"), ("1920", "DNSP, com Carlos Chagas"),
          ("1930", "Ministério da Educação e Saúde"), ("1942", "SESP, com apoio dos EUA"),
          ("1953", "Ministério da Saúde")],
         "Sanitarismo campanhista", "campanhas contra doenças específicas, polícia sanitária, direção centralizada"),
        (R, "c", "AÇÕES CURATIVAS E INDIVIDUAIS", "Medicina previdenciária", "stethoscope",
         [("1923", "CAPs, por empresa"), ("1933", "IAPs, por categoria profissional"),
          ("1966", "INPS unifica os institutos"), ("1974", "MPAS, FAS e PPA"),
          ("1977", "INAMPS (SINPAS)")],
         "Médico-assistencial privatista", "hospital, especialista, compra de serviços privados, exclusão de quem não contribuía"),
    ]
    for (x, cls, head, sub, ic, items, model, mdesc) in cols:
        s.rect(x, 8, cw, 50, 12, cls)
        s.icon(ic, x + 14, 19, 28, "sw", 2)
        s.text(x + 52, 29, head, 10.2, 800, "w", ls=0.6)
        s.text(x + 52, 47, sub, 12.6, 700, "w")
        y = 70
        for (yr, t) in items:
            s.rect(x, y, cw, 28, 8, "ct")
            s.rect(x, y, 5, 28, 2.5, cls)
            s.text(x + 16, y + 18.5, yr, 10, 800, "cd" if cls == "c" else "c2")
            s.text(x + 66, y + 18.5, t, 10.2, 500, "ink", width=cw - 74)
            y += 32
        s.rect(x, y + 2, cw, 58, 12, "cl")
        s.text(x + 14, y + 22, model, 12.2, 800, "cd")
        s.text(x + 14, y + 39, mdesc, 9.8, 500, "ink2", width=cw - 26)
    # dicotomia no meio
    mx = (L + cw + R) / 2
    s.arrow(L + cw + 8, 136, R - 8, 136, "scd", "cd", 2.2, 8, both=True)
    s.text(mx, 126, "DICOTOMIA", 9.4, 850, "cd", "middle", ls=1)
    s.text(mx, 154, ["dois", "ministérios,", "dois", "orçamentos"], 9, 500, "mut", "middle", lh=1.2)
    # convergência no SUS
    yb = 318
    for (x, cls, *_r) in cols:
        s.arrow(x + cw / 2, 292, x + cw / 2, yb - 3, "scm", "cm", 2.4, 8)
    s.rect(110, yb, 460, 40, 20, "cd")
    ctext(s, 340, yb + 17, "SUS (1988): UM SISTEMA ÚNICO", 11.4, 850, "w", ls=0.6)
    ctext(s, 340, yb + 31, "integralidade junta prevenir e curar", 9.6, 500, "w")
    s.save("p3-dicotomia.svg")


def p3_previdencia(hide=None, name="p3-previdencia.svg"):
    s = SVG(680, 330)
    nodes = [
        ("caps", "CAPs", "1923", "building-2", "Lei Eloy Chaves",
         [("Organização", "por empresa"), ("Financiamento", "bipartite: empregados e empresa"), ("Gestão", "privada, colegiada")],
         "ferroviários; depois portuários e marítimos"),
        ("iaps", "IAPs", "1933", "users", "Era Vargas",
         [("Organização", "por categoria profissional"), ("Financiamento", "tripartite: + Estado"), ("Gestão", "semipública: Estado nomeia o presidente")],
         "marítimos, comerciários, bancários, industriários..."),
        ("inps", "INPS", "1966", "landmark", "Regime Militar",
         [("Organização", "instituto único, benefícios iguais"), ("Financiamento", "contribuições sobre a folha"), ("Gestão", "centralizada; fim da tripartite")],
         "trabalhador urbano com carteira; rurais (1971), domésticas (1972), autônomos (1973)"),
    ]
    gap, x0 = 30, 14
    w = (652 - 2 * gap) / 3
    for i, (key, nome, ano, ic, era, rows, cob) in enumerate(nodes):
        x = x0 + i * (w + gap)
        cls = ["cm", "c", "cd"][i]
        s.rect(x, 10, w, 312, 14, "ct")
        s.rect(x, 10, w, 56, 14, cls)
        s.rect(x, 50, w, 16, 0, cls)
        s.icon(ic, x + 14, 22, 30, "sw", 2)
        s.text(x + 54, 40, nome, 19, 850, "w")
        s.text(x + w - 14, 40, ano, 15, 700, "w", "end")
        s.text(x + 54, 57, era, 9.4, 600, "w")
        y = 88
        for (k, v) in rows:
            s.text(x + 14, y, k.upper(), 8.4, 800, "c" if cls != "c" else "cd", ls=0.9)
            if hide == key:
                s.rect(x + 12, y + 6, w - 24, 22, 6, "c2")
                ctext(s, x + w / 2, y + 21, "?", 13, 850, "w")
            else:
                s.text(x + 14, y + 17, v, 11.2, 650, "ink", width=w - 26)
            y += 56
        s.line(x + 14, 250, x + w - 14, 250, "sr", 1)
        s.text(x + 14, 266, "QUEM ERA COBERTO", 8.2, 800, "mut", ls=0.9)
        s.text(x + 14, 281, cob, 9.4, 500, "ink2", width=w - 24, lh=1.2)
        if i < 2:
            ax = x + w + 4
            s.arrow(ax, 160, ax + gap - 8, 160, "scd", "cd", 2.4, 8)
    s.save(name)


def p3_sinpas():
    s = SVG(680, 252)
    s.rect(250, 8, 180, 40, 10, "cd")
    ctext(s, 340, 25, "MPAS (1974)", 12.4, 850, "w")
    ctext(s, 340, 40, "Ministério da Previdência e Assistência Social", 7.8, 500, "w")
    s.line(340, 48, 340, 64, "scd", 2)
    s.rect(196, 64, 288, 34, 10, "c")
    ctext(s, 340, 86, "SINPAS (1977, Lei 6.439)", 12, 800, "w")
    org = [("INPS", "concede benefícios (aposentadorias, pensões)", True),
           ("INAMPS", "assistência médica: rede própria, contratada e conveniada", True),
           ("IAPAS", "arrecadação e gestão financeira", False),
           ("LBA", "assistência social", False),
           ("FUNABEM", "bem-estar do menor", False),
           ("DATAPREV", "processamento de dados", False),
           ("CEME", "medicamentos", False)]
    n = len(org)
    w, gap = 88, 6
    x0 = (680 - (n * w + (n - 1) * gap)) / 2
    yb = 128
    s.line(x0 + w / 2, 114, x0 + (n - 1) * (w + gap) + w / 2, 114, "scl", 2)
    s.line(340, 98, 340, 114, "scl", 2)
    for i, (sig, d, hi) in enumerate(org):
        x = x0 + i * (w + gap)
        s.line(x + w / 2, 114, x + w / 2, yb, "scl", 2)
        s.rect(x, yb, w, 112, 10, "c2" if hi else "ct")
        ctext(s, x + w / 2, yb + 22, sig, 11.4 if len(sig) < 7 else 10.2, 850, "w" if hi else "cd")
        ctext(s, x + w / 2, yb + 42, d, 9.2, 500, "w" if hi else "ink2", width=w - 10, lh=1.22)
    s.save("p3-sinpas.svg")


def p3_privatista():
    s = SVG(680, 330)
    # nós
    def node(x, y, w, h, title, desc, cls="ct", tcls="cd", dcls="ink2", ic=None):
        s.rect(x, y, w, h, 12, cls)
        tx = x + 14
        if ic:
            s.icon(ic, x + 12, y + 12, 22, "sc" if cls in ("ct", "cl") else "sw", 2)
            tx = x + 42
        s.text(tx, y + 27, title, 11.6, 800, tcls, width=w - (tx - x) - 10)
        nl = len(wrap(title, w - (tx - x) - 10, 11.6, 800))
        s.text(x + 14, y + 27 + nl * 14.8 + 2, desc, 9.6, 500, dcls, width=w - 26, lh=1.25)
    node(14, 14, 200, 86, "Trabalhadores e empresas", "contribuem sobre a folha de salários", "ct", "cd", "ink2", "briefcase")
    node(262, 14, 200, 86, "INPS / INAMPS", "o fundo da previdência paga a assistência dos segurados", "c", "w", "w", "landmark")
    node(510, 14, 156, 86, "Excluídos", "sem carteira: Santas Casas, saúde pública ou pagar do bolso", "cl", "cd", "ink2", "user-x")
    node(262, 150, 200, 92, "Hospitais e clínicas privados", "contratados ou conveniados, pagos por procedimento (unidades de serviço)", "cd", "w", "w", "hospital")
    node(14, 150, 200, 92, "FAS (1974)", "empréstimos com juros subsidiados para construir e reformar hospitais privados", "ct", "cd", "ink2", "hand-coins")
    node(510, 150, 156, 92, "PPA (1974)", "urgência em qualquer serviço: amplia os contratos privados", "ct", "cd", "ink2", "siren")
    s.arrow(214, 57, 258, 57, "scd", "cd", 2.4, 8)
    s.arrow(362, 102, 362, 146, "scd", "cd", 2.4, 8)
    s.text(372, 128, "compra serviços", 9.4, 600, "cd")
    s.arrow(214, 196, 258, 196, "scd", "cd", 2.4, 8)
    s.arrow(510, 196, 466, 196, "scd", "cd", 2.4, 8)
    # resultado
    s.rect(14, 268, 652, 52, 12, "c2")
    s.icon("trending-up", 28, 282, 24, "sw", 2)
    s.text(64, 289, "Resultado: mais procedimentos, custos crescentes e fraudes", 12, 800, "w")
    s.text(64, 307, "O dinheiro público financiou a expansão privada; a crise da previdência explode no início dos anos 1980.", 9.6, 500, "w")
    s.arrow(362, 244, 362, 264, "scd", "cd", 2.4, 8)
    s.save("p3-privatista.svg")


def p3_reforma():
    s = SVG(680, 266)
    steps = [("1976", "CEBES", "revista Saúde em Debate"),
             ("1979", "ABRASCO", "e o simpósio da Câmara"),
             ("1983", "AIS", "integra MS, INAMPS e secretarias"),
             ("1986", "8ª CNS", "marco da Reforma Sanitária"),
             ("1987", "SUDS", "convênios e estadualização"),
             ("1988", "CF 1988", "saúde: direito de todos"),
             ("1990", "Leis 8.080 e 8.142", "o SUS regulamentado")]
    n = len(steps)
    x0, w, gap = 14, 88, 6
    base = 222
    for i, (yr, t, d) in enumerate(steps):
        x = x0 + i * (w + gap)
        h = 86 + i * 20
        y = base - h
        cls = "c2" if t == "8ª CNS" else ["cl", "cl", "cm", "c2", "c", "cd", "cd"][i]
        tcls = "cd" if cls == "cl" else "w"
        s.rect(x, y, w, h, 10, cls)
        ctext(s, x + w / 2, y + 20, yr, 12.4, 850, tcls)
        ctext(s, x + w / 2, y + 38, t, 10.4 if len(t) < 10 else 9.4, 800, tcls, width=w - 8, lh=1.15)
        nl = len(wrap(t, w - 8, 10.4 if len(t) < 10 else 9.4, 800))
        ctext(s, x + w / 2, y + 38 + nl * 12.5 + 4, d, 8.6, 500, tcls, width=w - 10, lh=1.2)
    # selo do marco
    i8 = 3
    xm = x0 + i8 * (w + gap) + w / 2
    ym = base - (86 + i8 * 20) - 22
    s.rect(xm - 34, ym - 12, 68, 20, 10, "cd")
    ctext(s, xm, ym + 2, "MARCO", 9.2, 850, "w", ls=1.2)
    s.line(x0, base + 6, x0 + n * (w + gap) - gap, base + 6, "scd", 2)
    s.text(x0, base + 26, "Atores: departamentos de medicina preventiva das universidades, CEBES, ABRASCO, sindicatos, movimentos populares,", 9.4, 500, "ink2")
    s.text(x0, base + 39, "estudantes, intelectuais e parlamentares. Universalização, integralidade e descentralização eram as bandeiras.", 9.4, 500, "ink2")
    s.save("p3-reforma.svg")


def p3_endemia():
    s = SVG(680, 214)
    gx0, gx1, gy0, gy1 = 56, 470, 18, 178
    s.line(gx0, gy1, gx1, gy1, "sm", 1.4)
    s.line(gx0, gy0, gx0, gy1, "sm", 1.4)
    s.text(gx1, gy1 + 18, "tempo", 9.6, 600, "mut", "end")
    s.text(18, 24, ["nº de", "casos"], 9.6, 600, "mut")
    # faixa endêmica
    lo, hi = 132, 150
    s.rect(gx0 + 2, lo, gx1 - gx0 - 4, hi - lo, 0, "cl")
    s.line(gx0 + 2, lo - 14, gx1, lo - 14, "s2", 1.4, 'stroke-dasharray="5 4"')
    s.text(gx0 + 8, lo - 19, "limiar epidêmico", 9, 700, "c2")
    s.text(gx0 + 8, hi + 14, "nível endêmico (o esperado)", 9, 700, "cd")
    pts = [(60, 142), (84, 138), (104, 145), (126, 136), (148, 143), (170, 139), (192, 146), (214, 137),
           (236, 142), (254, 130), (270, 96), (284, 48), (298, 34), (312, 58), (326, 102), (342, 132),
           (360, 141), (382, 137), (404, 144), (426, 139), (448, 143), (466, 138)]
    d = "M" + " L".join(f"{x},{y}" for x, y in pts)
    s.path(d, "scd nf", 2.6)
    s.text(306, 26, "epidemia", 11, 800, "cd")
    # legenda à direita
    lx = 492
    defs = [("Endemia", "casos em nível constante e esperado numa região (ex.: malária na Amazônia)"),
            ("Epidemia", "aumento claro acima do esperado num período e lugar"),
            ("Surto", "epidemia restrita a um local pequeno"),
            ("Pandemia", "epidemia que atinge vários países ou continentes")]
    y = 30
    for (t, d2) in defs:
        s.text(lx, y, t, 11, 800, "cd")
        y += 14
        y += s.text(lx, y, d2, 9.4, 500, "ink2", width=176, lh=1.22) + 6
    s.save("p3-endemia.svg")


def p3_mapa():
    s = SVG(680, 346)
    cx, cy = 340, 173
    bw, bh = 238, 96
    branches = [
        ("Colônia e Império", ["• miasmas, quarentena, lazaretos", "• Santas Casas para os pobres", "• medicina liberal para a elite"], "L", 50, "cd"),
        ("República Velha", ["• Oswaldo Cruz: polícia sanitária", "• Revolta da Vacina (1904)", "• DNSP (1920) · CAPs (1923)"], "L", 173, "c"),
        ("Era Vargas e 1945–64", ["• MESP (1930) · IAPs (1933)", "• SESP (1942)", "• Ministério da Saúde (1953)"], "L", 296, "cm"),
        ("Regime Militar", ["• INPS (1966): unifica os IAPs", "• FAS e PPA (1974): setor privado", "• SINPAS/INAMPS (1977)"], "R", 50, "cd"),
        ("Crise e reformas", ["• PIASS (1976) · PREV-SAÚDE (1980)", "• CONASP (1981)", "• AIS (1983)"], "R", 173, "c"),
        ("Reforma Sanitária", ["• CEBES (1976) · ABRASCO (1979)", "• 8ª CNS (1986): o marco", "• SUDS (1987) → CF 1988"], "R", 296, "c2"),
    ]
    for (t, items, side, y, c) in branches:
        x = 14 + bw if side == "L" else 680 - 14 - bw
        s.path(f"M{cx},{cy} C{(cx+x)/2},{cy} {(cx+x)/2},{y} {x},{y}", "scl nf", 3)
    s.circle(cx, cy, 64, "cd")
    ctext(s, cx, cy - 8, "ANTES", 12.4, 800, "w", ls=1.4)
    ctext(s, cx, cy + 10, "DO SUS", 12.4, 800, "w", ls=1.4)
    ctext(s, cx, cy + 30, "1500–1988", 10.4, 700, "cl")
    for (t, items, side, y, c) in branches:
        bx = 14 if side == "L" else 680 - 14 - bw
        s.rect(bx, y - bh / 2, bw, bh, 12, "ct")
        s.rect(bx, y - bh / 2, bw, 28, 12, c)
        s.rect(bx, y - bh / 2 + 16, bw, 12, 0, c)
        ctext(s, bx + bw / 2, y - bh / 2 + 19, t, 12.4, 800, "w")
        for k, it in enumerate(items):
            if tw(it, 10.8, 500) > bw - 24:
                print("  aviso: linha longa no mapa:", it)
            s.text(bx + 14, y - 4 + k * 18, it, 10.8, 500, "ink")
    s.save("p3-mapa.svg")


def build_p3():
    p3_linha(); p3_dicotomia(); p3_previdencia(); p3_sinpas(); p3_privatista(); p3_reforma(); p3_endemia(); p3_mapa()
    for k in ("caps", "iaps", "inps"):
        p3_previdencia(hide=k, name=f"p3-previdencia-oculta-{k}.svg")



# =========================================================================== P4

def ellipse(s, cx, cy, rx, ry, cls, extra=""):
    return s.add(f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" class="{cls}" {extra}/>')


def p4_sistemas():
    s = SVG(680, 300)
    cx = 340
    ellipse(s, cx, 150, 330, 142, "ct")
    ellipse(s, cx, 150, 330, 142, "scl nf", 'stroke-width="2"')
    ctext(s, cx, 36, "SISTEMA SOCIAL", 10.8, 850, "cd", ls=1.2)
    ctext(s, cx, 53, "educação · trabalho · renda · moradia · transporte · lazer", 10, 500, "ink2")
    ellipse(s, cx, 172, 240, 110, "cl")
    ctext(s, cx, 90, "SISTEMA DE SAÚDE", 10.8, 850, "cd", ls=1.2)
    ctext(s, cx, 107, "vigilância · saneamento · promoção da saúde · ações intersetoriais", 9.8, 500, "ink2")
    ellipse(s, cx, 202, 150, 68, "c")
    ctext(s, cx, 188, "SISTEMA DE SERVIÇOS DE SAÚDE", 10.6, 850, "w", ls=0.9)
    ctext(s, cx, 206, "UBS · ambulatórios · hospitais · SAMU", 10, 600, "w")
    ctext(s, cx, 224, "respondem às necessidades da população", 9.2, 500, "w", italic=True)
    s.save("p4-sistemas.svg")


def p4_componentes():
    s = SVG(680, 214)

    def box(x, y, w, h, ic, title, sub, cls, tcls, scls):
        s.rect(x, y, w, h, 12, cls)
        s.icon(ic, x + 12, y + (h - 24) / 2, 24, "sw" if tcls == "w" else "sc", 2)
        n = len(wrap(sub, w - 56, 9.4, 500))
        top = y + h / 2 - (14 + n * 12) / 2 + 11
        s.text(x + 46, top, title, 12, 800, tcls)
        s.text(x + 46, top + 16, sub, 9.4, 500, scls, width=w - 56, lh=1.2)
    box(14, 72, 150, 66, "users", "População", "usuários do sistema", "ct", "cd", "ink2")
    box(500, 72, 166, 66, "hospital", "Prestadores", "hospitais, clínicas, profissionais", "ct", "cd", "ink2")
    box(234, 8, 212, 56, "landmark", "Estado", "financiamento público", "c", "w", "w")
    box(234, 150, 212, 56, "wallet", "Seguradoras e planos", "financiamento privado", "cl", "cd", "ink2")
    s.arrow(164, 84, 232, 46, "scm", "cm", 2, 7)
    s.arrow(448, 46, 498, 84, "scm", "cm", 2, 7)
    s.arrow(164, 126, 232, 166, "sm", "mut", 2, 7)
    s.arrow(448, 166, 498, 126, "sm", "mut", 2, 7)
    s.arrow(498, 105, 166, 105, "scd", "cd", 2, 7)
    s.text(150, 52, "impostos e contribuições", 9.2, 600, "ink2", "end")
    s.text(500, 52, "financia e contrata", 9.2, 600, "ink2")
    s.text(150, 166, "mensalidades", 9.2, 600, "ink2", "end")
    s.text(500, 166, "paga os serviços", 9.2, 600, "ink2")
    ctext(s, 332, 99, "atendimento", 9.4, 700, "cd")
    s.save("p4-componentes.svg")


P4_MODELOS = [
    ("seguridade", "Seguridade social", "base: cidadania", "users", "cd",
     ["todos, como cidadãos", "toda a sociedade, por impostos e contribuições", "direito de cidadania",
      "Reino Unido (NHS) e Canadá", "universal"]),
    ("seguro", "Seguro social", "base: trabalho", "briefcase", "c",
     ["quem trabalha e contribui, e seus dependentes", "trabalhadores e empregadores, sobre a folha de salários",
      "benefício do trabalho", "Alemanha e França", "regulada"]),
    ("assistencia", "Assistência", "base: mercado", "shopping-cart", "cm",
     ["quem paga; o Estado cobre só pobres comprovados e idosos", "cada pessoa, do próprio bolso ou por seguro privado",
      "bem de consumo", "Estados Unidos", "invertida"]),
]
P4_LINHAS = ["Quem tem direito", "Quem paga", "A saúde é", "Exemplos", "Cidadania (Fleury)"]


def p4_protecao(hide=None, name="p4-protecao.svg"):
    gap, x0 = 12, 14
    w = (652 - 2 * gap) / 3
    sizes = [(10.4, 550), (10.4, 550), (12, 750), (10.4, 550), (12, 750)]
    steps = []
    for k in range(len(P4_LINHAS)):
        sz, wt = sizes[k]
        nl = max(len(wrap(m[5][k], w - 26, sz, wt)) for m in P4_MODELOS)
        steps.append(18 + nl * sz * 1.22 + 14)
    H = 88 + sum(steps) - 8
    s = SVG(680, int(H + 8))
    for i, (key, nome, base, ic, cls, vals) in enumerate(P4_MODELOS):
        x = x0 + i * (w + gap)
        s.rect(x, 8, w, H - 8, 14, "ct")
        s.rect(x, 8, w, 58, 14, cls)
        s.rect(x, 50, w, 16, 0, cls)
        s.icon(ic, x + 14, 22, 28, "sw", 2)
        if hide == key:
            s.rect(x + 52, 20, w - 66, 26, 7, "c2")
            ctext(s, x + 52 + (w - 66) / 2, 38, "?", 14, 850, "ink")
        else:
            s.text(x + 52, 36, nome, 14.4, 850, "w")
        s.text(x + 52, 54, base.upper(), 8.6, 700, "w", ls=0.9)
        y = 88
        for k, (lab, v) in enumerate(zip(P4_LINHAS, vals)):
            sz, wt = sizes[k]
            s.text(x + 14, y, lab.upper(), 8.2, 800, "c" if cls != "c" else "cd", ls=0.8)
            s.text(x + 14, y + 16, v, sz, wt, "cd" if wt > 600 else "ink", width=w - 26, lh=1.22)
            y += steps[k]
    s.save(name)


def p4_trajetoria():
    s = SVG(680, 186)
    base = 178
    steps = [
        (14, 190, 92, "cl", "cd", "ink2", "ATÉ 1923", "Caridade e campanhas",
         "Santas Casas para os pobres; saúde pública só nas epidemias"),
        (228, 206, 118, "c", "w", "w", "1923 A 1988", "Seguro social",
         "CAPs (1923), IAPs (1933), INPS (1966) e INAMPS (1977): direito só de quem contribuía"),
        (458, 208, 158, "cd", "w", "w", "DESDE 1988", "Seguridade social",
         "SUS: saúde é direito de todos e dever do Estado, sem exigir contribuição"),
    ]
    for (x, w, h, cls, tcls, dcls, yr, t, d) in steps:
        y = base - h
        s.rect(x, y, w, h, 12, cls)
        s.text(x + 14, y + 22, yr, 9.4, 800, tcls, ls=1)
        s.text(x + 14, y + 42, t, 14, 850, tcls)
        s.text(x + 14, y + 60, d, 9.6, 500, dcls, width=w - 26, lh=1.25)
    s.rect(472, base - 44, 180, 28, 14, "c2")
    ctext(s, 562, base - 25, "CF88, arts. 194 a 200", 10.4, 800, "ink")
    s.arrow(206, base - 46, 226, base - 46, "scd", "cd", 2.2, 7)
    s.arrow(436, base - 46, 456, base - 46, "scd", "cd", 2.2, 7)
    s.save("p4-trajetoria.svg")


P4_TRIPE = [
    ("previdencia", "Previdência social", "piggy-bank", "cm", "o trabalhador e seus dependentes", "contributiva e obrigatória"),
    ("saude", "Saúde", "heart-pulse", "c", "todos: direito de todos e dever do Estado", "independe de contribuição"),
    ("assistencia", "Assistência social", "hand-heart", "cm", "quem dela necessitar", "independe de contribuição"),
]


def p4_tripe(hide=None, name="p4-tripe.svg"):
    s = SVG(680, 300)
    s.add('<polygon points="30,78 340,10 650,78" class="cd"/>')
    ctext(s, 340, 50, "SEGURIDADE SOCIAL", 13.6, 850, "w", ls=1.4)
    ctext(s, 340, 67, "art. 194: ações integradas dos Poderes Públicos e da sociedade", 9.4, 500, "w")
    w, gap = 186, 22
    x0 = (680 - 3 * w - 2 * gap) / 2
    for i, (key, nome, ic, cls, quem, contrib) in enumerate(P4_TRIPE):
        x = x0 + i * (w + gap)
        s.rect(x, 88, w, 150, 10, "ct")
        s.rect(x, 88, w, 44, 10, cls)
        s.rect(x, 120, w, 12, 0, cls)
        s.icon(ic, x + 12, 98, 24, "sw", 2)
        if hide == key:
            s.rect(x + 44, 98, w - 58, 24, 7, "c2")
            ctext(s, x + 44 + (w - 58) / 2, 115, "?", 13, 850, "ink")
        else:
            s.text(x + 44, 115, nome, 12.4, 800, "w")
        s.text(x + 14, 152, "PARA QUEM", 8.2, 800, "c" if cls != "c" else "cd", ls=0.9)
        s.text(x + 14, 168, quem, 10.6, 650, "ink", width=w - 24, lh=1.22)
        s.text(x + 14, 204, "CONTRIBUIÇÃO", 8.2, 800, "c" if cls != "c" else "cd", ls=0.9)
        s.text(x + 14, 220, contrib, 10.6, 650, "ink", width=w - 24)
    s.rect(24, 248, 632, 44, 10, "cl")
    ctext(s, 340, 266, "BASE · ART. 195: financiada por toda a sociedade", 10.6, 800, "cd")
    ctext(s, 340, 283, "orçamentos da União, dos Estados, do DF e dos Municípios + contribuições sociais", 9.6, 500, "ink2")
    s.save(name)


def p4_financiamento():
    s = SVG(680, 304)
    # orçamentos
    s.rect(14, 8, 196, 218, 12, "ct")
    s.rect(14, 8, 196, 34, 12, "cm")
    s.rect(14, 30, 196, 12, 0, "cm")
    ctext(s, 112, 30, "ORÇAMENTOS PÚBLICOS", 10.4, 850, "w", ls=0.8)
    s.icon("landmark", 88, 70, 48, "sc", 1.6)
    ctext(s, 112, 148, "União, Estados,", 11.4, 700, "cd")
    ctext(s, 112, 164, "Distrito Federal", 11.4, 700, "cd")
    ctext(s, 112, 180, "e Municípios", 11.4, 700, "cd")
    ctext(s, 112, 200, "(impostos)", 9.4, 500, "ink2")
    ctext(s, 223, 124, "+", 22, 800, "cd")
    # contribuições
    x, w = 236, 430
    s.rect(x, 8, w, 218, 12, "ct")
    s.rect(x, 8, w, 34, 12, "c")
    s.rect(x, 30, w, 12, 0, "c")
    s.text(x + 14, 30, "CONTRIBUIÇÕES SOCIAIS (INCISOS DO ART. 195)", 10.4, 850, "w", ls=0.8)
    rows = [("I", "do **empregador e da empresa**: folha de salários, receita ou faturamento*, lucro"),
            ("II", "do **trabalhador** e demais segurados, exceto sobre aposentadoria e pensão do regime geral (INSS)"),
            ("III", "sobre **concursos de prognósticos** (loterias e apostas)"),
            ("IV", "do **importador** de bens ou serviços*"),
            ("V", "sobre **bens e serviços** (CBS), incluída pela EC 132/2023")]
    y = 50
    for (n, t) in rows:
        nl = len(wrap(t.replace("**", ""), w - 64, 9.8, 500))
        hh = 26 if nl == 1 else 38
        s.rect(x + 12, y + (hh - 22) / 2, 30, 22, 6, "cl")
        ctext(s, x + 27, y + hh / 2 + 4, n, 10, 850, "cd")
        s.text(x + 52, y + hh / 2 + 3.5 - (nl - 1) * 6, t, 9.8, 500, "ink", width=w - 64, lh=1.2)
        y += hh + 3
    s.text(666, 240, "* revogados a partir de 2027 pela EC 132/2023 (reforma tributária), que os troca pela CBS", 8.8, 500, "mut", "end", italic=True)
    # destino
    s.arrow(112, 228, 112, 264, "scd", "cd", 2.2, 8)
    s.arrow(451, 246, 451, 264, "scd", "cd", 2.2, 8)
    s.rect(14, 266, 652, 32, 10, "cd")
    ctext(s, 340, 287, "SEGURIDADE SOCIAL: saúde · previdência · assistência social", 11.4, 800, "w")
    s.save("p4-financiamento.svg")


P4_196 = [
    ("A saúde é direito de todos", "universalidade · cidadania", True),
    ("e dever do Estado,", "responsabilidade do Estado", False),
    ("garantido mediante políticas sociais e econômicas", "conceito ampliado · determinação social · intersetorialidade", False),
    ("que visem à redução do risco de doença e de outros agravos", "prevenção dos riscos", False),
    ("e ao acesso universal e igualitário às ações e serviços", "universalidade · igualdade (equidade)", True),
    ("para sua promoção, proteção e recuperação.", "integralidade", True),
]


def p4_art196():
    s = SVG(680, 290)
    s.text(14, 16, "O TEXTO DO ART. 196", 8.8, 800, "mut", ls=1.3)
    s.text(436, 16, "O QUE O TRECHO REVELA", 8.8, 800, "mut", ls=1.3)
    y, h, gap = 26, 38, 5
    for (txt, conc, princ) in P4_196:
        s.rect(14, y, 382, h, 10, "ct")
        s.rect(14, y, 5, h, 2.5, "c")
        nl = len(wrap(txt, 350, 11.4, 600))
        s.text(30, y + h / 2 + 4 - (nl - 1) * 7, txt, 11.4, 600, "ink", width=350, lh=1.15, italic=True)
        s.arrow(398, y + h / 2, 432, y + h / 2, "scm", "cm", 1.8, 6)
        cls, tcls = ("c", "w") if princ else ("cl", "cd")
        s.rect(436, y + 3, 230, h - 6, 16, cls)
        nl2 = len(wrap(conc, 206, 10.4, 750))
        ctext(s, 551, y + h / 2 + 4 - (nl2 - 1) * 6.5, conc, 10.4, 750, tcls, width=206, lh=1.2)
        y += h + gap
    s.text(666, 286, "Em azul forte, os três princípios doutrinários que a prova pede.", 8.8, 500, "mut", "end", italic=True)
    s.save("p4-art196.svg")


def p4_direcao():
    s = SVG(680, 214)
    cols = [(14, 120, "ESFERA"), (148, 254, "DIREÇÃO ÚNICA (GESTOR)"), (416, 250, "PARTICIPAÇÃO DA COMUNIDADE")]
    for (x, w, t) in cols:
        s.text(x, 16, t, 8.6, 800, "mut", ls=1.2)
    rows = [("Nacional", "União", "Ministério da Saúde", "Conselho Nacional de Saúde"),
            ("Estadual", "Estados e DF", "Secretaria Estadual de Saúde", "Conselho Estadual de Saúde"),
            ("Municipal", "Municípios", "Secretaria Municipal de Saúde", "Conselho Municipal de Saúde")]
    y = 26
    for i, (esf, ente, gestor, cons) in enumerate(rows):
        cls = ["cd", "c", "cm"][i]
        s.rect(14, y, 120, 44, 10, cls)
        s.text(26, y + 20, esf, 12, 800, "w")
        s.text(26, y + 35, ente, 9.4, 500, "w")
        s.arrow(136, y + 22, 146, y + 22, "scm", "cm", 1.8, 6)
        s.rect(148, y, 254, 44, 10, "cl")
        s.icon("landmark", 160, y + 11, 22, "sc", 2)
        s.text(192, y + 27, gestor, 11.4, 750, "cd")
        s.rect(416, y, 250, 44, 10, "ct")
        s.icon("users", 428, y + 11, 22, "sc", 2)
        s.text(460, y + 27, cons, 11, 650, "ink")
        y += 52
    s.rect(14, 184, 652, 26, 8, "c2")
    ctext(s, 340, 201, "Conferências de saúde a cada 4 anos, em cada esfera, avaliam a situação e propõem diretrizes (Lei 8.142/1990)", 9.6, 650, "ink")
    s.save("p4-direcao.svg")


P4_PRINC = {
    "doutrinarios": ("DOUTRINÁRIOS", "o que o SUS garante: a finalidade", "c", [
        ("Universalidade", "acesso para todos, em todos os níveis de atenção"),
        ("Igualdade / equidade", "sem privilégios; mais a quem precisa mais"),
        ("Integralidade", "prevenção e cura, do individual ao coletivo"),
    ]),
    "organizativos": ("ORGANIZATIVOS", "como o SUS se organiza para cumprir os doutrinários", "cd", [
        ("Descentralização", "direção única em cada esfera; ênfase nos municípios"),
        ("Regionalização e hierarquização", "territórios e níveis de complexidade crescente"),
        ("Participação e controle social", "conselhos e conferências de saúde"),
    ]),
}


def p4_principios(hide=None, name="p4-principios.svg"):
    s = SVG(680, 300)
    s.rect(230, 8, 220, 38, 19, "cd")
    ctext(s, 340, 32, "PRINCÍPIOS DO SUS", 12.4, 850, "w", ls=1.2)
    s.path("M340,46 L340,58 M172,58 L508,58 M172,58 L172,72 M508,58 L508,72", "scm nf", 2)
    for gi, key in enumerate(("doutrinarios", "organizativos")):
        titulo, sub, cls, itens = P4_PRINC[key]
        x, w = (14, 316) if gi == 0 else (350, 316)
        s.rect(x, 72, w, 196, 14, "ct")
        s.rect(x, 72, w, 46, 14, cls)
        s.rect(x, 104, w, 14, 0, cls)
        ctext(s, x + w / 2, 92, titulo, 12.4, 850, "w", ls=1.4)
        ctext(s, x + w / 2, 109, sub, 9.2, 500, "w")
        y = 128
        for (nome, desc) in itens:
            s.rect(x + 10, y, w - 20, 42, 10, "w")
            if hide == key:
                s.rect(x + 20, y + 7, 150, 16, 5, "c2")
                ctext(s, x + 95, y + 19, "?", 11, 850, "ink")
            else:
                s.text(x + 22, y + 19, nome, 11.6, 800, "cd")
            s.text(x + 22, y + 34, desc, 9.4, 500, "ink2")
            y += 46
    ctext(s, 340, 290, "O ABC do SUS (1990) lista ainda resolubilidade e complementaridade do setor privado entre os organizativos.", 9, 500, "mut", italic=True)
    s.save(name)


def p4_equidade():
    s = SVG(680, 276)
    ground, fence_top = 196, 116
    panels = [(14, "IGUALDADE", "todos recebem o mesmo apoio", (1, 1, 1)),
              (346, "EQUIDADE", "cada um recebe o apoio de que precisa", (0, 1, 2))]
    people = [(104, "cd"), (84, "c"), (56, "cm")]  # (altura, cor)
    for (px, titulo, sub, boxes) in panels:
        s.rect(px, 8, 320, 206, 14, "ct")
        s.icon("heart-pulse", px + 140, 24, 40, "s2", 2.2)
        s.text(px + 160, 82, "SAÚDE", 9.6, 850, "c2", "middle", ls=2)
        # cerca
        s.rect(px + 18, fence_top, 284, ground - fence_top, 3, "cl")
        for k in range(1, 12):
            xx = px + 18 + k * 284 / 12
            s.line(xx, fence_top + 3, xx, ground - 2, "sw", 2)
        s.line(px + 18, fence_top, px + 302, fence_top, "scm", 2.4)
        s.line(px + 10, ground, px + 310, ground, "scd", 2.4)
        for j, ((hgt, cls), nb) in enumerate(zip(people, boxes)):
            cx = px + 78 + j * 82
            yb = ground
            for b in range(nb):
                s.rect(cx - 21, yb - 22, 42, 22, 3, "c2")
                s.line(cx - 19, yb - 22, cx + 19, yb - 22, "scd", 1)
                yb -= 22
            body_top = yb - hgt + 24
            s.rect(cx - 13, body_top, 26, hgt - 24, 11, cls)
            s.circle(cx, body_top - 12, 11, cls)
        ctext(s, px + 160, 236, titulo, 13, 850, "cd", ls=1.6)
        ctext(s, px + 160, 252, sub, 10, 500, "ink2")
    ctext(s, 340, 272, "equidade = igualdade + justiça", 11, 750, "c")
    s.save("p4-equidade.svg")


def p4_hierarquia():
    s = SVG(680, 262)
    ax, ay, by, hb = 214, 12, 250, 196

    def hw(y):
        return hb * (y - ay) / (by - ay)
    levels = [(ay, 92, "cd", "ALTA", "complexidade", "Hospitais de referência: cirurgia cardíaca, oncologia, transplantes, hemodiálise"),
              (92, 172, "c", "MÉDIA COMPLEXIDADE", "especialistas e apoio diagnóstico", "Ambulatórios de especialidades, exames de imagem e de laboratório, UPA"),
              (172, by, "cm", "ATENÇÃO PRIMÁRIA À SAÚDE", "porta de entrada · ordena o cuidado", "UBS e Saúde da Família: acolhe, acompanha e resolve a maior parte dos problemas")]
    for (y0, y1, cls, t, sub, desc) in levels:
        pts = f"{ax - hw(y0):.1f},{y0} {ax + hw(y0):.1f},{y0} {ax + hw(y1):.1f},{y1} {ax - hw(y1):.1f},{y1}"
        s.add(f'<polygon points="{pts}" class="{cls}"/>')
        s.add(f'<polygon points="{pts}" class="sw nf" stroke-width="2.5" stroke-linejoin="round"/>')
        ym = (y0 + y1) / 2 + (14 if y0 == ay else 0)
        ctext(s, ax, ym - 2, t, 11.2 if y0 != ay else 10.4, 850, "w", ls=0.8)
        ctext(s, ax, ym + 13, sub, 8.8, 500, "w")
        # descrição à direita
        yd = (y0 + y1) / 2 + (10 if y0 == ay else 0)
        s.line(ax + hw(yd) + 6, yd, 436, yd, "scl", 1.6, 'stroke-dasharray="3 3"')
        s.rect(436, yd - 26, 230, 52, 10, "ct")
        s.text(448, yd - 5 - (len(wrap(desc, 208, 9.6, 500)) - 2) * 6, desc, 9.6, 500, "ink", width=208, lh=1.25)
    # legenda de referência e contrarreferência
    s.arrow(22, 72, 22, 20, "scd", "cd", 2.2, 7)
    s.text(32, 30, "referência:", 9.4, 800, "cd")
    s.text(32, 43, ["encaminha a um", "nível mais complexo"], 8.8, 500, "ink2", lh=1.2)
    s.arrow(22, 92, 22, 144, "scm", "cm", 2.2, 7)
    s.text(32, 104, "contrarreferência:", 9.4, 800, "c")
    s.text(32, 117, ["devolve à APS, que", "segue o cuidado"], 8.8, 500, "ink2", lh=1.2)
    s.save("p4-hierarquia.svg")


def p4_mapa():
    s = SVG(680, 346)
    cx, cy = 340, 173
    bw, bh = 238, 96
    branches = [
        ("Proteção social", ["• seguridade, seguro e assistência", "• antes: seguro social (CAPs, IAPs)", "• CF88: seguridade social"], "L", 50, "cd"),
        ("Seguridade (arts. 194 e 195)", ["• saúde, previdência e assistência", "• só a previdência é contributiva", "• financiada por toda a sociedade"], "L", 173, "c"),
        ("Saúde (arts. 196 e 197)", ["• direito de todos, dever do Estado", "• conceito ampliado de saúde", "• ações de relevância pública"], "L", 296, "cm"),
        ("Arts. 198 a 200", ["• 198: diretrizes do sistema único", "• 199: privado só complementar", "• 200: competências do SUS"], "R", 50, "cd"),
        ("Princípios doutrinários", ["• universalidade", "• igualdade e equidade", "• integralidade"], "R", 173, "c"),
        ("Princípios organizativos", ["• descentralização (direção única)", "• regionalização e hierarquização", "• participação e controle social"], "R", 296, "cm"),
    ]
    for (t, items, side, y, c) in branches:
        x = 14 + bw if side == "L" else 680 - 14 - bw
        s.path(f"M{cx},{cy} C{(cx+x)/2},{cy} {(cx+x)/2},{y} {x},{y}", "scl nf", 3)
    s.circle(cx, cy, 64, "cd")
    ctext(s, cx, cy - 8, "O SUS", 12.4, 800, "w", ls=1.4)
    ctext(s, cx, cy + 10, "NA CF88", 12.4, 800, "w", ls=1.4)
    ctext(s, cx, cy + 30, "5/10/1988", 10.4, 700, "cl")
    for (t, items, side, y, c) in branches:
        bx = 14 if side == "L" else 680 - 14 - bw
        s.rect(bx, y - bh / 2, bw, bh, 12, "ct")
        s.rect(bx, y - bh / 2, bw, 28, 12, c)
        s.rect(bx, y - bh / 2 + 16, bw, 12, 0, c)
        ctext(s, bx + bw / 2, y - bh / 2 + 19, t, 12.4, 800, "w")
        for k, it in enumerate(items):
            if tw(it, 10.8, 500) > bw - 24:
                print("  aviso: linha longa no mapa:", it)
            s.text(bx + 14, y - 4 + k * 18, it, 10.8, 500, "ink")
    s.save("p4-mapa.svg")


def build_p4():
    p4_sistemas(); p4_componentes(); p4_protecao(); p4_trajetoria(); p4_tripe(); p4_financiamento()
    p4_art196(); p4_direcao(); p4_principios(); p4_equidade(); p4_hierarquia(); p4_mapa()
    for k in ("seguridade", "seguro", "assistencia"):
        p4_protecao(hide=k, name=f"p4-protecao-oculta-{k}.svg")
    for k in ("previdencia", "saude", "assistencia"):
        p4_tripe(hide=k, name=f"p4-tripe-oculta-{k}.svg")
    for k in ("doutrinarios", "organizativos"):
        p4_principios(hide=k, name=f"p4-principios-oculta-{k}.svg")

if __name__ == "__main__":
    alvo = sys.argv[1:] or ["p1", "p2", "p3", "p4"]
    for a in alvo:
        fn = globals().get(f"build_{a}")
        if fn:
            fn()
