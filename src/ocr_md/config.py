"""Paramètres réglables (EX-67) : valeurs par défaut et fichier de configuration TOML.

Chaque paramètre porte sa valeur par défaut, son type, ses bornes et une description ;
le tableau du guide administrateur sera généré à partir de cette liste. Les valeurs par
défaut des seuils sont des valeurs de départ, à calibrer (EX-76). Celles marquées
« proposition » ne figurent pas dans le cahier des charges.
"""

import dataclasses
import pathlib
import tomllib
from typing import Any

from . import plateforme


class ErreurConfiguration(Exception):
    """Fichier de configuration illisible, paramètre inconnu ou valeur invalide."""


@dataclasses.dataclass(frozen=True)
class Definition:
    nom: str
    defaut: Any
    description: str
    minimum: float | None = None
    maximum: float | None = None
    choix: tuple[str, ...] | None = None


DEFINITIONS: tuple[Definition, ...] = (
    # Classification des pages (EX-22)
    Definition("texte_min_caracteres", 30, "Caractères extractibles hors espaces au-dessous desquels une page n'a pas de texte suffisant", 0, 100000),
    Definition("image_couverture_min", 0.80, "Part de la page couverte par une image au-delà de laquelle le texte est superposé à une image", 0, 1),
    Definition("image_presence_min", 0.30, "Part de la page couverte par des images pour qu'une page sans texte soit classée « image »", 0, 1),
    Definition("densite_texte_ajoute_max", 0.5, "Caractères par cm² au-dessous desquels le texte d'une page scannée est une mention ajoutée (horodatage)", 0, 1000),
    # OCR (EX-25)
    Definition("ocr_dpi", 300, "Résolution de rendu des pages pour l'OCR", 72, 1200),
    Definition("langue_ocr", "fr-FR", "Langue principale de reconnaissance"),
    Definition("langue_ocr_secondaire", "en-US", "Langue secondaire, si le moteur en accepte plusieurs"),
    # Confiance Apple Vision (EX-35)
    Definition("confiance_moyenne_min", 0.70, "Confiance moyenne pondérée au-dessous de laquelle une page est douteuse", 0, 1),
    Definition("confiance_basse", 0.50, "Confiance au-dessous de laquelle un texte est jugé peu sûr", 0, 1),
    Definition("part_confiance_basse_max", 0.20, "Part du texte peu sûr au-delà de laquelle une page est douteuse", 0, 1),
    Definition("page_blanche_ecart_type_max", 8.0, "Écart type des niveaux de gris au-dessous duquel une page est uniformément blanche (proposition)", 0, 255),
    # Heuristique lexicale (EX-36)
    # Seuil des mots inconnus selon l'origine du texte : Apple Vision corrige ses erreurs en
    # mots plausibles (correction linguistique), ce qui abaisse cet indicateur pour lui seul.
    Definition("mots_inconnus_max_couche_existante", 0.35, "Part de mots absents du lexique au-delà de laquelle une page à couche OCR existante est douteuse (valeur du cahier ; calibrage définitif en recette, TM-08)", 0, 1),
    Definition("mots_inconnus_max_windows", 0.35, "Part de mots absents du lexique au-delà de laquelle une page reconnue par Windows.Media.Ocr est douteuse (valeur du cahier ; calibrage définitif en recette, TM-08)", 0, 1),
    Definition("mots_inconnus_max_vision", 0.165, "Part de mots absents du lexique au-delà de laquelle une page reconnue par Apple Vision est douteuse (milieu de l'écart propre à Vision sur le jeu de test ; calibrage définitif en recette, TM-08)", 0, 1),
    Definition("mots_evaluables_min", 40, "Nombre minimal de mots évaluables pour appliquer l'indicateur des mots inconnus", 0, 100000),
    Definition("taux_caracteres_aberrants_max", 0.03, "Part de caractères aberrants au-delà de laquelle une page est douteuse (valeur du cahier ; calibrage définitif en recette, TM-08)", 0, 1),
    Definition("taux_mots_fragmentes_max", 0.25, "Part de mots d'une seule lettre au-delà de laquelle une page est douteuse (valeur du cahier ; calibrage définitif en recette, TM-08)", 0, 1),
    Definition("taux_melange_chiffres_lettres_max", 0.10, "Part de mots mêlant chiffres et lettres au-delà de laquelle une page est douteuse", 0, 1),
    Definition("densite_min", 0.11, "Densité (caractères par cm²) au-dessous de laquelle une page non blanche est douteuse (milieu de l'écart du jeu de test, la valeur du cahier, 0,2, signalant à tort un tableau clairsemé ; calibrage définitif en recette, TM-08)", 0, 1000),
    Definition("densite_max", 60.0, "Densité (caractères par cm²) au-delà de laquelle une page est douteuse", 0, 10000),
    Definition("lexique_complementaire", [], "Mots ajoutés au lexique (sigles, vocabulaire métier)"),
    # Office (EX-45)
    Definition("xlsx_lignes_max", 2000, "Nombre de lignes par feuille au-delà duquel la feuille est tronquée", 1, 1048576),
    # Robustesse (EX-64, EX-65)
    Definition("delai_hydratation_s", 120, "Délai maximal de lecture d'un fichier non disponible localement (kDrive)", 1, 3600),
    Definition("tentatives_ecriture", 3, "Nouvelles tentatives d'écriture d'une sortie verrouillée", 0, 20),
    Definition("intervalle_tentatives_s", 1.0, "Intervalle entre deux tentatives d'écriture (proposition)", 0, 60),
    # Parallélisme (REC-06)
    Definition("processus", 1, "Nombre de fichiers traités en parallèle", 1, 1),
)

