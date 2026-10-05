#!/usr/bin/env python3
"""Gera os PDFs do material de estudo a partir de fonte/partes/parteN.md.

Uso:  python3 fonte/build.py [1 2 3 4] [L1 L2 L3 L4]
      Números geram as partes (fonte/partes/parteN.md); LN gera a lista de questões
      da aula N (fonte/listas/listaN.md). Sem argumentos gera as partes e as listas.

Sintaxe extra no Markdown (além de Markdown padrão com tabelas):
  # Kicker || Título                 -> título de seção com linha de apoio
  :::tipo Título opcional  ...  :::  -> caixas: def, prova, alerta, alem, conexao, mnemo, ok
  :::quote Fonte ... :::             -> citação em destaque
  :::cols [c3] ... +++ ... :::       -> colunas
  :::card Título | etiqueta ... :::  -> cartão (use dentro de :::cols)
  :::tbl Legenda | classes ... :::   -> quadro (tabela Markdown dentro)
  :::q Cabeçalho | fonte ... >>> resposta ... :::  -> questão de prova com resposta-modelo
       flags no cabeçalho: !split (pode quebrar a página), !autoral (questão própria),
       !linhasN (N linhas para responder à mão)
  :::r Cabeçalho | fonte ... :::     -> resposta comentada (gabarito no fim das listas)
  :::recap Título ... :::            -> resumo final
  :::tl ... :::                      -> linha do tempo (linhas "- ano | texto", "- == Era", "- *ano | texto" destaca)
  :::side arquivo | classes | legenda | crédito ... :::  -> texto ao lado de uma figura
  :::slide arquivo | título ... :::  -> miniatura de slide com comentário
  ::svg arquivo.svg | classes | legenda | crédito    -> figura SVG inline
  ::img caminho | classes | legenda | crédito        -> figura raster
  ::gallery g3 | img1 ;; Título ;; crédito || img2 ;; Título ;; crédito ...
  ::anki tag | texto                                 -> chamada para os cards
  ==texto==  -> destaque;   :i:nome:  -> ícone inline
"""
import html, json, re, sys, asyncio, subprocess
from pathlib import Path

import markdown
import yaml

FONTE = Path(__file__).resolve().parent
RAIZ = FONTE.parent
ESTILO = FONTE / "estilo"
ICONES = Path("/root/build/npm/package/icons")
ICONES_LOCAL = ESTILO / "icons"
SAIDA = RAIZ / "PDFs"
TMP = FONTE / ".build"

BOX = {
    "def": ("Definição", "book-open"),
    "prova": ("Na prova", "target"),
    "alerta": ("Pegadinha", "triangle-alert"),
    "alem": ("Para ir além", "telescope"),
    "conexao": ("Conexão", "link"),
    "mnemo": ("Para memorizar", "brain"),
    "ok": ("Em resumo", "circle-check"),
    "slide": ("No slide da aula", "presentation"),
}


def icon(name, cls=""):
    """SVG do Lucide (ISC) com stroke herdado; copia para estilo/icons para o repo ser autossuficiente."""
    local = ICONES_LOCAL / f"{name}.svg"
    if not local.exists():
        src = ICONES / f"{name}.svg"
        ICONES_LOCAL.mkdir(parents=True, exist_ok=True)
        local.write_text(src.read_text())
    svg = local.read_text()
    svg = re.sub(r"<!--.*?-->", "", svg, flags=re.S).strip()
    svg = re.sub(r'\s(width|height)="24"', "", svg)
    svg = svg.replace('stroke="currentColor"', 'stroke="currentColor"')
    if cls:
        svg = svg.replace("<svg", f'<svg class="{cls}"', 1)
    return svg


def inline_svg(name):
    p = FONTE / "svg" / name
    s = p.read_text()
    s = re.sub(r"<\?xml.*?\?>", "", s, flags=re.S)
    s = re.sub(r"<!DOCTYPE.*?>", "", s, flags=re.S)
    return s.strip()


def md(text):
    """Markdown -> HTML para trechos internos."""
    return markdown.markdown(
        text, extensions=["extra", "sane_lists"], output_format="html5"
    )


