"""Essai PV-11 : tkinter dans le Python 3.12 géré par uv (python-build-standalone).

Ouvre une fenêtre de progression minimale, la met à jour, la ferme seule après 2 s,
et écrit un compte rendu JSON (version Tcl/Tk, facteur d'échelle). Lancer par pythonw.
"""
import json
import pathlib
import sys
import tkinter as tk
from tkinter import ttk

sortie = pathlib.Path(__file__).parent / "sortie" / "resultat_pv11.json"
racine = tk.Tk()
racine.title("ocr-md : essai PV-11")
etiquette = ttk.Label(racine, text="Fichier 1 sur 3 : Mémoire d'été.pdf, page 2")
etiquette.pack(padx=20, pady=10)
barre = ttk.Progressbar(racine, length=300, maximum=3)
barre.pack(padx=20, pady=10)
ttk.Button(racine, text="Annuler", command=racine.destroy).pack(pady=10)
etat = {"etapes": 0}


def avancer():
    etat["etapes"] += 1
    barre["value"] = etat["etapes"]
    if etat["etapes"] < 3:
        racine.after(500, avancer)
    else:
        racine.after(500, racine.destroy)


racine.after(500, avancer)
info = {"python": sys.version.split()[0], "interpreteur": pathlib.Path(sys.executable).parent.name,
        "tk": racine.tk.call("info", "patchlevel"), "scaling": racine.tk.call("tk", "scaling"),
        "theme": ttk.Style().theme_use()}
racine.mainloop()
info["etapes_vues"] = etat["etapes"]
sortie.write_text(json.dumps(info, ensure_ascii=False), encoding="utf-8")
