"""Ventilation du temps de conversion d'un PDF par étape (recette du 27/11/2026).

Usage, en local, sur un fichier quelconque (aucun texte n'est affiché, seulement des durées) :
    uv run python tests/perf/ventiler.py FICHIER.pdf [--tableaux auto|md|html]

Étapes mesurées : ouverture et classification des pages, extraction Markdown par
PyMuPDF4LLM (dont analyse de mise en page par le modèle pymupdf-layout), détection des
tableaux natifs (`find_tables`) et rendu HTML des tableaux complexes (dont seconde passe de
la bibliothèque, repli de EX-44). Les compteurs sont posés en enveloppant les fonctions de
la bibliothèque le temps de la mesure ; le fichier n'est pas modifié.
"""

import argparse
import collections
import contextlib
import pathlib
import sys
import time

if __package__ in (None, ""):
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import pymupdf  # noqa: E402

from ocr_md import analyse_pdf, config, correctifs, markdown_pdf  # noqa: E402

DUREES: dict[str, float] = collections.defaultdict(float)
APPELS: dict[str, int] = collections.Counter()


@contextlib.contextmanager
def chronometre(objet, nom: str, etiquette: str):
    origine = getattr(objet, nom)

    def enveloppe(*args, **kwargs):
        t = time.perf_counter()
        try:
            return origine(*args, **kwargs)
        finally:
            DUREES[etiquette] += time.perf_counter() - t
            APPELS[etiquette] += 1

    setattr(objet, nom, enveloppe)
    try:
        yield
    finally:
        setattr(objet, nom, origine)


def ventiler(chemin: pathlib.Path, tableaux: str = "auto") -> dict:
    import tempfile

    import pymupdf.layout  # noqa: F401  (chargé comme dans l'outil)
    import pymupdf4llm  # noqa: F401
    correctifs.appliquer()
    p = config.charger()
    # Chauffe, hors mesure : chargement du modèle de mise en page sur une page d'essai.
    with tempfile.TemporaryDirectory() as d:
        essai = pymupdf.open()
        essai.new_page().insert_text((72, 72), "Chauffe du modèle de mise en page.")
        essai.save(pathlib.Path(d) / "chauffe.pdf")
        essai.close()
        markdown_pdf.convertir(str(pathlib.Path(d) / "chauffe.pdf"))
    DUREES.clear()
    APPELS.clear()
    t0 = time.perf_counter()
    doc = pymupdf.open(chemin)
    analyses = analyse_pdf.analyser(doc, p)
    pages = doc.page_count
    doc.close()
    DUREES["ouverture et classification"] = time.perf_counter() - t0
    with chronometre(pymupdf, "_get_layout", "mise en page (modèle pymupdf-layout)"), \
            chronometre(markdown_pdf, "_to_markdown", "PyMuPDF4LLM (total, mise en page comprise)"), \
            chronometre(pymupdf.Page, "find_tables", "détection des tableaux natifs"), \
            chronometre(markdown_pdf, "_rendre_tableaux_natifs", "tableaux complexes (détection et rendu HTML)"):
        t1 = time.perf_counter()
        markdown_pdf.convertir(str(chemin), tableaux=tableaux)
        DUREES["conversion Markdown (total)"] = time.perf_counter() - t1
    categories = collections.Counter(a.categorie for a in analyses)
    return {"pages": pages, "categories": dict(categories), "durees": dict(DUREES), "appels": dict(APPELS)}


def main(arguments=None) -> int:
    a = argparse.ArgumentParser(description="Ventilation du temps de conversion d'un PDF")
    a.add_argument("fichier")
    a.add_argument("--tableaux", choices=("auto", "md", "html"), default="auto")
    o = a.parse_args(arguments)
    pymupdf.TOOLS.mupdf_display_errors(False)
    # Premier appel à vide : chargement du modèle, hors mesure.
    with contextlib.redirect_stdout(None):
        r = ventiler(pathlib.Path(o.fichier), o.tableaux)
    print(f"{r['pages']} page(s) : " + ", ".join(f"{k} {v}" for k, v in r["categories"].items()))
    for etape, duree in r["durees"].items():
        appels = r["appels"].get(etape)
        print(f"  {etape} : {duree:.2f} s" + (f" ({appels} appel(s))" if appels else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
