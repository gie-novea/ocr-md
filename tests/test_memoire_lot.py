"""Mémoire sur un lot de gros fichiers (EX-59) : la mémoire prise pendant un fichier est
rendue à la fin du fichier et ne s'accumule pas d'un fichier à l'autre.

Taille du lot : 10 fichiers de 200 pages à chaque envoi ; 20 fichiers de 500 pages si la
variable d'environnement OCR_MD_ESSAI_LOT vaut « complet » (passage nocturne de la CI).
Moteur factice, rendu à 72 dpi. Mesure dans un sous-processus : mémoire résidente après
chaque fichier et pic échantillonné pendant chaque fichier.
"""

import json
import os
import pathlib
import subprocess
import sys

import pytest

SCRIPT = r'''
import gc, json, pathlib, shutil, sys, threading, time
import psutil
from tests.donnees import generer
from ocr_md import cli, config, traitement
from ocr_md.ocr.factice import MoteurFactice

racine, nb_fichiers, nb_pages = pathlib.Path(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
g = generer.Generateur(racine / "gen", 1)
g.f17_volumineux(nb_pages=nb_pages)
lot = racine / "P" / "lot"
lot.mkdir(parents=True)
for i in range(nb_fichiers):
    shutil.copyfile(racine / "gen" / "volumineux" / f"17_{nb_pages}_pages.pdf", lot / f"F{i:02d}.pdf")
parametres = config.charger(fichier_utilisateur=racine / "absent.toml")
parametres.valeurs["ocr_dpi"] = 72
processus = psutil.Process()
etat = {"pic": 0, "fin": False}

def echantillonner():
    while not etat["fin"]:
        etat["pic"] = max(etat["pic"], processus.memory_info().rss)
        time.sleep(0.02)

threading.Thread(target=echantillonner, daemon=True).start()
apres, pics = [], []
original = traitement._traiter_element

def mesurer(*a, **k):
    etat["pic"] = processus.memory_info().rss
    resultat = original(*a, **k)
    pics.append(etat["pic"])
    gc.collect()
    apres.append(processus.memory_info().rss)
    return resultat

traitement._traiter_element = mesurer
code = traitement.executer(cli.analyser(["--sortie", "pdf", str(lot)]), parametres,
                           moteur=MoteurFactice(g.ocr_factice))
etat["fin"] = True
print(json.dumps({"code": code, "apres": apres, "pics": pics}))
'''


@pytest.mark.exigence("EX-59")
def test_memoire_rendue_entre_les_fichiers_d_un_lot(tmp_path):
    complet = os.environ.get("OCR_MD_ESSAI_LOT") == "complet"
    nb_fichiers, nb_pages = (20, 500) if complet else (10, 200)
    r = subprocess.run([sys.executable, "-c", SCRIPT, str(tmp_path), str(nb_fichiers), str(nb_pages)],
                       capture_output=True, text=True, cwd=pathlib.Path(__file__).parents[1], timeout=3600)
    assert r.returncode == 0, r.stderr[-3000:]
    m = json.loads(r.stdout.strip().splitlines()[-1])
    mo = lambda v: round(v / 2**20)
    apres, pics = [mo(v) for v in m["apres"]], [mo(v) for v in m["pics"]]
    print(f"lot de {nb_fichiers} fichiers de {nb_pages} pages : mémoire après chaque fichier {apres} Mo ; "
          f"pic pendant chaque fichier {pics} Mo")
    assert m["code"] == 0 and len(apres) == nb_fichiers
    # Pas d'accumulation : du 2e au dernier fichier, la mémoire résiduelle ne monte pas de plus
    # de 15 Mo (elle peut baisser : macOS rend la mémoire de façon différée).
    assert max(apres[1:]) - apres[1] < 15, apres
    # Ce qu'un fichier prend est rendu : le pic d'un fichier dépasse la mémoire résiduelle
    # de moins de 100 Ko par page.
    assert max(p - a for p, a in zip(pics[1:], apres[1:])) < nb_pages * 0.1, (pics, apres)
