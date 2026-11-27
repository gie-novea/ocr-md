# Guide administrateur d'ocr-md

Destiné au référent technique qui installe l'outil, le règle et traite les incidents. Le guide utilisateur (`guide-utilisateur-windows.md`, `guide-utilisateur-macos.md`) couvre l'usage courant.

## 1. Ce que fait l'outil

ocr-md rend lisibles les pièces d'un pli de candidature (PDF, images, .docx, .xlsx, .xlsm, .pptx, et le contenu des archives .zip) : il produit, dans un dossier `_OCR` placé à côté du dossier traité, un PDF consultable (texte sélectionnable et cherchable) et un Markdown destiné à une IA, avec un rapport (`ocr_rapport.csv`), un fichier d'avertissements (`_AVERTISSEMENTS.md`) et un journal (`ocr_journal.log`). La reconnaissance de caractères (OCR) utilise le moteur du système : `Windows.Media.Ocr` sous Windows, Apple Vision sous macOS. Aucun document ne quitte le poste : l'outil ne se connecte jamais au réseau pendant un traitement (EX-03).

## 2. Prérequis

| Élément | Exigence | État |
|---|---|---|
| Windows | Windows 10 ou 11, 64 bits, module OCR français (`Language.OCR~~~fr-FR~0.0.1.0`) | présence par défaut du module non établie (PV-03) : `ocr-md verifier` le contrôle |
| macOS | 10.15 ou plus ; vérifié sur macOS 15.7.9 (Intel) et 26.7.2 (Apple Silicon) | versions du parc à relever en recette (PV-08 d) |
| Processeur Mac | Apple Silicon et Intel | vérifiés en intégration continue |
| Droits | compte standard : tout s'installe dans le profil, sans élévation (EX-02) | à confirmer en recette (TM-01, PV-01) |
| Réseau | à l'installation et à la mise à jour seulement (section 6) | |
| Espace disque | 340 à 410 Mo dans le profil (section 13) | |

## 3. Installation

La source de distribution est l'archive d'une étiquette publiée sur GitHub, installée par `uv` sans Git. Pendant la recette, c'est la version candidate `v1.0.0-rc1` (`https://github.com/gie-novea/ocr-md/archive/refs/tags/v1.0.0-rc1.zip`, publication marquée « pre-release ») ; la version finale `v1.0.0` sera publiée après la recette et le recalibrage des seuils (section 4). Les scripts sont idempotents : les relancer répare une installation sans créer de doublon.

**Windows.** Télécharger l'archive ci-dessus, l'extraire, puis double-cliquer sur `installation\installer-windows.cmd`. Si Windows affiche un avertissement de sécurité sur un fichier téléchargé (SmartScreen, « Le fichier provient d'un autre ordinateur »), choisir « Exécuter quand même », ou cocher « Débloquer » dans les propriétés de l'archive avant de l'extraire.

**macOS (méthode principale).** Ouvrir le Terminal (Applications, Utilitaires) et coller la ligne suivante, qui télécharge l'archive par `curl` (donc sans mise en quarantaine par Gatekeeper) et lance le script d'installation :

```
cd /tmp && rm -rf ocr-md-* && curl -LsSf https://github.com/gie-novea/ocr-md/archive/refs/tags/v1.0.0-rc1.zip -o ocr-md.zip && unzip -oq ocr-md.zip && bash ocr-md-*/installation/installer-macos.command
```

**macOS (secours).** Extraire l'archive téléchargée par le navigateur, puis double-cliquer sur `installation/installer-macos.command`. Si macOS refuse de l'ouvrir (« développeur non identifié »), faire clic droit sur le fichier, puis « Ouvrir », puis confirmer « Ouvrir ».

Étapes du script (affichées, avec un message final de succès ou d'échec indiquant l'étape) : (1) installation de `uv` dans le profil s'il manque ; (2) installation de Python 3.12 géré par `uv`, vérifiée par `uv python find` (`uv` peut afficher une erreur alors que l'installation a réussi) ; (3) installation de l'outil par `uv tool install` ; (4) création des trois raccourcis ; (5) diagnostic `ocr-md verifier`.

