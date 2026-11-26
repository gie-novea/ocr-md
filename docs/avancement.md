# Avancement de ocr-md

Plan de référence : `docs/plan-v1.md`. Résultats détaillés des points PV : `docs/verifications.md` (non dupliqués ici).

## Jalon -1 : plan (26/11/2026)

Fait :
- plan de réalisation validé et versionné (`docs/plan-v1.md`), avec les réponses du commanditaire.

Écarts au cahier des charges (corrections demandées par le commanditaire, appliquées dans `docs/cahier-des-charges.md`) :
- section 11.1 : chaînes libres entre guillemets, valeurs énumérées sans guillemets ; exemples 11.7 et 11.5 alignés. `origine_texte` reste entre guillemets (ses valeurs contiennent « : », invalide en YAML sans guillemets) ;
- EX-23, EX-82, section 11.2 : nouveau statut `couche_expediteur`, qui prime sur `natif`, `ocrise` et `mixte`, et cède devant `douteux`. Interprétation à confirmer : le front matter ne reçoit pas de nouveau champ ; le cas s'y lit par `pages_couche_existante` non vide et par `origine_texte`, et la consigne au socle des skills est renforcée ;
- EX-82 : guillemets seulement si nécessaire (`QUOTE_MINIMAL`), exemple corrigé ;
- EX-41 : une page douteuse sans texte reçoit le repère douteux et la ligne « page sans texte exploitable ».

Questions ouvertes :
- EX-01 : code de l'outil existant (avant le jalon 1) ;
- source de distribution (avant le jalon 9) ;
- PC SODEB et versions de macOS du parc.

## Jalon 0 : essais de faisabilité (26/11/2026)

Détail des résultats, versions et décisions : `docs/verifications.md`. Scripts : `essais/`.

Fait :
- PV-05 levé : point d'entrée `pymupdf4llm.to_markdown` (code livré par PyMuPDF 2.2) ; texte invisible repris ; `ocr_function` jamais appelée sur une page déjà dotée d'un calque ; repli inutile ;
- PV-06 levé sous Windows : calque invisible en Noto Sans (OFL), écriture par mot, pages droites, inclinées, pivotées et rognées correctes, rendu et images inchangés ;
- PV-04 levé : projection PyWinRT retenue, liste des paquets `winrt-*` établie, 0,1 à 0,2 s par page, réduction A0 et lancement sans console validés ;
- PV-03 levé pour ce poste, PV-11 levé sous Windows, PV-13 levé avec repli ;
- PV-02 (Windows) et PV-09 : scripts prêts, essais manuels à faire ;
- fonctions de fabrication synthétique communes (`essais/commun/fabrication.py`), à reprendre au jalon 2.

Points à trancher par le commanditaire (arrêt B) :
- PV-04 : le moteur Windows rend « oe », « ae » et l'apostrophe droite au lieu de œ, æ et ’. Le CA (a) de EX-30 et l'objectif de 95 % (section 7.3) ne sont atteints qu'en comparant avec ces équivalences (98,8 % alors). Recommandation : critères avec équivalences, sans corriger le texte reconnu ;
- PV-13 : le rendu HTML de PyMuPDF4LLM ne restitue pas les fusions ; l'outil produira lui-même le HTML des tableaux natifs fusionnés ; pas de garantie sur les tableaux scannés ;
- PV-12 : autoriser le téléchargement du lexique de Grammalecte (MPL 2.0), recommandé, ou de Lexique 3 (CC BY-SA 4.0).

Reste à faire avant ou pendant les jalons suivants :
- tests manuels PV-02 (SendTo, 30 et 200 fichiers) et PV-09 (dossier kDrive de test) ;
- PV-06 (b) et PV-08 par la CI macOS (jalon 1) ;
- PV-01, PV-10 en recette ;
- comportement trompeur de `uv python install` à reproduire au jalon 9.

Écarts au cahier des charges constatés :
- section 3.4 et PV-05 : `pymupdf4llm` et `pymupdf-layout` 2.2 sont des paquets vides ; le code vient de `pymupdf` 2.2 ; `onnxruntime` (MIT) devient une dépendance transitive ;
- EX-44 : `table_output="html"` ne conserve pas les fusions (voir PV-13) ;
- EX-30 et 7.3 : voir PV-04.

