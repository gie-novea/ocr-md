"""Aiguillage par plateforme : emplacements dans le profil, description du système.

Ce module ne fait aucun import propre à une plateforme au chargement (EX-07). Les
mécanismes d'intégration (raccourcis, notifications, détection kDrive) y seront ajoutés
dans des sous-modules importés à la demande.
"""

import os
import pathlib
import platform
import sys

NOM_OUTIL = "ocr-md"


def systeme() -> str:
    """Renvoie « windows », « macos » ou « linux » (ou le nom brut pour un autre système)."""
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    if sys.platform.startswith("linux"):
        return "linux"
    return sys.platform


def description_systeme() -> str:
    """Version du système et architecture, pour le journal et le diagnostic."""
    s = systeme()
    if s == "windows":
        version = platform.version()
        nom = "Windows 11" if int(version.split(".")[2]) >= 22000 else "Windows 10"
        return f"{nom} ({version}, {platform.machine()})"
    if s == "macos":
        return f"macOS {platform.mac_ver()[0]} ({platform.machine()})"
    return f"{platform.system()} {platform.release()} ({platform.machine()})"


def systeme_pris_en_charge() -> bool:
    """Windows 10 ou 11 ; macOS 10.15 ou plus (EX-71). Linux sert aux tests seulement."""
    s = systeme()
    if s == "windows":
        return int(platform.release() or 0) >= 10
    if s == "macos":
        version = tuple(int(x) for x in (platform.mac_ver()[0] or "0").split(".")[:2])
        return version >= (10, 15)
    return False


def _base(variable: str, repli: pathlib.Path) -> pathlib.Path:
    valeur = os.environ.get(variable)
    return pathlib.Path(valeur) if valeur else repli


def dossier_configuration() -> pathlib.Path:
    """Dossier du fichier de configuration de l'utilisateur, dans son profil."""
    s = systeme()
    maison = pathlib.Path.home()
    if s == "windows":
        return _base("APPDATA", maison / "AppData" / "Roaming") / NOM_OUTIL
    if s == "macos":
        return maison / "Library" / "Application Support" / NOM_OUTIL
    return _base("XDG_CONFIG_HOME", maison / ".config") / NOM_OUTIL


def fichier_configuration() -> pathlib.Path:
    return dossier_configuration() / "config.toml"


def dossier_temporaire() -> pathlib.Path:
    """Dossier temporaire propre à l'outil, dans le profil (EX-28)."""
    s = systeme()
    maison = pathlib.Path.home()
    if s == "windows":
        return _base("LOCALAPPDATA", maison / "AppData" / "Local") / NOM_OUTIL / "temp"
    if s == "macos":
        return maison / "Library" / "Caches" / NOM_OUTIL / "temp"
    return _base("XDG_CACHE_HOME", maison / ".cache") / NOM_OUTIL / "temp"


def dossier_inscriptible(dossier: pathlib.Path) -> bool:
    """Test d'écriture réel : sous Windows, os.access ignore les ACL (repris de l'outil
    existant). Crée puis supprime un fichier vide ; ne sert qu'aux dossiers de l'outil."""
    try:
        dossier.mkdir(parents=True, exist_ok=True)
        essai = dossier / f".ocr-md-essai-{os.getpid()}.tmp"
        essai.write_bytes(b"")
        essai.unlink()
        return True
    except OSError:
        return False
