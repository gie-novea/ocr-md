# Essais de faisabilité (jalon 0)

Prototypes courts et isolés, hors paquet, qui lèvent les points PV-xx du cahier des charges. Résultats consignés dans `docs/verifications.md`. Données entièrement synthétiques, fabriquées par `commun/fabrication.py` (fonctions reprises par le générateur du jeu de test au jalon 2).

Environnement (depuis ce dossier, sous Windows) :

```
uv venv --python 3.12 .venv
uv pip install --python .venv pymupdf==2.2 pymupdf4llm==2.2 (essais du jalon 0 ; le paquet est figé en 1.28.2, voir docs/verifications.md) pymupdf-fonts pillow numpy winrt-Windows.Media.Ocr winrt-Windows.Globalization winrt-Windows.Graphics.Imaging winrt-Windows.Storage.Streams
```

| Dossier | Point | Commande |
|---|---|---|
| `pv02/` | raccourci « Envoyer vers » | `../.venv/Scripts/python creer_raccourci.py` |
| `pv04/` | OCR Windows | `../.venv/Scripts/python essai_pv04.py` |
| `pv05/` | `ocr_function`, texte invisible | `../.venv/Scripts/python essai_pv05.py` |
| `pv06/` | calque invisible Unicode | `../.venv/Scripts/python essai_pv06.py` |
| `pv09/` | diagnostic kDrive | `python diagnostic_fichier.py FICHIER` |
| `pv11/` | tkinter (Python géré par uv) | `pythonw essai_pv11.py` |
| `pv13/` | cellules fusionnées | `../.venv/Scripts/python essai_pv13.py` |

Les sorties volumineuses (`*/sortie/`) ne sont pas versionnées, à l'exception des résultats `resultat_*.json`.
