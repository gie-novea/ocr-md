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
