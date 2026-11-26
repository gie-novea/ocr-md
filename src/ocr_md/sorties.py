"""Sorties : dossier miroir `_OCR`, nommage, règle de relance, écritures atomiques
(EX-50 à EX-53, EX-63, EX-65).

Toutes les écritures passent par `Ecrivain` : chaque sortie est d'abord écrite sous un nom
temporaire dans son dossier de destination, puis renommée ; les sorties d'un même fichier
ne sont renommées qu'une fois toutes produites, de sorte qu'un fichier en erreur ou annulé
ne laisse aucune sortie partielle.
"""

import os
import pathlib
import sys
import time

NOM_DOSSIER_OCR = "_OCR"
MARQUE_TEMPORAIRE = ".ocr-md-tmp-"
LONGUEUR_SURE = 240  # au-delà, forme étendue \\?\ sous Windows (limite historique : 260)


def chemin_systeme(chemin: pathlib.Path | str) -> str:
    """Chemin utilisable par le système de fichiers. Sous Windows, les chemins longs passent
    par la forme étendue \\\\?\\, sans exiger la stratégie « chemins longs » (EX-63)."""
    texte = os.path.abspath(str(chemin))
    if sys.platform == "win32" and len(texte) >= LONGUEUR_SURE and not texte.startswith("\\\\?\\"):
        if texte.startswith("\\\\"):
            return "\\\\?\\UNC\\" + texte[2:]
        return "\\\\?\\" + texte
    return texte


def nom_pdf(source: pathlib.Path, type_: str) -> str:
    """PDF consultable : même nom pour un PDF, nom complet suivi de .pdf pour une image (EX-51)."""
    return source.name if type_ == "pdf" else source.name + ".pdf"


def nom_md(source: pathlib.Path) -> str:
    """Markdown : nom complet de la source, extension comprise, suivi de .md (EX-51)."""
    return source.name + ".md"


def dossier_destination(element) -> pathlib.Path:
    """Dossier miroir de la source dans `_OCR` (EX-50)."""
    relatif_dossier = pathlib.PurePosixPath(element.relatif).parent
    return element.parent / NOM_DOSSIER_OCR / pathlib.Path(*relatif_dossier.parts)


def sorties_prevues(element, sortie: str) -> dict[str, pathlib.Path]:
    """Sorties attendues pour la sortie demandée : {"pdf": chemin, "md": chemin}.
    Aucune sortie PDF pour les fichiers Office (EX-20)."""
    dossier = dossier_destination(element)
    prevues = {}
    if sortie in ("pdf", "les-deux") and element.type in ("pdf", "image"):
        prevues["pdf"] = dossier / nom_pdf(element.source, element.type)
    if sortie in ("md", "les-deux") and element.type in ("pdf", "image", "docx", "xlsx", "pptx"):
        prevues["md"] = dossier / nom_md(element.source)
    return prevues


def a_jour(element, prevues: dict[str, pathlib.Path]) -> bool:
    """Toutes les sorties demandées existent et sont plus récentes que la source (EX-52)."""
    if not prevues:
        return False
    try:
        date_source = os.stat(chemin_systeme(element.source)).st_mtime
        return all(os.stat(chemin_systeme(p)).st_mtime > date_source for p in prevues.values())
    except OSError:
        return False


def source_plus_recente(element, existantes: dict[str, pathlib.Path]) -> bool:
    """La source a été modifiée après au moins une des sorties existantes."""
    date_source = os.stat(chemin_systeme(element.source)).st_mtime
    return any(os.stat(chemin_systeme(p)).st_mtime < date_source for p in existantes.values())


def date_sorties(existantes: dict[str, pathlib.Path]) -> str:
    import datetime
    t = max(os.stat(chemin_systeme(p)).st_mtime for p in existantes.values())
    return datetime.datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M:%S")


def nettoyer_temporaires(dossier_ocr: pathlib.Path) -> int:
    """Supprime les fichiers temporaires laissés par une exécution interrompue (EX-53)."""
    n = 0
    if not os.path.isdir(chemin_systeme(dossier_ocr)):
        return 0
    for racine, _dossiers, fichiers in os.walk(chemin_systeme(dossier_ocr)):
        for f in fichiers:
            if MARQUE_TEMPORAIRE in f:
                try:
                    os.remove(os.path.join(racine, f))
                    n += 1
                except OSError:
                    pass
    return n


def avec_tentatives(action, tentatives: int, intervalle_s: float):
    """Exécute l'action ; en cas de verrou (antivirus, synchronisation), la retente
    `tentatives` fois, espacées de intervalle_s (EX-65)."""
    for essai in range(tentatives + 1):
        try:
            return action()
        except PermissionError:
            if essai == tentatives:
                raise
            time.sleep(intervalle_s)


def ecrire_atomique(cible: pathlib.Path, producteur, tentatives: int = 3, intervalle_s: float = 1.0) -> None:
    """Écrit un fichier unique de façon atomique : producteur(chemin_temporaire)."""
    e = Ecrivain(tentatives, intervalle_s)
    try:
        e.preparer(cible, producteur)
        e.valider()
    finally:
        e.abandonner()


class Ecrivain:
    """Écritures atomiques d'un groupe de sorties (celles d'un même fichier source)."""

    def __init__(self, tentatives: int = 3, intervalle_s: float = 1.0):
        self.tentatives = tentatives
        self.intervalle_s = intervalle_s
        self._en_attente: list[tuple[str, str]] = []  # (temporaire, définitif)

    def preparer(self, cible: pathlib.Path, producteur) -> None:
        """Produit la sortie sous un nom temporaire, dans le dossier de destination.
        producteur(chemin) reçoit un chemin utilisable directement par le système."""
        definitif = chemin_systeme(cible)
        os.makedirs(os.path.dirname(definitif), exist_ok=True)
        temporaire = os.path.join(os.path.dirname(definitif), f"{cible.name}{MARQUE_TEMPORAIRE}{os.getpid()}")
        self._en_attente.append((temporaire, definitif))
        avec_tentatives(lambda: producteur(temporaire), self.tentatives, self.intervalle_s)

    def dernier_temporaire(self) -> str:
        """Chemin temporaire de la dernière sortie préparée (lisible avant validation)."""
        return self._en_attente[-1][0]

    def valider(self) -> list[str]:
        """Renomme toutes les sorties préparées ; renvoie leurs noms."""
        noms = []
        for temporaire, definitif in self._en_attente:
            avec_tentatives(lambda t=temporaire, d=definitif: os.replace(t, d), self.tentatives, self.intervalle_s)
            noms.append(os.path.basename(definitif))
        self._en_attente.clear()
        return noms

    def abandonner(self) -> None:
        for temporaire, _ in self._en_attente:
            try:
                os.remove(temporaire)
            except OSError:
                pass
        self._en_attente.clear()


def supprimer_sorties(prevues: dict[str, pathlib.Path]) -> None:
    """Retire les sorties d'un fichier passé en erreur, pour qu'aucune sortie périmée ne
    subsiste à côté d'une ligne « erreur » du rapport."""
    for p in prevues.values():
        try:
            os.remove(chemin_systeme(p))
        except OSError:
            pass
