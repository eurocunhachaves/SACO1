#!/usr/bin/env python3
"""Gera os baralhos Anki (.apkg) de Saúde Coletiva I a partir de fonte/cards/aulaN.yaml.

Uso:
    python3 fonte/cards/gerar.py            # as quatro aulas + o pacote completo
    python3 fonte/cards/gerar.py 2 4        # só as aulas indicadas (sem o completo)

Saída em Flashcards/: um .apkg por aula e SACO1-Completo.apkg com os quatro baralhos.
Os IDs dos modelos, dos baralhos e os GUIDs das notas são fixos: reimportar uma versão
nova atualiza os cards já existentes sem apagar o histórico de revisões.
"""
import hashlib
import io
import re
import shutil
import subprocess
import sys
from pathlib import Path

import genanki
import yaml
from PIL import Image

AQUI = Path(__file__).resolve().parent
FONTE = AQUI.parent
RAIZ = FONTE.parent
BUILD = AQUI / "_build"
SAIDA = RAIZ / "Flashcards"
LIMITE = 150 * 1024  # tamanho máximo de cada imagem nos cards

NOMES = {
    1: "Conceito de Saúde",
    2: "Promoção da Saúde",
    3: "Políticas de Saúde antes do SUS",
    4: "O SUS na CF88",
}
ARQUIVOS = {
    1: "SACO1-Aula1-Conceito-de-Saude.apkg",
    2: "SACO1-Aula2-Promocao-da-Saude.apkg",
    3: "SACO1-Aula3-Politicas-de-Saude-antes-do-SUS.apkg",
    4: "SACO1-Aula4-O-SUS-na-CF88.apkg",
}
PDFS = {
    1: "SACO1-Parte1-Conceito-de-Saude.pdf",
    2: "SACO1-Parte2-Promocao-da-Saude.pdf",
    3: "SACO1-Parte3-Politicas-de-Saude-antes-do-SUS.pdf",
    4: "SACO1-Parte4-O-SUS-na-CF88.pdf",
}


def id_fixo(*partes):
    """Inteiro estável (entre 2^30 e 2^31) derivado de um texto, para IDs de modelo e baralho."""
    h = hashlib.sha1("::".join(map(str, partes)).encode()).hexdigest()
    return (1 << 30) + int(h[:8], 16) % (1 << 30)


# ---------------------------------------------------------------- estilo dos cards
FONTES = {
    "_saco1-inter.woff2": "inter-latin-standard-normal.woff2",
    "_saco1-inter-italico.woff2": "inter-latin-standard-italic.woff2",
    "_saco1-serif.woff2": "source-serif-4-latin-standard-normal.woff2",
    "_saco1-serif-italico.woff2": "source-serif-4-latin-standard-italic.woff2",
}

