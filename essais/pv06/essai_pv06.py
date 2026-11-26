"""Essai PV-06 : écriture du calque texte invisible avec une police Unicode.

Cas testés (page A4, scan simulé à 300 dpi) :
  A droite ; B inclinée de 1,5 degré avec bruit ; C rotation 90 ; D rotation 270 ;
  E boîte de rognage décalée.
Deux stratégies : par ligne (étirement horizontal) et par mot (étirement par mot).
Contrôles : caractères restitués par pdftotext, mots retrouvés par search_for au bon
endroit (centre dans la boîte de vérité agrandie de 10 %), rendu 100 dpi inchangé,
flux image inchangé, poids avant et après sous-ensemble de police.
Usage : ../.venv/Scripts/python essai_pv06.py
"""

import hashlib
import json
import pathlib
import subprocess
import sys

import numpy as np
import pymupdf

sys.path.insert(0, str(pathlib.Path(__file__).parents[1] / "commun"))
import fabrication as fab  # noqa: E402

ICI = pathlib.Path(__file__).parent
SORTIE = ICI / "sortie"
SORTIE.mkdir(exist_ok=True)
DPI = 300
POLICE = fab.POLICE
NOM_POLICE = "ocrmd"
ASC, DESC = POLICE.ascender, POLICE.descender  # descender négatif


# ----------------------------------------------------------------------------------
# Fonction candidate pour le module calque : pixels de l'image rendue -> page
# ----------------------------------------------------------------------------------
def matrice_pixels_vers_page(page, largeur_px, hauteur_px):
    """Matrice qui envoie un point de l'image rendue de la page (telle qu'affichée,
    rotation appliquée) vers le repère non pivoté de la page utilisé par insert_text."""
    affiche = page.rect  # rectangle affiché (rotation appliquée), origine (0, 0)
    echelle = pymupdf.Matrix(affiche.width / largeur_px, affiche.height / hauteur_px)
    return echelle * page.derotation_matrix


def ecrire_calque(page, elements, largeur_px, hauteur_px, visible=False):
    """elements = [(texte, (x0, y0, x1, y1) en pixels de l'image affichée)]."""
    page.insert_font(fontname=NOM_POLICE, fontbuffer=POLICE.buffer)
    m = matrice_pixels_vers_page(page, largeur_px, hauteur_px)
    rot = page.rotation
    for texte, (x0, y0, x1, y1) in elements:
        if not texte.strip():
            continue
        # Boîte dans le repère affiché (points), puis coins dans le repère non pivoté.
        r = pymupdf.Rect(x0, y0, x1, y1) * pymupdf.Matrix(page.rect.width / largeur_px,
                                                         page.rect.height / hauteur_px)
        taille = r.height / (ASC - DESC)
        longueur = POLICE.text_length(texte, fontsize=taille)
        sx = r.width / longueur if longueur else 1
        # Point de base (repère affiché) : bas gauche relevé du jambage.
        base_affiche = pymupdf.Point(r.x0, r.y1 + DESC * taille)
        base = base_affiche * page.derotation_matrix
        # Étirement horizontal puis rotation du texte pour compenser la rotation de page.
        morph = (base, pymupdf.Matrix(sx, 1) * pymupdf.Matrix(rot))
        page.insert_text(base, texte, fontname=NOM_POLICE, fontsize=taille,
                         render_mode=0 if visible else 3, color=(1, 0, 0), morph=morph)
    return m


# ----------------------------------------------------------------------------------
# Fabrication des cas
# ----------------------------------------------------------------------------------
def cas(nom, rotation=0, angle=0.0, bruit=0.0, rognage=False):
    src = pymupdf.open()
    native = fab.page_native(src, fab.LIGNES_REFERENCE, mot_unique=f"MOTCAS{nom}")
    jpeg, (w, h), transfo = fab.scanner(native, dpi=DPI, angle=angle, bruit=bruit)
    doc = pymupdf.open()
    if rotation in (90, 270):
        page = doc.new_page(width=842, height=595)  # repère non pivoté couché
    else:
        page = doc.new_page(width=595, height=842)
    if rognage:
        page.set_mediabox(pymupdf.Rect(0, 0, 655, 922))
        page.set_cropbox(pymupdf.Rect(30, 40, 625, 882))
    page.set_rotation(rotation)
    # Insertion de l'image pour qu'elle apparaisse droite une fois la page pivotée.
    cible = page.rect * page.derotation_matrix
    page.insert_image(cible, stream=jpeg, rotate=rotation)
    return doc, native, (w, h), transfo


def verifier_affichage(doc, native):
    """Écart moyen entre le rendu affiché du scan et la page native (doit être faible)."""
    a = doc[0].get_pixmap(dpi=50, colorspace=pymupdf.csGRAY)
    b = native.get_pixmap(dpi=50, colorspace=pymupdf.csGRAY)
    if (a.width, a.height) != (b.width, b.height):
        return 999.0
    x = np.frombuffer(a.samples, np.uint8).astype(float)
    y = np.frombuffer(b.samples, np.uint8).astype(float)
    return float(np.abs(x - y).mean())


