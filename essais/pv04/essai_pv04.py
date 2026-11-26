"""Essai PV-04 : OCR Windows par la projection PyWinRT, puis chaîne complète.

Mesures :
  1. langues, MaxImageDimension, durée par page ;
  2. taux de mots de référence retrouvés (page droite, page inclinée et bruitée, page floue) ;
  3. caractères exigés par EX-30 restitués ou non par le moteur ;
  4. calibrage boîte de ligne / taille de police réelle (pour le calque) ;
  5. TextAngle sur la page inclinée ;
  6. page A0 : réduction de résolution sous MaxImageDimension ;
  7. chaîne complète : OCR Windows -> calque (fonction de PV-06) -> pdftotext ->
     Markdown PyMuPDF4LLM avec adaptateur compteur (0 appel attendu) ;
  8. lancement sans console par pythonw.exe.
Usage : ../.venv/Scripts/python essai_pv04.py
"""

import io
import json
import pathlib
import re
import subprocess
import sys
import time
import unicodedata

import pymupdf
from PIL import Image

ICI = pathlib.Path(__file__).parent
sys.path.insert(0, str(ICI.parent / "commun"))
sys.path.insert(0, str(ICI.parent / "pv06"))
import fabrication as fab  # noqa: E402
import ocr_windows_proto as ow  # noqa: E402
from essai_pv06 import ecrire_calque  # noqa: E402

SORTIE = ICI / "sortie"
SORTIE.mkdir(exist_ok=True)
DPI = 300
TAILLE_PT = 12


def normaliser(mot):
    mot = unicodedata.normalize("NFC", mot)
    return re.sub(r"^[^\w€]+|[^\w€]+$", "", mot)


def mots_reference():
    return [normaliser(m) for m in (" ".join(fab.LIGNES_REFERENCE)).split() if normaliser(m)]


def taux_retrouves(texte_lu):
    lus = {normaliser(m) for m in texte_lu.split()}
    ref = mots_reference()
    absents = [m for m in ref if m not in lus]
    return round(1 - len(absents) / len(ref), 3), absents


def reconnaitre_page(moteur, img):
    t0 = time.perf_counter()
    lignes, angle = ow.reconnaitre(moteur, img)
    duree = time.perf_counter() - t0
    texte = "\n".join(" ".join(m[0] for m in l) for l in lignes)
    return lignes, angle, duree, texte


def cas_scan(nom, **params):
    doc = pymupdf.open()
    native = fab.page_native(doc, fab.LIGNES_REFERENCE, mot_unique=f"MOTUNIQUE{nom}")
    jpeg, taille, _ = fab.scanner(native, dpi=DPI, **params)
    return native, jpeg, Image.open(io.BytesIO(jpeg))


def calibrage_lignes(lignes):
    """Hauteur de l'union des boîtes de mots d'une ligne / taille de police réelle en px."""
    taille_px = TAILLE_PT * DPI / 72
    rapports = []
    for l in lignes:
        y0 = min(m[1][1] for m in l)
        y1 = max(m[1][3] for m in l)
        rapports.append(round((y1 - y0) / taille_px, 3))
    return rapports


def chaine_complete(moteur, cas):
    """PDF de pages scannées -> calque par OCR Windows -> pdftotext et Markdown."""
    doc = pymupdf.open()
    lignes_par_page = []
    for nom, native, jpeg, img in cas:
        page = doc.new_page(width=595, height=842)
        page.insert_image(page.rect, stream=jpeg)
        lignes, _, _, _ = reconnaitre_page(moteur, img)
        lignes_par_page.append(lignes)
        # Écriture par ligne : texte de la ligne, boîte union (stratégie « ligne »).
        elements = []
        for l in lignes:
            texte = " ".join(m[0] for m in l)
            elements.append((texte, (min(m[1][0] for m in l), min(m[1][1] for m in l),
                                     max(m[1][2] for m in l), max(m[1][3] for m in l))))
        ecrire_calque(page, elements, *img.size)
    doc.subset_fonts()
    chemin = SORTIE / "chaine_complete.pdf"
    doc.save(chemin, garbage=4, deflate=True)
    sortie_pdftotext = subprocess.run(["pdftotext", "-enc", "UTF-8", str(chemin), "-"],
                                      capture_output=True).stdout.decode("utf-8")
    pages_pdftotext = sortie_pdftotext.split("\f")

    import pymupdf4llm
    appels = []

    def adaptateur(page, dpi=300, pixmap=None, language="eng", keep_ocr_text=False, **kw):
        appels.append(page.number + 1)

    morceaux = pymupdf4llm.to_markdown(str(chemin), page_chunks=True, ocr_function=adaptateur,
                                       ocr_language="fra")
    res = []
    for i, (nom, *_r) in enumerate(cas):
        md = morceaux[i]["text"]
        mots_md = {normaliser(m) for m in md.split()}
        mots_pdf = {normaliser(m) for m in pages_pdftotext[i].split()}
        commun = len(mots_md & mots_pdf)
        res.append({
            "cas": nom,
            "retrouves_pdftotext": taux_retrouves(pages_pdftotext[i])[0],
            "retrouves_markdown": taux_retrouves(md)[0],
            "recouvrement_md_vs_pdftotext": round(commun / max(1, len(mots_pdf)), 3),
            "recouvrement_pdftotext_vs_md": round(commun / max(1, len(mots_md)), 3),
        })
    return {"appels_ocr_pendant_markdown": appels, "pages": res,
            "poids_pdf": chemin.stat().st_size}


