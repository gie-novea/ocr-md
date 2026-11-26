"""Essai PV-09 : diagnostic d'un fichier kDrive (ou autre) sans le modifier.

Affiche, pour chaque fichier passé en argument : taille déclarée, attributs Windows
(OFFLINE, RECALL_ON_OPEN, RECALL_ON_DATA_ACCESS, SPARSE, REPARSE_POINT), drapeaux et
blocs alloués sous macOS, puis le résultat et la durée d'une lecture de 1 Ko avec délai.
N'écrit rien à côté des fichiers ; à utiliser uniquement sur un dossier de test synthétique.
Usage : python diagnostic_fichier.py [--delai 120] FICHIER [FICHIER ...]
"""
import argparse
import concurrent.futures
import json
import os
import stat
import sys
import time

ATTRIBUTS_WINDOWS = {
    "READONLY": 0x1, "HIDDEN": 0x2, "SYSTEM": 0x4, "ARCHIVE": 0x20, "SPARSE_FILE": 0x200,
    "REPARSE_POINT": 0x400, "OFFLINE": 0x1000, "PINNED": 0x80000, "UNPINNED": 0x100000,
    "RECALL_ON_OPEN": 0x40000, "RECALL_ON_DATA_ACCESS": 0x400000,
}


def lire_debut(chemin):
    with open(chemin, "rb") as f:
        return f.read(1024)


def diagnostiquer(chemin, delai):
    st = os.stat(chemin)
    res = {"fichier": chemin, "taille_declaree": st.st_size}
    if sys.platform == "win32":
        a = st.st_file_attributes
        res["attributs"] = [n for n, v in ATTRIBUTS_WINDOWS.items() if a & v]
        res["attributs_hex"] = hex(a)
    else:
        res["st_flags"] = getattr(st, "st_flags", None)
        res["blocs_alloues"] = getattr(st, "st_blocks", None)
        res["sans_donnees_locales_probable"] = (st.st_size > 0 and getattr(st, "st_blocks", 1) == 0)
        res["dataless_macos"] = bool(getattr(st, "st_flags", 0) & 0x40000000)  # SF_DATALESS
    t0 = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(1) as ex:
        futur = ex.submit(lire_debut, chemin)
        try:
            debut = futur.result(timeout=delai)
            res["lecture"] = "ok"
            res["octets_lus"] = len(debut)
            res["signature_pdf"] = debut.startswith(b"%PDF-")
        except concurrent.futures.TimeoutError:
            res["lecture"] = f"délai de {delai} s dépassé"
        except OSError as e:
            res["lecture"] = f"erreur : {e}"
    res["duree_lecture_s"] = round(time.perf_counter() - t0, 2)
    return res


def main():
    p = argparse.ArgumentParser(description="Diagnostic de disponibilité locale de fichiers")
    p.add_argument("--delai", type=float, default=120)
    p.add_argument("fichiers", nargs="+")
    a = p.parse_args()
    for f in a.fichiers:
        print(json.dumps(diagnostiquer(f, a.delai), ensure_ascii=False), flush=True)
    os._exit(0)  # ne pas attendre une lecture bloquée


if __name__ == "__main__":
    main()
