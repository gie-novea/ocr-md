"""Cible de test PV-02 : consigne les arguments reçus (nombre, longueur totale, extraits).

Lancée par un raccourci « Envoyer vers » ; écrit sortie/journal_arguments.jsonl.
"""
import datetime
import json
import pathlib
import sys

arguments = sys.argv[1:]
ligne = {
    "date": datetime.datetime.now().isoformat(timespec="seconds"),
    "executable": sys.executable,
    "nombre_arguments": len(arguments),
    "options": [a for a in arguments if a.startswith("--")],
    "longueur_totale": sum(len(a) + 3 for a in arguments),
    "premiers": arguments[:3],
    "derniers": arguments[-2:],
}
with open(pathlib.Path(__file__).with_name("sortie") / "journal_arguments.jsonl", "a", encoding="utf-8") as f:
    f.write(json.dumps(ligne, ensure_ascii=False) + "\n")
