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