**Autre source.** Pour installer depuis un autre emplacement (copie locale de l'archive, dossier, paquet « wheel », autre étiquette) : paramètre `-Source` du script Windows (`installer-windows.cmd -Source CHEMIN`), premier argument du script macOS, ou variable d'environnement `OCR_MD_SOURCE`.

## 4. Mise à jour

`installation\mettre-a-jour-windows.cmd` ou `installation/mettre-a-jour-macos.command` : réinstallation de la dernière version depuis la source de distribution (`uv tool install --force --reinstall`), recréation des raccourcis, diagnostic, affichage de l'ancienne et de la nouvelle version. Le fichier de configuration de l'utilisateur est conservé. L'outil ne se met jamais à jour seul et ne vérifie pas l'existence de nouvelles versions (EX-72).

L'étiquette installée est un paramètre unique, en tête de `installation/commun-windows.ps1` (`$Etiquette`) et de `installation/commun-macos.sh` (`ETIQUETTE`). Le script de mise à jour installe l'étiquette inscrite dans le script lui-même : il faut donc lancer celui de l'archive de la nouvelle version.

**Passer d'une version candidate à la version finale** (mainteneur, puis référent) :

1. dans le dépôt : version `1.0.0` dans `pyproject.toml` et `src/ocr_md/__init__.py` (puis `uv lock`), seuils recalibrés en recette dans `src/ocr_md/config.py` et `docs/calibrage.md`, rubrique `[1.0.0]` du CHANGELOG, étiquette `v1.0.0` dans les deux scripts communs, la ligne d'installation des guides et le README ; tests et intégration continue verts ;
2. créer l'étiquette `v1.0.0` sur ce commit, l'envoyer, et publier la version sur GitHub sans la marque « pre-release » ; l'intégration continue vérifie alors l'installation depuis l'étiquette (workflow « installation depuis l'étiquette ») ;
3. sur chaque poste de recette : télécharger l'archive `v1.0.0`, l'extraire et lancer `installation\mettre-a-jour-windows.cmd` ou `installation/mettre-a-jour-macos.command` (ou, sous macOS, la nouvelle ligne d'installation du guide, qui réinstalle sans doublon) ; contrôler que `ocr-md --version` affiche `1.0.0` et que la configuration est conservée ;
4. diffuser aux membres les guides désignant `v1.0.0`.

Une nouvelle version candidate (`v1.0.0-rc2`, version `1.0.0rc2`) suit les mêmes étapes, publiée en « pre-release ».

## 5. Désinstallation

`installation\desinstaller-windows.cmd` ou `installation/desinstaller-macos.command` : retrait des trois raccourcis, désinstallation de l'outil (`uv tool uninstall`), suppression du dossier temporaire ; suppression du fichier de configuration après confirmation ; désinstallation de `uv` et de ses Pythons proposée, jamais imposée (d'autres outils peuvent en dépendre). Les dossiers `_OCR` produits ne sont jamais touchés (EX-73).

## 6. Connexions réseau de l'installation et de la mise à jour

À autoriser sur le pare-feu ou le serveur mandataire, en HTTPS (port 443), pendant l'installation et la mise à jour seulement :

| Adresse | Usage |
|---|---|
| `astral.sh` | script d'installation de `uv` |
| `github.com` | archive de l'outil ; binaires de `uv` et de Python (redirections) |
| `codeload.github.com` | téléchargement effectif des archives de dépôt GitHub |
| `objects.githubusercontent.com`, `release-assets.githubusercontent.com` | téléchargement effectif des binaires publiés sur GitHub (`uv`, Python) |
| `pypi.org`, `files.pythonhosted.org` | paquets Python dépendants |

Liste établie d'après le fonctionnement de `uv` et de GitHub ; à confirmer en recette derrière le pare-feu de la SODEB (TM-01). Le mode qualité (v1.1) ajoutera Hugging Face pour le téléchargement des modèles.

## 7. Emplacements dans le profil

