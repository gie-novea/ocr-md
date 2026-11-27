"""Moteur OCR macOS : Apple Vision, niveau « accurate » (EX-26).

Vision renvoie des observations au niveau de la ligne (texte, confiance, boîte normalisée,
origine en bas à gauche : PV-06 b). Les boîtes des mots sont obtenues de deux façons
(PV-14) :
- mode « mots » (défaut) : appel direct de Vision par pyobjc et, pour chaque mot de la
  ligne, `VNRecognizedText.boundingBoxForRange:error:` ; un mot dont la boîte n'est pas
  fournie est placé au prorata de ses caractères dans la boîte de la ligne ;
- mode « prorata » : bibliothèque ocrmac (lignes seulement), mots répartis au prorata des
  caractères dans la boîte de la ligne.
"""

import io
import re
import time

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
    return tuple(Mot(m.group(), (x0 + m.start() * pas, y0, x0 + m.end() * pas, y1), confiance)
                 for m in re.finditer(r"\S+", texte))


def _png(image: Image.Image) -> bytes:
    """Image transmise à Vision : PNG sans perte, en niveaux de gris, compression rapide.
    La conversion en RVB et la compression par défaut coûtaient 0,7 à 1 s par page à 300 dpi
    (près d'un quart du temps de reconnaissance sous macOS) ; ainsi, environ 0,1 s."""
    if image.mode not in ("L", "RGB"):
        image = image.convert("L")
    tampon = io.BytesIO()
    image.save(tampon, format="PNG", compress_level=1)
    return tampon.getvalue()


def _utf16(texte: str) -> int:
    return len(texte.encode("utf-16-le")) // 2


def vision_avec_mots(image: Image.Image, langues: list[str], chronos: dict | None = None,
                     correction: bool = True):
    """Appel direct de Vision. Renvoie [(texte, confiance, boîte_ligne, [(mot, boîte|None)])],
    boîtes normalisées (x, y, largeur, hauteur), origine en bas à gauche. `chronos` reçoit
    les durées cumulées : conversion de l'image (png), reconnaissance (vision), boîtes.
    `correction` : correction linguistique de Vision (usesLanguageCorrection), active par
    défaut ; désactivable pour l'essai PV-15 seulement."""
    chronos = chronos if chronos is not None else {}
    t0 = time.perf_counter()
    donnees = _png(image)
    t1 = time.perf_counter()
    import Foundation
    import objc
    import Vision
    sortie = []
    with objc.autorelease_pool():
        requete = Vision.VNRecognizeTextRequest.alloc().init()
        requete.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
        requete.setRecognitionLanguages_(langues)
        requete.setUsesLanguageCorrection_(bool(correction))
        gestionnaire = Vision.VNImageRequestHandler.alloc().initWithData_options_(donnees, None)
        retour = gestionnaire.performRequests_error_([requete], None)
        t2 = time.perf_counter()
        ok, erreur = retour if isinstance(retour, tuple) else (bool(retour), None)
        if not ok or erreur is not None:
            raise RuntimeError(f"échec de Vision : {erreur}")
        for observation in requete.results() or []:
            candidats = observation.topCandidates_(1)
            if not candidats:
                continue
            candidat = candidats[0]
            texte = str(candidat.string())
            b = observation.boundingBox()
            boite_ligne = (b.origin.x, b.origin.y, b.size.width, b.size.height)
            mots = []
            for m in re.finditer(r"\S+", texte):
                plage = Foundation.NSMakeRange(_utf16(texte[: m.start()]), _utf16(m.group()))
                try:
                    r = candidat.boundingBoxForRange_error_(plage, None)
                    rect = r[0] if isinstance(r, tuple) else r
                except Exception:
                    rect = None
                if rect is None:
                    mots.append((m.group(), None))
                else:
                    bb = rect.boundingBox()
                    mots.append((m.group(), (bb.origin.x, bb.origin.y, bb.size.width, bb.size.height)))
            sortie.append((texte, float(candidat.confidence()), boite_ligne, mots))
    t3 = time.perf_counter()
    for cle, duree in (("png", t1 - t0), ("vision", t2 - t1), ("boites", t3 - t2)):
        chronos[cle] = chronos.get(cle, 0.0) + duree
    return sortie


class MoteurMacos:
    nom = "apple-vision"

    def __init__(self, langue: str = "fr-FR", langue_secondaire: str | None = "en-US", mode: str = "mots",
                 correction_linguistique: bool = True):
        disponibles = langues_disponibles()
        if disponibles and langue not in disponibles:
            raise MoteurIndisponible(f"langue {langue} non disponible pour Apple Vision")
        self.langues = [langue] + ([langue_secondaire] if langue_secondaire else [])
        self.mode = mode
        self.correction_linguistique = correction_linguistique  # False : essai PV-15 seulement
        self.statistiques = {"mots_boite_vision": 0, "mots_prorata": 0}
        self.chronos: dict[str, float] = {}  # durées cumulées : png, vision, boîtes (mesure PV-14)

    def description(self) -> str:
        return f"Apple Vision (accurate, {', '.join(self.langues)})"

    def langues_disponibles(self) -> list[str]:
        return langues_disponibles()

    def dimension_max(self) -> None:
        return None

    def reconnaitre(self, image: Image.Image) -> ResultatOcr:
        largeur, hauteur = image.size
        lignes = []
        if self.mode == "mots":
            for texte, confiance, boite_ligne, mots in vision_avec_mots(image, self.langues, self.chronos,
                                                                              self.correction_linguistique):
                ligne_px = boite_en_pixels(boite_ligne, largeur, hauteur)
                resultat_mots = []
                prorata = mots_estimes(texte, ligne_px, confiance)
                for (mot, boite), repli in zip(mots, prorata):
                    if boite is not None and boite[2] > 0 and boite[3] > 0:
                        self.statistiques["mots_boite_vision"] += 1
                        resultat_mots.append(Mot(mot, boite_en_pixels(boite, largeur, hauteur), confiance))
                    else:
                        self.statistiques["mots_prorata"] += 1
                        resultat_mots.append(repli)
                if resultat_mots:
                    lignes.append(Ligne(tuple(resultat_mots), confiance))
        else:
            from ocrmac import ocrmac
            resultats = ocrmac.OCR(image.convert("RGB"), recognition_level="accurate",
                                   language_preference=self.langues).recognize()
            for texte, confiance, boite in resultats:
                mots = mots_estimes(texte, boite_en_pixels(boite, largeur, hauteur), float(confiance))
                self.statistiques["mots_prorata"] += len(mots)
                if mots:
                    lignes.append(Ligne(mots, float(confiance)))
        # Ordre de lecture : de haut en bas, puis de gauche à droite.
        lignes.sort(key=lambda l: (round(l.boite[1] / 10), l.boite[0]))
        return ResultatOcr(tuple(lignes), largeur, hauteur, None, niveau_mots=True)
