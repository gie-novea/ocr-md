"""Interface commune des moteurs OCR (section 3.3).

Entrée : une image Pillow. Sortie : des lignes de mots, chacun avec sa boîte englobante
en pixels de l'image (origine en haut à gauche) et une confiance éventuelle.
"""

import dataclasses
from typing import Protocol

from PIL import Image


class MoteurIndisponible(Exception):
    """Le moteur du système ou la langue demandée n'est pas disponible."""


@dataclasses.dataclass(frozen=True)
class Mot:
    texte: str
    boite: tuple[float, float, float, float]  # x0, y0, x1, y1 en pixels, origine en haut à gauche
    confiance: float | None = None


@dataclasses.dataclass(frozen=True)
class Ligne:
    mots: tuple[Mot, ...]
    confiance: float | None = None  # confiance de la ligne si le moteur ne la donne pas par mot

    @property
    def texte(self) -> str:
        return " ".join(m.texte for m in self.mots)

    @property
    def boite(self) -> tuple[float, float, float, float]:
        b = [m.boite for m in self.mots]
        return (min(x[0] for x in b), min(x[1] for x in b), max(x[2] for x in b), max(x[3] for x in b))


@dataclasses.dataclass(frozen=True)
class ResultatOcr:
    lignes: tuple[Ligne, ...]
    largeur: int
    hauteur: int
    angle_texte: float | None = None
    niveau_mots: bool = True  # False si les boîtes des mots sont estimées depuis la ligne

    @property
    def texte(self) -> str:
        return "\n".join(l.texte for l in self.lignes)


class MoteurOcr(Protocol):
    nom: str  # valeur du champ moteur_ocr du front matter

    def description(self) -> str: ...

    def langues_disponibles(self) -> list[str]: ...

    def dimension_max(self) -> int | None: ...

    def reconnaitre(self, image: Image.Image) -> ResultatOcr: ...