CSS = r"""
@font-face { font-family: "SACO Inter"; src: url("_saco1-inter.woff2") format("woff2"); font-weight: 100 900; font-style: normal; }
@font-face { font-family: "SACO Inter"; src: url("_saco1-inter-italico.woff2") format("woff2"); font-weight: 100 900; font-style: italic; }
@font-face { font-family: "SACO Serif"; src: url("_saco1-serif.woff2") format("woff2"); font-weight: 200 900; font-style: normal; }
@font-face { font-family: "SACO Serif"; src: url("_saco1-serif-italico.woff2") format("woff2"); font-weight: 200 900; font-style: italic; }

.card {
  margin: 0; padding: 0;
  background: #eef1f5;
  color: #1d2433;
  font-family: "SACO Inter", "Inter", "Helvetica Neue", Arial, sans-serif;
  text-align: left;
  -webkit-font-smoothing: antialiased;
}
.saco {
  --c: #0f766e; --cd: #0b4f4a; --cl: #e3f4f1; --ct: #f1faf8;
  --ink: #1d2433; --ink2: #3b4456; --mut: #6b7385; --rule: #e1e5ec; --papel: #ffffff;
  --prova: #6d28d9; --prova-bg: #f3efff; --alerta: #c2410c;
  max-width: 680px; margin: 22px auto 28px; background: var(--papel);
  border-radius: 18px; overflow: hidden;
  box-shadow: 0 1px 2px rgba(16, 24, 40, .06), 0 10px 28px rgba(16, 24, 40, .09);
}
.saco[data-aula^="Aula 2"] { --c: #4d7c0f; --cd: #355708; --cl: #edf5df; --ct: #f6faef; }
.saco[data-aula^="Aula 3"] { --c: #b45309; --cd: #7c3a0a; --cl: #fbefe1; --ct: #fdf7f0; }
.saco[data-aula^="Aula 4"] { --c: #1d4ed8; --cd: #1e3a8a; --cl: #e4ecfd; --ct: #f3f6fe; }

.topo {
  display: flex; justify-content: space-between; align-items: center; gap: 12px;
  background: var(--c); color: #fff; padding: 11px 22px;
  font-size: 10.5px; font-weight: 700; letter-spacing: .15em; text-transform: uppercase; line-height: 1.3;
}
.topo .aula { text-align: right; opacity: .92; }
.corpo { padding: 22px 26px 22px; }
.kicker {
  display: flex; flex-wrap: wrap; align-items: center; gap: 6px 10px; margin: 0 0 10px;
  color: var(--c); font-size: 11px; font-weight: 800; letter-spacing: .13em; text-transform: uppercase; line-height: 1.3;
}
.selo {
  color: var(--prova); background: var(--prova-bg); border-radius: 999px;
  padding: 3px 9px 3px; font-size: 9.5px; letter-spacing: .12em;
}
.pergunta { font-size: 21px; line-height: 1.38; font-weight: 600; color: var(--ink); letter-spacing: -.005em; }
.pergunta b { color: var(--cd); font-weight: 750; }
hr#answer { border: 0; border-top: 1.5px dashed var(--rule); margin: 20px 0 18px; }
.resposta { font-size: 20px; line-height: 1.42; font-weight: 500; color: var(--ink); }
.resposta b { color: var(--cd); font-weight: 750; }
.resposta p, .extra p, .texto p { margin: 0; }
.resposta p + p, .extra p + p, .texto p + p, .resposta ul + p, .extra ul + p { margin-top: .55em; }
.resposta ul, .extra ul, .texto ul { margin: 6px 0 0; padding-left: 1.15em; }
.resposta li { margin: 3px 0; }
.resposta li::marker { color: var(--c); }
.fig { margin: 16px 0 2px; text-align: center; }
.fig img {
  display: inline-block; max-width: 100%; max-height: 360px; height: auto;
  border-radius: 12px; border: 1px solid var(--rule); background: #fff;
}
.fig img.recorte { display: none; }
.extra {
  margin-top: 18px; padding: 12px 15px 13px; border-radius: 12px;
  background: var(--ct); border-left: 3px solid var(--c);
  font-family: "SACO Serif", "Source Serif 4", Georgia, serif; font-size: 16px; line-height: 1.52; color: var(--ink2);
}
.extra b { color: var(--cd); }
.extra .div, .resposta .div { color: var(--alerta); }
.rodape {
  display: flex; flex-wrap: wrap; gap: 6px 18px; margin-top: 18px; padding-top: 12px; border-top: 1px solid var(--rule);
  font-size: 11.5px; line-height: 1.4; color: var(--mut);
}
.rodape span b { font-size: 9.5px; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; margin-right: 6px; }
.rodape .r-prova b { color: var(--prova); }
.rodape .r-fonte b { color: var(--c); }

/* lacunas (cloze) */
.texto { font-size: 20px; line-height: 1.45; font-weight: 500; color: var(--ink); }
.texto b { color: var(--cd); font-weight: 750; }
.cloze { color: var(--c); font-weight: 800; background: var(--cl); border-radius: 6px; padding: 0 .18em; }
.cloze-inactive { color: inherit; background: none; font-weight: inherit; }

/* telas pequenas */
@media (max-width: 520px) {
  .saco { margin: 0; border-radius: 0; box-shadow: none; min-height: 100vh; }
  .topo { padding: 10px 16px; font-size: 9.5px; }
  .topo span:first-child { display: none; }
  .corpo { padding: 18px 18px 20px; }
  .pergunta { font-size: 19px; }
  .resposta, .texto { font-size: 18px; }
  .extra { font-size: 15px; }
  .fig img.com-recorte { display: none; }
  .fig img.recorte { display: inline-block; max-height: none; }
}

/* modo noturno */
.nightMode.card, .night_mode.card, .card.nightMode, .card.night_mode { background: #12151b; color: #e6e9ef; }
.nightMode .saco, .night_mode .saco {
  --c: #2dd4bf; --cd: #5eead4; --cl: rgba(45, 212, 191, .16); --ct: rgba(45, 212, 191, .07);
  --ink: #e8ebf1; --ink2: #c4cad6; --mut: #8d95a5; --rule: #2f3542; --papel: #1b1f27;
  --prova: #c4b5fd; --prova-bg: rgba(167, 139, 250, .16); --alerta: #fdba74;
  box-shadow: none; border: 1px solid #2a2f3a;
}
.nightMode .saco[data-aula^="Aula 2"], .night_mode .saco[data-aula^="Aula 2"] { --c: #a3e635; --cd: #bef264; --cl: rgba(163, 230, 53, .15); --ct: rgba(163, 230, 53, .06); }
.nightMode .saco[data-aula^="Aula 3"], .night_mode .saco[data-aula^="Aula 3"] { --c: #fb923c; --cd: #fdba74; --cl: rgba(251, 146, 60, .16); --ct: rgba(251, 146, 60, .07); }
.nightMode .saco[data-aula^="Aula 4"], .night_mode .saco[data-aula^="Aula 4"] { --c: #60a5fa; --cd: #93c5fd; --cl: rgba(96, 165, 250, .16); --ct: rgba(96, 165, 250, .07); }
.nightMode .topo, .night_mode .topo { background: #232936; color: var(--c); }
.nightMode .fig img, .night_mode .fig img { border-color: #2f3542; filter: brightness(.93); }
"""

