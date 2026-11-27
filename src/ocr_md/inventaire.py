"""Inventaire des éléments passés en entrée (EX-14, EX-18, EX-19, EX-50, EX-62, EX-64).

Parcours récursif des dossiers, exclusions, détermination du type par l'extension puis
confirmation par la signature du fichier, regroupement par dossier parent (chaque groupe
donne un dossier `_OCR`), détection des fichiers kDrive non disponibles localement.
Aucune écriture : les fichiers sources ne sont ouverts qu'en lecture.
"""

import concurrent.futures
import dataclasses
import os
import pathlib
import stat
import sys
import unicodedata
import zipfile

from .sorties import NOM_DOSSIER_OCR, chemin_systeme

EXTENSIONS = {
    ".pdf": "pdf",
    ".jpg": "image", ".jpeg": "image", ".png": "image", ".tif": "image", ".tiff": "image",
    ".docx": "docx", ".xlsx": "xlsx", ".pptx": "pptx",
    ".xlsm": "xlsx",  # classeur à macros : lu comme un .xlsx, macros ignorées, jamais exécutées
    ".zip": "zip",    # archive : extraite hors de la source, contenu traité (module archives)
}
MESSAGES_NON_PRIS_EN_CHARGE = {
    **dict.fromkeys((".doc", ".xls", ".ppt", ".pps"),
                    "ancien format Office : l'enregistrer au format .docx, .xlsx ou .pptx, ou en PDF, puis relancer"),
    **dict.fromkeys((".eml", ".msg"),
                    "e-mail non pris en charge : enregistrer les pièces jointes et les traiter séparément"),
}
MESSAGE_FORMAT_INCONNU = "format non pris en charge"
MESSAGE_SIGNATURE = "le contenu du fichier ne correspond pas à son extension"
MESSAGE_OFFICE_PROTEGE = ("fichier Office protégé par mot de passe : l'enregistrer sans mot de passe dans son "
                          "application, puis relancer")
ENTETE_CFB = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"  # conteneur des fichiers Office chiffrés
MESSAGE_KDRIVE = ("fichier kDrive non disponible sur ce poste (en ligne uniquement) : dans l'Explorateur ou "
                  "le Finder, clic droit sur le dossier, puis \"Toujours conserver sur cet appareil\" (ou "
                  "équivalent), attendre la fin de la synchronisation, puis relancer")
NOMS_EXCLUS = {".ds_store", "thumbs.db", "desktop.ini"}

# Attributs Windows d'un fichier non disponible localement (PV-09)
_ATTRIBUTS_EN_LIGNE = 0x1000 | 0x40000 | 0x400000  # OFFLINE, RECALL_ON_OPEN, RECALL_ON_DATA_ACCESS
_SF_DATALESS = 0x40000000  # macOS


class ErreurFichier(Exception):
    """Erreur propre à un fichier : message en français, destiné au rapport."""


@dataclasses.dataclass(frozen=True)
class Element:
    source: pathlib.Path       # chemin du fichier source
    parent: pathlib.Path       # dossier parent de l'élément passé en entrée (contient _OCR)
    relatif: str               # chemin relatif au parent, séparateur « / », forme NFC
    type: str                  # pdf, image, docx, xlsx, pptx, autre
    message: str = ""          # pour « autre » : raison du non-traitement
    profondeur: int = 0        # 0 : fichier sur le disque ; 1 : dans une archive ; 2 : archive dans une archive

    @property
    def pris_en_charge(self) -> bool:
        return self.type != "autre"


@dataclasses.dataclass
class Groupe:
    """Éléments d'un même dossier parent : un dossier _OCR, un rapport, un journal."""
    parent: pathlib.Path
    elements: list[Element] = dataclasses.field(default_factory=list)
    introuvables: list[str] = dataclasses.field(default_factory=list)  # chemins relatifs

    @property
    def dossier_ocr(self) -> pathlib.Path:
        return self.parent / NOM_DOSSIER_OCR


def nfc(texte: str) -> str:
    return unicodedata.normalize("NFC", texte)


def est_exclu(chemin: pathlib.Path) -> bool:
    """Dossiers _OCR, fichiers cachés, temporaires d'Office et fichiers système (EX-14)."""
    nom = chemin.name
    if nom.startswith(".") or nom.startswith("~$") or nom.lower() in NOMS_EXCLUS:
        return True
    if sys.platform == "win32":
        try:
            attributs = os.stat(chemin_systeme(chemin), follow_symlinks=False).st_file_attributes
            if attributs & (stat.FILE_ATTRIBUTE_HIDDEN | stat.FILE_ATTRIBUTE_SYSTEM):
                return True
        except OSError:
            pass
    return False


def type_par_extension(chemin: pathlib.Path) -> tuple[str, str]:
    ext = chemin.suffix.lower()
    if ext in EXTENSIONS:
        return EXTENSIONS[ext], ""
    return "autre", MESSAGES_NON_PRIS_EN_CHARGE.get(ext, MESSAGE_FORMAT_INCONNU)


def _parcourir(dossier: pathlib.Path):
    """Fichiers d'un dossier, récursivement, triés, sans les éléments exclus."""
    try:
        entrees = sorted(os.scandir(chemin_systeme(dossier)), key=lambda e: nfc(e.name))
    except OSError:
        return
    for e in entrees:
        p = dossier / e.name
        if e.name == NOM_DOSSIER_OCR or est_exclu(p):
            continue
        if e.is_dir(follow_symlinks=False):
            yield from _parcourir(p)
        elif e.is_file(follow_symlinks=False):
            yield p


