"""Archives .zip (recette du 27/11/2026) : extraction hors de la source, puis traitement du
contenu comme des fichiers ordinaires.

Le contenu d'une archive `dossier/nom.zip` est extrait dans un dossier de travail temporaire
du profil (jamais à côté de la source) ; chaque fichier extrait devient un élément de chemin
relatif `dossier/nom.zip/…`, dont les sorties prennent place dans `_OCR/dossier/nom.zip/…`
et dont la ligne du rapport porte ce chemin. Le dossier de travail est supprimé après le
traitement de l'archive.

Garde-fous :
- taille décompressée totale bornée (`archive_taille_max_mo`), contrôlée sur les tailles
  déclarées puis pendant l'extraction (une archive qui ment sur ses tailles est arrêtée) ;
- un seul niveau d'imbrication : une archive contenue dans une archive est extraite, une
  archive contenue dans celle-ci ne l'est pas (`non_pris_en_charge`) ;
- noms sans l'indicateur UTF-8 : décodés en UTF-8 s'ils en sont, sinon en cp850 (page de code
  des archives créées par l'Explorateur de Windows en français), et non en cp437 ;
- chemins absolus, remontées (« .. ») et caractères interdits sous Windows neutralisés ;
- archive chiffrée par mot de passe : `non_pris_en_charge`, avec un message ; un fichier
  chiffré dans une archive qui ne l'est pas entièrement donne sa propre ligne.
Aucun fichier d'une archive n'est exécuté ; les fichiers extraits ne sont qu'ouverts en lecture.
"""

import dataclasses
import os
import pathlib
import shutil
import unicodedata
import uuid
import zipfile

from . import plateforme
from .inventaire import NOMS_EXCLUS, Element, ErreurFichier, type_par_extension
from .sorties import chemin_systeme

MESSAGE_CHIFFREE = ("archive chiffrée par mot de passe : l'extraire avec son mot de passe, puis traiter le "
                    "dossier extrait")
MESSAGE_FICHIER_CHIFFRE = ("fichier chiffré par mot de passe dans l'archive : l'extraire avec son mot de passe, "
                           "puis le traiter")
MESSAGE_ENDOMMAGEE = "archive .zip endommagée"
MESSAGE_IMBRICATION = ("archive contenue dans une archive elle-même contenue dans une archive : l'extraire, puis "
                       "traiter le dossier extrait")
MESSAGE_COMPRESSION = ("archive compressée par une méthode non prise en charge : l'extraire, puis traiter le "
                       "dossier extrait")
PROFONDEUR_MAX = 1  # une archive de profondeur 0 (sur le disque) ou 1 (dans une archive) est extraite
_INTERDITS = set('<>:"|?*') | {chr(i) for i in range(32)}
_BLOC = 1024 * 1024


class NonPrisEnCharge(ErreurFichier):
    """Fichier à signaler en `non_pris_en_charge` (et non en `erreur`), avec ce message."""


def message_trop_volumineuse(taille_mo: float, max_mo: int) -> str:
    return (f"archive trop volumineuse une fois décompressée ({taille_mo:.0f} Mo, maximum {max_mo} Mo) : "
            "l'extraire, puis traiter le dossier extrait")


@dataclasses.dataclass
class Developpement:
    elements: list           # éléments du contenu, dans l'ordre des chemins
    dossier: pathlib.Path    # dossier de travail à supprimer après traitement

    def nettoyer(self) -> None:
        shutil.rmtree(chemin_systeme(self.dossier), ignore_errors=True)


def nom_decode(info: zipfile.ZipInfo) -> str:
    """Nom d'un membre : UTF-8 si l'indicateur le dit ; sinon les octets d'origine sont
    décodés en UTF-8 s'ils en forment un, et en cp850 à défaut (Python les a lus en cp437)."""
    if info.flag_bits & 0x800:
        return info.filename
    brut = info.filename.encode("cp437", errors="replace")
    try:
        return brut.decode("utf-8")
    except UnicodeDecodeError:
        return brut.decode("cp850", errors="replace")