_PAR_NOM = {d.nom: d for d in DEFINITIONS}


@dataclasses.dataclass(frozen=True)
class Parametres:
    valeurs: dict
    sources: tuple[str, ...]  # fichiers de configuration effectivement lus

    def __getattr__(self, nom):
        try:
            return self.valeurs[nom]
        except KeyError:
            raise AttributeError(nom) from None


def _valider(nom: str, valeur: Any) -> Any:
    d = _PAR_NOM.get(nom)
    if d is None:
        raise ErreurConfiguration(f"paramètre inconnu : « {nom} »")
    attendu = type(d.defaut)
    if attendu is float and isinstance(valeur, int) and not isinstance(valeur, bool):
        valeur = float(valeur)
    if attendu is list:
        if not isinstance(valeur, list) or not all(isinstance(x, str) for x in valeur):
            raise ErreurConfiguration(f"« {nom} » doit être une liste de chaînes")
        return list(valeur)
    if isinstance(valeur, bool) or not isinstance(valeur, attendu):
        noms = {int: "un entier", float: "un nombre", str: "une chaîne"}
        raise ErreurConfiguration(f"« {nom} » doit être {noms.get(attendu, attendu.__name__)}")
    if d.minimum is not None and valeur < d.minimum or d.maximum is not None and valeur > d.maximum:
        raise ErreurConfiguration(f"« {nom} » doit être compris entre {d.minimum} et {d.maximum}")
    if d.choix and valeur not in d.choix:
        raise ErreurConfiguration(f"« {nom} » doit valoir l'une des valeurs : {', '.join(d.choix)}")
    return valeur


def _lire(chemin: pathlib.Path) -> dict:
    try:
        with open(chemin, "rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        raise ErreurConfiguration(f"fichier de configuration introuvable : {chemin}") from None
    except tomllib.TOMLDecodeError as e:
        raise ErreurConfiguration(f"fichier de configuration illisible ({chemin}) : {e}") from None
    except OSError as e:
        raise ErreurConfiguration(f"fichier de configuration inaccessible ({chemin}) : {e}") from None


def charger(fichier: pathlib.Path | None = None, *, fichier_utilisateur: pathlib.Path | None = None) -> Parametres:
    """Valeurs par défaut, puis fichier du profil s'il existe, puis fichier passé par --config."""
    valeurs = {d.nom: (list(d.defaut) if isinstance(d.defaut, list) else d.defaut) for d in DEFINITIONS}
    sources = []
    profil = fichier_utilisateur or plateforme.fichier_configuration()
    for chemin in ([profil] if profil.is_file() else []) + ([pathlib.Path(fichier)] if fichier else []):
        for nom, valeur in _lire(chemin).items():
            valeurs[nom] = _valider(nom, valeur)
        sources.append(str(chemin))
    return Parametres(valeurs, tuple(sources))