def inventorier(chemins: list[pathlib.Path]) -> list[Groupe]:
    """Regroupe les fichiers à traiter par dossier parent de l'élément d'entrée (EX-50).

    Un même fichier n'apparaît qu'une fois, même s'il est atteint par deux éléments."""
    groupes: dict[str, Groupe] = {}
    vus: set[str] = set()
    for brut in chemins:
        element = pathlib.Path(os.path.abspath(brut))
        if NOM_DOSSIER_OCR in element.parts:
            continue  # une sortie d'ocr-md n'est jamais retraitée
        parent = element.parent
        cle = nfc(str(parent)).lower() if sys.platform != "linux" else nfc(str(parent))
        groupe = groupes.setdefault(cle, Groupe(parent))
        if not os.path.lexists(chemin_systeme(element)):
            groupe.introuvables.append(nfc(element.name))
            continue
        fichiers = _parcourir(element) if element.is_dir() else ([] if est_exclu(element) else [element])
        for f in fichiers:
            identite = nfc(str(f)).lower()
            if identite in vus:
                continue
            vus.add(identite)
            relatif = nfc(f.relative_to(parent).as_posix())
            type_, message = type_par_extension(f)
            groupe.elements.append(Element(f, parent, relatif, type_, message))
    return list(groupes.values())


# ------------------------------------------------------------------------------ signatures
def _lire_debut(chemin: pathlib.Path, taille: int = 2048) -> bytes:
    with open(chemin_systeme(chemin), "rb") as f:
        return f.read(taille)


def probablement_en_ligne(chemin: pathlib.Path) -> bool:
    """Fichier probablement non disponible localement (kDrive Lite Sync, PV-09)."""
    try:
        st = os.stat(chemin_systeme(chemin))
    except OSError:
        return False
    if sys.platform == "win32":
        return bool(getattr(st, "st_file_attributes", 0) & _ATTRIBUTS_EN_LIGNE)
    if sys.platform == "darwin":
        return bool(getattr(st, "st_flags", 0) & _SF_DATALESS) or (st.st_size > 0 and getattr(st, "st_blocks", 1) == 0)
    return False


def lire_debut_avec_delai(chemin: pathlib.Path, delai_s: float, lecteur=None) -> bytes:
    """Lit le début du fichier ; pour un fichier en ligne uniquement, l'ouverture déclenche
    en principe le téléchargement : on attend au plus delai_s secondes (EX-64)."""
    executeur = concurrent.futures.ThreadPoolExecutor(1)
    futur = executeur.submit(lecteur or _lire_debut, chemin)
    try:
        return futur.result(timeout=delai_s)
    except concurrent.futures.TimeoutError:
        raise ErreurFichier(MESSAGE_KDRIVE) from None
    except OSError:
        raise ErreurFichier(MESSAGE_KDRIVE) from None
    finally:
        executeur.shutdown(wait=False)


def signature_conforme(type_: str, debut: bytes, chemin: pathlib.Path) -> bool:
    if type_ == "pdf":
        return b"%PDF-" in debut[:1024]
    if type_ == "image":
        return (debut.startswith(b"\xff\xd8\xff") or debut.startswith(b"\x89PNG\r\n\x1a\n")
                or debut.startswith(b"II*\x00") or debut.startswith(b"MM\x00*"))
    if type_ == "zip":
        return debut.startswith((b"PK\x03\x04", b"PK\x05\x06"))
    if type_ in ("docx", "xlsx", "pptx"):
        if not debut.startswith(b"PK\x03\x04"):
            return False
        dossier = {"docx": "word/", "xlsx": "xl/", "pptx": "ppt/"}[type_]
        try:
            with zipfile.ZipFile(chemin_systeme(chemin)) as z:
                noms = z.namelist()
        except (zipfile.BadZipFile, OSError):
            return False
        return "[Content_Types].xml" in noms and any(n.startswith(dossier) for n in noms)
    return True


def controler(element: Element, delai_hydratation_s: float, lecteur=None) -> None:
    """Contrôles préalables à l'ouverture : disponibilité locale et signature (EX-18, EX-64).
    Lève ErreurFichier avec le message du rapport."""
    lecteur = lecteur or _lire_debut
    if probablement_en_ligne(element.source):
        debut = lire_debut_avec_delai(element.source, delai_hydratation_s, lecteur)
    else:
        try:
            debut = lecteur(element.source)
        except OSError as e:
            raise ErreurFichier(f"lecture impossible : {e.strerror or e}") from None
    if not signature_conforme(element.type, debut, element.source):
        if element.type in ("docx", "xlsx", "pptx") and office_chiffre(debut, element.source):
            raise ErreurFichier(MESSAGE_OFFICE_PROTEGE)
        raise ErreurFichier(MESSAGE_SIGNATURE)


def office_chiffre(debut: bytes, chemin: pathlib.Path, taille_max: int = 8 * 1024 * 1024) -> bool:
    """Fichier .docx, .xlsx ou .pptx chiffré par mot de passe : conteneur CFB portant le flux
    « EncryptedPackage » (format ECMA-376 chiffré)."""
    if not debut.startswith(ENTETE_CFB):
        return False
    try:
        with open(chemin_systeme(chemin), "rb") as f:
            contenu = f.read(taille_max)
    except OSError:
        return False
    return "EncryptedPackage".encode("utf-16-le") in contenu