Décisions du commanditaire sur le jalon 0 (26/11/2026) :
- interprétations validées : `origine_texte` entre guillemets ; pas de nouveau champ de front matter pour `couche_expediteur` ;
- équivalences `œ`/`oe`, `æ`/`ae`, `’`/`'` admises dans les critères (EX-30 a, 7.3) et appliquées avant la recherche dans le lexique (EX-36) ; texte reconnu inchangé ; fichier 18 ajouté au jeu de test ;
- tableaux : HTML des tableaux natifs fusionnés produit par l'outil ; repère « tableau reconnu par OCR » devant tout tableau d'une page reconnue par OCR (EX-44 et 11.4 mis à jour) ; DPGF et cadre de décomposition des honoraires ajoutés au fichier 6, version scannée 6b ajoutée ;
- lexique : Grammalecte (MPL 2.0).

## Jalon 1 : squelette, configuration, ligne de commande, CI (26/11/2026)

Fait :
- EX-01 : outil existant fourni et lu ; éléments repris consignés dans le CHANGELOG (« Reprise de l'existant ») ; aucune dépendance à l'exécution ;
- `pyproject.toml` (Python `>=3.12,<3.13`, dépendances propres à chaque plateforme par marqueurs `sys_platform`, lanceur sans console `ocr-mdw`), `uv.lock` versionné, licence AGPL-3.0 (`LICENSE`), `README.md`, `CHANGELOG.md`, `LICENCES-TIERCES.md` (données embarquées) ;
- `config` : 24 paramètres avec valeur par défaut, bornes et description ; fichier TOML du profil puis `--config` ; paramètre inconnu ou valeur invalide : erreur d'usage (EX-67) ;
- `cli` : interface complète de EX-11 en français, codes de retour (EX-12), `--qualite` renvoyant 2 avec le message de la v1.1, `--version` (versions, moteur, licence, adresse du code source), `verifier` (système, moteur OCR et langues, dossiers du profil) ; le traitement des fichiers lui-même arrive aux jalons 3 à 8 ;
- `ocr` : interface commune, moteur Windows (`Windows.Media.Ocr`, attente de l'opération WinRT sans `asyncio`) et moteur macOS (Apple Vision par `ocrmac`), choisis à l'exécution ;
- `qualite` : lexique embarqué (PV-12 levé) et normalisation des équivalences ;
- tests : 63 tests (réseau neutralisé pour tous, EX-03), dont tests d'architecture (EX-07, EX-08) et tests des moteurs réels (niveau 2). Sous Windows : 60 réussis, 3 sautés (propres à macOS). Mots de référence retrouvés par `Windows.Media.Ocr` : 97,6 % ; page à ligatures : 100 %, moins de 10 % de mots inconnus ;
- CI GitHub Actions (`.github/workflows/tests.yml`) : Windows, macOS Apple Silicon, macOS Intel (`macos-15-intel`), Linux ; Python géré par uv ; sous macOS, OCR Apple Vision réel et test de la convention des boîtes (PV-06 b, PV-08 a). **Non exécutée : aucun envoi vers un dépôt distant sans accord.**

Reste à faire :
- premier passage de la CI après envoi vers GitHub (à autoriser) : confirmer la convention des boîtes de Vision, la présence de fr-FR sous macOS, le fonctionnement sur Mac Intel et la disponibilité du module OCR français sur l'image Windows de GitHub ;
- PV-02 : essai à 200 éléments ; supprimer le journal `essais/pv02/sortie/journal_arguments.jsonl`, qui contient des chemins réels ;
- PV-09 : dossier kDrive de test.

Écarts et précisions :
- `--pages` implique la reprise d'OCR des pages listées, avec ou sans `--refaire-ocr` (lecture de EX-39) ;
- la sous-commande `raccourcis` répond « fonction réalisée au jalon 9 » (code 2) d'ici là ; le traitement renvoie 1 avec un message d'ici le jalon 3 ;
- paramètres ajoutés, marqués « proposition » dans le code : `page_blanche_ecart_type_max` (8), `intervalle_tentatives_s` (1 s) ; `processus` borné à 1 en v1 (REC-06) ;
- sous macOS, Vision ne donnant que des lignes, les boîtes des mots sont estimées au prorata des caractères (écriture du calque par ligne, voir PV-06).
