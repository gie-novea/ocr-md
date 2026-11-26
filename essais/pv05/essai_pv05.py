"""Essai PV-05 : ocr_function de PyMuPDF4LLM et reprise du texte invisible.

Fabrique un PDF synthétique de 3 pages :
  page 1 : texte natif visible (mot unique ALPHAMOT) ;
  page 2 : image de texte + calque invisible (mode de rendu 3) posé à l'avance (BETAMOT) ;
  page 3 : image de texte sans aucune couche texte (GAMMAMOT).
Puis appelle to_markdown avec une ocr_function instrumentée et relève :
  - le nombre et les pages des appels de l'ocr_function ;
  - la présence des mots uniques dans le Markdown de chaque page ;
  - l'effet de use_ocr=False, force_text, ignore_alpha ;
  - toute mention de Tesseract ou de RapidOCR dans les messages.
Usage : ../.venv/Scripts/python essai_pv05.py
"""

import contextlib
import hashlib
import io
import json
import pathlib
import sys

import pymupdf

ICI = pathlib.Path(__file__).parent
SORTIE = ICI / "sortie"
SORTIE.mkdir(exist_ok=True)
POLICE = pymupdf.Font("notos")  # Noto Sans, OFL, paquet pymupdf-fonts
TEXTE = "Œuvre à réaliser : coût 1 250 € « clé en main », déjà prévu l’été."


def page_texte(doc, mot):
    """Ajoute une page de texte natif visible et la renvoie."""
    page = doc.new_page(width=595, height=842)
    page.insert_font(fontname="notos", fontbuffer=POLICE.buffer)
    page.insert_text((72, 100), f"{mot} {TEXTE}", fontname="notos", fontsize=12)
    page.insert_text((72, 130), "Deuxième ligne de contrôle.", fontname="notos", fontsize=12)
    return page


def image_de(mot, dpi=300):
    """Rend une page de texte en image PNG (simule un scan)."""
    tmp = pymupdf.open()
    page_texte(tmp, mot)
    return tmp[0].get_pixmap(dpi=dpi).tobytes("png")


def ecrire_invisible(page, lignes):
    """Pose un calque invisible (mode de rendu 3) ; lignes = [(x, y, texte)]."""
    page.insert_font(fontname="notos", fontbuffer=POLICE.buffer)
    for x, y, texte in lignes:
        page.insert_text((x, y), texte, fontname="notos", fontsize=12, render_mode=3)


def fabriquer(chemin):
    doc = pymupdf.open()
    page_texte(doc, "ALPHAMOT")
    p2 = doc.new_page(width=595, height=842)
    p2.insert_image(p2.rect, stream=image_de("BETAMOT"))
    ecrire_invisible(p2, [(72, 100, f"BETAMOT {TEXTE}"), (72, 130, "Deuxième ligne de contrôle.")])
    p3 = doc.new_page(width=595, height=842)
    p3.insert_image(p3.rect, stream=image_de("GAMMAMOT"))
    doc.save(chemin, garbage=3, deflate=True)


APPELS = []


def ocr_instrumentee(page, dpi=300, pixmap=None, language="eng", keep_ocr_text=False, **kw):
    """Adaptateur factice conforme au contrat : écrit un calque invisible sur la page."""
    APPELS.append({"page": page.number + 1, "dpi": dpi, "language": language,
                   "keep_ocr_text": keep_ocr_text, "pixmap": pixmap is not None,
                   "autres": sorted(kw)})
    ecrire_invisible(page, [(72, 100, f"GAMMAMOT {TEXTE}"), (72, 130, "Deuxième ligne de contrôle.")])


def convertir(chemin, **options):
    import pymupdf4llm
    APPELS.clear()
    tampon = io.StringIO()
    with contextlib.redirect_stdout(tampon), contextlib.redirect_stderr(tampon):
        morceaux = pymupdf4llm.to_markdown(str(chemin), page_chunks=True, **options)
    messages = tampon.getvalue()
    pages = {}
    for i, m in enumerate(morceaux, 1):
        t = m["text"]
        pages[i] = {mot: (mot in t) for mot in ("ALPHAMOT", "BETAMOT", "GAMMAMOT")}
        pages[i]["accents_ok"] = all(c in t for c in "Œà€«»’é")
    return {
        "options": {k: (v.__name__ if callable(v) else v) for k, v in options.items()},
        "appels_ocr": list(APPELS),
        "pages": pages,
        "cles_morceau": sorted(morceaux[0].keys()),
        "mention_tesseract": "esseract" in messages,
        "mention_rapidocr": "RapidOCR" in messages,
        "messages": messages.strip().splitlines()[-5:],
    }


def main():
    import importlib.metadata as md
    chemin = SORTIE / "pv05_trois_pages.pdf"
    fabriquer(chemin)
    empreinte = hashlib.sha256(chemin.read_bytes()).hexdigest()
    res = {
        "versions": {p: md.version(p) for p in ("pymupdf", "pymupdf4llm", "pymupdf_layout")},
        "python": sys.version.split()[0],
        "document_to_markdown": hasattr(pymupdf.Document, "to_markdown"),
        "essais": [
            convertir(chemin, ocr_function=ocr_instrumentee),
            convertir(chemin, ocr_function=ocr_instrumentee, force_text=False),
            convertir(chemin, ocr_function=ocr_instrumentee, ignore_alpha=True),
            convertir(chemin, use_ocr=False),
            convertir(chemin, ocr_function=ocr_instrumentee, force_ocr=True),
        ],
    }
    res["source_inchangee"] = hashlib.sha256(chemin.read_bytes()).hexdigest() == empreinte
    texte = json.dumps(res, ensure_ascii=False, indent=1)
    (SORTIE / "resultat_pv05.json").write_text(texte, encoding="utf-8")
    print(texte)


if __name__ == "__main__":
    main()
