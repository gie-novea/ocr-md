"""Contrôles d'ouverture des PDF (EX-21) ; la conversion est ajoutée au jalon 4."""

import dataclasses
import pathlib

import pymupdf

from ..inventaire import ErreurFichier
from ..sorties import chemin_systeme

MESSAGE_PROTEGE = "PDF protégé par mot de passe"
MESSAGE_ENDOMMAGE = "PDF endommagé"
MESSAGE_SIGNE = ("la copie produite dans _OCR ne conserve pas la validité de la signature ; "
                 "l'original signé reste la référence")

# Les messages de MuPDF ne doivent pas encombrer la console : ils sont relus au besoin.
pymupdf.TOOLS.mupdf_display_errors(False)


@dataclasses.dataclass(frozen=True)
class InfoPdf:
    pages: int
    signe: bool
    repare: bool


def _page_vide(page) -> bool:
    return not page.get_text("text").strip() and not page.get_images() and not page.get_drawings()


def ouvrir(chemin: pathlib.Path):
    """Ouvre le PDF en lecture ; lève ErreurFichier « protégé » ou « endommagé »."""
    try:
        doc = pymupdf.open(chemin_systeme(chemin), filetype="pdf")
    except Exception:
        raise ErreurFichier(MESSAGE_ENDOMMAGE) from None
    if doc.needs_pass:
        doc.close()
        raise ErreurFichier(MESSAGE_PROTEGE)
    return doc


def controler_pdf(chemin: pathlib.Path) -> InfoPdf:
    """Vérifie que le PDF s'ouvre et que ses pages se lisent.

    Endommagé si : ouverture impossible, aucune page, page illisible, ou document réparé
    à l'ouverture dont aucune page ne contient plus ni texte, ni image, ni dessin (cas
    d'un fichier tronqué). Une réparation qui laisse un contenu lisible est admise."""
    doc = ouvrir(chemin)
    try:
        if doc.page_count == 0:
            raise ErreurFichier(MESSAGE_ENDOMMAGE)
        vides = 0
        for page in doc:
            try:
                vides += _page_vide(page)
            except Exception:
                raise ErreurFichier(MESSAGE_ENDOMMAGE) from None
        if doc.is_repaired and vides == doc.page_count:
            raise ErreurFichier(MESSAGE_ENDOMMAGE)
        signe = doc.get_sigflags() >= 1
        return InfoPdf(doc.page_count, signe, doc.is_repaired)
    finally:
        doc.close()