def essai_a0(moteur):
    """Page A0 (841 x 1189 mm) : la résolution est réduite sous MaxImageDimension."""
    largeur_pt, hauteur_pt = 2384, 3370
    m = ow.dimension_max()
    dpi_max = int(m / (max(largeur_pt, hauteur_pt) / 72))
    dpi = min(DPI, dpi_max)
    doc = pymupdf.open()
    page = fab.page_native(doc, fab.LIGNES_REFERENCE, largeur=largeur_pt, hauteur=hauteur_pt,
                           taille=40)
    pix = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY)
    img = Image.frombytes("L", (pix.width, pix.height), pix.samples)
    erreur_a_300 = None
    try:
        big = page.get_pixmap(dpi=DPI, colorspace=pymupdf.csGRAY)
        ow.reconnaitre(moteur, Image.frombytes("L", (big.width, big.height), big.samples))
    except Exception as e:  # attendu : refus au-delà de la dimension maximale
        erreur_a_300 = f"{type(e).__name__}: {e}"
    lignes, _, duree, texte = reconnaitre_page(moteur, img)
    return {"dpi_retenu": dpi, "taille_px": img.size, "erreur_a_300_dpi": erreur_a_300,
            "retrouves": taux_retrouves(texte)[0], "duree_s": round(duree, 2)}


def essai_pythonw():
    """Lance un OCR par pythonw.exe (sans console) et lit le résultat écrit sur disque."""
    script = ICI / "_pythonw_ocr.py"
    resultat = SORTIE / "pythonw_resultat.json"
    resultat.unlink(missing_ok=True)
    script.write_text(
        "import io, json, sys, pathlib\n"
        f"sys.path.insert(0, r'{ICI.parent / 'commun'}'); sys.path.insert(0, r'{ICI}')\n"
        "import fabrication as fab, ocr_windows_proto as ow, pymupdf\n"
        "from PIL import Image\n"
        "d = pymupdf.open(); p = fab.page_native(d, fab.LIGNES_REFERENCE)\n"
        "jpg, _, _ = fab.scanner(p, 300)\n"
        "lignes, a = ow.reconnaitre(ow.creer_moteur(), Image.open(io.BytesIO(jpg)))\n"
        f"pathlib.Path(r'{resultat}').write_text(json.dumps({{'lignes': len(lignes)}}))\n",
        encoding="utf-8")
    pythonw = pathlib.Path(sys.executable).with_name("pythonw.exe")
    r = subprocess.run([str(pythonw), str(script)], timeout=120)
    script.unlink()
    return {"code_retour": r.returncode,
            "resultat": json.loads(resultat.read_text()) if resultat.exists() else None}


def main():
    import importlib.metadata as md
    moteur = ow.creer_moteur("fr-FR")
    res = {
        "versions": {p: md.version(p) for p in ("winrt-runtime", "winrt-Windows.Media.Ocr",
                                                "pymupdf")},
        "langues": ow.langues_disponibles(),
        "max_image_dimension": ow.dimension_max(),
        "langue_moteur": moteur.recognizer_language.language_tag,
    }
    cas = [
        ("droite", *cas_scan("droite", bruit=4)),
        ("inclinee", *cas_scan("inclinee", angle=1.5, bruit=12)),
        ("floue", *cas_scan("floue", flou=3.0, bruit=30, qualite_jpeg=40)),
    ]
    res["pages"] = []
    for nom, native, jpeg, img in cas:
        lignes, angle, duree, texte = reconnaitre_page(moteur, img)
        taux, absents = taux_retrouves(texte)
        res["pages"].append({
            "cas": nom, "duree_s": round(duree, 3), "text_angle": angle,
            "retrouves": taux, "absents": absents,
            "caracteres_exiges_absents": "".join(c for c in fab.CARACTERES_EXIGES if c not in texte),
            "rapport_hauteur_ligne_sur_taille": calibrage_lignes(lignes),
        })
    res["chaine_complete"] = chaine_complete(moteur, cas[:2])
    res["a0"] = essai_a0(moteur)
    res["pythonw"] = essai_pythonw()
    texte = json.dumps(res, ensure_ascii=False, indent=1)
    (SORTIE / "resultat_pv04.json").write_text(texte, encoding="utf-8")
    print(texte)


if __name__ == "__main__":
    main()
