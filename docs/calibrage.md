# Calibrage des seuils de qualité (EX-76)

Produit par `tests/calibrage.py` le 27/11/2026 sur le jeu de test synthétique (graine 2026, fichier 21 compris) : moteur factice et `Windows.Media.Ocr` sur le poste de développement Windows 11, Apple Vision dans la CI macOS (Apple Silicon et Intel, run 45986963307, correction linguistique désactivée). Les tableaux ne contiennent que des nombres.

## Méthode

Pour chaque indicateur et chaque origine du texte (couche OCR existante, ou moteur de l'outil), le script donne l'écart entre la page saine la plus défavorable et la page dégradée la plus favorable. Les pages saines et dégradées sont celles que déclare le manifeste (vérité terrain), et non celles que déclenchent les seuils en vigueur. Règle du commanditaire (27/11/2026) : la valeur du cahier est retenue si elle tombe dans l'écart ; sinon, le milieu de l'écart. Le fichier 21 (trois pages moyennement dégradées, lisibles en partie) a été ajouté pour que l'écart soit mesurable pour chaque moteur. Les seuils définitifs seront fixés en recette (TM-08), avec ce même script lancé sur un dossier local de documents réels : `uv run python tests/calibrage.py DOSSIER --moteur systeme`.

## Mots inconnus : un seuil par origine du texte

Pages d'au moins 40 mots évaluables seulement.

| Origine du texte | Page saine la plus défavorable | Page dégradée la plus favorable | Cahier | Seuil retenu |
|---|---|---|---|---|
| couche OCR existante | 0,000 | 0,383 (fichier 4, p. 3) | 0,35, dans l'écart | `mots_inconnus_max_couche_existante` = 0,35 |
| `Windows.Media.Ocr` | 0,000 | 0,127 (fichier 21, p. 1, 79 % de mots retrouvés) | 0,35, hors de l'écart | `mots_inconnus_max_windows` = 0,064 (milieu) |
| Apple Vision, Apple Silicon | 0,027 (fichier 2, p. 4) | 0,076 (fichier 21, p. 1) | 0,35, hors de l'écart | |
| Apple Vision, Intel | 0,050 (fichier 19, p. 1) | 0,061 (fichier 21, p. 1) | 0,35, hors de l'écart | |
| Apple Vision, deux Mac réunis | 0,050 | 0,061 | 0,35, hors de l'écart | `mots_inconnus_max_vision` = 0,055 (milieu) |

Mesures des pages du fichier 21 (mots retrouvés, mots inconnus) :

| Page | `Windows.Media.Ocr` | Vision, Apple Silicon | Vision, Intel |
|---|---|---|---|
| 1 : scan 150 dpi, léger flou | 79 %, 0,127 | 86 %, 0,076 | 90 %, 0,061 |
| 2 : tampon sur le texte | 76 %, 0,136 | 85 %, 0,111 | 84 %, 0,141 |
| 3 : photocopie de photocopie | 63 %, 0,500 | 88 %, 0,141 | 81 %, 0,217 |

Points d'attention pour la recette (TM-08) :
- les marges sont étroites : Windows 0,064 contre des pages saines à 0,000 ; Vision 0,055 entre 0,050 et 0,061. Les pages saines du jeu synthétique sont plus propres que des documents réels (noms communs rares, sigles, vocabulaire technique) : ces seuils risquent de signaler à tort des pages saines réelles. Ils sont à recalibrer en priorité en recette ;
- Vision lit bien mieux que Windows les pages moyennement dégradées (81 à 90 % des mots retrouvés contre 63 à 79 %) : sur ces pages, le taux de mots inconnus de Vision reste proche de celui des pages saines, et l'indicateur les sépare mal.

## Confiance (Apple Vision)

Seuil `confiance_moyenne_min` = 0,70 (cahier), conservé : il est dans l'écart entre la page illisible du fichier 5 (0,51 et 0,52) et les pages saines (0,79 au moins). Sa marge côté pages saines est étroite (0,787 sur la page 2 du fichier 18, Mac Intel) : il est prioritaire en recette (TM-08). Les pages moyennement dégradées du fichier 21 ont une confiance de 0,70 à 0,79, au même niveau que les pages saines : la confiance ne les sépare pas.

## Autres indicateurs

| Indicateur | Seuil | Commentaire |
|---|---|---|
| caractères aberrants | 0,03 (cahier) | 0,113 sur la page 2 du fichier 4, construite pour l'éprouver |
| mots fragmentés | 0,25 (cahier) | pages saines au plus à 0,059 ; pages 2 et 3 du fichier 4 à 0,496 et 0,320 |
| densité minimale | 0,11 | la valeur du cahier (0,2) signalerait à tort un tableau sain clairsemé (fichier 6b, p. 1, à 0,164) ; page illisible lue par Windows à 0,053 |
| mélanges chiffres et lettres | 0,10 (cahier) | aucune page du jeu n'est construite pour l'éprouver |

Avec la méthode du manifeste, l'écart calculé pour ces indicateurs est souvent sans objet : chaque page dégradée n'éprouve que certains indicateurs, et la page dégradée « la plus favorable » pour un indicateur est alors une page qu'un autre indicateur détecte. Ces seuils ne sont donc pas déduits des tableaux ci-dessous ; ils restent ceux décidés le 27/11/2026.

Résultat avec ces seuils : aucune erreur de verdict avec le moteur factice, `Windows.Media.Ocr` et Apple Vision (voir la rubrique Apple Vision en fin de fichier).

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
| pdf/21_moyennement_degrade.pdf | 1 | factice | 121 | 43 | 0.488 | 0.000 | 0.000 | 0.132 | 0.932 | 0.55 | douteuse | douteuse |
| pdf/21_moyennement_degrade.pdf | 2 | factice | 116 | 56 | 0.446 | 0.000 | 0.000 | 0.121 | 0.962 | 0.55 | douteuse | douteuse |
| pdf/21_moyennement_degrade.pdf | 3 | factice | 118 | 51 | 0.588 | 0.000 | 0.000 | 0.161 | 0.964 | 0.55 | douteuse | douteuse |

27 page(s) mesurée(s) ; erreurs de verdict par rapport à la vérité terrain : 0

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
| taux_mots_inconnus | 0.000 (lot/Lot 1/Candidat A/Annexes/Attestation URSSAF.pdf p. 1) | 0.446 (pdf/21_moyennement_degrade.pdf p. 2) | 0.35 | oui | 0.223 |
| taux_caracteres_aberrants | 0.000 (lot/Lot 1/Candidat A/Annexes/Attestation URSSAF.pdf p. 1) | 0.000 (pdf/05_illisible.pdf p. 2) | 0.03 | pas d'écart |  |
| taux_mots_fragmentes | 0.059 (pdf/06b_tableaux_scannes.pdf p. 1) | 0.000 (pdf/21_moyennement_degrade.pdf p. 1) | 0.25 | pas d'écart |  |
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
| pdf/21_moyennement_degrade.pdf | 1 | windows-media-ocr | 113 | 63 | 0.127 | 0.000 | 0.018 | 0.000 | 0.882 |  | douteuse | douteuse |
| pdf/21_moyennement_degrade.pdf | 2 | windows-media-ocr | 111 | 59 | 0.136 | 0.000 | 0.036 | 0.000 | 0.794 |  | douteuse | douteuse |
| pdf/21_moyennement_degrade.pdf | 3 | windows-media-ocr | 108 | 66 | 0.500 | 0.000 | 0.009 | 0.000 | 0.925 |  | douteuse | douteuse |

27 page(s) mesurée(s) ; erreurs de verdict par rapport à la vérité terrain : 0

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
| taux_mots_inconnus | 0.000 (lot/Lot 1/Candidat A/Annexes/Attestation URSSAF.pdf p. 1) | 0.127 (pdf/21_moyennement_degrade.pdf p. 1) | 0.35 | non | 0.064 |
| taux_caracteres_aberrants | 0.000 (lot/Lot 1/Candidat A/Annexes/Attestation URSSAF.pdf p. 1) | 0.000 (pdf/05_illisible.pdf p. 2) | 0.03 | pas d'écart |  |
| taux_mots_fragmentes | 0.059 (pdf/06b_tableaux_scannes.pdf p. 1) | 0.009 (pdf/21_moyennement_degrade.pdf p. 3) | 0.25 | pas d'écart |  |
| taux_melange_chiffres_lettres | 0.019 (pdf/06b_tableaux_scannes.pdf p. 3) | 0.000 (pdf/05_illisible.pdf p. 2) | 0.1 | pas d'écart |  |
| densite | 0.164 (pdf/06b_tableaux_scannes.pdf p. 1) | 0.925 (pdf/21_moyennement_degrade.pdf p. 3) | 0.2 | pas d'écart |  |

## Apple Vision (CI macOS, run 45986963307, correction linguistique désactivée, seuil 0,21 alors en vigueur)

Avec le seuil provisoire de 0,21, deux pages du fichier 21 étaient jugées saines sur chaque Mac (Apple Silicon : pages 1 et 3 ; Intel : pages 1 et 2) ; les autres verdicts étaient conformes. Écart des mots inconnus : Apple Silicon 0,027 (fichier 2, p. 4) à 0,076 (fichier 21, p. 1), milieu 0,051 ; Intel 0,050 (fichier 19, p. 1) à 0,061 (fichier 21, p. 1), milieu 0,055. Seuil retenu : 0,055. Tableaux complets dans le journal de la CI, étape « Calibrage avec Apple Vision ».
Contrôle avec le seuil retenu (CI run 45991048588) : avec `mots_inconnus_max_vision` = 0,055, aucune erreur de verdict sur les 27 pages, sur Apple Silicon comme sur Intel.
