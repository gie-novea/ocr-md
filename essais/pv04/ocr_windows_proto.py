"""Prototype du moteur ocr/windows par la projection PyWinRT de Windows.Media.Ocr.

Entrée : image Pillow (niveaux de gris ou RGB). Sortie : liste de lignes, chaque ligne
étant une liste de mots (texte, boîte en pixels (x0, y0, x1, y1), confiance None).
Windows.Media.Ocr ne fournit pas de confiance (OcrWord : text et bounding_rect seuls).
"""

import asyncio

from PIL import Image
from winrt.windows.globalization import Language
from winrt.windows.graphics.imaging import BitmapPixelFormat, SoftwareBitmap
from winrt.windows.media.ocr import OcrEngine
from winrt.windows.storage.streams import Buffer


def langues_disponibles():
    return [l.language_tag for l in OcrEngine.available_recognizer_languages]


def dimension_max():
    return OcrEngine.max_image_dimension


def creer_moteur(langue="fr-FR"):
    lang = Language(langue)
    if not OcrEngine.is_language_supported(lang):
        return None
    return OcrEngine.try_create_from_language(lang)


def vers_software_bitmap(img: Image.Image) -> SoftwareBitmap:
    """Copie une image Pillow dans un SoftwareBitmap Gray8, sans fichier intermédiaire."""
    gris = img.convert("L")
    w, h = gris.size
    donnees = gris.tobytes()
    tampon = Buffer(len(donnees))
    tampon.length = len(donnees)
    memoryview(tampon)[:] = donnees
    return SoftwareBitmap.create_copy_from_buffer(tampon, BitmapPixelFormat.GRAY8, w, h)


async def _reconnaitre(moteur, bitmap):
    return await moteur.recognize_async(bitmap)


def reconnaitre(moteur, img: Image.Image):
    """Reconnaît une image ; renvoie (lignes, angle_texte)."""
    w, h = img.size
    m = dimension_max()
    if max(w, h) > m:
        raise ValueError(f"image {w}x{h} au-delà de MaxImageDimension={m}")
    resultat = asyncio.run(_reconnaitre(moteur, vers_software_bitmap(img)))
    lignes = []
    for ligne in resultat.lines:
        mots = []
        for mot in ligne.words:
            r = mot.bounding_rect
            mots.append((mot.text, (r.x, r.y, r.x + r.width, r.y + r.height), None))
        lignes.append(mots)
    angle = resultat.text_angle  # IReference[float] ou None
    return lignes, (None if angle is None else float(angle))
