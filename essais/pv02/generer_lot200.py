"""Génère essais/pv02/lot200/ : 200 fichiers synthétiques vides pour l'essai PV-02.

Les noms sont longs à dessein : avec le chemin du dossier, la ligne de commande transmise
par « Envoyer vers » pour les 200 fichiers dépasse la limite de 32 767 caractères de
Windows, ce qui permet d'observer le comportement au-delà de la limite.
Usage : python generer_lot200.py
"""
import pathlib

DOSSIER = pathlib.Path(__file__).parent / "lot200"
DOSSIER.mkdir(exist_ok=True)
for n in range(1, 201):
    nom = f"Pièce synthétique {n:03d} - candidat fictif - dossier d'essai de transmission des chemins longs - lot unique.pdf"
    (DOSSIER / nom).write_bytes(b"")
longueur = sum(len(str(p.resolve())) + 3 for p in DOSSIER.iterdir())
print(f"{len(list(DOSSIER.iterdir()))} fichiers ; ligne de commande estimée : {longueur} caractères")
