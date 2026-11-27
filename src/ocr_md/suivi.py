"""Suivi de la progression d'un lot (EX-17) : fichier en cours, rang sur le total, page en cours
pendant l'OCR. L'orchestrateur appelle un objet `Suivi` ; la console (`--sans-interface`) et la
fenêtre de progression (`interface`) en fournissent chacune une version."""

import sys


class Suivi:
    """Suivi sans effet (tests, appels programmés)."""

    def fichier(self, rang: int, total: int, relatif: str) -> None:
        pass

    def page(self, numero: int, total: int) -> None:
        pass


class SuiviConsole(Suivi):
    """Progression sur la sortie standard (`--sans-interface`)."""

    def __init__(self, flux=None):
        self.flux = flux or sys.stdout

    def fichier(self, rang: int, total: int, relatif: str) -> None:
        print(f"[{rang}/{total}] {relatif}", file=self.flux, flush=True)


class SuiviFile(Suivi):
    """Événements déposés dans une file, lue par la fenêtre de progression (autre fil)."""

    def __init__(self, file):
        self.file = file

    def fichier(self, rang: int, total: int, relatif: str) -> None:
        self.file.put(("fichier", rang, total, relatif))

    def page(self, numero: int, total: int) -> None:
        self.file.put(("page", numero, total))
