# Inventaire des licences tierces

L'inventaire des dépendances Python (directes et transitives) sera généré à partir de l'environnement verrouillé au jalon 10 (EX-78). Cette page recense dès maintenant les données embarquées.

## Données embarquées

| Élément | Version | Licence | Origine | Empreinte SHA-256 de la source | Fichiers dans le dépôt |
|---|---|---|---|---|---|
| Lexique des formes fléchies du français, Grammalecte (Olivier R., Dicollecte) | 7.7 (archive du 15/12/2025, téléchargée le 26/11/2026) | MPL 2.0, sans mention « Incompatible With Secondary Licenses » : compatible avec la distribution sous AGPL-3.0 | https://grammalecte.net/dic/lexique-grammalecte-fr-v7.7.zip | `bdccf2065e252010253171000a38de84581407896b6bc60aca7d4d69dab7e4d2` | `src/ocr_md/donnees/lexique/formes-fr.txt.gz` (fichier dérivé, reste sous MPL 2.0, avis d'origine conservé en tête), `src/ocr_md/donnees/lexique/LICENCE-MPL-2.0.txt` ; construit par `outils/construire_lexique.py` |
| Lexique complémentaire d'ocr-md | 1 | AGPL-3.0 (projet) | rédigé pour le projet | sans objet | `src/ocr_md/donnees/lexique/complementaire.txt` |

La police embarquée (Noto Sans, SIL OFL 1.1) sera ajoutée au jalon 4.
