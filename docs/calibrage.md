# Calibrage des seuils de qualité (EX-76)

Produit par `tests/calibrage.py` le 27/11/2026 sur le jeu de test synthétique (graine 2026, fichier 21 compris, 33 pages reconnues ou à couche OCR) : moteur factice et `Windows.Media.Ocr` sur le poste de développement Windows 11, Apple Vision dans la CI macOS (Apple Silicon et Intel, correction linguistique désactivée). Les tableaux ne contiennent que des nombres.

## Principe (décisions du commanditaire du 27/11/2026)

- Les indicateurs lexicaux (EX-36) ne visent que la dégradation grossière : sur les pages moyennement dégradées du fichier 21, le taux de mots inconnus ne discrimine pas (sous Vision, 0,050 pour la page saine la plus défavorable contre 0,061 pour la page dégradée la plus favorable) ; un seuil placé dans cet écart signalerait en masse de vraies pages saines.
- La dégradation moyenne relève de l'indicateur `qualite_image` (EX-35), calculé sur l'image de la page avant l'OCR, donc indépendant du moteur.
- Règle de calibrage : milieu de l'écart entre la page saine la plus défavorable et la page dégradée la plus proche au-delà ; calibrage définitif en recette (TM-08), avec ce même script lancé sur un dossier local de documents réels : `uv run python tests/calibrage.py DOSSIER --moteur systeme`.

## Mots inconnus (dégradation grossière)

Pages d'au moins 40 mots évaluables seulement.

| Origine du texte | Écart retenu | Seuil |
|---|---|---|
| couche OCR existante | 0,000 à 0,383 (fichier 4, p. 3) | `mots_inconnus_max_couche_existante` = 0,35 (cahier, dans l'écart) |
| `Windows.Media.Ocr` | la page illisible ne garde qu'un mot évaluable (détectée par la densité et l'image) | `mots_inconnus_max_windows` = 0,35 (cahier) |
| Apple Vision, sans correction linguistique | 0,040 (fichier 2, p. 4, Intel) à 0,373 (fichier 5, p. 2, Apple Silicon ; 0,418 sur Intel) | `mots_inconnus_max_vision` = 0,21 (milieu) |

## Qualité de l'image (`qualite_image`)

**Règle revue en recette (27/11/2026).** Sur un lot réel de 700 pages reconnues, l'image seule rendait douteuses 494 pages dont le profil lexical était celui des pages bonnes (mots inconnus : médiane 0,015 contre 0,011 ; neuvième décile 0,068 contre 0,056). Décision du commanditaire : l'image médiocre devient une information secondaire (front matter et rapport, sans avertissement) ; l'image seule ne rend la page douteuse qu'en cas de dégradation sévère ; sinon, il faut aussi un texte limite. Règle proposée par Claude Code et appliquée :

| Cas | Verdict | Seuils |
|---|---|---|
| résolution très faible | douteuse (`image_faible_qualite`) | `image_resolution_severe_dpi` = 120 (valeur de départ, à calibrer) |
| image médiocre et texte limite (au moins 40 mots évaluables) | douteuse (`image_faible_qualite`, cause « texte reconnu limite ») | `mots_inconnus_limite_windows` = 0,10 ; `mots_inconnus_limite_vision` = 0,055 |
| image médiocre seule | bonne ; `qualite_image: mediocre` | `image_resolution_min_dpi` = 200, `image_part_gris_max` = 0,50, `image_contraste_min` = 183, `image_bruit_max` = 3,75 |