def inline(text):
    h = md(text).strip()
    if h.startswith("<p>") and h.endswith("</p>") and h.count("<p>") == 1:
        h = h[3:-4]
    return h


def figure(kind, src, classes="", caption="", cred=""):
    cls = " ".join(c for c in classes.split() if c)
    if kind == "svg":
        art = f'<div class="art">{inline_svg(src)}</div>'
    else:
        extra = ' class="photo"' if "photo" in cls else ""
        art = f'<div class="art"><img src="{src}"{extra} alt=""></div>'
    cap = ""
    if caption or cred:
        c = inline(caption) if caption else ""
        if cred:
            c += f'<span class="cred">{inline(cred)}</span>'
        cap = f"<figcaption>{c}</figcaption>"
    wcls = ""
    m = re.search(r"\bw(\d+)\b", cls)
    style = ""
    if m:
        style = f' style="--w:{m.group(1)}%"'
        art = art.replace('<div class="art">', f'<div class="art" style="width:{m.group(1)}%">', 1)
        cls = re.sub(r"\bw\d+\b", "", cls).strip()
    return f'<figure class="{cls}"{style}>{art}{cap}</figure>'


def timeline(lines):
    out = ['<ol class="tl">']
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        if ln.startswith("- "):
            ln = ln[2:]
        if ln.startswith("=="):
            out.append(f'<li class="era"><span class="e">{inline(ln[2:].strip())}</span></li>')
            continue
        key = ln.startswith("*")
        if key:
            ln = ln[1:]
        y, _, e = ln.partition("|")
        out.append(
            f'<li class="{"key" if key else ""}"><span class="y">{inline(y.strip())}</span>'
            f'<span class="e">{inline(e.strip())}</span></li>'
        )
    out.append("</ol>")
    return "\n".join(out)


def gallery(spec):
    cls, _, items = spec.partition("|")
    figs = []
    for it in items.split("||"):
        parts = [p.strip() for p in it.split(";;")]
        src = parts[0]
        title = parts[1] if len(parts) > 1 else ""
        cred = parts[2] if len(parts) > 2 else ""
        cap = f"<b>{inline(title)}</b>" if title else ""
        if cred:
            cap += inline(cred)
        figs.append(
            f'<figure><div class="art"><img src="{src}" alt=""></div><figcaption>{cap}</figcaption></figure>'
        )
    return f'<div class="gallery {cls.strip()}">' + "".join(figs) + "</div>"


