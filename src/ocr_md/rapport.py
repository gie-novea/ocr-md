"""Rapport `ocr_rapport.csv` (EX-82) et journal `ocr_journal.log` (EX-66).

Le rapport s'ouvre par double-clic dans Excel configuré en français : UTF-8 avec BOM,
point-virgule, fins de ligne CRLF, guillemets seulement si nécessaire, virgule décimale,
listes de pages séparées par des espaces. Il est réécrit de façon atomique après chaque
fichier (EX-61). Le journal ne contient aucun texte extrait des documents.
"""

import csv
import dataclasses
import io
import logging
import logging.handlers
import os
import pathlib
import traceback

from . import __version__
from .sorties import NOM_DOSSIER_OCR, chemin_systeme, ecrire_atomique

NOM_RAPPORT = "ocr_rapport.csv"
NOM_JOURNAL = "ocr_journal.log"
TAILLE_MAX_JOURNAL = 5 * 1024 * 1024

COLONNES = ("chemin_relatif", "type", "pages", "statut", "pages_ocr", "pages_douteuses", "motif_douteux",
            "origine_texte", "sorties", "action", "duree_s", "date_traitement", "message", "version_outil")


@dataclasses.dataclass
class LigneRapport:
    chemin_relatif: str
    type: str
    pages: int | None = None
    statut: str = ""
    pages_ocr: tuple[int, ...] = ()
    pages_douteuses: tuple[int, ...] = ()
    motif_douteux: tuple[str, ...] = ()
    origine_texte: str = ""
    sorties: tuple[str, ...] = ()
    action: str = "traite"
    duree_s: float | None = None
    date_traitement: str = ""
    message: str = ""
    version_outil: str = __version__

    def vers_csv(self) -> list[str]:
        return [
            self.chemin_relatif, self.type, "" if self.pages is None else str(self.pages), self.statut,
            " ".join(map(str, self.pages_ocr)), " ".join(map(str, self.pages_douteuses)),
            " ".join(self.motif_douteux), self.origine_texte, " | ".join(self.sorties), self.action,
            "" if self.duree_s is None else f"{self.duree_s:.1f}".replace(".", ","),
            self.date_traitement, " ".join(self.message.split()), self.version_outil,
        ]

    @classmethod
    def depuis_csv(cls, valeurs: dict) -> "LigneRapport":
        def entiers(t):
            return tuple(int(x) for x in t.split()) if t else ()
        return cls(
            chemin_relatif=valeurs["chemin_relatif"], type=valeurs["type"],
            pages=int(valeurs["pages"]) if valeurs["pages"] else None, statut=valeurs["statut"],
            pages_ocr=entiers(valeurs["pages_ocr"]), pages_douteuses=entiers(valeurs["pages_douteuses"]),
            motif_douteux=tuple(valeurs["motif_douteux"].split()), origine_texte=valeurs["origine_texte"],
            sorties=tuple(s for s in valeurs["sorties"].split(" | ") if s), action=valeurs["action"],
            duree_s=float(valeurs["duree_s"].replace(",", ".")) if valeurs["duree_s"] else None,
            date_traitement=valeurs["date_traitement"], message=valeurs["message"],
            version_outil=valeurs["version_outil"])


def chemin_rapport(dossier_ocr: pathlib.Path) -> pathlib.Path:
    return dossier_ocr / NOM_RAPPORT


def lire(dossier_ocr: pathlib.Path) -> dict[str, LigneRapport]:
    """Lignes du rapport existant, par chemin relatif ; vide s'il n'existe pas ou est illisible."""
    chemin = chemin_systeme(chemin_rapport(dossier_ocr))
    if not os.path.isfile(chemin):
        return {}
    try:
        with open(chemin, encoding="utf-8-sig", newline="") as f:
            lecteur = csv.DictReader(f, delimiter=";")
            if tuple(lecteur.fieldnames or ()) != COLONNES:
                return {}
            return {l["chemin_relatif"]: LigneRapport.depuis_csv(l) for l in lecteur}
    except (OSError, ValueError, KeyError, csv.Error):
        return {}


def ecrire(dossier_ocr: pathlib.Path, lignes: dict[str, LigneRapport], tentatives=3, intervalle_s=1.0) -> None:
    """Réécrit le rapport complet, trié par chemin, de façon atomique."""
    tampon = io.StringIO(newline="")
    w = csv.writer(tampon, delimiter=";", quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
    w.writerow(COLONNES)
    for cle in sorted(lignes, key=str.casefold):
        w.writerow(lignes[cle].vers_csv())
    octets = tampon.getvalue().encode("utf-8-sig")

    def producteur(chemin):
        with open(chemin, "wb") as f:
            f.write(octets)

    ecrire_atomique(chemin_rapport(dossier_ocr), producteur, tentatives, intervalle_s)


def bilan(lignes) -> dict[str, int]:
    """Nombres de la fenêtre de fin, recalculés depuis les lignes du rapport (EX-16)."""
    lignes = list(lignes)
    traitees = [l for l in lignes if l.action == "traite"]
    return {
        "traites": sum(1 for l in traitees if l.statut not in ("erreur", "non_pris_en_charge")),
        "signales": sum(1 for l in traitees if l.statut in ("douteux", "non_pris_en_charge")
                        or (l.statut == "natif" and not l.sorties and l.message)),
        "erreurs": sum(1 for l in traitees if l.statut == "erreur"),
        "ignores_a_jour": sum(1 for l in lignes if l.action == "ignore_a_jour"),
        "annules": sum(1 for l in lignes if l.action == "annule"),
    }


class Journal:
    """Journal d'un dossier _OCR : noms de fichiers, numéros de page, nombres et messages
    techniques seulement (EX-66). Rotation au-delà de 5 Mo."""

    def __init__(self, dossier_ocr: pathlib.Path):
        self._log = logging.getLogger(f"ocr_md.journal.{id(self)}")
        self._log.propagate = False
        self._log.setLevel(logging.INFO)
        os.makedirs(chemin_systeme(dossier_ocr), exist_ok=True)
        self._gestionnaire = logging.handlers.RotatingFileHandler(
            chemin_systeme(dossier_ocr / NOM_JOURNAL), maxBytes=TAILLE_MAX_JOURNAL, backupCount=2,
            encoding="utf-8")
        self._gestionnaire.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s",
                                                          "%Y-%m-%d %H:%M:%S"))
        self._log.addHandler(self._gestionnaire)

    def info(self, message: str) -> None:
        self._log.info(message)

    def avertissement(self, message: str) -> None:
        self._log.warning(message)

    def erreur(self, relatif: str, exc: BaseException) -> None:
        trace = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        self._log.error(f"{relatif} : {type(exc).__name__}\n{trace.rstrip()}")

    def fermer(self) -> None:
        self._log.removeHandler(self._gestionnaire)
        self._gestionnaire.close()


__all__ = ["COLONNES", "Journal", "LigneRapport", "NOM_DOSSIER_OCR", "NOM_JOURNAL", "NOM_RAPPORT", "bilan",
           "chemin_rapport", "ecrire", "lire"]
