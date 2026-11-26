"""Moteur OCR macOS : Apple Vision par ocrmac, niveau « accurate » (EX-26).

Vision renvoie des observations au niveau de la ligne, avec une confiance et une boîte
normalisée. Convention retenue (à confirmer par la CI macOS, PV-06 b) : coordonnées
(x, y, largeur, hauteur) entre 0 et 1, origine en bas à gauche de l'image. Les boîtes des
mots sont estimées en répartissant la largeur de la ligne au prorata des caractères.
"""

from PIL import Image

from .base import Ligne, MoteurIndisponible, Mot, ResultatOcr

ORIGINE_EN_BAS = True


def langues_disponibles() -> list[str]:
    """Langues de VNRecognizeTextRequest au niveau « accurate » (liste vide si inconnue)."""
    try:
        import Vision
        requete = Vision.VNRecognizeTextRequest.alloc().init()
        requete.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
        langues, _erreur = requete.supportedRecognitionLanguagesAndReturnError_(None)
        return [str(l) for l in (langues or [])]
    except Exception:
        return []


def boite_en_pixels(boite_normalisee, largeur: int, hauteur: int, origine_en_bas: bool = ORIGINE_EN_BAS):
    x, y, l, h = boite_normalisee
    x0, x1 = x * largeur, (x + l) * largeur
    if origine_en_bas:
        y0, y1 = (1 - y - h) * hauteur, (1 - y) * hauteur
    else:
        y0, y1 = y * hauteur, (y + h) * hauteur
    return (x0, y0, x1, y1)


def mots_estimes(texte: str, boite, confiance):
    """Répartit la boîte de la ligne entre ses mots, au prorata du nombre de caractères."""
    x0, y0, x1, y1 = boite
    if not texte:
        return ()
    pas = (x1 - x0) / len(texte)
    mots, debut = [], 0
    for morceau in texte.split(" "):
        if morceau:
            mots.append(Mot(morceau, (x0 + debut * pas, y0, x0 + (debut + len(morceau)) * pas, y1), confiance))
        debut += len(morceau) + 1
    return tuple(mots)


class MoteurMacos:
    nom = "apple-vision"

    def __init__(self, langue: str = "fr-FR", langue_secondaire: str | None = "en-US"):
        disponibles = langues_disponibles()
        if disponibles and langue not in disponibles:
            raise MoteurIndisponible(f"langue {langue} non disponible pour Apple Vision")
        self.langues = [langue] + ([langue_secondaire] if langue_secondaire else [])

    def description(self) -> str:
        return f"Apple Vision (accurate, {', '.join(self.langues)})"

    def langues_disponibles(self) -> list[str]:
        return langues_disponibles()

    def dimension_max(self) -> None:
        return None

    def reconnaitre(self, image: Image.Image) -> ResultatOcr:
        from ocrmac import ocrmac
        largeur, hauteur = image.size
        resultats = ocrmac.OCR(image.convert("RGB"), recognition_level="accurate",
                               language_preference=self.langues).recognize()
        lignes = []
        for texte, confiance, boite in resultats:
            mots = mots_estimes(texte, boite_en_pixels(boite, largeur, hauteur), float(confiance))
            if mots:
                lignes.append(Ligne(mots, float(confiance)))
        # Ordre de lecture : de haut en bas, puis de gauche à droite.
        lignes.sort(key=lambda l: (round(l.boite[1] / 10), l.boite[0]))
        return ResultatOcr(tuple(lignes), largeur, hauteur, None, niveau_mots=False)
