# ocr-md

Utilitaire de bureau (macOS et Windows) qui rend lisibles les pièces d'un pli de candidature : PDF scannés reconnus par le moteur OCR du système (Apple Vision, `Windows.Media.Ocr`), images, PDF natifs et fichiers Office. Pour chaque pièce, il produit dans un dossier `_OCR` un PDF consultable et un Markdown annoté destiné à l'analyse par IA, avec un rapport et un fichier d'avertissements qui signalent les pages dont le texte est douteux. Aucun document ne quitte le poste. Projet du GIE NOVEA.

## Installation rapide

Dans le profil de l'utilisateur, sans droits d'administrateur.

- **Windows** : télécharger https://github.com/gie-novea/ocr-md/archive/refs/tags/v1.0.0-rc1.zip (version candidate, en recette), l'extraire, double-cliquer sur `installation\installer-windows.cmd`.
- **macOS** : coller dans le Terminal :

  ```
  cd /tmp && rm -rf ocr-md-* && curl -LsSf https://github.com/gie-novea/ocr-md/archive/refs/tags/v1.0.0-rc1.zip -o ocr-md.zip && unzip -oq ocr-md.zip && bash ocr-md-*/installation/installer-macos.command
  ```

Ensuite : clic droit sur un dossier, puis « Envoyer vers » (Windows) ou « Actions rapides » (macOS), puis « OCR - Les deux ».

## Documentation

- Utilisateurs : `docs/guide-utilisateur-windows.md`, `docs/guide-utilisateur-macos.md`.
- Référent : `docs/guide-administrateur.md` (installation, réseau, paramètres, messages, diagnostic), `docs/recette-manuelle.md`, `docs/calibrage.md`, `docs/verifications.md`.
- Format des sorties pour les skills : `docs/specification-front-matter.md`, `schema/front-matter-v1.json`.
- Spécification : `docs/cahier-des-charges.md` ; plan et avancement : `docs/plan-v1.md`, `docs/avancement.md`.

## Développement

`uv sync` puis `uv run pytest` (moteur factice sur toutes les plateformes, moteur réel sous Windows et macOS). Documents générés (tableau des paramètres du guide administrateur, `tests/TRACABILITE.md`, `LICENCES-TIERCES.md`, spécification du front matter) : `uv run python outils/documentation.py`. Calibrage des seuils : `uv run python tests/calibrage.py`. Performance sur le lot type : `uv run python tests/perf/lot_type.py`.

## Licence

GNU AGPL-3.0 (fichier `LICENSE`), imposée par PyMuPDF et PyMuPDF4LLM ; le code source de chaque version est publié dans ce dépôt (adresse affichée par `ocr-md --version`). Lexique embarqué : Grammalecte, MPL 2.0 ; police embarquée : Noto Sans, OFL 1.1. Inventaire des licences : `LICENCES-TIERCES.md`.