def rendu(page, dpi=100):
    return np.frombuffer(page.get_pixmap(dpi=dpi).samples, np.uint8).astype(int)


def flux_images(doc):
    return {x: hashlib.sha256(doc.xref_stream_raw(x)).hexdigest()
            for x in range(1, doc.xref_length()) if doc.xref_get_key(x, "Subtype")[1] == "/Image"}


def pdftotext(chemin):
    r = subprocess.run(["pdftotext", "-enc", "UTF-8", str(chemin), "-"], capture_output=True)
    return r.stdout.decode("utf-8", "replace")


def essai(nom, strategie, **params):
    doc, native, (w, h), transfo = cas(nom, **params)
    ecart_affichage = verifier_affichage(doc, native)
    page = doc[0]
    avant_rendu = rendu(page)
    avant_flux = flux_images(doc)
    chemin_sans = SORTIE / f"{nom}_{strategie}_sans_calque.pdf"
    doc.save(chemin_sans, garbage=4, deflate=True)
    elements = fab.ocr_simule(native, DPI, transfo, niveau=strategie)
    ecrire_calque(page, elements, w, h)
    apres_rendu = rendu(page)
    ecart_rendu = float(np.abs(avant_rendu - apres_rendu).mean())
    chemin = SORTIE / f"{nom}_{strategie}.pdf"
    doc.save(chemin, garbage=4, deflate=True)
    poids_complet = chemin.stat().st_size
    doc.subset_fonts()
    doc.save(chemin, garbage=4, deflate=True)
    poids_sous_ensemble = chemin.stat().st_size

    relu = pymupdf.open(chemin)
    p = relu[0]
    flux_identiques = flux_images(relu) == avant_flux
    texte = pdftotext(chemin)
    manquants = [c for c in fab.CARACTERES_EXIGES if c not in texte]
    # search_for : mots de référence, centre dans la boîte de vérité agrandie de 10 %.
    mots = [(m, b) for m, b in fab.ocr_simule(native, DPI, transfo, "mot")
            if len(m) >= 5 and m.isalpha()]
    m_aff = pymupdf.Matrix(p.rect.width / w, p.rect.height / h)
    trouves, bien_places = 0, 0
    for mot, b in mots:
        res = p.search_for(mot)
        if not res:
            continue
        trouves += 1
        verite = pymupdf.Rect(b) * m_aff * p.derotation_matrix
        verite.normalize()
        dx, dy = verite.width * 0.05, verite.height * 0.05
        grande = pymupdf.Rect(verite.x0 - dx, verite.y0 - dy, verite.x1 + dx, verite.y1 + dy)
        if any(grande.contains((r.tl + r.br) / 2) for r in res):
            bien_places += 1
    # Mots de référence restitués par pdftotext (ordre ignoré).
    ref = set(" ".join(fab.LIGNES_REFERENCE).split())
    lus = set(texte.split())
    rappel = len(ref & lus) / len(ref)
    # Contrôle visuel : calque visible en rouge.
    vis = pymupdf.open(chemin_sans)
    ecrire_calque(vis[0], elements, w, h, visible=True)
    vis[0].get_pixmap(dpi=100).save(SORTIE / f"{nom}_{strategie}_controle.png")
    return {
        "cas": nom, "strategie": strategie, "params": params,
        "ecart_affichage_scan_vs_natif": round(ecart_affichage, 2),
        "ecart_rendu_avant_apres": ecart_rendu,
        "flux_images_identiques": flux_identiques,
        "caracteres_manquants_pdftotext": manquants,
        "rappel_mots_pdftotext": round(rappel, 3),
        "search_for": f"{bien_places}/{trouves} bien placés sur {len(mots)} cherchés",
        "poids_octets": {"sans_calque": chemin_sans.stat().st_size,
                         "police_complete": poids_complet,
                         "sous_ensemble": poids_sous_ensemble},
    }


def main():
    resultats = []
    for strategie in ("ligne", "mot"):
        resultats += [
            essai("A_droite", strategie),
            essai("B_inclinee", strategie, angle=1.5, bruit=12),
            essai("C_rot90", strategie, rotation=90),
            essai("D_rot270", strategie, rotation=270),
            essai("E_rognage", strategie, rognage=True),
        ]
    texte = json.dumps({"pymupdf": pymupdf.__version__, "police": POLICE.name,
                        "resultats": resultats}, ensure_ascii=False, indent=1)
    (SORTIE / "resultat_pv06.json").write_text(texte, encoding="utf-8")
    for r in resultats:
        print(r["cas"], r["strategie"], "affichage", r["ecart_affichage_scan_vs_natif"],
              "rendu", r["ecart_rendu_avant_apres"], "flux", r["flux_images_identiques"],
              "manquants", "".join(r["caracteres_manquants_pdftotext"]) or "-",
              "rappel", r["rappel_mots_pdftotext"], "search", r["search_for"],
              "poids", r["poids_octets"])


if __name__ == "__main__":
    main()