TOPO = ('<div class="topo"><span>Saúde Coletiva I</span><span class="aula">{{Aula}}</span></div>')
KICKER = ('<div class="kicker">{{#Tema}}<span>{{Tema}}</span>{{/Tema}}'
          '{{#Prova}}<span class="selo">caiu em prova</span>{{/Prova}}</div>')
RODAPE = ('<div class="rodape">{{#Prova}}<span class="r-prova"><b>Caiu em</b>{{Prova}}</span>{{/Prova}}'
          '{{#Fonte}}<span class="r-fonte"><b>No PDF</b>{{Fonte}}</span>{{/Fonte}}</div>')
ABRE = '<div class="saco" data-aula="{{text:Aula}}">' + TOPO + '<div class="corpo">' + KICKER
FECHA = '</div></div>'

BASICO_FRENTE = (ABRE + '<div class="pergunta">{{Frente}}</div>'
                 '{{#ImagemFrente}}<div class="fig">{{ImagemFrente}}</div>{{/ImagemFrente}}' + FECHA)
BASICO_VERSO = (ABRE + '<div class="pergunta">{{Frente}}</div>'
                '{{#ImagemFrente}}<div class="fig">{{ImagemFrente}}</div>{{/ImagemFrente}}'
                '<hr id="answer"><div class="resposta">{{Verso}}</div>'
                '{{#Imagem}}<div class="fig">{{Imagem}}</div>{{/Imagem}}'
                '{{#Extra}}<div class="extra">{{Extra}}</div>{{/Extra}}' + RODAPE + FECHA)
CLOZE_FRENTE = ABRE + '<div class="texto">{{cloze:Texto}}</div>' + FECHA
CLOZE_VERSO = (ABRE + '<div class="texto">{{cloze:Texto}}</div>'
               '{{#Imagem}}<div class="fig">{{Imagem}}</div>{{/Imagem}}'
               '{{#Extra}}<div class="extra">{{Extra}}</div>{{/Extra}}' + RODAPE + FECHA)
OCLUSAO_FRENTE = (ABRE + '<div class="pergunta">{{Pergunta}}</div>'
                  '<div class="fig">{{ImagemOculta}}</div>' + FECHA)
OCLUSAO_VERSO = (ABRE + '<div class="pergunta">{{Pergunta}}</div>'
                 '<div class="fig">{{ImagemRevelada}}</div>'
                 '<hr id="answer"><div class="resposta">{{Resposta}}</div>'
                 '{{#Extra}}<div class="extra">{{Extra}}</div>{{/Extra}}' + RODAPE + FECHA)

CAMPOS_COMUNS = ["Extra", "Tema", "Prova", "Fonte", "Aula"]

