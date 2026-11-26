"""Moteur OCR factice, déterministe, sans dépendance système (section 3.3, EX-75).

Il sert aux tests sur toutes les plateformes, y compris Linux. Chaque image du jeu de test
porte, dans sa marge supérieure gauche, un marqueur de cases noires et blanches qui code
un identifiant. Le moteur lit ce marqueur et renvoie le texte, les boîtes et les
confiances que le manifeste du jeu de test associe à cet identifiant. Une image sans
marqueur donne un résultat vide. Chaque appel est compté (compteur d'appels de EX-24).

Le marqueur est formé de 18 cases carrées alignées : une case noire de début, 16 bits de
l'identifiant (bit de poids fort en premier, noir = 1) et une case noire de fin. Les
positions sont exprimées en fraction de la largeur de l'image, ce qui rend la lecture
indépendante de la résolution de rendu.
"""

import json
import pathlib

from PIL import Image, ImageDraw, ImageStat

from .base import Ligne, Mot, ResultatOcr

X0, PAS, COTE, Y0 = 0.020, 0.012, 0.008, 0.008  # fractions de la largeur de l'image
BITS = 16


def _cases(largeur: int):
    for i in range(BITS + 2):
        x = (X0 + i * PAS) * largeur
        y = Y0 * largeur
        yield i, (x, y, x + COTE * largeur, y + COTE * largeur)


def dessiner_marqueur(image: Image.Image, identifiant: int) -> Image.Image:
    """Dessine le marqueur de l'identifiant (0 à 65535) sur une copie de l'image."""
    if not 0 <= identifiant < 2 ** BITS:
        raise ValueError("identifiant hors limites")
    resultat = image.copy()
    dessin = ImageDraw.Draw(resultat)
    noir = 0 if resultat.mode in ("L", "1") else (0, 0, 0)
    blanc = 255 if resultat.mode in ("L", "1") else (255, 255, 255)
    bits = [1] + [(identifiant >> (BITS - 1 - k)) & 1 for k in range(BITS)] + [1]
    for i, boite in _cases(resultat.width):
        dessin.rectangle(boite, fill=noir if bits[i] else blanc)
    return resultat


def lire_marqueur(image: Image.Image) -> int | None:
    """Renvoie l'identifiant porté par l'image, ou None si aucun marqueur n'est lisible."""
    gris = image.convert("L")
    bits = []
    for _i, (x0, y0, x1, y1) in _cases(gris.width):
        # Moyenne du quart central de la case : tolère bruit, JPEG et rééchantillonnage.
        dx, dy = (x1 - x0) / 4, (y1 - y0) / 4
        zone = gris.crop((int(x0 + dx), int(y0 + dy), max(int(x1 - dx), int(x0 + dx) + 1),
                          max(int(y1 - dy), int(y0 + dy) + 1)))
        bits.append(1 if ImageStat.Stat(zone).mean[0] < 128 else 0)
    if bits[0] != 1 or bits[-1] != 1:
        return None
    valeur = 0
    for b in bits[1:-1]:
        valeur = (valeur << 1) | b
    return valeur


class MoteurFactice:
    """Moteur de test. `pages` associe un identifiant à un dict :
    {"lignes": [{"mots": [[texte, [x0, y0, x1, y1]], ...], "confiance": float}], ...}
    où les boîtes sont en fraction de la largeur et de la hauteur de l'image.
    `avec_confiance=False` imite Windows.Media.Ocr (aucune confiance)."""

    def __init__(self, pages: dict, *, avec_confiance: bool = True, nom: str = "factice"):
        self._pages = {int(k): v for k, v in pages.items()}
        self.avec_confiance = avec_confiance
        self.nom = nom
        self.appels: list[int | None] = []  # identifiants lus, dans l'ordre des appels

    @classmethod
    def depuis_manifeste(cls, chemin: pathlib.Path | str, **kw) -> "MoteurFactice":
        donnees = json.loads(pathlib.Path(chemin).read_text(encoding="utf-8"))
        return cls(donnees["ocr_factice"], **kw)

    @property
    def nombre_appels(self) -> int:
        return len(self.appels)

    def description(self) -> str:
        return f"moteur factice ({'avec' if self.avec_confiance else 'sans'} confiance)"

    def langues_disponibles(self) -> list[str]:
        return ["fr-FR", "en-US"]

    def dimension_max(self) -> int | None:
        return None

    def reconnaitre(self, image: Image.Image) -> ResultatOcr:
        identifiant = lire_marqueur(image)
        self.appels.append(identifiant)
        largeur, hauteur = image.size
        page = self._pages.get(identifiant) if identifiant is not None else None
        if page is None:
            return ResultatOcr((), largeur, hauteur)
        lignes = []
        for ligne in page["lignes"]:
            confiance = ligne.get("confiance") if self.avec_confiance else None
            mots = tuple(
                Mot(texte, (b[0] * largeur, b[1] * hauteur, b[2] * largeur, b[3] * hauteur), confiance)
                for texte, b in ligne["mots"])
            if mots:
                lignes.append(Ligne(mots, confiance))
        return ResultatOcr(tuple(lignes), largeur, hauteur, page.get("angle"))