Seuils limites : entre les pages saines et les pages moyennement dégradées du jeu de test, qui ont toutes une image médiocre (part de gris). Sous `Windows.Media.Ocr`, les pages du fichier 21 ont 0,127, 0,136 et 0,500 de mots inconnus, et les pages saines du jeu 0,000 (scans synthétiques sans faute) : 0,10, placé au-dessus du neuvième décile des pages bonnes du lot de recette (0,056) plutôt qu'au milieu de l'écart synthétique (0,064). Sous Vision, l'écart est de 0,050 (page saine la plus défavorable) à 0,061 (page dégradée la plus favorable) : 0,055, valeur refusée comme seuil général le 27/11/2026, retenue ici parce qu'elle ne joue que sur une image déjà médiocre. Résolution : 200 dpi et plus sont bons (réglages courants des copieurs), 150 dpi est médiocre, sous 120 dpi la page est douteuse. Sur le jeu de test, la règle donne zéro erreur de verdict avec le moteur factice et `Windows.Media.Ocr` (vérification d'Apple Vision : intégration continue).

Ces valeurs sont des valeurs de départ : elles sont à recalibrer sur la vérité terrain du commanditaire (une vingtaine de pages jugées à l'œil) avec `tests/recalibrage.py` (guide administrateur, section 9).

Mesures sur l'image transmise au moteur (rendu à `ocr_dpi`, niveaux de gris), avant l'OCR :

| Page | Résolution effective | Part de gris du trait | Contraste | Bruit du fond |
|---|---|---|---|---|
| pages saines (23 pages, fichiers 2, 3, 5, 6b, 10, 15, 18, 19) | 300 dpi | 0,204 à 0,344 | 255 | 1,12 à 2,79 |
| fichier 5, p. 2 (illisible) | 300 dpi | 0,986 | 111 | 12,32 |
| fichier 21, p. 1 (scan 150 dpi, léger flou) | 150 dpi | 0,990 | 129 | 6,99 |
| fichier 21, p. 2 (tampon sur le texte) | 300 dpi | 0,654 | 254 | 4,72 |
| fichier 21, p. 3 (photocopie de photocopie) | 200 dpi | 0,828 | 203 | 4,94 |

| Mesure | Page saine la plus défavorable | Page dégradée la plus proche au-delà | Seuil | Pages dégradées distinguées |
|---|---|---|---|---|
| résolution effective | 300 dpi | 200 dpi (fichier 21, p. 3) | `image_resolution_min_dpi` = 200 (250 jusqu'à la recette) | fichier 21, p. 1 |
| part de gris du trait | 0,344 (fichier 10, PNG) | 0,654 (fichier 21, p. 2) | `image_part_gris_max` = 0,50 | les quatre |
| contraste | 255 | 111 (fichier 5, p. 2 : dégradation grossière seulement) | `image_contraste_min` = 183 | fichier 5, p. 2, fichier 21, p. 1 |
| bruit du fond | 2,79 (fichier 2, p. 2) | 4,72 (fichier 21, p. 2) | `image_bruit_max` = 3,75 | les quatre |

Écarts à la règle et points d'attention :
- contraste : les pages saines synthétiques ont toutes un contraste maximal (papier blanc pur, encre noire pure) ; le milieu de l'écart brut (254,5) signalerait presque tout scan réel. Le seuil est pris entre les pages saines et la page illisible (dégradation grossière), les pages moyennement dégradées étant déjà distinguées par la part de gris et le bruit ;
- résolution : le seuil de 250 dpi signalait les scans à 200 dpi, réglage par défaut de nombreux copieurs ; ramené à 200 dpi (image médiocre au-dessous) et complété par le seuil sévère de 120 dpi (recette du 27/11/2026) ;
- bruit et part de gris : mesurés sur des scans synthétiques (bruit gaussien, JPEG) ; à recalibrer sur des scans réels ;
- netteté par la variance du laplacien (demandée) : mesurée, non retenue, car elle ne sépare pas les pages du jeu. Sans débruitage, la page illisible a la plus forte variance (le bruit la gonfle) ; rapportée à la quantité d'encre et après filtre médian, les pages saines vont de 31 à 42 et les pages dégradées de 13 à 278 (la page 1 du fichier 21, floue, est à 35, dans la plage des pages saines). La part de gris du trait la remplace pour la netteté.

## Confiance (Apple Vision)

Seuil `confiance_moyenne_min` = 0,70 (cahier), conservé : dans l'écart entre la page illisible du fichier 5 (0,51 et 0,52) et les pages saines (0,79 au moins). Sa marge côté pages saines est étroite (0,787 sur la page 2 du fichier 18, Mac Intel) : prioritaire en recette (TM-08). Les pages moyennement dégradées du fichier 21 (0,70 à 0,79) ne sont pas séparées par la confiance ; elles le sont par la règle de l'image (image médiocre et texte limite).

## Autres indicateurs

| Indicateur | Seuil | Commentaire |
|---|---|---|
| caractères aberrants | 0,03 (cahier) | 0,113 sur la page 2 du fichier 4, construite pour l'éprouver |
| mots fragmentés | 0,25 (cahier) | pages saines au plus à 0,059 ; pages 2 et 3 du fichier 4 à 0,496 et 0,320 |
| densité minimale | 0,11 | la valeur du cahier (0,2) signalerait à tort un tableau sain clairsemé (fichier 6b, p. 1, à 0,164) ; page illisible lue par Windows à 0,053 |
| mélanges chiffres et lettres | 0,10 (cahier) | aucune page du jeu n'est construite pour l'éprouver |

Résultat avec ces seuils : aucune erreur de verdict sur les 33 pages avec le moteur factice et avec `Windows.Media.Ocr` ; Apple Vision : voir la rubrique de fin de fichier.

## Moteur factice (vérité terrain du manifeste, confiances imposées)

| fichier | page | origine | mots | évaluables | inconnus | aberrants | fragmentés | mélanges | densité | confiance | verdict | attendu |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| images/10_exif6.jpg | 1 | factice | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.167 | 0.95 | bonne | bonne |
| images/10_extension_majuscules.PNG | 1 | factice | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.175 | 0.95 | bonne | bonne |
| images/10_page.png | 1 | factice | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.165 | 0.95 | bonne | bonne |
| images/10_trois_trames.tiff | 1 | factice | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.170 | 0.95 | bonne | bonne |
| images/10_trois_trames.tiff | 2 | factice | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.170 | 0.95 | bonne | bonne |
| images/10_trois_trames.tiff | 3 | factice | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.170 | 0.95 | bonne | bonne |
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

33 page(s) mesurée(s) ; erreurs de verdict par rapport à la vérité terrain : 0

Qualité de l'image (mesures avant OCR, indépendantes du moteur) :

| images/10_exif6.jpg | 1 | 300 dpi | gris 0.2376 | contraste 255 | bruit 1.28 | bonne |
| images/10_extension_majuscules.PNG | 1 | 300 dpi | gris 0.3427 | contraste 255 | bruit 1.615 | bonne |
| images/10_page.png | 1 | 300 dpi | gris 0.3437 | contraste 255 | bruit 1.608 | bonne |
| images/10_trois_trames.tiff | 1 | 300 dpi | gris 0.2401 | contraste 255 | bruit 1.119 | bonne |
| images/10_trois_trames.tiff | 2 | 300 dpi | gris 0.2394 | contraste 255 | bruit 1.119 | bonne |
| images/10_trois_trames.tiff | 3 | 300 dpi | gris 0.2395 | contraste 255 | bruit 1.12 | bonne |
| lot/Lot 1/Candidat A/Annexes/Attestation URSSAF.pdf | 1 | 300 dpi | gris 0.234 | contraste 255 | bruit 1.987 | bonne |
| lot/Lot 1/Candidat B/DC2.pdf | 1 | 300 dpi | gris 0.2355 | contraste 255 | bruit 1.977 | bonne |
| pdf/02_scanne.pdf | 1 | 300 dpi | gris 0.2685 | contraste 255 | bruit 2.781 | bonne |
| pdf/02_scanne.pdf | 2 | 300 dpi | gris 0.2703 | contraste 255 | bruit 2.786 | bonne |
| pdf/02_scanne.pdf | 3 | 300 dpi | gris 0.2693 | contraste 255 | bruit 2.783 | bonne |
| pdf/02_scanne.pdf | 4 | 300 dpi | gris 0.2675 | contraste 255 | bruit 2.78 | bonne |
| pdf/03_mixte.pdf | 4 | 300 dpi | gris 0.2355 | contraste 255 | bruit 1.978 | bonne |
| pdf/03_mixte.pdf | 5 | 300 dpi | gris 0.2355 | contraste 255 | bruit 1.98 | bonne |
| pdf/05_illisible.pdf | 1 | 300 dpi | gris 0.2355 | contraste 255 | bruit 1.978 | bonne |
| pdf/05_illisible.pdf | 2 | 300 dpi | gris 0.9855 | contraste 111 | bruit 12.317 | douteuse |
| pdf/06b_tableaux_scannes.pdf | 1 | 300 dpi | gris 0.2038 | contraste 255 | bruit 1.205 | bonne |
| pdf/06b_tableaux_scannes.pdf | 2 | 300 dpi | gris 0.212 | contraste 255 | bruit 1.272 | bonne |
| pdf/06b_tableaux_scannes.pdf | 3 | 300 dpi | gris 0.213 | contraste 255 | bruit 1.308 | bonne |
| pdf/06b_tableaux_scannes.pdf | 4 | 300 dpi | gris 0.2486 | contraste 255 | bruit 1.294 | bonne |
| pdf/18_ligatures.pdf | 1 | 300 dpi | gris 0.2696 | contraste 255 | bruit 2.148 | bonne |
| pdf/18_ligatures.pdf | 2 | 300 dpi | gris 0.2697 | contraste 255 | bruit 2.149 | bonne |
| pdf/19_mention_plateforme.pdf | 1 | 300 dpi | gris 0.2387 | contraste 255 | bruit 1.988 | bonne |
| pdf/19_mention_plateforme.pdf | 2 | 300 dpi | gris 0.238 | contraste 255 | bruit 1.991 | bonne |
| pdf/21_moyennement_degrade.pdf | 1 | 150 dpi | gris 0.9902 | contraste 129 | bruit 6.987 | douteuse |
| pdf/21_moyennement_degrade.pdf | 2 | 300 dpi | gris 0.6535 | contraste 254 | bruit 4.721 | douteuse |
| pdf/21_moyennement_degrade.pdf | 3 | 200 dpi | gris 0.8275 | contraste 203 | bruit 4.936 | douteuse |

Écart par mesure de qualite_image :

| mesure | page saine la plus défavorable | page dégradée la plus proche au-delà | milieu | pages dégradées distinguées |
|---|---|---|---|---|
| resolution_dpi | 300 (images/10_exif6.jpg p. 1) | 200 (pdf/21_moyennement_degrade.pdf p. 3) | 250.0 | pdf/21_moyennement_degrade.pdf p. 1, pdf/21_moyennement_degrade.pdf p. 3 |
| part_gris | 0.3437 (images/10_page.png p. 1) | 0.6535 (pdf/21_moyennement_degrade.pdf p. 2) | 0.499 | pdf/05_illisible.pdf p. 2, pdf/21_moyennement_degrade.pdf p. 1, pdf/21_moyennement_degrade.pdf p. 2, pdf/21_moyennement_degrade.pdf p. 3 |
| contraste | 255 (images/10_exif6.jpg p. 1) | 254 (pdf/21_moyennement_degrade.pdf p. 2) | 254.5 | pdf/05_illisible.pdf p. 2, pdf/21_moyennement_degrade.pdf p. 1, pdf/21_moyennement_degrade.pdf p. 2, pdf/21_moyennement_degrade.pdf p. 3 |
| bruit | 2.786 (pdf/02_scanne.pdf p. 2) | 4.721 (pdf/21_moyennement_degrade.pdf p. 2) | 3.753 | pdf/05_illisible.pdf p. 2, pdf/21_moyennement_degrade.pdf p. 1, pdf/21_moyennement_degrade.pdf p. 2, pdf/21_moyennement_degrade.pdf p. 3 |

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
| taux_mots_inconnus | 0.000 (images/10_exif6.jpg p. 1) | 0.446 (pdf/21_moyennement_degrade.pdf p. 2) | 0.35 | oui | 0.223 |
| taux_caracteres_aberrants | 0.000 (images/10_exif6.jpg p. 1) | 0.000 (pdf/05_illisible.pdf p. 2) | 0.03 | pas d'écart |  |
| taux_mots_fragmentes | 0.059 (pdf/06b_tableaux_scannes.pdf p. 1) | 0.000 (pdf/21_moyennement_degrade.pdf p. 1) | 0.25 | pas d'écart |  |
| taux_melange_chiffres_lettres | 0.000 (images/10_exif6.jpg p. 1) | 0.087 (pdf/05_illisible.pdf p. 2) | 0.1 | non | 0.043 |
| densite | 0.164 (pdf/06b_tableaux_scannes.pdf p. 1) | 1.182 (pdf/05_illisible.pdf p. 2) | 0.2 | pas d'écart |  |

## Moteur réel du poste : Windows.Media.Ocr, fr-FR

| fichier | page | origine | mots | évaluables | inconnus | aberrants | fragmentés | mélanges | densité | confiance | verdict | attendu |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| images/10_exif6.jpg | 1 | windows-media-ocr | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.167 |  | bonne | bonne |
| images/10_extension_majuscules.PNG | 1 | windows-media-ocr | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.175 |  | bonne | bonne |
| images/10_page.png | 1 | windows-media-ocr | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.165 |  | bonne | bonne |
| images/10_trois_trames.tiff | 1 | windows-media-ocr | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.170 |  | bonne | bonne |
| images/10_trois_trames.tiff | 2 | windows-media-ocr | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.170 |  | bonne | bonne |
| images/10_trois_trames.tiff | 3 | windows-media-ocr | 143 | 75 | 0.000 | 0.000 | 0.000 | 0.000 | 1.170 |  | bonne | bonne |
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

33 page(s) mesurée(s) ; erreurs de verdict par rapport à la vérité terrain : 0

Qualité de l'image (mesures avant OCR, indépendantes du moteur) :

| images/10_exif6.jpg | 1 | 300 dpi | gris 0.2376 | contraste 255 | bruit 1.28 | bonne |
| images/10_extension_majuscules.PNG | 1 | 300 dpi | gris 0.3427 | contraste 255 | bruit 1.615 | bonne |
| images/10_page.png | 1 | 300 dpi | gris 0.3437 | contraste 255 | bruit 1.608 | bonne |
| images/10_trois_trames.tiff | 1 | 300 dpi | gris 0.2401 | contraste 255 | bruit 1.119 | bonne |
| images/10_trois_trames.tiff | 2 | 300 dpi | gris 0.2394 | contraste 255 | bruit 1.119 | bonne |
| images/10_trois_trames.tiff | 3 | 300 dpi | gris 0.2395 | contraste 255 | bruit 1.12 | bonne |
| lot/Lot 1/Candidat A/Annexes/Attestation URSSAF.pdf | 1 | 300 dpi | gris 0.234 | contraste 255 | bruit 1.987 | bonne |
| lot/Lot 1/Candidat B/DC2.pdf | 1 | 300 dpi | gris 0.2355 | contraste 255 | bruit 1.977 | bonne |
| pdf/02_scanne.pdf | 1 | 300 dpi | gris 0.2685 | contraste 255 | bruit 2.781 | bonne |
| pdf/02_scanne.pdf | 2 | 300 dpi | gris 0.2703 | contraste 255 | bruit 2.786 | bonne |
| pdf/02_scanne.pdf | 3 | 300 dpi | gris 0.2693 | contraste 255 | bruit 2.783 | bonne |
| pdf/02_scanne.pdf | 4 | 300 dpi | gris 0.2675 | contraste 255 | bruit 2.78 | bonne |
| pdf/03_mixte.pdf | 4 | 300 dpi | gris 0.2355 | contraste 255 | bruit 1.978 | bonne |
| pdf/03_mixte.pdf | 5 | 300 dpi | gris 0.2355 | contraste 255 | bruit 1.98 | bonne |
| pdf/05_illisible.pdf | 1 | 300 dpi | gris 0.2355 | contraste 255 | bruit 1.978 | bonne |
| pdf/05_illisible.pdf | 2 | 300 dpi | gris 0.9855 | contraste 111 | bruit 12.317 | douteuse |
| pdf/06b_tableaux_scannes.pdf | 1 | 300 dpi | gris 0.2038 | contraste 255 | bruit 1.205 | bonne |
| pdf/06b_tableaux_scannes.pdf | 2 | 300 dpi | gris 0.212 | contraste 255 | bruit 1.272 | bonne |
| pdf/06b_tableaux_scannes.pdf | 3 | 300 dpi | gris 0.213 | contraste 255 | bruit 1.308 | bonne |
| pdf/06b_tableaux_scannes.pdf | 4 | 300 dpi | gris 0.2486 | contraste 255 | bruit 1.294 | bonne |
| pdf/18_ligatures.pdf | 1 | 300 dpi | gris 0.2696 | contraste 255 | bruit 2.148 | bonne |
| pdf/18_ligatures.pdf | 2 | 300 dpi | gris 0.2697 | contraste 255 | bruit 2.149 | bonne |
| pdf/19_mention_plateforme.pdf | 1 | 300 dpi | gris 0.2387 | contraste 255 | bruit 1.988 | bonne |
| pdf/19_mention_plateforme.pdf | 2 | 300 dpi | gris 0.238 | contraste 255 | bruit 1.991 | bonne |
| pdf/21_moyennement_degrade.pdf | 1 | 150 dpi | gris 0.9902 | contraste 129 | bruit 6.987 | douteuse |
| pdf/21_moyennement_degrade.pdf | 2 | 300 dpi | gris 0.6535 | contraste 254 | bruit 4.721 | douteuse |
| pdf/21_moyennement_degrade.pdf | 3 | 200 dpi | gris 0.8275 | contraste 203 | bruit 4.936 | douteuse |

Écart par mesure de qualite_image :

| mesure | page saine la plus défavorable | page dégradée la plus proche au-delà | milieu | pages dégradées distinguées |
|---|---|---|---|---|
| resolution_dpi | 300 (images/10_exif6.jpg p. 1) | 200 (pdf/21_moyennement_degrade.pdf p. 3) | 250.0 | pdf/21_moyennement_degrade.pdf p. 1, pdf/21_moyennement_degrade.pdf p. 3 |
| part_gris | 0.3437 (images/10_page.png p. 1) | 0.6535 (pdf/21_moyennement_degrade.pdf p. 2) | 0.499 | pdf/05_illisible.pdf p. 2, pdf/21_moyennement_degrade.pdf p. 1, pdf/21_moyennement_degrade.pdf p. 2, pdf/21_moyennement_degrade.pdf p. 3 |
| contraste | 255 (images/10_exif6.jpg p. 1) | 254 (pdf/21_moyennement_degrade.pdf p. 2) | 254.5 | pdf/05_illisible.pdf p. 2, pdf/21_moyennement_degrade.pdf p. 1, pdf/21_moyennement_degrade.pdf p. 2, pdf/21_moyennement_degrade.pdf p. 3 |
| bruit | 2.786 (pdf/02_scanne.pdf p. 2) | 4.721 (pdf/21_moyennement_degrade.pdf p. 2) | 3.753 | pdf/05_illisible.pdf p. 2, pdf/21_moyennement_degrade.pdf p. 1, pdf/21_moyennement_degrade.pdf p. 2, pdf/21_moyennement_degrade.pdf p. 3 |

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
| taux_mots_inconnus | 0.000 (images/10_exif6.jpg p. 1) | 0.127 (pdf/21_moyennement_degrade.pdf p. 1) | 0.35 | non | 0.064 |
| taux_caracteres_aberrants | 0.000 (images/10_exif6.jpg p. 1) | 0.000 (pdf/05_illisible.pdf p. 2) | 0.03 | pas d'écart |  |
| taux_mots_fragmentes | 0.059 (pdf/06b_tableaux_scannes.pdf p. 1) | 0.009 (pdf/21_moyennement_degrade.pdf p. 3) | 0.25 | pas d'écart |  |
| taux_melange_chiffres_lettres | 0.019 (pdf/06b_tableaux_scannes.pdf p. 3) | 0.000 (pdf/05_illisible.pdf p. 2) | 0.1 | pas d'écart |  |
| densite | 0.164 (pdf/06b_tableaux_scannes.pdf p. 1) | 0.925 (pdf/21_moyennement_degrade.pdf p. 3) | 0.2 | pas d'écart |  |
