"""Calque texte invisible (EX-30) et adaptateur conforme à `ocr_function` (section 3.1).

Le texte reconnu est écrit en mode de rendu 3 (invisible) avec la police Noto Sans
embarquée, mot par mot quand le moteur fournit des mots (Windows), ligne par ligne sinon
(Apple Vision), positionné et étiré d'après la boîte englobante (PV-06). Les coordonnées
du moteur sont des pixels de l'image de la page telle qu'affichée (rotation appliquée) ;
elles sont converties vers le repère non pivoté de la page.
"""

import functools
import importlib.resources

import pymupdf

NOM_POLICE = "ocrmd-noto"
# Hauteur d'une boîte du moteur rapportée à la taille de police (PV-04 : 1,03 en moyenne
# sous Windows ; les boîtes de ligne de Vision sont du même ordre).
RAPPORT_HAUTEUR_TAILLE = 1.0
RELEVEMENT_LIGNE_DE_BASE = 0.2  # part de la hauteur de boîte sous la ligne de base


@functools.lru_cache(maxsize=1)
def police() -> pymupdf.Font:
    octets = (importlib.resources.files("ocr_md") / "donnees" / "polices" / "NotoSans-Regular.ttf").read_bytes()
    return pymupdf.Font(fontbuffer=octets)


def elements_a_ecrire(resultat):
    """[(texte, boîte en pixels)] : mots si le moteur les fournit, lignes sinon."""
    if resultat.niveau_mots:
        return [(m.texte, m.boite) for l in resultat.lignes for m in l.mots]
    return [(l.texte, l.boite) for l in resultat.lignes]


def ecrire_calque(page, resultat) -> int:
    """Écrit le calque invisible du résultat d'OCR sur la page ; renvoie le nombre
    d'éléments écrits. L'image de la page n'est pas modifiée."""
    elements = [(t, b) for t, b in elements_a_ecrire(resultat) if t.strip()]
    if not elements:
        return 0
    f = police()
    page.insert_font(fontname=NOM_POLICE, fontbuffer=f.buffer)
    echelle = pymupdf.Matrix(page.rect.width / resultat.largeur, page.rect.height / resultat.hauteur)
    derotation = page.derotation_matrix
    rotation = page.rotation
    # Une seule forme par page : tout le calque tient dans un flux de contenu unique, au lieu
    # d'un flux par mot (mémoire et poids du fichier, EX-59).
    forme = page.new_shape()
    for texte, boite in elements:
        r = pymupdf.Rect(boite) * echelle  # repère affiché, en points
        if r.is_empty or r.height <= 0:
            continue
        taille = max(r.height / RAPPORT_HAUTEUR_TAILLE, 1.0)
        longueur = f.text_length(texte, fontsize=taille)
        etirement = r.width / longueur if longueur else 1.0
        base = pymupdf.Point(r.x0, r.y1 - RELEVEMENT_LIGNE_DE_BASE * r.height) * derotation
        forme.insert_text(base, texte, fontname=NOM_POLICE, fontsize=taille, render_mode=3,
                          morph=(base, pymupdf.Matrix(etirement, 1) * pymupdf.Matrix(rotation)))
    forme.commit()
    # Le flux du calque (environ 300 octets par mot) est compressé tout de suite : il reste
    # sinon en clair en mémoire jusqu'à l'enregistrement du document (EX-59).
    xref = page.get_contents()[-1]
    page.parent.update_stream(xref, page.parent.xref_stream(xref), compress=True)
    return len(elements)


class AdaptateurOcr:
    """Fonction conforme au contrat `ocr_function` de PyMuPDF4LLM (PV-05) :
    exec_ocr(page, dpi=..., pixmap=None, language=..., keep_ocr_text=False).

    L'OCR a déjà été fait une fois par l'outil et inscrit dans le PDF consultable : la
    bibliothèque n'appelle cette fonction que pour une page sans texte (page vide ou page
    où le moteur n'a rien reconnu). L'adaptateur ne refait alors aucune reconnaissance,
    pour que le Markdown ne contienne que le texte du PDF consultable (EX-40), et garantit
    qu'aucun autre moteur (Tesseract, RapidOCR) n'est appelé (EX-08). Il compte ses appels."""

    def __init__(self):
        self.appels: list[int] = []

    def __call__(self, page, dpi=300, pixmap=None, language="fra", keep_ocr_text=False, **_kw):
        self.appels.append(page.number + 1)
