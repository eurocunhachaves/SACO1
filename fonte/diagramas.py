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


if __name__ == "__main__":
    alvo = sys.argv[1:] or ["p1", "p2", "p3", "p4"]
    for a in alvo:
        fn = globals().get(f"build_{a}")
        if fn:
            fn()
