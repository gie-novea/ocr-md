# Calibrage des seuils de qualité (EX-76)

Produit par `tests/calibrage.py` le 27/11/2026 sur le jeu de test synthétique (graine 2026) : moteur factice et `Windows.Media.Ocr` sur le poste de développement Windows 11, Apple Vision dans la CI macOS (Apple Silicon et Intel). Les tableaux ne contiennent que des nombres.

## Méthode

Pour chaque indicateur et chaque origine du texte (couche OCR existante, ou moteur de l'outil), le script donne l'écart entre la page saine la plus défavorable et la page dégradée la plus favorable. Les pages saines et dégradées sont celles que déclare le manifeste (vérité terrain), et non celles que déclenchent les seuils en vigueur. Règle du commanditaire (27/11/2026) : la valeur du cahier est retenue si elle tombe dans l'écart ; sinon, le milieu de l'écart. Les seuils définitifs seront fixés en recette (TM-08), avec ce même script lancé sur un dossier local de documents réels : `uv run python tests/calibrage.py DOSSIER --moteur systeme`.

## Mots inconnus : un seuil par origine du texte

Apple Vision corrige ses erreurs de lecture en mots plausibles (correction linguistique) : sur la page illisible du fichier 5, il produit surtout des mots du lexique, et son taux de mots inconnus reste sous 0,35 alors que la page est fausse. Un seuil unique abaissé pour lui multiplierait les faux positifs sur les couches d'expéditeurs et sous Windows. D'où trois seuils, réglables dans la configuration (décision du commanditaire du 27/11/2026). Pages d'au moins 40 mots évaluables seulement.

| Origine du texte | Page saine la plus défavorable | Page dégradée la plus favorable | Cahier | Seuil retenu |
|---|---|---|---|---|
| couche OCR existante | 0,000 | 0,383 (fichier 4, p. 3) | 0,35, dans l'écart | `mots_inconnus_max_couche_existante` = 0,35 |
| `Windows.Media.Ocr` | 0,000 | aucune : la page illisible du fichier 5 ne garde qu'un mot évaluable (elle est détectée par la densité) | 0,35, pas d'écart mesurable | `mots_inconnus_max_windows` = 0,35 |
| Apple Vision, Apple Silicon | 0,027 (fichier 2, p. 4) | 0,298 (fichier 5, p. 2) | 0,35, hors de l'écart | |
| Apple Vision, Intel | 0,040 (fichier 2, p. 4) | 0,290 (fichier 5, p. 2) | 0,35, hors de l'écart | |
| Apple Vision, deux Mac réunis | 0,040 | 0,290 | 0,35, hors de l'écart | `mots_inconnus_max_vision` = 0,165 (milieu) |

Le seuil de Vision reste provisoire : l'essai PV-15 (correction linguistique désactivée, `docs/verifications.md`) peut le faire évoluer.

## Autres indicateurs

| Indicateur | Seuil | Commentaire |
|---|---|---|
| caractères aberrants | 0,03 (cahier) | 0,113 sur la page 2 du fichier 4, construite pour l'éprouver |
| mots fragmentés | 0,25 (cahier) | pages saines au plus à 0,059 ; pages 2 et 3 du fichier 4 à 0,496 et 0,320 |
| densité minimale | 0,11 | la valeur du cahier (0,2) signalerait à tort un tableau sain clairsemé (fichier 6b, p. 1, à 0,164) ; page illisible lue par Windows à 0,053 |
| mélanges chiffres et lettres | 0,10 (cahier) | aucune page du jeu n'est construite pour l'éprouver |
| confiance moyenne (Vision) | 0,70 (cahier) | voir PV-15 : la confiance renvoyée sur Mac Intel vaut 1,0 même sur la page illisible |

Avec la méthode du manifeste, l'écart calculé pour ces indicateurs est souvent sans objet : chaque page dégradée n'éprouve que certains indicateurs, et la page dégradée « la plus favorable » pour un indicateur est alors une page qu'un autre indicateur détecte (par exemple, mots fragmentés sous Windows : page illisible à 0,071 pour 14 mots, détectée par la densité). Ces seuils ne sont donc pas déduits des tableaux ci-dessous ; ils restent ceux décidés le 27/11/2026.

Résultat : aucune erreur de verdict avec le moteur factice et `Windows.Media.Ocr` ; avec Apple Vision, voir la CI (rubrique en fin de fichier).

## Moteur factice (vérité terrain du manifeste, confiances imposées)

| fichier | page | origine | mots | évaluables | inconnus | aberrants | fragmentés | mélanges | densité | confiance | verdict | attendu |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| lot/Lot 1/Candidat A/Annexes/Attestation URSSAF.pdf | 1 | factice | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.176 | 0.95 | bonne | bonne |
| lot/Lot 1/Candidat B/DC2.pdf | 1 | factice | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.171 | 0.95 | bonne | bonne |
| pdf/02_scanne.pdf | 1 | factice | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.168 | 0.95 | bonne | bonne |
| pdf/02_scanne.pdf | 2 | factice | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.168 | 0.95 | bonne | bonne |
| pdf/02_scanne.pdf | 3 | factice | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.168 | 0.95 | bonne | bonne |
| pdf/02_scanne.pdf | 4 | factice | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.168 | 0.95 | bonne | bonne |
| pdf/03_mixte.pdf | 4 | factice | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.169 | 0.95 | bonne | bonne |
| pdf/03_mixte.pdf | 5 | factice | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.169 | 0.95 | bonne | bonne |
| pdf/04_couche_degradee.pdf | 1 | couche_existante | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.171 |  | bonne | bonne |
| pdf/04_couche_degradee.pdf | 2 | couche_existante | 282 | 44 | 0.886 | 0.113 | 0.496 | 0.064 | 1.331 |  | douteuse | douteuse |
| pdf/04_couche_degradee.pdf | 3 | couche_existante | 222 | 47 | 0.383 | 0.021 | 0.320 | 0.090 | 1.204 |  | douteuse | douteuse |
| pdf/04_couche_degradee.pdf | 4 | couche_existante | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.171 |  | bonne | bonne |
| pdf/05_illisible.pdf | 1 | factice | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.168 | 0.95 | bonne | bonne |
| pdf/05_illisible.pdf | 2 | factice | 299 | 28 | 0.536 | 0.000 | 0.545 | 0.087 | 1.182 | 0.3 | douteuse | douteuse |
| pdf/06b_tableaux_scannes.pdf | 1 | factice | 17 | 5 | 0.000 | 0.000 | 0.059 | 0.000 | 0.164 | 0.95 | bonne | bonne |
| pdf/06b_tableaux_scannes.pdf | 2 | factice | 28 | 9 | 0.000 | 0.000 | 0.000 | 0.000 | 0.215 | 0.95 | bonne | bonne |
| pdf/06b_tableaux_scannes.pdf | 3 | factice | 53 | 11 | 0.000 | 0.000 | 0.019 | 0.000 | 0.396 | 0.95 | bonne | bonne |
| pdf/06b_tableaux_scannes.pdf | 4 | factice | 53 | 5 | 0.000 | 0.000 | 0.000 | 0.000 | 0.278 | 0.95 | bonne | bonne |
| pdf/18_ligatures.pdf | 1 | factice | 147 | 104 | 0.000 | 0.000 | 0.000 | 0.000 | 1.280 | 0.95 | bonne | bonne |
| pdf/18_ligatures.pdf | 2 | factice | 147 | 104 | 0.000 | 0.000 | 0.000 | 0.000 | 1.280 | 0.95 | bonne | bonne |
| pdf/19_mention_plateforme.pdf | 1 | factice | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.169 | 0.95 | bonne | bonne |
| pdf/19_mention_plateforme.pdf | 2 | factice | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.169 | 0.95 | bonne | bonne |
| pdf/20_couche_saine.pdf | 1 | couche_existante | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.169 |  | bonne | bonne |
| pdf/20_couche_saine.pdf | 2 | couche_existante | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.169 |  | bonne | bonne |

24 page(s) mesurée(s) ; erreurs de verdict par rapport à la vérité terrain : 0

Écart par indicateur, origine du texte « couche_existante » (pages saines et dégradées du manifeste) :

| indicateur | page saine la plus défavorable | page dégradée la plus favorable | valeur du cahier | dans l'écart | milieu |
|---|---|---|---|---|---|
| taux_mots_inconnus | 0.000 (pdf/04_couche_degradee.pdf p. 1) | 0.383 (pdf/04_couche_degradee.pdf p. 3) | 0.35 | oui | 0.192 |
| taux_caracteres_aberrants | 0.000 (pdf/04_couche_degradee.pdf p. 1) | 0.021 (pdf/04_couche_degradee.pdf p. 3) | 0.03 | non | 0.011 |
| taux_mots_fragmentes | 0.000 (pdf/04_couche_degradee.pdf p. 1) | 0.320 (pdf/04_couche_degradee.pdf p. 3) | 0.25 | oui | 0.16 |
| taux_melange_chiffres_lettres | 0.000 (pdf/04_couche_degradee.pdf p. 1) | 0.064 (pdf/04_couche_degradee.pdf p. 2) | 0.1 | non | 0.032 |
| densite | 1.169 (pdf/20_couche_saine.pdf p. 1) | 1.331 (pdf/04_couche_degradee.pdf p. 2) | 0.2 | pas d'écart |  |

Écart par indicateur, origine du texte « factice » (pages saines et dégradées du manifeste) :

| indicateur | page saine la plus défavorable | page dégradée la plus favorable | valeur du cahier | dans l'écart | milieu |
|---|---|---|---|---|---|
| taux_mots_inconnus | 0.000 (lot/Lot 1/Candidat A/Annexes/Attestation URSSAF.pdf p. 1) | aucune | 0.35 |  |  |
| taux_caracteres_aberrants | 0.000 (lot/Lot 1/Candidat A/Annexes/Attestation URSSAF.pdf p. 1) | 0.000 (pdf/05_illisible.pdf p. 2) | 0.03 | pas d'écart |  |
| taux_mots_fragmentes | 0.059 (pdf/06b_tableaux_scannes.pdf p. 1) | 0.545 (pdf/05_illisible.pdf p. 2) | 0.25 | oui | 0.302 |
| taux_melange_chiffres_lettres | 0.000 (lot/Lot 1/Candidat A/Annexes/Attestation URSSAF.pdf p. 1) | 0.087 (pdf/05_illisible.pdf p. 2) | 0.1 | non | 0.043 |
| densite | 0.164 (pdf/06b_tableaux_scannes.pdf p. 1) | 1.182 (pdf/05_illisible.pdf p. 2) | 0.2 | pas d'écart |  |

## Moteur réel du poste : Windows.Media.Ocr, fr-FR

| fichier | page | origine | mots | évaluables | inconnus | aberrants | fragmentés | mélanges | densité | confiance | verdict | attendu |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| lot/Lot 1/Candidat A/Annexes/Attestation URSSAF.pdf | 1 | windows-media-ocr | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.174 |  | bonne | bonne |
| lot/Lot 1/Candidat B/DC2.pdf | 1 | windows-media-ocr | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.171 |  | bonne | bonne |
| pdf/02_scanne.pdf | 1 | windows-media-ocr | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.166 |  | bonne | bonne |
| pdf/02_scanne.pdf | 2 | windows-media-ocr | 144 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.166 |  | bonne | bonne |
| pdf/02_scanne.pdf | 3 | windows-media-ocr | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.166 |  | bonne | bonne |
| pdf/02_scanne.pdf | 4 | windows-media-ocr | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.161 |  | bonne | bonne |
| pdf/03_mixte.pdf | 4 | windows-media-ocr | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.169 |  | bonne | bonne |
| pdf/03_mixte.pdf | 5 | windows-media-ocr | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.169 |  | bonne | bonne |
| pdf/04_couche_degradee.pdf | 1 | couche_existante | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.171 |  | bonne | bonne |
| pdf/04_couche_degradee.pdf | 2 | couche_existante | 282 | 44 | 0.886 | 0.113 | 0.496 | 0.064 | 1.331 |  | douteuse | douteuse |
| pdf/04_couche_degradee.pdf | 3 | couche_existante | 222 | 47 | 0.383 | 0.021 | 0.320 | 0.090 | 1.204 |  | douteuse | douteuse |
| pdf/04_couche_degradee.pdf | 4 | couche_existante | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.171 |  | bonne | bonne |
| pdf/05_illisible.pdf | 1 | windows-media-ocr | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.166 |  | bonne | bonne |
| pdf/05_illisible.pdf | 2 | windows-media-ocr | 14 | 1 | 0.000 | 0.000 | 0.071 | 0.000 | 0.053 |  | douteuse | douteuse |
| pdf/06b_tableaux_scannes.pdf | 1 | windows-media-ocr | 17 | 5 | 0.000 | 0.000 | 0.059 | 0.000 | 0.164 |  | bonne | bonne |
| pdf/06b_tableaux_scannes.pdf | 2 | windows-media-ocr | 28 | 9 | 0.000 | 0.000 | 0.000 | 0.000 | 0.215 |  | bonne | bonne |
| pdf/06b_tableaux_scannes.pdf | 3 | windows-media-ocr | 52 | 11 | 0.000 | 0.000 | 0.019 | 0.019 | 0.393 |  | bonne | bonne |
| pdf/06b_tableaux_scannes.pdf | 4 | windows-media-ocr | 49 | 6 | 0.000 | 0.000 | 0.000 | 0.000 | 0.269 |  | bonne | bonne |
| pdf/18_ligatures.pdf | 1 | windows-media-ocr | 147 | 104 | 0.000 | 0.000 | 0.000 | 0.000 | 1.280 |  | bonne | bonne |
| pdf/18_ligatures.pdf | 2 | windows-media-ocr | 147 | 104 | 0.000 | 0.000 | 0.000 | 0.000 | 1.280 |  | bonne | bonne |
| pdf/19_mention_plateforme.pdf | 1 | windows-media-ocr | 158 | 80 | 0.000 | 0.000 | 0.000 | 0.000 | 1.288 |  | bonne | bonne |
| pdf/19_mention_plateforme.pdf | 2 | windows-media-ocr | 158 | 80 | 0.000 | 0.000 | 0.000 | 0.000 | 1.286 |  | bonne | bonne |
| pdf/20_couche_saine.pdf | 1 | couche_existante | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.169 |  | bonne | bonne |
| pdf/20_couche_saine.pdf | 2 | couche_existante | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.169 |  | bonne | bonne |

24 page(s) mesurée(s) ; erreurs de verdict par rapport à la vérité terrain : 0

Écart par indicateur, origine du texte « couche_existante » (pages saines et dégradées du manifeste) :

| indicateur | page saine la plus défavorable | page dégradée la plus favorable | valeur du cahier | dans l'écart | milieu |
|---|---|---|---|---|---|
| taux_mots_inconnus | 0.000 (pdf/04_couche_degradee.pdf p. 1) | 0.383 (pdf/04_couche_degradee.pdf p. 3) | 0.35 | oui | 0.192 |
| taux_caracteres_aberrants | 0.000 (pdf/04_couche_degradee.pdf p. 1) | 0.021 (pdf/04_couche_degradee.pdf p. 3) | 0.03 | non | 0.011 |
| taux_mots_fragmentes | 0.000 (pdf/04_couche_degradee.pdf p. 1) | 0.320 (pdf/04_couche_degradee.pdf p. 3) | 0.25 | oui | 0.16 |
| taux_melange_chiffres_lettres | 0.000 (pdf/04_couche_degradee.pdf p. 1) | 0.064 (pdf/04_couche_degradee.pdf p. 2) | 0.1 | non | 0.032 |
| densite | 1.169 (pdf/20_couche_saine.pdf p. 1) | 1.331 (pdf/04_couche_degradee.pdf p. 2) | 0.2 | pas d'écart |  |

Écart par indicateur, origine du texte « windows-media-ocr » (pages saines et dégradées du manifeste) :

| indicateur | page saine la plus défavorable | page dégradée la plus favorable | valeur du cahier | dans l'écart | milieu |
|---|---|---|---|---|---|
| taux_mots_inconnus | 0.000 (lot/Lot 1/Candidat A/Annexes/Attestation URSSAF.pdf p. 1) | aucune | 0.35 |  |  |
| taux_caracteres_aberrants | 0.000 (lot/Lot 1/Candidat A/Annexes/Attestation URSSAF.pdf p. 1) | 0.000 (pdf/05_illisible.pdf p. 2) | 0.03 | pas d'écart |  |
| taux_mots_fragmentes | 0.059 (pdf/06b_tableaux_scannes.pdf p. 1) | 0.071 (pdf/05_illisible.pdf p. 2) | 0.25 | non | 0.065 |
| taux_melange_chiffres_lettres | 0.019 (pdf/06b_tableaux_scannes.pdf p. 3) | 0.000 (pdf/05_illisible.pdf p. 2) | 0.1 | pas d'écart |  |
| densite | 0.164 (pdf/06b_tableaux_scannes.pdf p. 1) | 0.053 (pdf/05_illisible.pdf p. 2) | 0.2 | non | 0.108 |

## Apple Vision (CI macOS, run 45980728997, correction linguistique active)

Aucune erreur de verdict sur les deux Mac avec le seuil `mots_inconnus_max_vision` = 0,165. Écart des mots inconnus (pages d'au moins 40 mots évaluables) : Apple Silicon 0,027 (fichier 2, p. 4) à 0,298 (fichier 5, p. 2), milieu 0,163 ; Intel 0,040 (fichier 2, p. 4) à 0,290 (fichier 5, p. 2), milieu 0,165. Confiance moyenne de la page illisible : 0,725 (Apple Silicon) et 1,0 (Intel, voir PV-15 dans `docs/verifications.md`). Tableaux complets dans le journal de la CI, étape « Calibrage avec Apple Vision ».