MODELO_BASICO = genanki.Model(
    id_fixo("saco1", "modelo", "basico"), "SACO1 Básico",
    fields=[{"name": n} for n in ["Frente", "Verso", "ImagemFrente", "Imagem"] + CAMPOS_COMUNS],
    templates=[{"name": "Card", "qfmt": BASICO_FRENTE, "afmt": BASICO_VERSO}],
    css=CSS, sort_field_index=0,
)
MODELO_CLOZE = genanki.Model(
    id_fixo("saco1", "modelo", "cloze"), "SACO1 Lacunas",
    fields=[{"name": n} for n in ["Texto", "Imagem"] + CAMPOS_COMUNS],
    templates=[{"name": "Lacuna", "qfmt": CLOZE_FRENTE, "afmt": CLOZE_VERSO}],
    css=CSS, model_type=genanki.Model.CLOZE, sort_field_index=0,
)
MODELO_OCLUSAO = genanki.Model(
    id_fixo("saco1", "modelo", "oclusao"), "SACO1 Oclusão",
    fields=[{"name": n} for n in ["Pergunta", "ImagemOculta", "ImagemRevelada", "Resposta"] + CAMPOS_COMUNS],
    templates=[{"name": "Oclusão", "qfmt": OCLUSAO_FRENTE, "afmt": OCLUSAO_VERSO}],
    css=CSS, sort_field_index=0,
)


# ---------------------------------------------------------------- texto
def inline(t):
    t = t.strip()
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", t)
    return t


def html(t):
    """Markdown mínimo: **negrito**, *itálico*, listas com "- " e parágrafos separados por linha em branco."""
    if t is None:
        return ""
    blocos = [b for b in re.split(r"\n\s*\n", str(t).strip()) if b.strip()]
    lista = lambda b: all(l.lstrip().startswith("- ") for l in b.split("\n"))
    if len(blocos) == 1 and not lista(blocos[0]):
        return "<br>".join(inline(l) for l in blocos[0].split("\n"))
    out = []
    for b in blocos:
        if lista(b):
            out.append("<ul>" + "".join(f"<li>{inline(l.lstrip()[2:])}</li>" for l in b.split("\n")) + "</ul>")
        else:
            out.append("<p>" + "<br>".join(inline(l) for l in b.split("\n")) + "</p>")
    return "".join(out)


# ---------------------------------------------------------------- imagens
def localizar(nome):
    for d in (FONTE / "svg", FONTE / "img" / "web", FONTE / "img" / "slides", FONTE / "img", BUILD / "recortes"):
        p = d / nome
        if p.exists():
            return p
    raise FileNotFoundError(f"imagem não encontrada: {nome}")


# Nos quadros de três colunas, o texto fica ilegível numa tela de celular. Cada card de oclusão
# desses quadros leva também um recorte da coluna (ou do bloco) em jogo, que substitui o quadro
# inteiro quando a tela tem até 520 px. Caixas (x, y, largura, altura) no viewBox de cada SVG.
def _colunas(prefixo, chaves, x0, w, gap, y, h, folga=8):
    return {f"{prefixo}-oculta-{k}.svg": (x0 + i * (w + gap) - folga, y, w + 2 * folga, h)
            for i, k in enumerate(chaves)}


RECORTES = {
    **_colunas("p3-previdencia", ("caps", "iaps", "inps"), 14, 592 / 3, 30, 2, 326, folga=2),
    **_colunas("p4-protecao", ("seguridade", "seguro", "assistencia"), 14, 628 / 3, 12, 2, 336),
    **_colunas("p4-tripe", ("previdencia", "saude", "assistencia"), 39, 186, 22, 82, 162),
    **_colunas("p4-principios", ("doutrinarios", "organizativos"), 14, 316, 20, 64, 210),
}


def nome_recorte(oculta, revelada=False):
    return f"{Path(oculta).stem}-celular{'-revelada' if revelada else ''}.svg"


