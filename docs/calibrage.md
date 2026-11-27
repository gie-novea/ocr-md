# Calibrage des seuils de qualité (EX-76)

Produit par `tests/calibrage.py` le 27/11/2026 sur le jeu de test synthétique (graine 2026), poste de développement Windows 11. Le tableau ne contient que des nombres.

## Seuils retenus par défaut

Le jeu synthétique est très propre (les pages saines ont des indicateurs presque nuls) : il ne justifie pas d'abaisser les valeurs de départ du cahier (décision du commanditaire du 27/11/2026). Règle appliquée, indicateur par indicateur : si la valeur du cahier tombe dans l'écart entre la page saine la plus défavorable et la page dégradée la plus favorable, elle est retenue ; sinon, le milieu de l'écart est retenu. Les pages dégradées prises en compte pour un indicateur sont celles qu'il déclenche : une page dégradée par un autre défaut ne dit rien de lui (par exemple, la page 2 du fichier 5 lue par `Windows.Media.Ocr` ne garde que 14 mots et relève de la densité, non des mots fragmentés).

| Indicateur | Page saine la plus défavorable | Page dégradée la plus favorable | Cahier | Seuil retenu |
|---|---|---|---|---|
| mots inconnus (pages d'au moins 40 mots évaluables) | 0,000 | 0,383 (fichier 4, p. 3) | 0,35, dans l'écart | 0,35 |
| caractères aberrants | 0,000 | 0,113 (fichier 4, p. 2) | 0,03, dans l'écart | 0,03 |
| mots fragmentés | 0,059 (fichier 6b, p. 1) | 0,320 (fichier 4, p. 3) | 0,25, dans l'écart | 0,25 |
| densité minimale (seuil « en deçà ») | 0,164 (fichier 6b, p. 1, tableau clairsemé) | 0,053 (fichier 5, p. 2, moteur réel) | 0,2, hors de l'écart | 0,11 (milieu : 0,108) |
| mélanges chiffres et lettres | 0,019 (fichier 6b, p. 3) | aucune page du jeu ne l'éprouve | 0,10 | 0,10 |
| confiance moyenne (Vision) | 0,95 (imposée) | 0,30 (imposée, fichier 5, p. 2) | 0,70, dans l'écart | 0,70 |

Avec ces seuils, aucune erreur de verdict, avec le moteur factice comme avec `Windows.Media.Ocr` réel. La page 3 du fichier 4 (caractères aberrants 0,021, sous 0,03) reste douteuse par les mots inconnus et les mots fragmentés. Les seuils définitifs seront fixés en recette (TM-08), avec ce même script lancé sur un dossier local de documents réels : `uv run python tests/calibrage.py DOSSIER --moteur systeme`.

## Moteur factice (vérité terrain du manifeste, confiances imposées)

| fichier | page | catégorie | mots | évaluables | inconnus | aberrants | fragmentés | mélanges | densité | confiance | verdict | attendu |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| lot/Lot 1/Candidat A/Annexes/Attestation URSSAF.pdf | 1 | image | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.176 | 0.95 | bonne | bonne |
| lot/Lot 1/Candidat B/DC2.pdf | 1 | image | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.171 | 0.95 | bonne | bonne |
| pdf/02_scanne.pdf | 1 | image | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.168 | 0.95 | bonne | bonne |
| pdf/02_scanne.pdf | 2 | image | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.168 | 0.95 | bonne | bonne |
| pdf/02_scanne.pdf | 3 | image | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.168 | 0.95 | bonne | bonne |
| pdf/02_scanne.pdf | 4 | image | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.168 | 0.95 | bonne | bonne |
| pdf/03_mixte.pdf | 4 | image | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.169 | 0.95 | bonne | bonne |
| pdf/03_mixte.pdf | 5 | image | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.169 | 0.95 | bonne | bonne |
| pdf/04_couche_degradee.pdf | 1 | couche_existante | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.171 |  | bonne | bonne |
| pdf/04_couche_degradee.pdf | 2 | couche_existante | 282 | 44 | 0.886 | 0.113 | 0.496 | 0.064 | 1.331 |  | douteuse | douteuse |
| pdf/04_couche_degradee.pdf | 3 | couche_existante | 222 | 47 | 0.383 | 0.021 | 0.320 | 0.090 | 1.204 |  | douteuse | douteuse |
| pdf/04_couche_degradee.pdf | 4 | couche_existante | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.171 |  | bonne | bonne |
| pdf/05_illisible.pdf | 1 | image | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.168 | 0.95 | bonne | bonne |
| pdf/05_illisible.pdf | 2 | image | 299 | 28 | 0.536 | 0.000 | 0.545 | 0.087 | 1.182 | 0.3 | douteuse | douteuse |
| pdf/06b_tableaux_scannes.pdf | 1 | image | 17 | 5 | 0.000 | 0.000 | 0.059 | 0.000 | 0.164 | 0.95 | bonne | bonne |
| pdf/06b_tableaux_scannes.pdf | 2 | image | 28 | 9 | 0.000 | 0.000 | 0.000 | 0.000 | 0.215 | 0.95 | bonne | bonne |
| pdf/06b_tableaux_scannes.pdf | 3 | image | 53 | 11 | 0.000 | 0.000 | 0.019 | 0.000 | 0.396 | 0.95 | bonne | bonne |
| pdf/06b_tableaux_scannes.pdf | 4 | image | 53 | 5 | 0.000 | 0.000 | 0.000 | 0.000 | 0.278 | 0.95 | bonne | bonne |
| pdf/18_ligatures.pdf | 1 | image | 147 | 104 | 0.000 | 0.000 | 0.000 | 0.000 | 1.280 | 0.95 | bonne | bonne |
| pdf/18_ligatures.pdf | 2 | image | 147 | 104 | 0.000 | 0.000 | 0.000 | 0.000 | 1.280 | 0.95 | bonne | bonne |
| pdf/19_mention_plateforme.pdf | 1 | image | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.169 | 0.95 | bonne | bonne |
| pdf/19_mention_plateforme.pdf | 2 | image | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.169 | 0.95 | bonne | bonne |
| pdf/20_couche_saine.pdf | 1 | couche_existante | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.169 |  | bonne | bonne |
| pdf/20_couche_saine.pdf | 2 | couche_existante | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.169 |  | bonne | bonne |

24 page(s) mesurée(s) ; erreurs de verdict par rapport à la vérité terrain : 0

Écart par indicateur (pages dégradées : celles que l'indicateur déclenche) :

| indicateur | page saine la plus défavorable | page dégradée la plus favorable | valeur du cahier | dans l'écart | milieu |
|---|---|---|---|---|---|
| taux_mots_inconnus | 0.000 (lot/Lot 1/Candidat A/Annexes/Attestation URSSAF.pdf p. 1) | 0.383 (pdf/04_couche_degradee.pdf p. 3) | 0.35 | oui | 0.192 |
| taux_caracteres_aberrants | 0.000 (lot/Lot 1/Candidat A/Annexes/Attestation URSSAF.pdf p. 1) | 0.113 (pdf/04_couche_degradee.pdf p. 2) | 0.03 | oui | 0.057 |
| taux_mots_fragmentes | 0.059 (pdf/06b_tableaux_scannes.pdf p. 1) | 0.320 (pdf/04_couche_degradee.pdf p. 3) | 0.25 | oui | 0.189 |
| taux_melange_chiffres_lettres | 0.000 (lot/Lot 1/Candidat A/Annexes/Attestation URSSAF.pdf p. 1) | aucune | 0.1 |  |  |
| densite | 0.164 (pdf/06b_tableaux_scannes.pdf p. 1) | aucune | 0.2 |  |  |

seuils de marge maximale (pour information) : taux_mots_inconnus_max = 0.192, taux_caracteres_aberrants_max = 0.057, taux_mots_fragmentes_max = 0.189

## Moteur réel du poste : Windows.Media.Ocr, fr-FR

| fichier | page | catégorie | mots | évaluables | inconnus | aberrants | fragmentés | mélanges | densité | confiance | verdict | attendu |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| lot/Lot 1/Candidat A/Annexes/Attestation URSSAF.pdf | 1 | image | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.174 |  | bonne | bonne |
| lot/Lot 1/Candidat B/DC2.pdf | 1 | image | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.171 |  | bonne | bonne |
| pdf/02_scanne.pdf | 1 | image | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.166 |  | bonne | bonne |
| pdf/02_scanne.pdf | 2 | image | 144 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.166 |  | bonne | bonne |
| pdf/02_scanne.pdf | 3 | image | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.166 |  | bonne | bonne |
| pdf/02_scanne.pdf | 4 | image | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.161 |  | bonne | bonne |
| pdf/03_mixte.pdf | 4 | image | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.169 |  | bonne | bonne |
| pdf/03_mixte.pdf | 5 | image | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.169 |  | bonne | bonne |
| pdf/04_couche_degradee.pdf | 1 | couche_existante | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.171 |  | bonne | bonne |
| pdf/04_couche_degradee.pdf | 2 | couche_existante | 282 | 44 | 0.886 | 0.113 | 0.496 | 0.064 | 1.331 |  | douteuse | douteuse |
| pdf/04_couche_degradee.pdf | 3 | couche_existante | 222 | 47 | 0.383 | 0.021 | 0.320 | 0.090 | 1.204 |  | douteuse | douteuse |
| pdf/04_couche_degradee.pdf | 4 | couche_existante | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.171 |  | bonne | bonne |
| pdf/05_illisible.pdf | 1 | image | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.166 |  | bonne | bonne |
| pdf/05_illisible.pdf | 2 | image | 14 | 1 | 0.000 | 0.000 | 0.071 | 0.000 | 0.053 |  | douteuse | douteuse |
| pdf/06b_tableaux_scannes.pdf | 1 | image | 17 | 5 | 0.000 | 0.000 | 0.059 | 0.000 | 0.164 |  | bonne | bonne |
| pdf/06b_tableaux_scannes.pdf | 2 | image | 28 | 9 | 0.000 | 0.000 | 0.000 | 0.000 | 0.215 |  | bonne | bonne |
| pdf/06b_tableaux_scannes.pdf | 3 | image | 52 | 11 | 0.000 | 0.000 | 0.019 | 0.019 | 0.393 |  | bonne | bonne |
| pdf/06b_tableaux_scannes.pdf | 4 | image | 49 | 6 | 0.000 | 0.000 | 0.000 | 0.000 | 0.269 |  | bonne | bonne |
| pdf/18_ligatures.pdf | 1 | image | 147 | 104 | 0.000 | 0.000 | 0.000 | 0.000 | 1.280 |  | bonne | bonne |
| pdf/18_ligatures.pdf | 2 | image | 147 | 104 | 0.000 | 0.000 | 0.000 | 0.000 | 1.280 |  | bonne | bonne |
| pdf/19_mention_plateforme.pdf | 1 | image | 158 | 80 | 0.000 | 0.000 | 0.000 | 0.000 | 1.288 |  | bonne | bonne |
| pdf/19_mention_plateforme.pdf | 2 | image | 158 | 80 | 0.000 | 0.000 | 0.000 | 0.000 | 1.286 |  | bonne | bonne |
| pdf/20_couche_saine.pdf | 1 | couche_existante | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.169 |  | bonne | bonne |
| pdf/20_couche_saine.pdf | 2 | couche_existante | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.169 |  | bonne | bonne |

24 page(s) mesurée(s) ; erreurs de verdict par rapport à la vérité terrain : 0

Écart par indicateur (pages dégradées : celles que l'indicateur déclenche) :

| indicateur | page saine la plus défavorable | page dégradée la plus favorable | valeur du cahier | dans l'écart | milieu |
|---|---|---|---|---|---|
| taux_mots_inconnus | 0.000 (lot/Lot 1/Candidat A/Annexes/Attestation URSSAF.pdf p. 1) | 0.383 (pdf/04_couche_degradee.pdf p. 3) | 0.35 | oui | 0.192 |
| taux_caracteres_aberrants | 0.000 (lot/Lot 1/Candidat A/Annexes/Attestation URSSAF.pdf p. 1) | 0.113 (pdf/04_couche_degradee.pdf p. 2) | 0.03 | oui | 0.057 |
| taux_mots_fragmentes | 0.059 (pdf/06b_tableaux_scannes.pdf p. 1) | 0.320 (pdf/04_couche_degradee.pdf p. 3) | 0.25 | oui | 0.189 |
| taux_melange_chiffres_lettres | 0.019 (pdf/06b_tableaux_scannes.pdf p. 3) | aucune | 0.1 |  |  |
| densite | 0.164 (pdf/06b_tableaux_scannes.pdf p. 1) | 0.053 (pdf/05_illisible.pdf p. 2) | 0.2 | non | 0.108 |

seuils de marge maximale (pour information) : taux_mots_inconnus_max = 0.192, taux_caracteres_aberrants_max = 0.057, taux_mots_fragmentes_max = 0.189, densite_min = 0.108
