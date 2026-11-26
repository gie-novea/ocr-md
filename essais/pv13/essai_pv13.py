"""Essai PV-13 : détection des cellules fusionnées et rendu HTML des tableaux.

Page 1 : tableau simple (une ligne d'en-tête, aucune fusion).
Page 2 : tableau à double en-tête et cellules fusionnées (colspan et rowspan).
Version native (traits vectoriels) puis version scannée avec calque OCR Windows.
Relevés : find_tables (cellules None = fusion), to_markdown en Markdown et en HTML
(table_output="html") : présence de lignes « | », de <table>, de colspan/rowspan,
valeurs de cellules retrouvées.
Usage : ../.venv/Scripts/python essai_pv13.py
"""

import io
import json
import pathlib
import sys

import pymupdf
from PIL import Image

ICI = pathlib.Path(__file__).parent
sys.path.insert(0, str(ICI.parent / "commun"))
sys.path.insert(0, str(ICI.parent / "pv04"))
sys.path.insert(0, str(ICI.parent / "pv06"))
SORTIE = ICI / "sortie"
SORTIE.mkdir(exist_ok=True)

CSS = "table{border-collapse:collapse} td,th{border:1px solid black;padding:4px;font-size:11px}"
SIMPLE = """<table><tr><th>Intervenant</th><th>Fonction</th><th>Jours</th></tr>
<tr><td>Mme Durand</td><td>Architecte</td><td>42</td></tr>
<tr><td>M. Martin</td><td>Ingénieur fluides</td><td>18</td></tr></table>"""
FUSION = """<table>
<tr><th rowspan="2">Lot</th><th colspan="2">Montants</th><th rowspan="2">Délai</th></tr>
<tr><th>Tranche ferme</th><th>Tranche optionnelle</th></tr>
<tr><td>Gros œuvre</td><td>125 000 €</td><td>30 000 €</td><td rowspan="2">12 mois</td></tr>
<tr><td>Charpente</td><td colspan="2">48 500 € forfait global</td></tr>
</table>"""
VALEURS_FUSION = ["Lot", "Montants", "Délai", "Tranche ferme", "Tranche optionnelle", "Gros œuvre",
                  "125 000 €", "30 000 €", "12 mois", "Charpente", "48 500 € forfait global"]


def fabriquer_natif(chemin):
    doc = pymupdf.open()
    for html in (SIMPLE, FUSION):
        page = doc.new_page(width=595, height=842)
        page.insert_htmlbox(pymupdf.Rect(60, 80, 535, 400), html, css=CSS)
    doc.save(chemin)


def fabriquer_scanne(natif, chemin):
    import ocr_windows_proto as ow
    from essai_pv06 import ecrire_calque
    moteur = ow.creer_moteur()
    src = pymupdf.open(natif)
    doc = pymupdf.open()
    for p in src:
        pix = p.get_pixmap(dpi=300, colorspace=pymupdf.csGRAY)
        img = Image.frombytes("L", (pix.width, pix.height), pix.samples)
        tampon = io.BytesIO()
        img.save(tampon, "JPEG", quality=85)
        page = doc.new_page(width=p.rect.width, height=p.rect.height)
        page.insert_image(page.rect, stream=tampon.getvalue())
        lignes, _ = ow.reconnaitre(moteur, img)
        mots = [(m[0], m[1]) for l in lignes for m in l]
        ecrire_calque(page, mots, *img.size)
    doc.save(chemin)


def analyser(chemin):
    import pymupdf4llm
    doc = pymupdf.open(chemin)
    res = {"find_tables": []}
    for p in doc:
        tabs = p.find_tables()
        info = []
        for t in tabs.tables:
            lignes = [[c is None for c in r.cells] for r in t.rows]
            info.append({"lignes": t.row_count, "colonnes": t.col_count,
                         "cellules_none": sum(sum(x) for x in lignes),
                         "en_tete_externe": t.header.external,
                         "en_tete": t.header.names, "extrait": t.extract()})
        res["find_tables"].append(info)
    for mode, opts in (("markdown", {}), ("html", {"table_output": "html"})):
        morceaux = pymupdf4llm.to_markdown(chemin, page_chunks=True, use_ocr=False, **opts)
        res[mode] = []
        for i, m in enumerate(morceaux):
            t = m["text"]
            res[mode].append({"lignes_pipe": sum(1 for l in t.splitlines() if l.startswith("|")),
                              "table_html": "<table" in t, "colspan": "colspan" in t,
                              "rowspan": "rowspan" in t,
                              "valeurs_absentes": [v for v in VALEURS_FUSION if v not in t]
                              if i == 1 else None})
            (SORTIE / f"{pathlib.Path(chemin).stem}_{mode}_p{i + 1}.md").write_text(t, encoding="utf-8")
    return res


def main():
    natif = SORTIE / "tableaux_natif.pdf"
    scanne = SORTIE / "tableaux_scanne.pdf"
    fabriquer_natif(natif)
    fabriquer_scanne(natif, scanne)
    res = {"natif": analyser(str(natif)), "scanne": analyser(str(scanne))}
    texte = json.dumps(res, ensure_ascii=False, indent=1)
    (SORTIE / "resultat_pv13.json").write_text(texte, encoding="utf-8")
    print(texte)


if __name__ == "__main__":
    main()