def chemin_sur(nom: str) -> tuple[str, ...] | None:
    """Parties d'un chemin de membre, neutralisées ; None si le membre est à écarter
    (remontée, dossier, fichier exclu ou métadonnées du Finder)."""
    parties = [p for p in nom.replace("\\", "/").split("/") if p not in ("", ".")]
    if not parties or ".." in parties or nom.endswith(("/", "\\")):
        return None
    if parties[0].endswith(":"):  # lecteur Windows (« C: »)
        parties = parties[1:]
    if not parties or parties[0] == "__MACOSX":
        return None
    propres = []
    for p in parties:
        p = unicodedata.normalize("NFC", "".join("_" if c in _INTERDITS else c for c in p)).rstrip(" .")
        if not p:
            return None
        propres.append(p)
    nom_fichier = propres[-1]
    if nom_fichier.startswith((".", "~$")) or nom_fichier.lower() in NOMS_EXCLUS:
        return None
    return tuple(propres)


def _extraire(z: zipfile.ZipFile, info: zipfile.ZipInfo, cible: pathlib.Path, budget: list[int]) -> None:
    """Copie bornée : au plus la taille déclarée du membre, et au plus le budget restant."""
    os.makedirs(chemin_systeme(cible.parent), exist_ok=True)
    ecrits = 0
    with z.open(info) as source, open(chemin_systeme(cible), "wb") as dest:
        while bloc := source.read(_BLOC):
            ecrits += len(bloc)
            budget[0] -= len(bloc)
            if ecrits > info.file_size or budget[0] < 0:
                raise ErreurFichier(MESSAGE_ENDOMMAGEE)
            dest.write(bloc)


def developper(element: Element, taille_max_mo: int, profondeur: int = 0) -> Developpement:
    """Extrait l'archive dans un dossier de travail et renvoie ses éléments. Lève
    NonPrisEnCharge (chiffrée, trop volumineuse, trop imbriquée) ou ErreurFichier."""
    if profondeur > PROFONDEUR_MAX:
        raise NonPrisEnCharge(MESSAGE_IMBRICATION)
    try:
        z = zipfile.ZipFile(chemin_systeme(element.source))
    except (zipfile.BadZipFile, OSError, ValueError):
        raise ErreurFichier(MESSAGE_ENDOMMAGEE) from None
    dossier = plateforme.dossier_temporaire() / f"processus-{os.getpid()}" / "archives" / uuid.uuid4().hex
    try:
        with z:
            membres = [i for i in z.infolist() if not i.is_dir()]
            fichiers = []
            vus = set()
            for info in membres:
                parties = chemin_sur(nom_decode(info))
                if parties is None or "/".join(parties).casefold() in vus:
                    continue
                vus.add("/".join(parties).casefold())
                fichiers.append((info, parties))
            chiffres = [info for info, _ in fichiers if info.flag_bits & 0x1]
            if fichiers and len(chiffres) == len(fichiers):
                raise NonPrisEnCharge(MESSAGE_CHIFFREE)
            taille = sum(info.file_size for info, _ in fichiers if not info.flag_bits & 0x1)
            if taille > taille_max_mo * 1024 * 1024:
                raise NonPrisEnCharge(message_trop_volumineuse(taille / 1024 / 1024, taille_max_mo))
            date = os.stat(chemin_systeme(element.source)).st_mtime
            budget = [taille_max_mo * 1024 * 1024]
            elements = []
            for info, parties in sorted(fichiers, key=lambda x: "/".join(x[1]).casefold()):
                relatif = element.relatif + "/" + "/".join(parties)
                cible = dossier.joinpath(*parties)
                type_, message = type_par_extension(cible)
                if info.flag_bits & 0x1:
                    elements.append(Element(cible, element.parent, relatif, "autre", MESSAGE_FICHIER_CHIFFRE,
                                            profondeur + 1))
                    continue
                try:
                    _extraire(z, info, cible, budget)
                except NotImplementedError:  # Deflate64, par exemple
                    raise NonPrisEnCharge(MESSAGE_COMPRESSION) from None
                except (zipfile.BadZipFile, OSError, EOFError, ValueError, RuntimeError):
                    raise ErreurFichier(MESSAGE_ENDOMMAGEE) from None
                # Date de l'archive : la règle de relance compare les sorties à l'archive.
                os.utime(chemin_systeme(cible), (date, date))
                elements.append(Element(cible, element.parent, relatif, type_, message, profondeur + 1))
    except BaseException:
        shutil.rmtree(chemin_systeme(dossier), ignore_errors=True)
        raise
    return Developpement(elements, dossier)
