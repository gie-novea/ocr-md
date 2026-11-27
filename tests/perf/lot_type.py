"""Performance sur le lot type (EX-58) : 50 plis, 500 pages, dont 300 pages scannées au format
A4 à 300 dpi ; sortie `les-deux`.

Le script génère le lot synthétique (graine fixe), le traite, puis le relance sans
modification, et produit un relevé : durée totale, pages par minute, durée de la relance, pic
de mémoire résidente (échantillonné toutes les 50 ms). Objectifs du cahier (à confirmer en
recette, non garantis) : moins de 20 minutes, relance en moins de 30 secondes, moins de 1,5 Go.

Usage :
    uv run python tests/perf/lot_type.py [DOSSIER] [--moteur systeme|factice] [--plis N]
DOSSIER : dossier de travail (défaut : dossier temporaire, supprimé à la fin). Le relevé est
imprimé en fin d'exécution (nombres seulement) et écrit en JSON dans DOSSIER/releve.json.
"""

import argparse
import json
import pathlib
import platform
import shutil
import sys
import tempfile
import threading
import time

import pymupdf

if __package__ in (None, ""):
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from ocr_md import __version__, cli, config, ocr, traitement  # noqa: E402
from tests.donnees import fabrication as fab  # noqa: E402

PAGES_SCANNEES_PAR_PLI = 6   # 50 x 6 = 300 pages scannées
PAGES_NATIVES_PAR_PLI = 4    # 50 x 4 = 200 pages natives


def generer_lot(racine: pathlib.Path, plis: int) -> dict:
    """Plis « Candidat NN » : un PDF scanné de 6 pages (300 dpi) et un PDF natif de 4 pages.
    Renvoie la vérité du moteur factice (identifiant d'image -> mots et boîtes)."""
    verites = {}
    ident = 0
    for n in range(1, plis + 1):
        dossier = racine / "Lot type" / f"Candidat {n:02d}"
        dossier.mkdir(parents=True, exist_ok=True)
        source = pymupdf.open()
        for i in range(PAGES_SCANNEES_PAR_PLI):
            fab.page_native(source, fab.LIGNES_REFERENCE + fab.LIGNES_COURANTES, mot_unique=f"PLI{n:02d}P{i + 1:02d}",
                            pied=f"Page {i + 1} sur {PAGES_SCANNEES_PAR_PLI}")
        scanne = pymupdf.open()
        for page in source:
            ident += 1
            jpeg, taille, transfo = fab.scanner(page, dpi=300, angle=0.5, bruit=4, graine=ident, identifiant=ident)
            scanne.new_page(width=page.rect.width, height=page.rect.height).insert_image(page.rect, stream=jpeg)
            verites[str(ident)] = fab.verite_ocr(page, 300, transfo, taille)
        scanne.save(dossier / "Offre scannée.pdf", garbage=4, deflate=True)
        natif = pymupdf.open()
        for i in range(PAGES_NATIVES_PAR_PLI):
            fab.page_native(natif, fab.LIGNES_REFERENCE + fab.LIGNES_COURANTES, mot_unique=f"NAT{n:02d}P{i + 1:02d}")
        natif.save(dossier / "Mémoire technique.pdf", garbage=4, deflate=True)
    return verites


class Echantillonneur:
    """Pic de mémoire résidente du processus, échantillonné dans un fil secondaire."""

    def __init__(self, periode_s=0.05):
        import psutil
        self.processus = psutil.Process()
        self.periode_s = periode_s
        self.pic = 0
        self._fin = threading.Event()
        self._fil = threading.Thread(target=self._boucle, daemon=True)

    def _boucle(self):
        while not self._fin.is_set():
            self.pic = max(self.pic, self.processus.memory_info().rss)
            time.sleep(self.periode_s)

    def __enter__(self):
        self._fil.start()
        return self

    def __exit__(self, *exc):
        self._fin.set()
        self._fil.join()


def executer(arguments=None) -> dict:
    a = argparse.ArgumentParser(description="Performance d'ocr-md sur le lot type (EX-58)")
    a.add_argument("dossier", nargs="?")
    a.add_argument("--moteur", choices=("systeme", "factice"), default="systeme")
    a.add_argument("--plis", type=int, default=50)
    o = a.parse_args(arguments)
    temporaire = o.dossier is None
    racine = pathlib.Path(o.dossier or tempfile.mkdtemp(prefix="ocr-md-perf-"))
    try:
        debut = time.perf_counter()
        verites = generer_lot(racine, o.plis)
        generation_s = time.perf_counter() - debut
        parametres = config.charger(fichier_utilisateur=racine / "absent.toml")
        if o.moteur == "factice":
            from ocr_md.ocr.factice import MoteurFactice
            moteur = MoteurFactice(verites)
        else:
            moteur = ocr.moteur_systeme(parametres.langue_ocr, parametres.langue_ocr_secondaire)
        options = cli.analyser(["--sans-interface", "--sortie", "les-deux", str(racine / "Lot type")])
        pages = o.plis * (PAGES_SCANNEES_PAR_PLI + PAGES_NATIVES_PAR_PLI)
        with Echantillonneur() as memoire:
            t0 = time.perf_counter()
            bilan = traitement.BilanLot()
            code = traitement.executer(options, parametres, moteur=moteur, bilan=bilan,
                                       suivi=traitement.Suivi())
            duree = time.perf_counter() - t0
            t1 = time.perf_counter()
            bilan_relance = traitement.BilanLot()
            code_relance = traitement.executer(options, parametres, moteur=moteur, bilan=bilan_relance,
                                               suivi=traitement.Suivi())
            relance = time.perf_counter() - t1
        releve = {
            "outil": f"ocr-md {__version__}", "systeme": platform.platform(), "processeur": platform.machine(),
            "moteur": getattr(moteur, "nom", "?"), "plis": o.plis, "pages": pages,
            "pages_scannees": o.plis * PAGES_SCANNEES_PAR_PLI, "generation_s": round(generation_s, 1),
            "duree_s": round(duree, 1), "pages_par_minute": round(60 * pages / duree, 1),
            "relance_s": round(relance, 2), "pic_memoire_mo": round(memoire.pic / 2**20),
            "code": code, "code_relance": code_relance,
            "fichiers_traites": sum(1 for l in bilan.lignes if l.action == "traite"),
            "fichiers_ignores_a_jour": sum(1 for l in bilan_relance.lignes if l.action == "ignore_a_jour"),
            "objectifs": {"duree_s_max": 1200, "relance_s_max": 30, "pic_memoire_mo_max": 1536},
        }
        releve["objectifs_tenus"] = (releve["duree_s"] <= 1200 and releve["relance_s"] <= 30
                                     and releve["pic_memoire_mo"] <= 1536)
        if not temporaire:
            (racine / "releve.json").write_text(json.dumps(releve, ensure_ascii=False, indent=1), encoding="utf-8")
        print(json.dumps(releve, ensure_ascii=False))
        return releve
    finally:
        if temporaire:
            shutil.rmtree(racine, ignore_errors=True)


if __name__ == "__main__":
    executer()
