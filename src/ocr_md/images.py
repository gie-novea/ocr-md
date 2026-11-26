"""Assemblage des images en PDF image (EX-34).

Une page par image ou par trame de TIFF ; dimensions physiques déduites de la résolution
déclarée (300 dpi à défaut), plafonnées au format A3 ; orientation EXIF appliquée. Un JPEG
est intégré tel quel (sans recompression), son orientation étant rendue par une rotation
à l'insertion ; les autres formats sont intégrés sans perte (PNG).
"""

import io

import pymupdf
from PIL import Image, ImageOps

from .inventaire import ErreurFichier
from .sorties import chemin_systeme

DPI_DEFAUT = 300
A3_PT = (842, 1191)
# Orientation EXIF -> rotation d'insertion PyMuPDF (sens antihoraire) pour un JPEG intact.
ROTATION_EXIF = {1: 0, 3: 180, 6: 270, 8: 90}


def _dpi(img) -> float:
    dpi = img.info.get("dpi")
    try:
        valeur = float(dpi[0]) if dpi else 0.0
    except (TypeError, ValueError, IndexError):
        valeur = 0.0
    return valeur if valeur >= 50 else DPI_DEFAUT


def _taille_page(largeur_px, hauteur_px, dpi):
    l, h = largeur_px / dpi * 72, hauteur_px / dpi * 72
    plafond_l, plafond_h = (A3_PT if h >= l else A3_PT[::-1])
    facteur = min(1.0, plafond_l / l, plafond_h / h)
    return l * facteur, h * facteur


def _png(img) -> bytes:
    if img.mode not in ("1", "L", "RGB"):
        fond = Image.new("RGB", img.size, (255, 255, 255))
        fond.paste(img.convert("RGBA"), mask=img.convert("RGBA").split()[-1])
        img = fond
    tampon = io.BytesIO()
    img.save(tampon, "PNG")
    return tampon.getvalue()


def image_vers_pdf(chemin) -> pymupdf.Document:
    try:
        with open(chemin_systeme(chemin), "rb") as f:
            octets = f.read()
        img = Image.open(io.BytesIO(octets))
        img.load()
    except Exception:
        raise ErreurFichier("image illisible ou endommagée") from None
    doc = pymupdf.open()
    dpi = _dpi(img)
    orientation = img.getexif().get(0x0112, 1) if hasattr(img, "getexif") else 1
    if img.format == "JPEG" and getattr(img, "n_frames", 1) == 1 and orientation in ROTATION_EXIF:
        rotation = ROTATION_EXIF[orientation]
        l, h = img.size if rotation in (0, 180) else img.size[::-1]
        page = doc.new_page(width=_taille_page(l, h, dpi)[0], height=_taille_page(l, h, dpi)[1])
        page.insert_image(page.rect, stream=octets, rotate=rotation)
        return doc
    for n in range(getattr(img, "n_frames", 1)):
        img.seek(n)
        trame = ImageOps.exif_transpose(img) if n == 0 else img.copy()
        largeur, hauteur = _taille_page(trame.width, trame.height, _dpi(img))
        page = doc.new_page(width=largeur, height=hauteur)
        page.insert_image(page.rect, stream=_png(trame))
    return doc
