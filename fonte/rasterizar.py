#!/usr/bin/env python3
"""Converte diagramas SVG em PNG (com as fontes e cores da parte) para os cards e para revisão.

Uso: python3 fonte/rasterizar.py SAIDA_DIR largura_px p1-hnd.svg [p2-dw.svg ...]
A parte (cor) é deduzida do prefixo do arquivo (p1-, p2-...).
"""
import asyncio
import sys
from pathlib import Path

FONTE = Path(__file__).resolve().parent


async def main(out, width, names):
    from playwright.async_api import async_playwright
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    css = (FONTE / "estilo" / "base.css").as_uri()
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(device_scale_factor=2, viewport={"width": width // 2, "height": 800})
        for name in names:
            parte = name[1] if name.startswith("p") and name[1].isdigit() else "1"
            src = (FONTE / "svg" / name).read_text() if not name.startswith("/") else Path(name).read_text()
            html = (f'<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="{css}">'
                    f'<style>@page{{margin:0}} body{{margin:0;background:#fff}} #w{{width:{width//2}px;padding:10px;box-sizing:border-box}}</style>'
                    f'</head><body class="p{parte}"><div id="w">{src}</div></body></html>')
            tmp = FONTE / "_raster.html"
            tmp.write_text(html)
            await pg.goto(tmp.as_uri())
            await pg.evaluate("document.fonts.ready")
            el = await pg.query_selector("#w")
            dst = out / (Path(name).stem + ".png")
            await el.screenshot(path=str(dst))
            print("png", dst.name)
        await b.close()
        (FONTE / "_raster.html").unlink(missing_ok=True)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], int(sys.argv[2]), sys.argv[3:]))
