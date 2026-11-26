"""Moteur OCR Windows : Windows.Media.Ocr par la projection PyWinRT (EX-27, PV-04).

Windows.Media.Ocr ne fournit aucun indice de confiance (OcrWord : texte et boîte seuls) ;
la qualité est jugée par l'heuristique lexicale (EX-35).
"""

import threading

from PIL import Image
from winrt.windows.foundation import AsyncStatus
from winrt.windows.globalization import Language
from winrt.windows.graphics.imaging import BitmapPixelFormat, SoftwareBitmap
from winrt.windows.media.ocr import OcrEngine
from winrt.windows.storage.streams import Buffer

from .base import Ligne, MoteurIndisponible, Mot, ResultatOcr

DELAI_OCR_S = 120  # délai maximal de reconnaissance d'une page


def langues_disponibles() -> list[str]:
    return [l.language_tag for l in OcrEngine.available_recognizer_languages]


class MoteurWindows:
    nom = "windows-media-ocr"

    def __init__(self, langue: str = "fr-FR"):
        lang = Language(langue)
        if not OcrEngine.is_language_supported(lang):
            raise MoteurIndisponible(f"langue {langue} non disponible pour Windows.Media.Ocr")
        self._moteur = OcrEngine.try_create_from_language(lang)
        if self._moteur is None:
            raise MoteurIndisponible(f"création du moteur Windows.Media.Ocr impossible ({langue})")
        self.langue = self._moteur.recognizer_language.language_tag

    def description(self) -> str:
        return f"Windows.Media.Ocr ({self.langue})"

    def langues_disponibles(self) -> list[str]:
        return langues_disponibles()

    def dimension_max(self) -> int:
        return OcrEngine.max_image_dimension

    @staticmethod
    def _bitmap(image: Image.Image) -> SoftwareBitmap:
        gris = image.convert("L")
        donnees = gris.tobytes()
        tampon = Buffer(len(donnees))
        tampon.length = len(donnees)
        memoryview(tampon)[:] = donnees
        return SoftwareBitmap.create_copy_from_buffer(tampon, BitmapPixelFormat.GRAY8, *gris.size)

    def reconnaitre(self, image: Image.Image) -> ResultatOcr:
        largeur, hauteur = image.size
        if max(largeur, hauteur) > self.dimension_max():
            raise ValueError(f"image {largeur}x{hauteur} au-delà de la dimension maximale du moteur")

        # Attente directe de l'opération WinRT : asyncio créerait sous Windows une paire de
        # sockets locale, inutile ici et bloquée par la neutralisation réseau des tests.
        operation = self._moteur.recognize_async(self._bitmap(image))
        terminee = threading.Event()
        operation.completed = lambda _op, _etat: terminee.set()
        if not terminee.wait(DELAI_OCR_S):
            operation.cancel()
            raise TimeoutError(f"OCR non terminé après {DELAI_OCR_S} s")
        if operation.status != AsyncStatus.COMPLETED:
            raise RuntimeError(f"échec de Windows.Media.Ocr (état {operation.status}, code {operation.error_code})")
        resultat = operation.get_results()
        lignes = []
        for ligne in resultat.lines:
            mots = []
            for mot in ligne.words:
                r = mot.bounding_rect
                mots.append(Mot(mot.text, (r.x, r.y, r.x + r.width, r.y + r.height)))
            if mots:
                lignes.append(Ligne(tuple(mots)))
        angle = resultat.text_angle
        return ResultatOcr(tuple(lignes), largeur, hauteur, None if angle is None else float(angle))
