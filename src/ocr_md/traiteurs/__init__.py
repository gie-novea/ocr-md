"""Traiteurs par type de fichier : interface commune et choix selon le type.

L'orchestrateur (`traitement`) fournit à chaque traiteur un `Contexte` ; le traiteur lit la
source, produit ses sorties par `contexte.ecrivain.preparer(...)` et renvoie un
`ResultatTraitement`. Il vérifie `contexte.arret` entre deux pages et lève `Annulation`
si l'arrêt est demandé. Toute autre exception met le fichier en erreur (EX-60).

Jalon 4 : PDF et images réalisés (PDF consultable ; Markdown provisoire jusqu'au jalon 6) ;
fichiers Office au jalon 8.
"""

import dataclasses
import pathlib
import threading

from ..inventaire import ErreurFichier


class Annulation(Exception):
    """Arrêt demandé par l'utilisateur : le fichier en cours n'est pas terminé."""


@dataclasses.dataclass
class ResultatTraitement:
    statut: str
    pages: int | None = None
    pages_ocr: tuple[int, ...] = ()
    pages_douteuses: tuple[int, ...] = ()
    motifs: tuple[str, ...] = ()
    origine: str = ""
    message: str = ""


@dataclasses.dataclass
class Contexte:
    element: object                    # inventaire.Element
    prevues: dict[str, pathlib.Path]   # sorties demandées : {"pdf": ..., "md": ...}
    options: object                    # cli.Options
    parametres: object                 # config.Parametres
    ecrivain: object                   # sorties.Ecrivain
    journal: object                    # rapport.Journal
    arret: threading.Event
    moteur: object | None = None       # FournisseurMoteur : moteur OCR obtenu à la demande

    def verifier_arret(self) -> None:
        if self.arret.is_set():
            raise Annulation()


class Traiteur:
    def traiter(self, contexte: Contexte) -> ResultatTraitement:  # pragma: no cover - interface
        raise NotImplementedError


class TraiteurNonRealise(Traiteur):
    """Conversion pas encore réalisée : le fichier est signalé en erreur avec un message clair."""

    def __init__(self, jalon: int, quoi: str):
        self.message = f"{quoi} : fonction réalisée au jalon {jalon}"

    def traiter(self, contexte: Contexte) -> ResultatTraitement:
        raise ErreurFichier(self.message)


def traiteurs_par_defaut() -> dict[str, Traiteur]:
    from .pdf import TraiteurImage, TraiteurPdf
    return {
        "pdf": TraiteurPdf(),
        "image": TraiteurImage(),
        "docx": TraiteurNonRealise(8, "conversion des fichiers Office"),
        "xlsx": TraiteurNonRealise(8, "conversion des fichiers Office"),
        "pptx": TraiteurNonRealise(8, "conversion des fichiers Office"),
    }
