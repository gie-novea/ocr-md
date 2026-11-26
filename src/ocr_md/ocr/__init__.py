"""Choix du moteur OCR selon la plateforme, à l'exécution (EX-07, EX-08).

Seuls les moteurs du système sont utilisés : Apple Vision sous macOS, Windows.Media.Ocr
sous Windows. Les modules propres à une plateforme sont importés ici à la demande.
"""

import os

from .. import plateforme
from .base import Ligne, MoteurIndisponible, MoteurOcr, Mot, ResultatOcr

__all__ = ["Ligne", "MoteurIndisponible", "MoteurOcr", "Mot", "ResultatOcr", "message_moteur_absent",
           "moteur_systeme"]


def message_moteur_absent() -> str:
    """Message de EX-71 lorsque le moteur OCR du système est indisponible."""
    if plateforme.systeme() == "windows":
        return ("Le module de reconnaissance de texte en français de Windows n'est pas installé sur ce poste. "
                "Les PDF déjà lisibles et les fichiers Office restent convertibles ; les PDF scannés et les "
                "images ne peuvent pas être traités. Transmettre à votre service informatique la commande "
                "suivante, à exécuter en administrateur : "
                "Add-WindowsCapability -Online -Name \"Language.OCR~~~fr-FR~0.0.1.0\"")
    if plateforme.systeme() == "macos":
        return "la reconnaissance de texte en français n'est pas disponible sur cette version de macOS"
    return "aucun moteur de reconnaissance de texte n'est disponible sur ce système"


def moteur_systeme(langue: str = "fr-FR", langue_secondaire: str | None = "en-US") -> MoteurOcr:
    """Renvoie le moteur du système ; lève MoteurIndisponible s'il manque.

    Pour les tests seulement : si la variable d'environnement OCR_MD_MOTEUR_FACTICE désigne
    le manifeste d'un jeu de test, le moteur factice est renvoyé à la place (sans
    confiance si OCR_MD_MOTEUR_FACTICE_SANS_CONFIANCE vaut 1, comme sous Windows).
    """
    manifeste = os.environ.get("OCR_MD_MOTEUR_FACTICE")
    if manifeste:
        from .factice import MoteurFactice
        sans = os.environ.get("OCR_MD_MOTEUR_FACTICE_SANS_CONFIANCE") == "1"
        return MoteurFactice.depuis_manifeste(manifeste, avec_confiance=not sans)
    s = plateforme.systeme()
    try:
        if s == "windows":
            from .windows import MoteurWindows
            return MoteurWindows(langue)
        if s == "macos":
            from .macos import MoteurMacos
            return MoteurMacos(langue, langue_secondaire)
    except ImportError as e:
        raise MoteurIndisponible(f"bibliothèque du moteur OCR absente : {e.name}") from None
    raise MoteurIndisponible(f"aucun moteur OCR du système sur la plateforme « {s} »")
