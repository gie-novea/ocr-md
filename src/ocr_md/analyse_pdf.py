"""Classification des pages d'un PDF (EX-22) et statut du document (EX-23).

Catégories : `native` (texte visible suffisant), `couche_existante` (texte suffisant mais
majoritairement invisible, ou superposé à une image couvrant la page), `image` (page
scannée à reconnaître), `vide`. Une page scannée qui ne porte qu'une mention ajoutée par
une plateforme (horodatage, numéro de pli) reste `image`.
"""

import dataclasses

import pymupdf

CM2_PAR_PT2 = (2.54 / 72) ** 2


@dataclasses.dataclass(frozen=True)
class AnalysePage:
    numero: int                 # à partir de 1
    categorie: str
    caracteres: int             # caractères extractibles hors espaces
    part_invisible: float       # part des caractères en mode de rendu invisible
    couverture_image: float     # part de la page couverte par des images
    densite: float              # caractères par cm²


def _surface_union(rects) -> float:
    """Surface exacte de l'union de rectangles (balayage sur une grille de coordonnées)."""
    rects = [r for r in rects if not r.is_empty]
    if not rects:
        return 0.0
    xs = sorted({r.x0 for r in rects} | {r.x1 for r in rects})
    total = 0.0
    for x0, x1 in zip(xs, xs[1:]):
        intervalles = sorted((r.y0, r.y1) for r in rects if r.x0 <= x0 and r.x1 >= x1)
        couvert, fin = 0.0, None
        for a, b in intervalles:
            if fin is None or a > fin:
                couvert += b - a
                fin = b
            elif b > fin:
                couvert += b - fin
                fin = b
        total += (x1 - x0) * couvert
    return total


def _caracteres(page) -> tuple[int, int]:
    """(caractères visibles, caractères invisibles), hors espaces, d'après le texte tracé."""
    visibles = invisibles = 0
    for span in page.get_texttrace():
        n = sum(1 for c in span["chars"] if not chr(c[0]).isspace())
        if span.get("type") == 3 or span.get("opacity", 1) == 0:  # mode de rendu 3 : invisible
            invisibles += n
        else:
            visibles += n
    return visibles, invisibles


def analyser_page(page, p) -> AnalysePage:
    """p : paramètres (config.Parametres)."""
    zone = page.rect
    surface = zone.width * zone.height or 1.0
    visibles, invisibles = _caracteres(page)
    total = visibles + invisibles
    images = [pymupdf.Rect(i["bbox"]) & zone for i in page.get_image_info()]
    couverture = min(1.0, _surface_union(images) / surface)
    densite = total / (surface * CM2_PAR_PT2)
    part_invisible = invisibles / total if total else 0.0
    if couverture >= p.image_couverture_min and densite < p.densite_texte_ajoute_max:
        categorie = "image"  # page scannée portant au plus une mention ajoutée
    elif total >= p.texte_min_caracteres:
        if part_invisible > 0.5 or couverture >= p.image_couverture_min:
            categorie = "couche_existante"
        else:
            categorie = "native"
    elif couverture >= p.image_presence_min:
        categorie = "image"
    else:
        categorie = "vide"
    return AnalysePage(page.number + 1, categorie, total, round(part_invisible, 3), round(couverture, 3),
                       round(densite, 3))


def analyser(doc, p) -> list[AnalysePage]:
    return [analyser_page(page, p) for page in doc]


def statut(categories_finales: list[str], pages_douteuses) -> str:
    """Statut du document (EX-23). categories_finales : catégorie de chaque page après
    traitement : « native », « ocr » (reconnue par l'outil), « couche_existante », « vide »."""
    if pages_douteuses:
        return "douteux"
    if "couche_existante" in categories_finales:
        return "couche_expediteur"
    non_vides = [c for c in categories_finales if c != "vide"]
    ocr = [c for c in non_vides if c == "ocr"]
    if not ocr:
        return "natif"
    return "ocrise" if len(ocr) == len(non_vides) else "mixte"


ORIGINES = {
    "natif": "texte natif du document",
    "ocr": "OCR réalisé par l'outil sur l'ensemble du document",
    "mixte": "mixte : texte natif et OCR réalisé par l'outil",
    "couche": "couche OCR fournie par l'expéditeur, non refaite",
    "couche_et_ocr": "mixte : couche OCR fournie par l'expéditeur et OCR réalisé par l'outil",
}


def origine(categories_finales: list[str]) -> str:
    """Valeur normalisée de origine_texte (section 11.2)."""
    couche = "couche_existante" in categories_finales
    ocr = "ocr" in categories_finales
    native = "native" in categories_finales
    if couche and ocr:
        return ORIGINES["couche_et_ocr"]
    if couche:
        return ORIGINES["couche"]
    if ocr and native:
        return ORIGINES["mixte"]
    if ocr:
        return ORIGINES["ocr"]
    return ORIGINES["natif"]
