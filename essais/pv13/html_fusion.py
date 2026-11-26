"""Essai complémentaire PV-13 : reconstruire colspan et rowspan à partir de find_tables.

Les cellules de Table.cells sont des boîtes ; les lignes et colonnes de la grille sont
déduites des bords ; une cellule couvrant plusieurs intervalles reçoit colspan/rowspan.
"""
import html
import sys

import pymupdf


def table_html(page, table):
    xs = sorted({round(c[0], 1) for c in table.cells if c} | {round(c[2], 1) for c in table.cells if c})
    ys = sorted({round(c[1], 1) for c in table.cells if c} | {round(c[3], 1) for c in table.cells if c})
    occupe = set()
    lignes_html = []
    cellules = sorted({tuple(round(v, 1) for v in c) for c in table.cells if c}, key=lambda c: (c[1], c[0]))
    par_ligne = {}
    for c in cellules:
        par_ligne.setdefault(ys.index(c[1]), []).append(c)
    for i in range(len(ys) - 1):
        tds = []
        for c in par_ligne.get(i, []):
            j = xs.index(c[0])
            cs = xs.index(c[2]) - j
            rs = ys.index(c[3]) - i
            texte = page.get_textbox(pymupdf.Rect(c)).strip().replace("\n", " ")
            attrs = (f' colspan="{cs}"' if cs > 1 else "") + (f' rowspan="{rs}"' if rs > 1 else "")
            tds.append(f"<td{attrs}>{html.escape(texte)}</td>")
        lignes_html.append("<tr>" + "".join(tds) + "</tr>")
    return "<table>" + "".join(lignes_html) + "</table>"


doc = pymupdf.open(sys.argv[1])
p = doc[1]
for t in p.find_tables().tables:
    print(table_html(p, t))
