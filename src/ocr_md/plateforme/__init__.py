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
        # platform.release() peut valoir « 2025Server » : on s'appuie sur le numéro de build.
        v = sys.getwindowsversion()
        nom = "Windows 11" if v.build >= 22000 else "Windows 10"
        if "server" in platform.release().lower():
            nom = f"Windows Server ({platform.release()})"
        return f"{nom} ({v.major}.{v.minor}.{v.build}, {platform.machine()})"
    if s == "macos":
        return f"macOS {platform.mac_ver()[0]} ({platform.machine()})"
    return f"{platform.system()} {platform.release()} ({platform.machine()})"


def systeme_pris_en_charge() -> bool:
    """Windows 10 ou 11 ; macOS 10.15 ou plus (EX-71). Linux sert aux tests seulement."""
    s = systeme()
    if s == "windows":
        return sys.getwindowsversion().major >= 10
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


LIMITE_LIGNE_DE_COMMANDE = 32767  # caractères, Windows (CreateProcess)
PART_ALERTE_LIGNE_DE_COMMANDE = 0.9


def longueur_ligne_de_commande() -> int | None:
    """Longueur de la ligne de commande du processus sous Windows (GetCommandLineW), None
    ailleurs (macOS transmet la sélection d'une Action rapide sans cette limite)."""
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        fonction = ctypes.windll.kernel32.GetCommandLineW
        fonction.restype = ctypes.c_wchar_p
        return len(fonction() or "")
    except Exception:
        return None


def ligne_de_commande_proche_de_la_limite(longueur: int | None = None) -> bool:
    """Sélection « Envoyer vers » proche de la limite de longueur de la ligne de commande de
    Windows (décision du commanditaire du 26/11/2026, PV-02) : au-delà de 90 % de 32 767
    caractères, des éléments ont pu être perdus ; l'outil le signale."""
    longueur = longueur_ligne_de_commande() if longueur is None else longueur
    return longueur is not None and longueur >= PART_ALERTE_LIGNE_DE_COMMANDE * LIMITE_LIGNE_DE_COMMANDE