def render_block(name, args, body_lines):
    body = "\n".join(body_lines)
    if name in BOX:
        label, ic = BOX[name]
        title = args.strip()
        bt = f'<span class="bt">{inline(title)}</span>' if title else ""
        extra = ""
        if name == "slide":
            src, _, title2 = args.partition("|")
            bt = f'<span class="bt">{inline(title2.strip())}</span>' if title2.strip() else ""
            inner = f'<div class="slidecard"><img src="{src.strip()}" alt=""><div>{md(body)}</div></div>'
            return f'<div class="box slide"><div class="bh">{icon(ic)}{label}{bt}</div>{inner}</div>'
        split = " split" if "!split" in title else ""
        if split:
            title = title.replace("!split", "").strip()
            bt = f'<span class="bt">{inline(title)}</span>' if title else ""
        return f'<div class="box {name}{split}"><div class="bh">{icon(ic)}{label}{bt}</div>{md(body)}</div>'
    if name == "quote":
        src = f'<span class="src">{inline(args)}</span>' if args.strip() else ""
        return f'<div class="quote">{inline(body)}{src}</div>'
    if name == "cols":
        cols = re.split(r"^\+\+\+\s*$", body, flags=re.M)
        inner = "".join(f"<div>{expand(c)}</div>" for c in cols)
        return f'<div class="cols {args.strip()}">{inner}</div>'
    if name == "card":
        title, _, tag = args.partition("|")
        cls = ""
        m = re.search(r"\{(.*?)\}", title)
        if m:
            cls = m.group(1)
            title = title.replace(m.group(0), "")
        t = f'<span class="tag">{inline(tag.strip())}</span>' if tag.strip() else ""
        return f'<div class="card {cls}">{t}<h4>{inline(title.strip())}</h4>{md(body)}</div>'
    if name == "tbl":
        cap, _, cls = args.partition("|")
        c = f'<div class="cap">{inline(cap.strip())}</div>' if cap.strip() else ""
        return f'<div class="tbl {cls.strip()}">{c}{md(body)}</div>'
    if name == "q":
        head, _, src = args.partition("|")
        cls = ""
        for flag in ("split", "autoral"):
            if f"!{flag}" in head:
                cls += f" {flag}"
                head = head.replace(f"!{flag}", "")
        linhas = ""
        m = re.search(r"!linhas(\d+)", head)
        if m:
            linhas = f'<div class="linhas" style="--n:{m.group(1)}"></div>'
            head = head.replace(m.group(0), "")
        qtext, _, ans = body.partition("\n>>>")
        ans_html = ""
        if ans.strip():
            ans_html = f'<div class="qa"><span class="lbl">Resposta-modelo</span>{expand(ans.strip())}</div>'
        return (
            f'<div class="q{cls}"><div class="qh"><span>{inline(head.strip())}</span>'
            f'<span class="src">{inline(src.strip())}</span></div>'
            f'<div class="qb">{expand(qtext)}</div>{linhas}{ans_html}</div>'
        )
    if name == "r":
        head, _, src = args.partition("|")
        cls = " autoral" if "!autoral" in head else ""
        head = head.replace("!autoral", "")
        return (
            f'<div class="q gab{cls}"><div class="qh"><span>{inline(head.strip())}</span>'
            f'<span class="src">{inline(src.strip())}</span></div>'
            f'<div class="qa">{expand(body)}</div></div>'
        )
    if name == "recap":
        return f'<div class="recap"><h4>{inline(args.strip() or "Resumo em 1 minuto")}</h4>{md(body)}</div>'
    if name == "tl":
        return timeline(body_lines)
    if name == "side":
        parts = [p.strip() for p in args.split("|")]
        src = parts[0]
        classes = parts[1] if len(parts) > 1 else ""
        cap = parts[2] if len(parts) > 2 else ""
        cred = parts[3] if len(parts) > 3 else ""
        kind = "svg" if src.endswith(".svg") and not src.startswith("img/") else "img"
        fig = figure(kind, src, " ".join(c for c in classes.split() if c not in ("left", "wide")), cap, cred)
        lay = " ".join(c for c in classes.split() if c in ("left", "wide"))
        txt = f"<div>{expand(body)}</div>"
        inner = (fig + txt) if "left" in lay else (txt + fig)
        return f'<div class="side {lay}">{inner}</div>'
    if name == "raw":
        return body
    raise ValueError(f"bloco desconhecido: {name}")


def expand(text):
    """Processa diretivas (com aninhamento) e devolve HTML."""
    lines = text.split("\n")
    out, i = [], 0
    buf = []

    def flush():
        if buf:
            out.append(md("\n".join(buf)))
            buf.clear()

    while i < len(lines):
        ln = lines[i]
        m = re.match(r"^:::(\w+)\s*(.*)$", ln)
        if m:
            name, args = m.group(1), m.group(2)
            depth, j, body = 1, i + 1, []
            while j < len(lines):
                if re.match(r"^:::\w+", lines[j]):
                    depth += 1
                elif lines[j].strip() == ":::":
                    depth -= 1
                    if depth == 0:
                        break
                body.append(lines[j])
                j += 1
            flush()
            out.append(render_block(name, args, body))
            i = j + 1
            continue
        m = re.match(r"^::(svg|img)\s+(.*)$", ln)
        if m:
            flush()
            parts = [p.strip() for p in m.group(2).split("|")]
            parts += [""] * (4 - len(parts))
            out.append(figure(m.group(1), *parts[:4]))
            i += 1
            continue
        m = re.match(r"^::gallery\s+(.*)$", ln)
        if m:
            flush()
            out.append(gallery(m.group(1)))
            i += 1
            continue
        m = re.match(r"^::anki\s+(.*)$", ln)
        if m:
            flush()
            tag, _, txt = m.group(1).partition("|")
            out.append(
                f'<div class="anki">{icon("layers")}<span>{inline(txt.strip() or "Revise no Anki")} '
                f'<code>{html.escape(tag.strip())}</code></span></div>'
            )
            i += 1
            continue
        m = re.match(r"^(#{1,2})\s+(.*)$", ln)
        if m:
            flush()
            out.append(heading(len(m.group(1)), m.group(2)))
            i += 1
            continue
        buf.append(ln)
        i += 1
    flush()
    return "\n".join(out)


