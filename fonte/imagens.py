#!/usr/bin/env python3
"""Prepara as imagens usadas no material.

- recorta slides das aulas (PDFs originais renderizados a 200 dpi em /root/build/hi)
- redimensiona as imagens livres (Wikimedia Commons) baixadas para
  /mnt/project-files/material-saco1/imagens-web
- gera as imagens de capa

Saída: fonte/img/slides/*.jpg, fonte/img/web/*.jpg|png
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps

FONTE = Path(__file__).resolve().parent
HI = Path("/root/build/hi")
WEB = Path("/mnt/project-files/material-saco1/imagens-web")
OUT_S = FONTE / "img" / "slides"
OUT_W = FONTE / "img" / "web"

# slides usados: (aula, número do slide)
SLIDES = {
    1: [4, 9, 10, 16, 18],
    2: [4, 5, 7, 8, 9, 10, 13, 14, 15, 16, 29, 30, 35],
    3: [3, 4, 7, 8, 9, 10, 13, 14, 16, 17, 22, 23, 28, 29],
    4: [3, 4, 9, 10, 13, 14, 16, 17, 20, 22, 23, 28, 30, 33, 35, 36],
}

# recortes quadrados para as capas: arquivo, caixa relativa (x0, y0, x1, y1)
CAPAS = {
    "p1-hero.jpg": ("p1-higia.jpg", (0.02, 0.0, 0.98, 0.42)),
    "p2-hero.jpg": ("p2-horta.jpg", (0.05, 0.0, 0.8, 1.0)),
    "p3-hero.jpg": ("p3-revolta-vacina.png", (0.0, 0.0, 1.0, 1.0)),
    "p4-hero.jpg": ("p4-ulysses.jpg", (0.0, 0.0, 1.0, 1.0)),
}


def slide_box(page_img, pos):
    """pos 0 = slide de cima, 1 = slide de baixo; caixa detectada (moldura do slide)"""
    im = page_img.convert("L")
    w, h = im.size
    y0, y1 = ((0.04, 0.5), (0.5, 0.96))[pos]
    reg = im.crop((0, int(h * y0), w, int(h * y1)))
    bb = reg.point(lambda p: 255 if p < 140 else 0).getbbox()
    return (bb[0], bb[1] + int(h * y0), bb[2], bb[3] + int(h * y0))


def slides():
    OUT_S.mkdir(parents=True, exist_ok=True)
    for aula, nums in SLIDES.items():
        for n in nums:
            page = (n + 1) // 2
            pos = 0 if n % 2 == 1 else 1
            cands = sorted(HI.glob(f"a{aula}-{page:02d}.png")) or sorted(HI.glob(f"a{aula}-{page}.png"))
            if not cands:
                print("sem página", aula, n)
                continue
            img = Image.open(cands[0])
            box = slide_box(img, pos)
            crop = img.crop((box[0] + 3, box[1] + 3, box[2] - 3, box[3] - 3)).convert("L")
            crop = ImageOps.autocontrast(crop, cutoff=0.5)
            crop = ImageEnhance.Sharpness(crop).enhance(1.3)
            crop.thumbnail((1100, 1100), Image.LANCZOS)
            dst = OUT_S / f"a{aula}-s{n:02d}.jpg"
            crop.save(dst, quality=84, optimize=True, progressive=True)
            print("slide", dst.name, crop.size)


def web():
    OUT_W.mkdir(parents=True, exist_ok=True)
    cred = json.loads((WEB / "creditos.json").read_text())
    for it in cred:
        src = WEB / it["arquivo"]
        if not src.exists():
            continue
        im = Image.open(src)
        im = ImageOps.exif_transpose(im)
        line_art = src.suffix == ".png" and it["arquivo"].split("-")[1] in ("mapa", "tabaco", "sus")
        if im.mode in ("RGBA", "LA", "P"):
            bg = Image.new("RGB", im.size, "white")
            bg.paste(im.convert("RGBA"), mask=im.convert("RGBA").split()[-1])
            im = bg
        im = im.convert("RGB")
        im.thumbnail((1400, 1400), Image.LANCZOS)
        if line_art:
            dst = OUT_W / (src.stem + ".png")
            im.save(dst, optimize=True)
        else:
            dst = OUT_W / (src.stem + ".jpg")
            im.save(dst, quality=84, optimize=True, progressive=True)
    print("web: ok")


def capas():
    for out, (src, (x0, y0, x1, y1)) in CAPAS.items():
        p = WEB / src
        if not p.exists():
            continue
        im = Image.open(p).convert("RGB")
        w, h = im.size
        box = (int(w * x0), int(h * y0), int(w * x1), int(h * y1))
        im = im.crop(box)
        # quadrado centralizado
        w, h = im.size
        s = min(w, h)
        im = im.crop(((w - s) // 2, 0, (w - s) // 2 + s, s))
        im = im.resize((1100, 1100), Image.LANCZOS)
        im.save(OUT_W / out, quality=86, optimize=True, progressive=True)
        print("capa", out)


if __name__ == "__main__":
    what = sys.argv[1:] or ["slides", "web", "capas"]
    for w in what:
        globals()[w]()