def gravar_recortes(cards):
    """Grava em _build/recortes as cópias dos SVGs com o viewBox reduzido à caixa de cada card."""
    pasta = BUILD / "recortes"
    pasta.mkdir(parents=True, exist_ok=True)
    for c in cards:
        caixa = RECORTES.get(c.get("oculta"))
        if not caixa:
            continue
        vb = 'viewBox="{:.1f} {:.1f} {:.1f} {:.1f}" style="overflow: hidden"'.format(*caixa)
        for chave, revelada in (("oculta", False), ("revelada", True)):
            svg = re.sub(r'viewBox="[^"]*"', vb, localizar(c[chave]).read_text(), count=1)
            svg = re.sub(r'<path d="M340,46 [^>]*/>', "", svg)  # conectores do topo de p4-principios
            destino = pasta / nome_recorte(c["oculta"], revelada)
            if not destino.exists() or destino.read_text() != svg:
                destino.write_text(svg)


def midia_nome(nome):
    p = Path(nome)
    ext = ".png" if p.suffix == ".svg" else p.suffix
    return f"saco1-{p.stem}{ext}"


def salvar_limitado(img, destino, foto):
    """Salva a imagem abaixo de LIMITE, reduzindo qualidade e tamanho se preciso."""
    largura = img.width
    while True:
        if foto:
            for q in (84, 80, 76, 72, 68, 64):
                buf = io.BytesIO()
                img.convert("RGB").save(buf, "JPEG", quality=q, optimize=True, progressive=True)
                if buf.tell() <= LIMITE:
                    destino.write_bytes(buf.getvalue())
                    return
        else:
            buf = io.BytesIO()
            img.convert("RGB").quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(
                buf, "PNG", optimize=True)
            if buf.tell() <= LIMITE:
                destino.write_bytes(buf.getvalue())
                return
        largura = int(largura * 0.88)
        img = img.resize((largura, round(img.height * largura / img.width)), Image.LANCZOS)


def preparar_midia(nomes):
    """Converte as imagens citadas nos cards e devolve {nome original: caminho da mídia}."""
    (BUILD / "png").mkdir(parents=True, exist_ok=True)
    (BUILD / "midia").mkdir(parents=True, exist_ok=True)
    svgs = sorted({n for n in nomes if n.endswith(".svg")})
    faltam = [n for n in svgs if not (BUILD / "png" / (Path(n).stem + ".png")).exists()
              or (BUILD / "png" / (Path(n).stem + ".png")).stat().st_mtime < localizar(n).stat().st_mtime]
    for largura, grupo in (("1280", [n for n in faltam if "-celular" not in n]),
                           ("720", [str(localizar(n)) for n in faltam if "-celular" in n])):
        if grupo:
            subprocess.run([sys.executable, str(FONTE / "rasterizar.py"), str(BUILD / "png"), largura, *grupo],
                           check=True, stdout=subprocess.DEVNULL)
    mapa = {}
    for n in sorted(set(nomes)):
        destino = BUILD / "midia" / midia_nome(n)
        origem = BUILD / "png" / (Path(n).stem + ".png") if n.endswith(".svg") else localizar(n)
        if not destino.exists() or destino.stat().st_mtime < origem.stat().st_mtime:
            img = Image.open(origem)
            if n.endswith(".svg"):
                foto = False
            elif origem.suffix.lower() in (".jpg", ".jpeg"):
                foto = True
            else:  # PNG: foto se tiver cores demais para uma paleta
                foto = img.convert("RGB").getcolors(1 << 16) is None
            if foto:
                img.thumbnail((1000, 900), Image.LANCZOS)
            salvar_limitado(img, destino, foto)
        mapa[n] = destino
    return mapa


def tag_img(nome, alt=""):
    return f'<img src="{midia_nome(nome)}" alt="{alt}">' if nome else ""


def tag_oclusao(c, chave):
    """Imagem do card de oclusão; com recorte, leva as duas versões e o CSS escolhe pela largura da tela."""
    if c["oculta"] not in RECORTES:
        return tag_img(c[chave])
    cel = nome_recorte(c["oculta"], chave == "revelada")
    return (f'<img class="com-recorte" src="{midia_nome(c[chave])}" alt="">'
            f'<img class="recorte" src="{midia_nome(cel)}" alt="">')


# ---------------------------------------------------------------- notas
def campos_comuns(c, aula):
    return [html(c.get("extra")), inline(str(c.get("tema", ""))), inline(str(c.get("prova", ""))),
            inline(str(c.get("fonte", ""))), f"Aula {aula} · {NOMES[aula]}"]


