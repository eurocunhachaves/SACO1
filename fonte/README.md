# Como gerar o material

Tudo o que está em `PDFs/` e `Flashcards/` sai desta pasta. Os comandos abaixo rodam a partir da raiz do repositório.

## Requisitos

```
python3 -m pip install markdown pyyaml pillow playwright pymupdf genanki fonttools brotli
python3 -m playwright install chromium
```

## Comandos

| O quê | Comando | Saída |
|---|---|---|
| Diagramas | `python3 fonte/diagramas.py [p1 p2 p3 p4]` | `fonte/svg/*.svg` |
| PDFs | `python3 fonte/build.py [1 2 3 4]` | `PDFs/*.pdf` |
| Flashcards | `python3 fonte/cards/gerar.py [1 2 3 4]` | `Flashcards/*.apkg` |
| Imagens | `python3 fonte/imagens.py` | `fonte/img/` |

Sem argumentos, cada comando gera tudo. O baralho completo (`SACO1-Completo.apkg`) só sai quando as quatro aulas são geradas juntas. O `imagens.py` serve apenas para reimportar as imagens: ele precisa das páginas dos slides originais renderizadas e das imagens baixadas do Wikimedia Commons, e o resultado já está no repositório.

## Onde mexer

- **Texto de uma parte:** `partes/parteN.md`. Além do Markdown comum, há caixas, quadros, questões de prova e figuras; a sintaxe está no topo de `build.py`.
- **Cards:** `cards/aulaN.yaml`. O formato está no topo de `cards/aula1.yaml`. Nunca mude nem reaproveite o `id` de um card: é por ele que o Anki reconhece o card ao importar de novo e mantém o histórico de revisões.
- **Visual:** `estilo/base.css` para os PDFs; o CSS dos cards fica em `cards/gerar.py`.
- **Diagramas:** cada um é uma função em `diagramas.py`. Os cards usam os mesmos SVGs, convertidos em PNG por `rasterizar.py`. As versões com partes escondidas (`*-oculta-*.svg`) alimentam os cards de oclusão.
- **Oclusão no celular:** quadros largos ganham um recorte da coluna em jogo, que substitui o quadro inteiro em telas de até 520 px. As caixas de recorte ficam em `RECORTES`, em `cards/gerar.py`.

## Conferir antes de publicar

- PDFs: `pdftoppm -r 70 -png PDFs/<arquivo>.pdf /tmp/paginas` e olhe as páginas, procurando linhas órfãs e figuras cortadas.
- Cards: importe o `.apkg` num perfil de teste do Anki e confira os cards novos no computador e no celular, no modo claro e no noturno.