| Élément | Windows | macOS |
|---|---|---|
| `uv` | `%USERPROFILE%\.local\bin\uv.exe` | `~/.local/bin/uv` |
| Commandes `ocr-md`, `ocr-mdw` | `%USERPROFILE%\.local\bin` | `~/.local/bin` |
| Environnement de l'outil | `uv tool dir` (en général `%APPDATA%\uv\tools\ocr-md`) | `uv tool dir` (en général `~/.local/share/uv/tools/ocr-md`) |
| Python 3.12 | `uv python dir` | `uv python dir` |
| Configuration | `%APPDATA%\ocr-md\config.toml` | `~/Library/Application Support/ocr-md/config.toml` |
| Dossier temporaire | `%LOCALAPPDATA%\ocr-md\temp` | `~/Library/Caches/ocr-md/temp` |
| Raccourcis | `%APPDATA%\Microsoft\Windows\SendTo\OCR - ….lnk` | `~/Library/Services/OCR - ….workflow` |
| Sorties | dossier `_OCR` à côté du dossier ou du fichier traité | idem |

`ocr-md verifier` affiche les emplacements de la configuration et du dossier temporaire et contrôle qu'ils sont accessibles en écriture.

## 8. Paramètres et seuils

Tous les paramètres ont une valeur par défaut ; ils se modifient dans le fichier `config.toml` du profil (emplacement affiché par `ocr-md verifier`), ou dans un fichier passé par `--config FICHIER`. Exemple :

```
ocr_dpi = 300
mots_inconnus_max_windows = 0.35
lexique_complementaire = ["DCE", "MAPA"]
```

Un paramètre inconnu ou une valeur hors bornes produit une erreur d'usage explicite (code 2). Les valeurs effectives sont écrites au journal de chaque lot.

<!-- debut : tableau des paramètres, généré -->

