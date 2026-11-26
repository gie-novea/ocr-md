"""Correctifs des bibliothèques tierces, appliqués au lancement, sans copie modifiée.

Correctif unique à ce jour : PyMuPDF4LLM, extraction des cellules de tableau en Markdown.

Défaut : `pymupdf4llm.helpers.utils.extract_cells(..., markdown=True)` retire les espaces
autour de chaque fragment de texte (« span ») d'une cellule. Un calque OCR invisible écrit
un objet texte par mot, chacun étiré à sa boîte : chaque mot devient un fragment distinct
et les mots d'une cellule sont collés (« Anna Smith » devient « AnnaSmith »). Exemple
minimal : `docs/ticket-pymupdf4llm-espaces-cellules.md`.

Correctif : quand tout le texte d'une cellule est invisible (calque OCR, sans mise en forme
possible), la cellule est extraite par le chemin « texte simple » de la même fonction, qui
conserve les espaces ; les autres cellules sont inchangées.

Application : en remplaçant l'attribut `extract_cells` du module `pymupdf4llm.helpers.utils`
(que `document_layout` appelle par cet attribut). Rien n'est modifié sur disque. Le
correctif n'est appliqué que si PyMuPDF et PyMuPDF4LLM sont exactement à la version
verrouillée ; sinon il est laissé de côté et la raison est inscrite au journal de chaque
lot (le défaut a pu être corrigé, ou la fonction avoir changé).
"""

import importlib.metadata

VERSION_VERROUILLEE = "1.28.2"
PAQUETS = ("pymupdf", "pymupdf4llm")


class _Etat:
    applique = False
    raison = "correctif non encore examiné"
    originale = None


ETAT = _Etat()


def _versions() -> dict[str, str]:
    versions = {}
    for paquet in PAQUETS:
        try:
            versions[paquet] = importlib.metadata.version(paquet)
        except importlib.metadata.PackageNotFoundError:
            versions[paquet] = "absent"
    return versions


def appliquer() -> bool:
    """Applique le correctif s'il convient (idempotent). Renvoie True s'il est actif."""
    if ETAT.applique:
        return True
    versions = _versions()
    if any(v != VERSION_VERROUILLEE for v in versions.values()):
        ETAT.raison = ("correctif des cellules de tableau de PyMuPDF4LLM non appliqué : version "
                       + ", ".join(f"{p} {v}" for p, v in versions.items())
                       + f" au lieu de {VERSION_VERROUILLEE} (vérifier si le défaut existe encore)")
        return False
    from pymupdf4llm.helpers import utils
    originale = utils.extract_cells

    def extract_cells(table_blocks, cell, markdown=False, ocrpage=False):
        if markdown:
            spans = [s for b in table_blocks if not utils.are_disjoint(b["bbox"], cell)
                     for l in b["lines"] if not utils.are_disjoint(l["bbox"], cell)
                     for s in l["spans"] if not utils.are_disjoint(s["bbox"], cell)]
            if spans and all(utils.is_ocr_text(s) for s in spans):
                texte = originale(table_blocks, cell, markdown=False, ocrpage=ocrpage)
                return texte.replace("\n", "<br>").replace("|", "\\|")
        return originale(table_blocks, cell, markdown=markdown, ocrpage=ocrpage)

    extract_cells.correctif_ocr_md = True
    ETAT.originale = originale
    utils.extract_cells = extract_cells
    ETAT.applique = True
    ETAT.raison = (f"correctif des cellules de tableau de PyMuPDF4LLM appliqué (PyMuPDF et PyMuPDF4LLM "
                   f"{VERSION_VERROUILLEE})")
    return True


def retirer() -> None:
    """Rétablit la fonction d'origine (tests)."""
    if ETAT.applique and ETAT.originale is not None:
        from pymupdf4llm.helpers import utils
        utils.extract_cells = ETAT.originale
    ETAT.applique = False
    ETAT.originale = None
    ETAT.raison = "correctif retiré"