# Toda nota leva a tag da versão. Importar não apaga as notas que saíram do baralho;
# quem já tinha a versão anterior as encontra com: "deck:SACO 1" -tag:SACO1::versao::2026-10-04
VERSAO = "2026-10-04"


def nota(c, aula):
    tags = [f"SACO1::Aula{aula}::{c['tag']}", f"SACO1::versao::{VERSAO}"]
    if c.get("prova"):
        tags.append("SACO1::prova")
    guid = genanki.guid_for("saco1", aula, c["id"])
    if "cloze" in c:
        f = [html(c["cloze"]), tag_img(c.get("img"))] + campos_comuns(c, aula)
        return genanki.Note(model=MODELO_CLOZE, fields=f, tags=tags, guid=guid)
    if "oculta" in c:
        f = [html(c["frente"]), tag_oclusao(c, "oculta"), tag_oclusao(c, "revelada"), html(c["verso"])] + campos_comuns(c, aula)
        return genanki.Note(model=MODELO_OCLUSAO, fields=f, tags=tags, guid=guid)
    f = [html(c["frente"]), html(c["verso"]), tag_img(c.get("img_frente")), tag_img(c.get("img"))] + campos_comuns(c, aula)
    return genanki.Note(model=MODELO_BASICO, fields=f, tags=tags, guid=guid)


def imagens_do_card(c):
    nomes = [c[k] for k in ("img", "img_frente", "oculta", "revelada") if c.get(k)]
    if c.get("oculta") in RECORTES:
        nomes += [nome_recorte(c["oculta"]), nome_recorte(c["oculta"], True)]
    return nomes


def carregar(aula):
    dados = yaml.safe_load((AQUI / f"aula{aula}.yaml").read_text())
    ids = set()
    for c in dados["cards"]:
        assert c["id"] not in ids, f"id repetido: {c['id']}"
        ids.add(c["id"])
        assert "tag" in c, f"card sem tag: {c['id']}"
    gravar_recortes(dados["cards"])
    return dados


def baralho(aula, dados):
    d = genanki.Deck(id_fixo("saco1", "baralho", aula), f"SACO 1::Aula {aula} – {NOMES[aula]}")
    d.description = (f"<b>Saúde Coletiva I · Aula {aula}: {NOMES[aula]}</b><br>"
                     f"{len(dados['cards'])} notas ligadas ao PDF <i>{PDFS[aula]}</i>. "
                     f"As tags <code>SACO1::Aula{aula}::…</code> seguem as seções do PDF; "
                     "<code>SACO1::prova</code> marca o que já caiu em prova.")
    for c in dados["cards"]:
        d.add_note(nota(c, aula))
    return d


def fontes_midia():
    (BUILD / "midia").mkdir(parents=True, exist_ok=True)
    out = []
    for destino, origem in FONTES.items():
        p = BUILD / "midia" / destino
        shutil.copyfile(FONTE / "estilo" / "fonts" / origem, p)
        out.append(p)
    return out


def main(aulas):
    SAIDA.mkdir(exist_ok=True)
    fontes = fontes_midia()
    todos_decks, toda_midia = [], set(fontes)
    for aula in aulas:
        dados = carregar(aula)
        nomes = [n for c in dados["cards"] for n in imagens_do_card(c)]
        mapa = preparar_midia(nomes)
        d = baralho(aula, dados)
        pacote = genanki.Package(d)
        pacote.media_files = [str(p) for p in fontes] + [str(p) for p in mapa.values()]
        pacote.write_to_file(str(SAIDA / ARQUIVOS[aula]))
        n_cards = sum(len(n.cards) for n in d.notes)
        tam = sum(p.stat().st_size for p in mapa.values())
        print(f"Aula {aula}: {len(d.notes)} notas, {n_cards} cards, {len(mapa)} imagens ({tam/1024:.0f} KB) -> {ARQUIVOS[aula]}")
        todos_decks.append(d)
        toda_midia |= set(mapa.values())
    if len(aulas) == 4:
        pacote = genanki.Package(todos_decks)
        pacote.media_files = sorted(str(p) for p in toda_midia)
        pacote.write_to_file(str(SAIDA / "SACO1-Completo.apkg"))
        print("Pacote completo -> SACO1-Completo.apkg")


if __name__ == "__main__":
    escolhidas = [int(a) for a in sys.argv[1:]] or [1, 2, 3, 4]
    main(escolhidas)