| Paramètre | Défaut | Bornes ou valeurs | Description |
|---|---|---|---|
| `texte_min_caracteres` | 30 | 0 à 100000 | Caractères extractibles hors espaces au-dessous desquels une page n'a pas de texte suffisant |
| `image_couverture_min` | 0,8 | 0 à 1 | Part de la page couverte par une image au-delà de laquelle le texte est superposé à une image |
| `image_presence_min` | 0,3 | 0 à 1 | Part de la page couverte par des images pour qu'une page sans texte soit classée « image » |
| `densite_texte_ajoute_max` | 0,5 | 0 à 1000 | Caractères par cm² au-dessous desquels le texte d'une page scannée est une mention ajoutée (horodatage) |
| `ocr_dpi` | 300 | 72 à 1200 | Résolution de rendu des pages pour l'OCR |
| `langue_ocr` | fr-FR |  | Langue principale de reconnaissance |
| `langue_ocr_secondaire` | en-US |  | Langue secondaire, si le moteur en accepte plusieurs |
| `confiance_moyenne_min` | 0,7 | 0 à 1 | Confiance moyenne pondérée au-dessous de laquelle une page est douteuse |
| `confiance_basse` | 0,5 | 0 à 1 | Confiance au-dessous de laquelle un texte est jugé peu sûr |
| `part_confiance_basse_max` | 0,2 | 0 à 1 | Part du texte peu sûr au-delà de laquelle une page est douteuse |
| `page_blanche_ecart_type_max` | 8 | 0 à 255 | Écart type des niveaux de gris au-dessous duquel une page est uniformément blanche (proposition) |
| `mots_inconnus_max_couche_existante` | 0,35 | 0 à 1 | Part de mots absents du lexique au-delà de laquelle une page à couche OCR existante est douteuse (valeur du cahier ; calibrage définitif en recette, TM-08) |
| `mots_inconnus_max_windows` | 0,35 | 0 à 1 | Part de mots absents du lexique au-delà de laquelle une page reconnue par Windows.Media.Ocr est douteuse (valeur du cahier, dégradation grossière ; calibrage définitif en recette, TM-08) |
| `mots_inconnus_max_vision` | 0,21 | 0 à 1 | Part de mots absents du lexique au-delà de laquelle une page reconnue par Apple Vision est douteuse (milieu de l'écart mesuré sur la page illisible, sans correction linguistique ; calibrage définitif en recette, TM-08) |
| `image_resolution_severe_dpi` | 120 | 0 à 2400 | Résolution effective (dpi) de l'image d'une page au-dessous de laquelle la page est douteuse par l'image seule (dégradation sévère ; recette du 27/11/2026, à recalibrer) |
| `mots_inconnus_limite_windows` | 0,1 | 0 à 1 | Part de mots inconnus au-delà de laquelle le texte d'une page reconnue par Windows.Media.Ocr est limite : une image médiocre rend alors la page douteuse (entre les pages saines et les pages moyennement dégradées du jeu de test ; à recalibrer) |
| `mots_inconnus_limite_vision` | 0,055 | 0 à 1 | Part de mots inconnus au-delà de laquelle le texte d'une page reconnue par Apple Vision est limite : une image médiocre rend alors la page douteuse (milieu de l'écart du jeu de test ; à recalibrer) |
| `image_resolution_min_dpi` | 200 | 0 à 2400 | Résolution effective (dpi) de l'image d'une page au-dessous de laquelle l'image est jugée médiocre (200 et 300 dpi, réglages courants des copieurs, sont bonnes ; à recalibrer) |
| `image_part_gris_max` | 0,5 | 0 à 1 | Part du trait en gris intermédiaires au-delà de laquelle l'image est jugée floue ou grisée |
| `image_contraste_min` | 183 | 0 à 255 | Écart entre le papier et l'encre (niveaux de gris) au-dessous duquel le contraste est jugé faible (dégradation grossière seulement : milieu entre les pages saines et la page illisible) |
| `image_bruit_max` | 3,75 | 0 à 255 | Écart type des niveaux de gris du fond au-delà duquel l'image est jugée bruitée |
| `mots_evaluables_min` | 40 | 0 à 100000 | Nombre minimal de mots évaluables pour appliquer l'indicateur des mots inconnus |
| `taux_caracteres_aberrants_max` | 0,03 | 0 à 1 | Part de caractères aberrants au-delà de laquelle une page est douteuse (valeur du cahier ; calibrage définitif en recette, TM-08) |
| `taux_mots_fragmentes_max` | 0,25 | 0 à 1 | Part de mots d'une seule lettre au-delà de laquelle une page est douteuse (valeur du cahier ; calibrage définitif en recette, TM-08) |
| `taux_melange_chiffres_lettres_max` | 0,1 | 0 à 1 | Part de mots mêlant chiffres et lettres au-delà de laquelle une page est douteuse |
| `densite_min` | 0,11 | 0 à 1000 | Densité (caractères par cm²) au-dessous de laquelle une page non blanche est douteuse (milieu de l'écart du jeu de test, la valeur du cahier, 0,2, signalant à tort un tableau clairsemé ; calibrage définitif en recette, TM-08) |
| `densite_max` | 60 | 0 à 10000 | Densité (caractères par cm²) au-delà de laquelle une page est douteuse |
| `lexique_complementaire` | liste vide |  | Mots ajoutés au lexique (sigles, vocabulaire métier) |
| `xlsx_lignes_max` | 2000 | 1 à 1048576 | Nombre de lignes par feuille au-delà duquel la feuille est tronquée |
| `archive_taille_max_mo` | 2048 | 1 à 1048576 | Taille décompressée totale (Mo) au-delà de laquelle une archive .zip n'est pas extraite (signalée « non prise en charge ») |
| `delai_hydratation_s` | 120 | 1 à 3600 | Délai maximal de lecture d'un fichier non disponible localement (kDrive) |
| `tentatives_ecriture` | 3 | 0 à 20 | Nouvelles tentatives d'écriture d'une sortie verrouillée |
| `intervalle_tentatives_s` | 1 | 0 à 60 | Intervalle entre deux tentatives d'écriture (proposition) |
| `processus` | 1 | 1 à 1 | Nombre de fichiers traités en parallèle |

<!-- fin : tableau des paramètres -->

## 9. Qualité du texte et calibrage

Chaque page reconnue ou à couche OCR existante reçoit un verdict « bonne » ou « douteuse » (EX-35, EX-36) ; une page douteuse est signalée dans le front matter, le bloc d'avertissement, le repère de page, les métadonnées du PDF, `_AVERTISSEMENTS.md` et le rapport. Indicateurs :

- lexicaux (mots inconnus, caractères aberrants, mots fragmentés, mélanges chiffres et lettres, densité) : ils visent la dégradation grossière ; le seuil des mots inconnus dépend de l'origine du texte (couche existante, Windows, Vision) ;
- confiance (Apple Vision seulement) ;
- qualité de l'image (`qualite_image`, mesurée avant l'OCR, indépendante du moteur) : résolution, netteté du trait, contraste, bruit. Une image médiocre n'est qu'une information (champ `qualite_image` du front matter, colonne du rapport), sans avertissement. L'image ne rend la page douteuse (motif `image_faible_qualite`) que si la résolution est très faible (sous `image_resolution_severe_dpi`, 120 dpi), ou si l'image est médiocre et que le texte reconnu est lui aussi limite (mots inconnus au-dessus de `mots_inconnus_limite_windows` ou `mots_inconnus_limite_vision`) (décision du commanditaire du 27/11/2026, après une recette où l'image seule signalait à tort la majorité des pages scannées).

Les seuils par défaut sont les milieux des écarts mesurés sur le jeu de test synthétique ; tableau complet, méthode et points d'attention dans `docs/calibrage.md`. Ils sont à recalibrer en recette (TM-08) sur un dossier de documents réels, en local, avec :

```
uv run python tests/calibrage.py DOSSIER --moteur systeme
```

(depuis une copie du dépôt ; le script n'écrit que des noms de fichiers, des numéros de page et des nombres). Seuils à vérifier en priorité : confiance de Vision (0,70 ; marge étroite côté pages saines), seuils de l'image et seuils limites des mots inconnus.

**Recalibrage sur une vérité terrain** (TM-08). Après un traitement de documents réels, le référent juge à l'œil une vingtaine de pages, puis le script `tests/recalibrage.py` propose les seuils :

1. préparer le gabarit, prérempli d'un échantillon de pages tiré du journal (pages douteuses par l'image, images médiocres, pages bonnes, pages douteuses par le texte) :
   ```
   uv run python tests/recalibrage.py gabarit "CHEMIN\_OCR" --nombre 20 --sortie verite-terrain.csv
   ```
   Un gabarit vide est aussi fourni : `docs/gabarit-verite-terrain.csv` (colonnes `fichier`, `page`, `verdict`, séparateur point-virgule, ouvrable dans Excel) ;
2. ouvrir chaque page dans le PDF d'origine et remplir la colonne `verdict` : « correct », « erreurs ponctuelles » ou « mauvais » ;
3. calculer les seuils proposés :
   ```
   uv run python tests/recalibrage.py calibrer "CHEMIN\_OCR" verite-terrain.csv
   ```
   Le script affiche, page par page, les mesures, le jugement, le verdict actuel et le verdict proposé, le nombre d'erreurs avant et après, et un extrait de fichier de configuration TOML à reporter dans `config.toml` (section 8). « Erreurs ponctuelles » ne compte pas par défaut (`--ponctuelles bonne` ou `--ponctuelles douteuse` pour lui donner un sens) ; une page « mauvais » jugée bonne coûte deux fois une fausse alerte (`--poids-oubli`).

Le journal et le gabarit rempli contiennent des noms de fichiers réels : ils restent sur le poste, hors du dépôt. Le journal ne garde pas la part de texte peu sûr d'Apple Vision : le recalibrage de la confiance s'appuie sur la seule confiance moyenne.

## 10. Diagnostic

`ocr-md verifier` contrôle le système, le moteur OCR et ses langues, les dossiers du profil, les raccourcis et le correctif de PyMuPDF4LLM ; code 3 si un prérequis bloquant manque. Le premier lancement après une installation ou une mise à jour refait ces contrôles et montre les échecs dans la fenêtre de fin.

Incidents courants :

- **Module OCR français absent (Windows)** : les PDF natifs et les fichiers Office restent traités ; les PDF scannés et les images passent en erreur avec le message ci-dessous. Installation par l'administrateur : `Add-WindowsCapability -Online -Name "Language.OCR~~~fr-FR~0.0.1.0"` (PowerShell en administrateur), puis relancer.
- **AppLocker, stratégie d'exécution ou antivirus** : le script `.cmd` lance PowerShell avec `-ExecutionPolicy Bypass` pour ce seul processus ; si une stratégie de groupe l'interdit, ou si AppLocker bloque `uv.exe` ou les exécutables du profil (`%USERPROFILE%\.local\bin`, `%APPDATA%\uv`), il faut une exception pour ces dossiers (PV-01, à vérifier en recette sur un poste de la SODEB).
- **Autorisations macOS** : au premier traitement d'un dossier des Documents, du Bureau ou d'un disque externe, macOS peut demander d'autoriser l'accès ; l'accepter. Si l'accès a été refusé : Réglages Système, Confidentialité et sécurité, Fichiers et dossiers.
- **Fichiers kDrive « en ligne uniquement »** : l'outil tente le téléchargement pendant `delai_hydratation_s` secondes, puis met le fichier en erreur (message ci-dessous). Rendre le dossier disponible hors ligne dans le client kDrive, puis relancer.
- **Chemins longs (Windows)** : pris en charge sans réglage (forme étendue des chemins) ; si une erreur persiste, rapprocher le dossier de la racine du disque.
- **Sélection de très nombreux fichiers (Windows)** : au-delà de 90 % de la longueur maximale de la ligne de commande, l'outil le signale ; sélectionner plutôt le dossier.
- **Fenêtre absente** : sans affichage possible, l'outil montre une notification en fin de lot et écrit sa progression dans `_OCR/_EN_COURS.txt`.

## 11. Messages de l'outil

Chaque message du rapport, de la fenêtre de fin ou de la ligne de commande, avec sa cause et son remède. Les parties variables sont notées « … ».

**Fichiers en erreur ou signalés (colonne `message` du rapport)**

- « le contenu du fichier ne correspond pas à son extension ». Cause : fichier renommé, ou substitut d'un fichier non synchronisé. Remède : ouvrir le fichier dans son application, l'enregistrer au bon format.
- « fichier kDrive non disponible sur ce poste (en ligne uniquement) : dans l'Explorateur ou le Finder, clic droit sur le dossier, puis "Toujours conserver sur cet appareil" (ou équivalent), attendre la fin de la synchronisation, puis relancer ». Cause : fichier en ligne uniquement (Lite Sync). Remède : celui du message.
- « lecture impossible : … ». Cause : fichier verrouillé, supprimé ou inaccessible pendant le traitement. Remède : fermer l'application qui l'utilise, vérifier les droits, relancer.
- « fichier ou dossier introuvable ». Cause : chemin passé en argument inexistant (déplacé ou renommé entre la sélection et le traitement). Remède : relancer sur l'emplacement actuel.
- « format non pris en charge ». Cause : extension inconnue de l'outil. Remède : convertir la pièce en PDF si elle doit être lue.
- « ancien format Office : l'enregistrer au format .docx, .xlsx ou .pptx, ou en PDF, puis relancer ». Cause : .doc, .xls, .ppt, .pps. Remède : celui du message.
- « e-mail non pris en charge : enregistrer les pièces jointes et les traiter séparément ». Cause : .eml, .msg. Remède : celui du message.
- « PDF protégé par mot de passe ». Cause : PDF chiffré. Remède : obtenir une version sans mot de passe auprès de l'expéditeur.
- « PDF endommagé ». Cause : fichier tronqué ou corrompu, irrécupérable. Remède : demander une nouvelle copie.
- « PDF endommagé et réparé : … ». Cause : PDF réparé à l'ouverture, des pages perdues, ou PDF que MuPDF ne sait pas ouvrir et dont les pages ont été récupérées par pypdf (« … récupérées par pypdf ») ; le document est douteux. Remède : vérifier sur l'original ; demander une nouvelle copie si nécessaire.
- « archive chiffrée par mot de passe : l'extraire avec son mot de passe, puis traiter le dossier extrait ». Cause : archive .zip dont tous les fichiers sont chiffrés. Remède : celui du message.
- « fichier chiffré par mot de passe dans l'archive : l'extraire avec son mot de passe, puis le traiter ». Cause : un fichier chiffré dans une archive par ailleurs lisible. Remède : celui du message.
- « archive .zip endommagée ». Cause : archive tronquée, corrompue, ou qui annonce des tailles fausses (garde-fou contre les archives piégées). Remède : demander une nouvelle copie.
- « archive trop volumineuse une fois décompressée (… Mo, maximum … Mo) : l'extraire, puis traiter le dossier extrait ». Cause : contenu au-delà de `archive_taille_max_mo`. Remède : celui du message, ou relever le paramètre (section 8).
- « archive contenue dans une archive elle-même contenue dans une archive : l'extraire, puis traiter le dossier extrait ». Cause : troisième niveau d'archive (un seul niveau d'imbrication est extrait). Remède : celui du message.
- « archive compressée par une méthode non prise en charge : l'extraire, puis traiter le dossier extrait ». Cause : méthode de compression que Python ne lit pas (Deflate64, par exemple). Remède : celui du message.
- « la copie produite dans _OCR ne conserve pas la validité de la signature ; l'original signé reste la référence ». Cause : PDF signé électroniquement. Remède : aucun ; citer l'original pour toute question de signature.
- « image illisible ou endommagée ». Cause : image corrompue ou format interne non lu. Remède : réenregistrer l'image (PNG ou JPEG).
- « image de faible qualité : … ». Cause : page reconnue à partir d'une image de très basse résolution, ou d'une image médiocre (basse résolution, floue, peu contrastée ou bruitée) dont le texte reconnu est aussi limite (causes en clair, page par page) ; la page est douteuse. Remède : vérifier sur l'original ; demander un meilleur scan si la page compte.
- « fichier Office protégé par mot de passe : l'enregistrer sans mot de passe dans son application, puis relancer ». Remède : celui du message.
- « fichier Office endommagé ou illisible : l'ouvrir dans son application, l'enregistrer de nouveau, puis relancer ». Remède : celui du message ; le détail technique est au journal.
- « pas de PDF consultable pour ce format : utiliser Convertir en Markdown ». Cause : fichier Office avec l'action « Rendre lisible (PDF) ». Remède : utiliser « Convertir en Markdown ».
- « traitement annulé avant la fin de ce fichier ». Cause : bouton « Annuler ». Remède : relancer ; les fichiers déjà traités sont ignorés car à jour.
- « erreur inattendue (…) : détails dans ocr_journal.log ». Cause : défaut de l'outil sur ce fichier. Remède : transmettre le journal (il ne contient aucun texte de document) au référent ou au mainteneur.
- « sélection proche de la limite de longueur de la ligne de commande de Windows : des éléments sélectionnés ont pu ne pas être transmis ; vérifier qu'ils figurent tous au rapport, ou sélectionner plutôt le dossier qui les contient ». Remède : celui du message.
- « Le module de reconnaissance de texte en français de Windows n'est pas installé sur ce poste. Les PDF déjà lisibles et les fichiers Office restent convertibles ; les PDF scannés et les images ne peuvent pas être traités. Transmettre à votre service informatique la commande suivante, à exécuter en administrateur : Add-WindowsCapability -Online -Name "Language.OCR~~~fr-FR~0.0.1.0" ». Remède : celui du message (section 10).
- « la reconnaissance de texte en français n'est pas disponible sur cette version de macOS ». Cause : macOS trop ancien. Remède : mettre à jour macOS.
- « aucun moteur de reconnaissance de texte n'est disponible sur ce système ». Cause : système autre que Windows ou macOS. Remède : utiliser un poste Windows ou macOS.

**Fenêtre de fin et ligne de commande**

- « écriture impossible dans … ». Cause : dossier parent du dossier traité non accessible en écriture (lecteur en lecture seule, partage protégé). Remède : copier le dossier dans un emplacement accessible en écriture, puis relancer.
- « Erreur inattendue : … ». Cause : défaut de l'outil hors d'un fichier particulier. Remède : transmettre le journal.
- « mode qualité disponible à partir de la version 1.1 » ; « aucun fichier ni dossier à traiter (ocr-md --aide pour l'usage) » ; « liste de pages invalide : … » ; « plage de pages invalide : … » ; « --pages n'est admis que si un seul fichier PDF est passé en entrée » ; « la sous-commande verifier n'accepte pas d'argument (option --precharger-modeles : v1.1) » ; « usage : ocr-md raccourcis --creer | --supprimer ». Cause : erreur d'usage de la ligne de commande (code 2). Remède : corriger la commande (`ocr-md --aide`).
- « paramètre inconnu : … » ; « fichier de configuration introuvable : … » ; « fichier de configuration illisible (… » ; « fichier de configuration inaccessible (… ». Cause : fichier de configuration erroné. Remède : corriger le fichier (section 8) ou le supprimer pour revenir aux valeurs par défaut.

**Diagnostic et raccourcis (`ocr-md verifier`, scripts)**

- « aucun moteur OCR du système sur la plateforme … » ; « bibliothèque du moteur OCR absente : … » ; « création du moteur Windows.Media.Ocr impossible (… ». Cause : moteur indisponible ou installation incomplète. Remède : relancer le script d'installation ; sous Windows, vérifier le module OCR français.
- « lanceur … » ; « création du raccourci … ». Cause : installation incomplète ou dossier « Envoyer vers » inaccessible. Remède : relancer le script d'installation.
- « raccourcis disponibles sous Windows et macOS seulement ». Cause : autre système. Remède : aucun.

## 12. Licence et code source

ocr-md est distribué sous licence AGPL-3.0 (fichier `LICENSE`), imposée par PyMuPDF et PyMuPDF4LLM. La distribution aux membres impose de fournir le code source correspondant à la version installée : il est publié à l'adresse affichée par `ocr-md --version` (dépôt GitHub `gie-novea/ocr-md`, étiquette de la version). L'inventaire des licences des dépendances et des données embarquées (lexique Grammalecte sous MPL-2.0, police Noto Sans sous OFL-1.1) est dans `LICENCES-TIERCES.md`, généré à partir de l'environnement verrouillé.

## 13. Vérifications, performance et poids

Les points à vérifier du cahier des charges (PV-01 à PV-15) et leurs résultats sont consignés dans `docs/verifications.md` ; ceux qui restent à lever le sont en recette : PV-01 (poste de la SODEB sous compte standard), PV-02 (essai à 200 éléments, Finder), PV-08 d (versions de macOS du parc), PV-09 et PV-10 (dossier kDrive de test).

**Performance sur le lot type** (EX-58 : 50 plis, 500 pages dont 300 scannées à 300 dpi, sortie « les deux » ; script `tests/perf/lot_type.py`). Objectifs du cahier, à confirmer en recette : moins de 20 minutes, relance en moins de 30 secondes, moins de 1,5 Go.

| Poste | Moteur | Durée | Pages par minute | Relance | Mémoire maximale |
|---|---|---|---|---|---|
| PC de développement, Windows 11 | `Windows.Media.Ocr` (fr-FR) | 2 min 10 s | 231 | 0,4 s | 413 Mo |
| Intégration continue, Windows Server 2025 | `Windows.Media.Ocr` (fr-FR) | 1 min 40 s | 300 | 0,2 s | 404 Mo |
| Intégration continue, Mac Apple Silicon, macOS 26.7.2 | Apple Vision | 8 min 36 s | 58 | 0,1 s | 714 Mo |
| Intégration continue, Mac Intel, macOS 15.7.9 | Apple Vision | 13 min 55 s | 36 | 0,3 s | 530 Mo |

Objectifs tenus sur les quatre postes. La reconnaissance d'Apple Vision est la plus lente (environ 1,7 s par page sur Apple Silicon et 2,8 s sur Intel, contre 0,2 s pour `Windows.Media.Ocr`). Les machines d'intégration continue sont des machines virtuelles : relevés à refaire sur les postes de la SODEB (TM-08).

**Poids de l'installation** (relevés de l'intégration continue) : environnement de l'outil 238 Mo sous Windows, 276 Mo (Apple Silicon) à 297 Mo (Intel) sous macOS, surtout PyMuPDF et PyMuPDF Layout, numpy et onnxruntime ; Python 3.12 géré par `uv` : 62 Mo (Windows) et 71 Mo (macOS) ; `uv` lui-même : environ 40 Mo ; soit 340 à 410 Mo dans le profil.