HEADS = []


def heading(level, text):
    cls = ""
    m = re.search(r"\{([^}]*)\}\s*$", text)
    if m:
        cls = m.group(1).replace(".", " ").strip()
        text = text[: m.start()].strip()
    kick = ""
    if "||" in text:
        kick, text = [t.strip() for t in text.split("||", 1)]
    hid = f"h{len(HEADS) + 1}"
    HEADS.append({"level": level, "text": text, "id": hid, "cls": cls})
    k = f'<span class="kick">{inline(kick)}</span>' if kick else ""
    tag = f"h{level}"
    if level == 1:
        return f'<{tag} id="{hid}" class="{cls}"><span>{k}{inline(text)}</span></{tag}>'
    return f'<{tag} id="{hid}" class="{cls}">{inline(text)}</{tag}>'


def pre_inline(text):
    text = re.sub(r"==(.+?)==", r"<mark>\1</mark>", text)
    text = re.sub(r":i:([a-z0-9-]+):", lambda m: icon(m.group(1), "ico"), text)
    return text


# ---------------------------------------------------------------- capa
def cover_bg(parte):
    W, H = 210, 297
    s = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid slice">']
    s.append('<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
             '<stop offset="0" style="stop-color:var(--c)"/><stop offset="1" style="stop-color:var(--c-dark)"/></linearGradient>'
             '<radialGradient id="r" cx="0.85" cy="0.1" r="0.9"><stop offset="0" stop-color="#fff" stop-opacity=".16"/>'
             '<stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient></defs>')
    s.append(f'<rect width="{W}" height="{H}" fill="url(#g)"/><rect width="{W}" height="{H}" fill="url(#r)"/>')
    if parte == 1:  # planos subindividual, individual e coletivo: círculos concêntricos
        for k, r in enumerate(range(12, 170, 13)):
            s.append(f'<circle cx="178" cy="70" r="{r}" fill="none" stroke="#fff" stroke-opacity="{0.13 - k*0.007:.3f}" stroke-width="0.5"/>')
        s.append('<circle cx="178" cy="70" r="5" fill="#fff" fill-opacity=".35"/>')
    elif parte == 2:  # pétalas radiais
        import math
        for k in range(18):
            a = k * math.pi / 9
            x, y = 175 + 58 * math.cos(a), 72 + 58 * math.sin(a)
            s.append(f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="34" ry="12" transform="rotate({math.degrees(a):.1f} {x:.1f} {y:.1f})" fill="none" stroke="#fff" stroke-opacity=".12" stroke-width="0.5"/>')
        for r in (20, 40, 92):
            s.append(f'<circle cx="175" cy="72" r="{r}" fill="none" stroke="#fff" stroke-opacity=".10" stroke-width="0.5"/>')
    elif parte == 3:  # linha do tempo
        for k in range(14):
            y = 22 + k * 9.5
            x0 = 110 + (k % 3) * 9
            s.append(f'<line x1="{x0}" y1="{y}" x2="{W}" y2="{y}" stroke="#fff" stroke-opacity=".10" stroke-width="0.5"/>')
            for t in range(4):
                cx = x0 + 12 + t * 23 + (k * 7 % 11)
                if cx < W:
                    s.append(f'<circle cx="{cx}" cy="{y}" r="{1.2 + (k+t)%3*0.5}" fill="#fff" fill-opacity=".16"/>')
    elif parte == 4:  # rede
        import random
        rnd = random.Random(7)
        pts = [(rnd.uniform(95, 210), rnd.uniform(5, 145)) for _ in range(34)]
        for a in range(len(pts)):
            for b in range(a + 1, len(pts)):
                (x1, y1), (x2, y2) = pts[a], pts[b]
                if (x1 - x2) ** 2 + (y1 - y2) ** 2 < 900:
                    s.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#fff" stroke-opacity=".12" stroke-width="0.45"/>')
        for x, y in pts:
            s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.5" fill="#fff" fill-opacity=".28"/>')
    s.append("</svg>")
    return "".join(s)


def cover(meta):
    items = "".join(f"<li>{inline(x)}</li>" for x in meta.get("nesta_parte", []))
    hero = ""
    if meta.get("hero"):
        hero = f'<div class="hero"><img src="{meta["hero"]}" alt=""></div>'
        if meta.get("hero_credito"):
            hero += f'<div class="hero-cap">{inline(meta["hero_credito"])}</div>'
    return f"""
<section class="cover">
  <div class="bg">{cover_bg(meta['parte'])}</div>
  <div class="top"><span>Saúde Coletiva I · Medicina UFCG</span><span class="pill">{meta['aula']}</span></div>
  <div class="num">0{meta['parte']}</div>
  <div class="titles">
    <div class="kicker">{meta['rotulo']} {meta['parte']} de 4</div>
    <h1 class="ctitle">{inline(meta['titulo'])}</h1>
    <div class="csub">{inline(meta['subtitulo'])}</div>
  </div>
  <div class="inside"><h4>Nesta {meta['rotulo'].lower()}</h4><ol>{items}</ol></div>
  {hero}
  <div class="foot"><span>Baseado nos slides do <b>Prof. Dr. Cristiano Moura</b><br>{inline(meta.get('base',''))}</span><span>Material de estudo · {meta.get('semestre','2026')}</span></div>
</section>"""


def opening(meta, pages, body_html):
    toc = []
    h1s = [h for h in HEADS if h["level"] == 1]
    for idx, h in enumerate(h1s):
        subs = []
        start = HEADS.index(h)
        for h2 in HEADS[start + 1:]:
            if h2["level"] == 1:
                break
            if h2["level"] == 2:
                subs.append(re.sub(r"<.*?>", "", inline(h2["text"])))
        num = "" if "nonum" in h["cls"] else str(sum(1 for x in h1s[: idx + 1] if "nonum" not in x["cls"]))
        pg = pages.get(h["id"], "")
        sm = f"<small>{' · '.join(subs)}</small>" if subs else ""
        toc.append(
            f'<li><span class="n">{num}</span><span class="t">{inline(h["text"])}{sm}</span><span class="pg">{pg}</span></li>'
        )
    goals = "".join(f"<li>{inline(g)}</li>" for g in meta.get("objetivos", []))
    goals_t = meta.get("objetivos_titulo", "Ao final desta parte você deve conseguir")
    dense = " dense" if len(h1s) > 9 else ""
    leg = []
    for k in ("def", "prova", "alerta", "mnemo", "conexao", "alem"):
        if f'class="box {k}' not in body_html:   # a legenda só mostra as caixas que a parte usa
            continue
        label, ic = BOX[k]
        col = {"def": "var(--c)", "prova": "var(--prova)", "alerta": "var(--alerta)", "mnemo": "var(--mnemo)",
               "conexao": "var(--conexao)", "alem": "var(--alem)"}[k]
        bg = {"def": "var(--c-tint)", "prova": "var(--prova-bg)", "alerta": "var(--alerta-bg)", "mnemo": "var(--mnemo-bg)",
              "conexao": "var(--conexao-bg)", "alem": "var(--alem-bg)"}[k]
        desc = {
            "def": "conceitos e definições literais das fontes",
            "prova": "como o professor costuma cobrar o tema",
            "alerta": "trocas de palavra que derrubam alternativas",
            "mnemo": "macetes e esquemas para fixar listas",
            "conexao": "ligações com as outras partes do material",
            "alem": "aprofundamento a partir das leituras",
        }[k]
        leg.append(
            f'<div class="it"><span class="sw" style="background:{bg};color:{col}">{icon(ic)}</span>'
            f'<span><b>{label}</b>{desc}</span></div>'
        )
    if meta["rotulo"] == "Lista":   # nas listas, a legenda explica os dois tipos de questão
        for cls, label, desc, bg, col in (
            ("q", "Questão de prova", "já caiu; o cabeçalho diz em que provas", "var(--prova-bg)", "var(--prova)"),
            ("q autoral", "Questão autoral", "tema importante que as provas ainda não cobraram", "var(--c-tint)", "var(--c)"),
        ):
            if f'class="{cls}' in body_html:
                leg.append(
                    f'<div class="it"><span class="sw" style="background:{bg};color:{col}">{icon("pencil-line")}</span>'
                    f'<span><b>{label}</b>{desc}</span></div>'
                )
    legenda = (f'<div class="eyebrow" style="margin:0 0 2mm">Como ler as caixas</div><div class="legend">{"".join(leg)}</div>'
               if leg else "")
    return f"""
<section class="opening{dense}">
  <div class="eyebrow">{meta['rotulo']} {meta['parte']} · {meta['aula']}</div>
  <h2 class="toc-title">Sumário</h2>
  <ol class="toc">{''.join(toc)}</ol>
  <div class="goals"><h4>{goals_t}</h4><ul>{goals}</ul></div>
  {legenda}
</section>"""


def page_style(meta):
    left = f"SAÚDE COLETIVA I  ·  {meta['rotulo'].upper()} {meta['parte']}"
    right = meta.get("cabecalho", meta["titulo"]).upper()
    return (
        "<style>@page { @top-left { content: \"%s\"; } @top-right { content: \"%s\"; } }</style>"
        % (left, right)
    )


def build_html(meta, body_html, pages):
    css = (ESTILO / "base.css").as_uri()
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<title>SACO 1 · {meta['rotulo']} {meta['parte']} · {re.sub('<.*?>','',meta['titulo'])}</title>
<link rel="stylesheet" href="{css}">
{page_style(meta)}
</head>
<body class="p{meta['parte']}">
{cover(meta)}
{opening(meta, pages, body_html)}
<main>
{body_html}
</main>
</body></html>"""


# Reamostra cada foto para o tamanho em que aparece na página (~200 dpi) antes de
# imprimir. Sem isso o Chromium embute o JPEG original inteiro e cada PDF passa de 6 MB.
ENXUGAR_FOTOS = """async () => {
  const DPI = 200 / 96, Q = 0.82;
  const imgs = [...document.images].filter(i => /\\.(jpe?g|png)$/i.test(i.getAttribute('src') || ''));
  await Promise.all(imgs.map(i => i.decode().catch(() => {})));
  await Promise.all(imgs.map(async i => {
    const r = i.getBoundingClientRect();
    if (!r.width || !r.height || !i.naturalWidth) return;
    const f = Math.min(1, Math.max(r.width * DPI / i.naturalWidth, r.height * DPI / i.naturalHeight));
    if (f > 0.9) return;
    const w = Math.round(i.naturalWidth * f), h = Math.round(i.naturalHeight * f);
    const c = document.createElement('canvas'); c.width = w; c.height = h;
    const g = c.getContext('2d'); g.imageSmoothingQuality = 'high';
    g.fillStyle = '#fff'; g.fillRect(0, 0, w, h); g.drawImage(i, 0, 0, w, h);
    // a densidade no srcset mantém o tamanho intrínseco original, e o layout não muda
    i.srcset = c.toDataURL('image/jpeg', Q) + ' ' + (w / i.naturalWidth) + 'x';
    i.removeAttribute('src');
    await i.decode().catch(() => {});
  }));
}"""


async def to_pdf(html_path, pdf_path):
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--allow-file-access-from-files"])
        pg = await b.new_page(viewport={"width": 794, "height": 1123})   # A4 a 96 dpi
        await pg.emulate_media(media="print")
        await pg.goto(html_path.as_uri())
        await pg.evaluate("document.fonts.ready")
        await pg.evaluate(ENXUGAR_FOTOS)
        await pg.wait_for_timeout(300)
        await pg.pdf(path=str(pdf_path), prefer_css_page_size=True, print_background=True,
                     outline=True, tagged=True)
        await b.close()


def plain(t):
    return re.sub(r"\s+", " ", re.sub(r"<.*?>", "", inline(t))).strip()


def find_pages(pdf_path):
    """página (1-based) de cada h1, procurando o título no topo das páginas do PDF"""
    import pymupdf
    doc = pymupdf.open(pdf_path)
    pages, start = {}, 2   # índice 0 = capa, 1 = sumário
    for h in [h for h in HEADS if h["level"] == 1]:
        probe = " ".join(plain(h["text"]).split()[:4])
        for pno in range(start, len(doc)):
            hits = doc[pno].search_for(probe)
            if hits and ("flow" in h["cls"] or min(r.y0 for r in hits) < 150):
                pages[h["id"]] = pno + 1
                start = pno
                break
    doc.close()
    return pages


def fix_outline(pdf_path, pages):
    """marcadores do PDF limpos: capa, sumário, seções numeradas e subseções"""
    import pymupdf
    doc = pymupdf.open(pdf_path)
    chrome = doc.get_toc()
    toc = [[1, "Capa", 1], [1, "Sumário", 2]]
    sec = 0
    sub = 0
    cur_page = 2
    for h in HEADS:
        title = plain(h["text"])
        if h["level"] == 1:
            nonum = "nonum" in h["cls"]
            if not nonum:
                sec += 1
            sub = 0
            cur_page = pages.get(h["id"], cur_page)
            toc.append([1, (f"{sec}. " if not nonum else "") + title, cur_page])
        elif h["level"] == 2:
            pg = next((t[2] for t in chrome if t[0] == 2 and t[1].strip() == title and t[2] >= cur_page), cur_page)
            num = ""
            if "nonum" not in h["cls"]:
                sub += 1
                num = f"{sec}.{sub} "
            toc.append([2, num + title, pg])
            cur_page = pg
    doc.set_toc(toc)
    tmp = pdf_path.with_suffix(".tmp.pdf")
    doc.save(tmp, garbage=4, deflate=True, use_objstms=1)
    doc.close()
    tmp.replace(pdf_path)


def build(n, lista=False):
    global HEADS
    nome = f"lista{n}" if lista else f"parte{n}"
    src = FONTE / ("listas" if lista else "partes") / f"{nome}.md"
    text = src.read_text()
    _, fm, body = text.split("---\n", 2)
    meta = yaml.safe_load(fm)
    meta["parte"] = n
    meta["rotulo"] = "Lista" if lista else "Parte"
    body = pre_inline(body)
    HEADS = []
    body_html = expand(body)
    TMP.mkdir(exist_ok=True)
    html_path = FONTE / f"_{nome}.html"   # na raiz de fonte/ para os caminhos relativos funcionarem
    pdf_path = SAIDA / meta["arquivo"]
    SAIDA.mkdir(exist_ok=True)
    # passadas: renderiza, descobre a página de cada seção e repete até estabilizar
    pages = {}
    for _ in range(4):
        html_path.write_text(build_html(meta, body_html, pages))
        asyncio.run(to_pdf(html_path, pdf_path))
        novo = find_pages(pdf_path)
        if novo == pages:
            break
        pages = novo
    fix_outline(pdf_path, pages)
    h1s = [h for h in HEADS if h["level"] == 1]
    print(f"{meta['rotulo']} {n}: {pdf_path.name}  ({len(pages)}/{len(h1s)} seções paginadas)")
    return pdf_path


if __name__ == "__main__":
    alvos = sys.argv[1:] or ["1", "2", "3", "4", "L1", "L2", "L3", "L4"]
    for a in alvos:
        lista = a.upper().startswith("L")
        build(int(a.lstrip("Ll")), lista)
