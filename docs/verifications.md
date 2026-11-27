# Vérifications des points PV-xx

Ce fichier consigne, pour chaque point à vérifier du cahier des charges (section 10), le résultat de l'essai, la date, les versions, la décision et le repli éventuel. Les scripts d'essai sont dans `essais/` (voir `essais/README.md`) ; leurs résultats chiffrés bruts sont dans `essais/*/sortie/resultat_*.json`.

Poste de développement : Windows 11 Pro (10.0.26300), compte de l'utilisateur sans élévation, uv 0.11.21, Python 3.12.10 (essais PV-04 à PV-06, PV-13) et Python 3.12.13 géré par uv (PV-11). Toutes les données d'essai sont synthétiques.

Versions constatées le 26/11/2026 : PyMuPDF 2.2, pymupdf4llm 2.2, pymupdf-layout 2.2, onnxruntime 1.32.0, pymupdf-fonts 1.0.5, Pillow 13.0.0, numpy 2.5.5, winrt-runtime 4.2.1, paquets winrt-Windows.* 10.0.28000.2957.

| Point | État | Résumé |
|---|---|---|
| PV-01 | à lever par le référent | poste SODEB sous compte standard ; voir aussi l'observation sur `uv python install` ci-dessous |
| PV-02 | partie Windows largement levée | `.lnk` créé sans droits ; sélection de 66 éléments transmise en un seul lancement ; 200 éléments non testés |
| PV-03 | levé pour le poste de développement | `fr-FR` disponible, détection sans élévation |
| PV-04 | levé | projection PyWinRT retenue ; œ, æ et ’ non restitués par le moteur (décision à prendre) |
| PV-05 | levé | `pymupdf4llm.to_markdown`, texte invisible repris, `ocr_function` jamais appelée sur une page déjà dotée d'un calque |
| PV-06 | levé | police Noto Sans, calque par mot (Windows) ou par ligne (Vision), toutes rotations ; (b) convention de Vision confirmée par la CI (origine en bas à gauche) ; (d) recherche dans Aperçu et Acrobat en recette (TM-05) |
| PV-07 | hors v1 | v1.1 |
| PV-08 | levé (a, b, c) ; (d) en recette | français en niveau « accurate » sur macOS 15.7.9 Intel et 26.7.2 Apple Silicon ; chaîne complète sur Mac Intel avec PyMuPDF 1.28.2 ; versions de macOS du parc à relever en recette |
| PV-09 | script prêt, essai à faire sur le dossier kDrive de test | |
| PV-10 | à lever par le référent | |
| PV-11 | levé (Windows, présence sur macOS) | tkinter présent dans le Python géré par uv : Tk 8.6.12 (Windows), 9.0.3 (macOS) ; affichage sous macOS en recette |
| PV-12 | levé | Grammalecte 7.7, MPL 2.0, 476 083 formes, chargement en 0,13 s |
| PV-14 | levé : méthode utilisable, retenue par défaut | boîtes fournies par Vision pour 100 % des mots ; aucun écart mesurable sur le jeu synthétique avec le critère EX-30 (b) ; coût de 0,11 à 0,12 s par page (3 à 5 %) |
| PV-13 | levé avec repli | détection des fusions fiable sur tableau natif ; rendu HTML de PyMuPDF4LLM inutilisable pour les fusions ; HTML produit par l'outil |

## PV-03. Pack OCR français de Windows

- Date : 26/11/2026.
- Méthode : Windows PowerShell 5.1, compte non élevé : `[Windows.Media.Ocr.OcrEngine]::AvailableRecognizerLanguages` ; confirmé ensuite depuis Python par `OcrEngine.available_recognizer_languages` et `OcrEngine.is_language_supported`.
- Résultat : `en-US` et `fr-FR` disponibles ; appels sans élévation réussis ; `MaxImageDimension` = 10000.
- Décision : la méthode de détection sans droits d'administrateur (EX-71) est confirmée. La présence du pack sur les PC de la SODEB reste à constater par `ocr-md verifier`.

## PV-04. OCR Windows par `winrt-Windows.Media.Ocr`

- Date : 26/11/2026. Essai : `essais/pv04/essai_pv04.py`, prototype `essais/pv04/ocr_windows_proto.py`.
- Paquets nécessaires (liste minimale constatée) : `winrt-runtime`, `winrt-Windows.Foundation`, `winrt-Windows.Foundation.Collections` (installés par dépendance), `winrt-Windows.Media.Ocr`, `winrt-Windows.Globalization` (`Language`), `winrt-Windows.Graphics.Imaging` (`SoftwareBitmap`), `winrt-Windows.Storage.Streams` (`Buffer`).
- Conversion Pillow vers `SoftwareBitmap` : image en niveaux de gris copiée dans un `Buffer` par `memoryview`, puis `SoftwareBitmap.create_copy_from_buffer(tampon, BitmapPixelFormat.GRAY8, w, h)`. Aucun fichier intermédiaire.
- Appel asynchrone : `asyncio.run(moteur.recognize_async(bitmap))` depuis du code synchrone, sans difficulté.
- Boîtes : `OcrWord.bounding_rect` en pixels de l'image, origine en haut à gauche (`x`, `y`, `width`, `height`). Boîtes plus serrées que la boîte typographique : la hauteur de l'union des mots d'une ligne vaut en moyenne 1,03 fois la taille de police réelle (0,92 à 1,22 selon les lettres présentes).
- `TextAngle` : renvoie -1,5 sur la page inclinée de 1,5 degré, 0 sur les pages droites. Les boîtes sont alignées sur les axes de l'image.
- Durée : 0,10 s pour une page A4 droite à 300 dpi, 0,22 s inclinée et bruitée, 0,24 s floue ; 0,5 s pour une page A0.
- `MaxImageDimension` : une page A0 à 300 dpi (9934 x 14042 px) est refusée ; la résolution est ramenée à 213 dpi (7053 x 9970 px) et la page est reconnue (85,5 % des mots). La règle de EX-25 fonctionne.
- Lancement sans console par `pythonw.exe` : réussi (code 0, résultat écrit sur disque).
- Qualité (objectif 7.3 : 95 % des mots de référence) :
  - page droite et page inclinée : 86,7 % des mots exacts. Sur 83 mots, 10 manquent uniquement parce que le moteur restitue « oe » pour « œ », « ae » pour « æ », « IC » pour « Æ » et l'apostrophe droite `'` pour l'apostrophe typographique `’` ; 1 erreur réelle (« DC1 » lu « DCI »). Hors ces substitutions systématiques, le taux est de 98,8 % ;
  - page floue et très bruitée : 66,3 %, comme attendu pour le fichier 5 du jeu de test.
- Chaîne complète (OCR Windows, calque, `pdftotext`, Markdown) : 0 appel à `ocr_function` pendant la conversion Markdown ; recouvrement des mots Markdown / `pdftotext` de 100 % dans les deux sens (critère EX-40 : 98 %).
- Décision : la projection PyWinRT est retenue (REC-03) ; `winocr` n'est pas nécessaire.
- **Écart au cahier des charges à trancher** : le CA (a) de EX-30 (« `pdftotext` restitue œ, æ, ’ ») et l'objectif de 95 % de la section 7.3 ne peuvent pas être atteints tels quels sous Windows, car le moteur ne produit pas ces caractères. Le calque, lui, les restitue (PV-06). Options : (1) les critères comparent après équivalence `œ/oe`, `æ/ae`, `’/'` ; (2) l'outil corrige le texte reconnu (apostrophe typographique, liste de mots en œ et æ du lexique). Recommandation : option 1, sans modification du texte reconnu.

## PV-05. `ocr_function` de PyMuPDF4LLM ; `pymupdf.layout` ; texte invisible

- Date : 26/11/2026. Essai : `essais/pv05/essai_pv05.py` (PDF de 3 pages : page native, page-image dotée d'un calque invisible, page-image sans texte ; `ocr_function` instrumentée).
- (e) Point d'entrée et version : PyMuPDF 2.2. Les paquets `pymupdf4llm` 2.2 et `pymupdf-layout` 2.2 sont des coquilles vides (aucun fichier dans leur `RECORD`) ; le code de `pymupdf4llm` et de `pymupdf/layout` est livré par le paquet `pymupdf` 2.2 (licence double AGPL-3.0 ou commerciale, d'après ses métadonnées). `pymupdf4llm` exige exactement la même version que `pymupdf`. `Document.to_markdown` n'est qu'un renvoi vers `pymupdf4llm.to_markdown`. Le « README version 1.28.x » cité en préparation est périmé.
- (a) Aucun import explicite de `pymupdf.layout` n'est nécessaire : le module « layout » est activé par défaut à l'import de `pymupdf4llm` lorsqu'il est disponible. Il s'appuie sur `onnxruntime` (licence MIT) et un modèle ONNX livré, qui ne font pas d'OCR. EX-08 n'interdit pas `onnxruntime` ; à signaler dans l'inventaire des licences.
- (b) Conditions d'appel d'une `ocr_function` fournie : la bibliothèque n'appelle pas son sélecteur de moteur (aucun message sur Tesseract ou RapidOCR). Pour chaque page, elle analyse la page ; si la page contient déjà du texte en mode OCR (texte invisible), elle le conserve et n'appelle pas la fonction (mode par défaut « OCR si nécessaire, garder l'ancien OCR »). La fonction n'est appelée que pour une page sans texte où l'OCR semble utile. Constat : 1 seul appel, pour la page sans calque, dans toutes les combinaisons testées (`force_text`, `ignore_alpha`, `force_ocr=True`).
- (c) Texte invisible : repris intégralement dans le Markdown, accents, œ, €, guillemets français et apostrophe typographique compris. `ignore_alpha` n'existe plus dans la voie « layout » (paramètre ignoré sans erreur) ; `force_text` est sans effet sur ce point.
- (d) Contrat réel de la fonction : appel `ocr_function(page, dpi=ocr_dpi, language=ocr_language, keep_ocr_text=False)`. `pixmap` n'est jamais transmis. `dpi` vaut `ocr_dpi` (défaut 150) ; `language` vaut `ocr_language` (défaut `"eng"`). La fonction doit écrire sur la page ; aucune valeur de retour n'est utilisée. La page modifiée est une copie en mémoire : le fichier source reste inchangé (empreinte SHA-256 identique). La bibliothèque appelle `page.remove_rotation()` avant l'analyse.
- `page_chunks=True` : une entrée par page, clés `metadata` (dont `page_number` à partir de 1), `text`, `page_boxes`, `toc_items`. Une page sans texte donne un texte vide : le repère et la mention « page sans texte exploitable » seront ajoutés par l'outil.
- Décision : point d'entrée `pymupdf4llm.to_markdown(chemin, page_chunks=True, ocr_function=adaptateur, ocr_language=...)`. L'adaptateur tient le registre prévu en 3.1 : pour une page déjà traitée par l'outil, il ne fait rien ; pour une page `vide` ou `aucun_texte_reconnu`, il ne fait rien non plus (l'OCR a déjà eu lieu une fois). Le repli de PV-05 n'est pas nécessaire.

## PV-06. Calque invisible avec police Unicode

- Date : 26/11/2026. Essai : `essais/pv06/essai_pv06.py`. Cas : A droite ; B inclinée de 1,5 degré et bruitée ; C rotation 90 ; D rotation 270 ; E boîte de rognage décalée. Deux stratégies : une écriture par ligne, une par mot.
- Police : Noto Sans Regular (paquet `pymupdf-fonts`, licence SIL OFL 1.1), qui couvre tous les caractères exigés. L'insertion en sous-ensemble se fait par `doc.subset_fonts()`.
- Méthode retenue : taille de police déduite de la hauteur de la boîte, étirement horizontal par `morph` (largeur de la boîte / `Font.text_length`), mode de rendu 3. Conversion du repère : pixels de l'image affichée vers points de la page affichée (échelle `page.rect` / taille de l'image), puis `page.derotation_matrix` vers le repère non pivoté ; le texte est tourné de `page.rotation` dans `morph`.
- Résultats (10 combinaisons) : (d) `pdftotext` restitue tous les caractères exigés et 100 % des mots de référence ; (a) et (b) `search_for` trouve 16 mots sur 16, tous centrés dans la boîte de vérité agrandie de 10 % ; (c) rotations 90 et 270 et boîte de rognage décalée correctes ; rendu à 100 dpi identique au pixel près avant et après le calque ; flux image identiques octet pour octet.
- (e) Poids : la police complète ajoute environ 260 Ko par document ; après sous-ensemble, environ 30 Ko (par ligne) à 47 Ko (par mot) pour une page de texte dense.
- Contrôle visuel : images `essais/pv06/sortie/*_controle.png` (calque rendu visible en rouge).
- Décision : écriture **par mot** lorsque le moteur fournit des mots (cas de Windows), car elle reste juste sur une page inclinée où la boîte d'une ligne entière est trop haute ; écriture par ligne sinon. Taille de police : à calibrer au jalon 4 sur les boîtes réelles des moteurs (sous Windows, hauteur de ligne ≈ 1,03 fois la taille réelle, voir PV-04).
- Reste à vérifier : (b) convention des boîtes d'Apple Vision (coordonnées normalisées, origine en bas à gauche selon la documentation d'Apple) par la CI macOS ; (d) recherche dans Aperçu et Acrobat en recette (TM-05) ; poids de la police répétée sur des documents de plusieurs pages (au jalon 4).

## PV-11. `tkinter` dans le Python géré par uv

- Date : 26/11/2026. Essai : `essais/pv11/essai_pv11.py`, lancé par `pythonw.exe` du Python 3.12.13 géré par uv.
- Résultat : tkinter présent, Tk 8.6.12, thème `vista`, facteur d'échelle 1,33 (écran à haute densité pris en compte), fenêtre de progression mise à jour puis fermée, aucune console.
- Observation pour les scripts d'installation : `uv python install 3.12` a affiché « Missing expected target directory for Python minor version link » et un code d'erreur, alors que l'installation est complète et utilisable. À reproduire depuis un PowerShell ordinaire au jalon 9 ; le script d'installation devra vérifier le résultat par `uv python find` plutôt que par le seul code de retour.
- Décision : REC-02 suivie (tkinter). Reste à vérifier sur macOS (icône dans le Dock) par la CI et en recette.

## PV-12. Lexique français

- Date : 26/11/2026. Source retenue par le commanditaire : lexique de Grammalecte.
- Fichier : https://grammalecte.net/dic/lexique-grammalecte-fr-v7.7.zip (archive du 15/12/2025, 12 325 782 octets), SHA-256 `bdccf2065e252010253171000a38de84581407896b6bc60aca7d4d69dab7e4d2`.
- Licence : MPL 2.0 (en-tête du fichier et `README_lexique.txt`) ; la mention « Incompatible With Secondary Licenses » est absente, ce qui permet la distribution avec un projet sous AGPL-3.0. L'avis MPL est conservé en tête du fichier dérivé ; le texte de la MPL 2.0 est livré à côté.
- Fichier embarqué : `src/ocr_md/donnees/lexique/formes-fr.txt.gz`, construit par `outils/construire_lexique.py` (colonne « Flexion », NFC, sans doublon) : 476 083 formes, 1,2 Mo.
- Chargement : 0,13 s (objectif : moins d'une seconde).
- Constat : le lexique contient « œuvre » et « cœur » mais pas « oeuvre » ni « coeur » ; la normalisation des équivalences (décision du 26/11/2026) est donc nécessaire avant la recherche. Avec elle, la page synthétique riche en ligatures reconnue par `Windows.Media.Ocr` compte moins de 10 % de mots inconnus (test `test_windows_ligatures_restent_dans_le_lexique`).

## PV-13. Cellules fusionnées

- Date : 26/11/2026. Essai : `essais/pv13/essai_pv13.py` et `essais/pv13/html_fusion.py`.
- Tableau natif à traits : `page.find_tables()` restitue la grille complète (4 x 4) et marque par `None` les 5 positions couvertes par une fusion ; la détection est fiable.
- `to_markdown(table_output="html")` : produit bien des balises `<table>`, mais **sans aucun `colspan` ni `rowspan`**, et coupe une cellule fusionnée (« 48 500 € forfait » / « global »). Le rendu Markdown coupe aussi un en-tête fusionné (« M » / « ontants »). Le CA de EX-44 n'est donc pas atteignable avec le rendu de la bibliothèque.
- Reconstruction par l'outil : à partir des boîtes de `Table.cells`, une fonction de 30 lignes produit un HTML exact (`rowspan="2"`, `colspan="2"`, toutes les valeurs).
- Tableau scanné (calque OCR, sans traits vectoriels) : `find_tables` trouve un tableau mais pas de fusions (0 `None`, colonnes regroupées) ; les fusions ne sont pas détectables.
- Décision (repli de EX-44 adapté) : pour une page native où `find_tables` détecte un tableau avec fusion ou double en-tête, l'outil produit lui-même le HTML du tableau et l'insère à la place du tableau rendu par la bibliothèque (méthode de remplacement à mettre au point au jalon 6). Pour une page reconnue par OCR contenant un tableau, rendu HTML de la bibliothèque, sans garantie sur les fusions (limite à documenter). À confirmer par le commanditaire.

## PV-02. Raccourcis « Envoyer vers » (partie Windows)

- Date : 26/11/2026. Essai : `essais/pv02/creer_raccourci.py`.
- Résultat : un `.lnk` est créé sans droits d'administrateur par l'objet COM `WScript.Shell`, appelé depuis Windows PowerShell (aucune dépendance Python ajoutée) ; cible, arguments (`--sortie md`) et fenêtre réduite relus correctement. Le raccourci a été créé dans `essais/pv02/sortie/`, pas dans SendTo.
- Test manuel du commanditaire (26/11/2026, raccourci copié dans SendTo) : 4 lancements consignés, chacun en un seul processus, avec `--sortie md` conservé en tête : 1 dossier ; 5 fichiers ; 66 dossiers (10 796 caractères de ligne de commande) ; 1 fichier. Chemins accentués et avec espaces transmis intacts. Le journal contient des chemins réels ; il n'est pas versionné et n'est pas reproduit ici.
- Conclusion : une sélection multiple est transmise en entier, en un seul lancement, au moins jusqu'à 66 éléments. La limite théorique de la ligne de commande Windows (32 767 caractères) correspond, avec des chemins de cette longueur (environ 160 caractères), à environ 200 éléments.
- Reste à faire : essai à 200 éléments (pour constater le comportement au-delà de la limite) ; accès par « Afficher d'autres options » sous Windows 11. En attendant, le repli de PV-02 (sélectionner le dossier plutôt que les fichiers) reste recommandé dans le guide.

## PV-09. Fichiers kDrive « en ligne uniquement »

- Date : 26/11/2026. Script : `essais/pv09/diagnostic_fichier.py` (taille déclarée, attributs Windows OFFLINE, RECALL_ON_OPEN, RECALL_ON_DATA_ACCESS, PINNED, UNPINNED, REPARSE_POINT ; sous macOS `st_flags`, `SF_DATALESS`, blocs alloués ; lecture de 1 Ko avec délai). Vérifié sur un fichier local ordinaire.
- Reste à faire : exécution sur le dossier kDrive de test, sur des fichiers en ligne uniquement et disponibles localement, quand le chemin et l'exception d'accès auront été fournis.

## Premier passage de la CI GitHub Actions (26/11/2026, run 45868464811)

- **PV-06 (b), levé** : Apple Vision (macOS 26.7.2, Apple Silicon) renvoie des boîtes normalisées (x, y, largeur, hauteur) dont l'origine est **en bas à gauche**. Pour le mot de contrôle, la conversion « origine en bas » donne (301, 337, 607, 388) pixels pour une vérité de (300, 322, 607, 390) ; l'hypothèse « origine en haut » tombe hors de la page. Le test `test_apple_vision_convention_des_boites` le vérifie à chaque passage.
- **PV-08 (a), levé pour macOS 26** : `fr-FR` figure parmi les langues de Vision au niveau « accurate ». Mots de référence retrouvés : 98,8 % ; page à ligatures : 100 %, avec moins de 10 % de mots inconnus. La version minimale de macOS reste à constater en recette.
- **PV-08 (b), bloquant** : l'installation échoue sur Mac Intel (`macos-15-intel`). PyMuPDF n'est plus publié pour macOS Intel depuis la version 2.0 (octobre 2026) ; la dernière version qui l'est est la 1.28.2 (août 2026). onnxruntime, requis par le module de mise en page, n'est plus publié pour macOS Intel au-delà de 1.23.2. Constat complémentaire : avec PyMuPDF, pymupdf4llm et pymupdf-layout 1.28.2 (pymupdf-layout sous double licence AGPL-3.0 ou commerciale), les essais PV-05 et PV-06 donnent sous Windows des résultats identiques à ceux de la 2.2. Décision à prendre par le commanditaire.
- **Windows (image Windows Server 2025 de GitHub)** : seul `en-US` était présent ; `Add-WindowsCapability` a installé le module OCR français (environ 15 minutes à chaque passage). Les tests du moteur réel n'ont pas pu s'exécuter, car `ocr-md verifier` a échoué avant : `platform.release()` y vaut « 2025Server ». Défaut corrigé (détection par le numéro de build).
- **Linux** : `ocr-md verifier` renvoie 3 (système non pris en charge pour l'usage), comme prévu ; l'étape est désormais tolérée sous Linux.
- **tkinter (PV-11, macOS)** : présent, mais le test attendait Tcl 8 ; le Python géré par uv embarque une autre version. Test assoupli (8.6 ou 9) ; la version sera affichée au prochain passage.

### Décision du commanditaire sur PV-08 (b) (26/11/2026)

- Version figée sur toutes les plateformes : PyMuPDF, pymupdf4llm et pymupdf-layout **1.28.2** (au lieu de 2.2). En 1.28.2, pymupdf4llm et pymupdf-layout sont de vrais paquets (non vides), sous double licence AGPL-3.0 ou commerciale ; pymupdf4llm dépend de pymupdf-layout, qui dépend d'onnxruntime, numpy, networkx et pyyaml.
- onnxruntime : la résolution universelle de uv retient **1.23.2 sur toutes les plateformes** (dernière version publiée pour macOS Intel), ce qui garde une seule version partout. sympy et pyreadline3 s'ajoutent comme dépendances transitives.
- Conséquence sur PV-05 : les constats faits en 2.2 restent valables en 1.28.2 (essai rejoué : même point d'entrée `pymupdf4llm.to_markdown`, même contrat de `ocr_function`, texte invisible repris, 1 seul appel pour la page sans calque). La remarque « paquets vides » ne vaut que pour la branche 2.x.
- Sous Windows : 61 tests réussis avec la 1.28.2. À confirmer par la CI sur macOS Apple Silicon et Intel.

## Deuxième passage de la CI (26/11/2026, run 45874712753, PyMuPDF 1.28.2) : succès sur les quatre plateformes

| Plateforme | Système | Tests | OCR réel | Tcl/Tk |
|---|---|---|---|---|
| macOS Apple Silicon | macOS 26.7.2 (arm64) | 62 réussis, 2 sautés (Windows) | Vision : 98,8 % des mots ; ligatures 100 % ; boîtes à origine en bas confirmées | 9.0.3 |
| macOS Intel | macOS 15.7.9 (x86_64) | 62 réussis, 2 sautés (Windows) | Vision : 96,4 % des mots ; ligatures 98,6 % ; `fr-FR` disponible ; origine en bas confirmée | 9.0.3 |
| Windows | Windows Server 2025 (10.0.26100) | 61 réussis, 3 sautés (macOS) | module fr-FR installé par la CI ; `Windows.Media.Ocr` : 97,6 % ; ligatures 100 % | 8.6.12 |
| Linux | Ubuntu | niveau 1 seulement | sans objet | sans objet |

- **PV-08 (b), levé** : la chaîne (PyMuPDF 1.28.2, mise en page avec onnxruntime 1.23.2, Vision) fonctionne sur Mac Intel ; PV-08 (a) confirmé aussi sur macOS 15.
- **PV-11 (macOS)** : le Python géré par uv embarque Tcl/Tk 9.0.3 sous macOS et 8.6.12 sous Windows ; présence confirmée, l'affichage d'une fenêtre (icône du Dock, haute densité) reste à vérifier en recette.

## PV-06 (b) et PV-08 levés (26/11/2026)

Résultats des passages de CI 45874712753, 45878421683, 45879565652 et 45886598176 (GitHub Actions) :

| Point | macOS Intel (15.7.9, x86_64) | macOS Apple Silicon (26.7.2, arm64) |
|---|---|---|
| PV-08 (a) : `fr-FR` parmi les langues de Vision au niveau « accurate » | oui | oui |
| Mots de référence retrouvés, page synthétique | 96,4 % | 98,8 % |
| Fichiers 2, 3, 10, 18 du jeu de test, par page | 96,3 % à 99,3 % | 98,5 % à 100 % |
| Page à ligatures | 98,6 % | 100 % |
| PV-06 (b) : origine des boîtes de Vision | en bas à gauche (test `test_apple_vision_convention_des_boites`) | en bas à gauche |
| PV-08 (b) : installation et chaîne complète | réussies (PyMuPDF 1.28.2, onnxruntime 1.23.2) | réussies |

- PV-06 (b) : levé. Vision renvoie (x, y, largeur, hauteur) entre 0 et 1, origine en bas à gauche ; la conversion du module `ocr/macos.py` est vérifiée à chaque passage de la CI.
- PV-08 (a) et (b) : levés pour macOS 15 et 26. (c) : convention des boîtes d'ocrmac, voir PV-06 (b). (d) : versions de macOS présentes à la SODEB, à relever en recette ; la version minimale supportée sera la plus ancienne constatée conforme.

## EX-59 : mémoire sur les gros documents et sur un lot (26/11/2026)

Constat de la CI du jalon 4 (pic mémoire, 100 puis 1 000 pages, moteur factice, 100 dpi) après les deux premières corrections (cache MuPDF vidé après chaque page ; calque d'une page en un seul flux compressé) : Windows 60 à 111 Mo, Mac Intel 62 à 118 Mo, Mac Apple Silicon 72 à 124 Mo, soit environ 55 Ko par page et un rapport de 1,7 à 1,9 (seuil de EX-59 : 2). Marge insuffisante.

Recherche de la cause (poste de développement, mesures `psutil` et `tracemalloc`, documents de 100 et 500 pages, 143 mots par page) :
- mémoire Python conservée pendant le traitement d'un document de 500 pages : 20 Mo, soit environ 40 Ko par page. Elle provient des résultats complets du moteur (mots, boîtes, confiances) conservés pour l'évaluation de la qualité ; ils étaient libérés à la fin du fichier ;
- sous-ensembles de police : sans effet (la police n'est insérée qu'une fois par document, `subset_fonts` n'intervient qu'à l'enregistrement) ;
- journal : écrit au fil de l'eau sur disque, sans tampon en mémoire ;
- reste, côté MuPDF : environ 16 Ko par page (document modifié en mémoire), libérés à la fermeture du document.

Correction : seul un résumé de chaque page reconnue est conservé (`ResumeOcr` : texte, nombre de caractères, confiance moyenne pondérée, part de texte peu sûr), ce qui suffit à EX-35 et EX-36.

Mesures après correction (poste de développement, moteur factice, 72 dpi) :
- lot de 4 fichiers de 500 pages : pic pendant chaque fichier de 82 à 84 Mo (100 Mo avant correction), mémoire après chaque fichier stable (75, 74, 75, 74 Mo) ;
- lot de 10 fichiers de 200 pages (`tests/test_memoire_lot.py`) : mémoire après chaque fichier constante (75 Mo), pic pendant chaque fichier 79 à 80 Mo ;
- le test passe à 20 fichiers de 500 pages lors de la passe complète de la CI (chaque nuit et sur les étiquettes v*).

La croissance pendant un fichier est donc rendue à la fin de chaque fichier et ne s'accumule pas sur le lot.

Mesures de la CI après correction (runs 45892587343 et 45893116911) :

| Plateforme | Pic 100 pages | Pic 1 000 pages | Rapport (seuil EX-59 : 2) | Lot 10 x 200 pages, mémoire après chaque fichier |
|---|---|---|---|---|
| Windows | 57 Mo | 67 à 69 Mo | 1,18 à 1,21 | 66 à 68 Mo |
| macOS Intel | 58 à 59 Mo | 74 à 76 Mo | 1,25 à 1,31 | 63 à 66 Mo |
| macOS Apple Silicon | 69 Mo | 83 Mo | 1,20 | 80 Mo |
| Linux | 489 à 501 Mo | 489 à 501 Mo | 1,00 | 88 à 90 Mo |

Marge sous le seuil : au moins 34 %. Sous Linux, le pic mesuré par `ru_maxrss` comprend le chargement initial des bibliothèques et masque la croissance ; la mesure de lot y reste significative.

## PV-14. Boîtes par mot avec Apple Vision

- Demande du commanditaire (26/11/2026) : obtenir des boîtes par mot sous macOS, mesurer le gain sur le taux de mots retrouvés et sur la position des mots (critère EX-30 b) et le coût en temps par page ; repli : répartition des mots au prorata des caractères dans la boîte de la ligne.
- Réalisation : `ocr/macos.py`, mode « mots » : appel direct de `VNRecognizeTextRequest` par pyobjc (ocrmac n'expose pas la méthode), découpage de chaque ligne en mots et `VNRecognizedText.boundingBoxForRange:error:` pour chacun (plages en unités UTF-16) ; un mot sans boîte est placé au prorata. Mode « prorata » conservé pour la comparaison.
- Mesure : `tests/test_pv14_vision_mots.py` (CI macOS Intel et Apple Silicon), pages des fichiers 2 et 18, trois écritures du calque comparées (par ligne, par mot au prorata, par mot avec boîtes Vision).
- Résultats (CI, run 45897735605, 6 pages : fichier 2 pages 1 à 4, fichier 18 pages 1 et 2) :

| Mesure | Mac Apple Silicon : ligne / prorata / Vision | Mac Intel : ligne / prorata / Vision |
|---|---|---|
| Mots dont la boîte est fournie par Vision | 100 % (mode Vision) | 100 % (mode Vision) |
| Mots de référence retrouvés dans le calque | 98,5 % à 100 %, identique dans les trois cas | 96,3 % à 99,3 %, identique dans les trois cas |
| Mots de référence bien placés (centre dans la boîte de vérité agrandie de 10 %) | 100 % / 100 % / 100 % | 100 % / 100 % / 100 % |
| Critère EX-30 (b) | 6/6 pages dans les trois cas | 6/6 pages dans les trois cas |
| Temps par page | 2,34 s / 2,34 s / 2,45 s | 3,32 s / 3,32 s / 3,44 s |

- Conclusion : `boundingBoxForRange:error:` est utilisable (aucun échec, aucun mot sans boîte). Le taux de mots retrouvés ne dépend pas du mode d'écriture (le texte est le même). Sur le jeu synthétique, le critère de position de EX-30 (b) est atteint aussi par la répartition au prorata : le texte, composé en une seule police à chasse régulière, rend le prorata presque exact ; le critère, centre dans la boîte agrandie de 10 %, ne permet donc pas de départager les méthodes. Le coût des boîtes Vision est de 0,11 à 0,12 s par page (3 à 5 %).
- Décision : le mode Vision est retenu par défaut, car il ne dépend pas de la régularité de la police (documents réels : polices proportionnelles, gras, chiffres). Le repli au prorata reste appliqué mot par mot si Vision ne fournit pas une boîte.
- Mesure plus fine possible (non faite) : écart moyen entre la boîte trouvée et la boîte de vérité (recouvrement), et page de test en police proportionnelle variée.

## PV-05 (complément, jalon 6) : comportements de PyMuPDF4LLM 1.28.2

Voir `docs/avancement.md`, jalon 6 : espaces retirés dans les cellules de tableau (correctif ciblé), page scannée portant du texte visible dont le calque est absorbé par la zone d'image (repli en texte simple), cellules fusionnées coupées sur les tableaux scannés (même repli).

## Correctif de PyMuPDF4LLM : application et contrôle (26/11/2026)

- Module isolé : `src/ocr_md/correctifs.py`. Aucune copie modifiée de la bibliothèque : le correctif remplace, en mémoire, l'attribut `extract_cells` du module `pymupdf4llm.helpers.utils` par une fonction qui délègue à l'originale ; `document_layout` appelle cette fonction par l'attribut du module, et reçoit donc la version corrigée.
- Moment : au lancement de chaque lot (`traitement.executer`) ; idempotent ; rappelé par `markdown_pdf` pour un usage direct.
- Contrôle de version : le correctif n'est appliqué que si PyMuPDF et PyMuPDF4LLM sont exactement en 1.28.2 (version verrouillée). Sinon, il n'est pas appliqué et la raison est écrite au journal de chaque dossier `_OCR` (« correctif ... non appliqué : version ... ») ; l'état est aussi journalisé quand il est appliqué.
- Portée : seules les cellules dont tout le texte est invisible (calque OCR) passent par le chemin « texte simple » de la fonction d'origine, qui conserve les espaces ; les cellules de texte natif sont inchangées.
- Tests (`tests/test_correctifs.py`) : l'exemple minimal du ticket produit « AnnaSmith » sans le correctif (le test échoue si le défaut disparaît : le correctif serait alors à retirer), « Anna Smith » avec (le test échoue si le correctif n'agit plus) ; version différente simulée : correctif non appliqué et raison renseignée ; application au lancement et mention au journal.
- Ticket pour le dépôt de PyMuPDF4LLM : `docs/ticket-pymupdf4llm-espaces-cellules.md` (à déposer par le commanditaire).

## Temps par page : rendu, reconnaissance, calque (26/11/2026)

- Instrumentation : pour chaque fichier, le journal indique la durée moyenne par page reconnue, ventilée entre rendu de la page, reconnaissance et écriture du calque, et, en fin de lot, le débit global en pages par minute (EX-57). Sous macOS, la reconnaissance est elle-même ventilée en conversion de l'image en PNG, appel de Vision et récupération des boîtes des mots (`tests/test_chaine_reelle.py`).
- Poste de développement (Windows 11, `Windows.Media.Ocr` fr-FR, 300 dpi, fichiers 2, 18 et 6b) : rendu 0,046 s (23 %), reconnaissance 0,129 s (63 %), calque 0,029 s (14 %).
- CI du 26/11/2026 (run 45901094203), fichiers 2, 18 et 6b, 300 dpi, moyennes par page reconnue :

| Plateforme | Rendu | Reconnaissance | Calque |
|---|---|---|---|
| Windows (CI, en-US) | 0,056 s (21 %) | 0,179 s (68 %) | 0,027 s (10 %) |
| Mac Apple Silicon (fr-FR) | 0,061 s (2 %) | 3,086 s (96 %) | 0,052 s (2 %) |
| Mac Intel (fr-FR) | 0,077 s (2 %) | 3,555 s (96 %) | 0,071 s (2 %) |

- Ventilation de la reconnaissance sous macOS (fichiers 2 et 18) : conversion de l'image en PNG 0,740 s (23 %) sur Apple Silicon et 0,992 s (24 %) sur Intel ; appel de Vision 2,393 s (75 %) et 3,021 s (73 %) ; boîtes des mots 0,007 et 0,016 s (moins de 1 %).
- Lecture : le rendu et le calque pèsent peu (2 % sous macOS). En revanche, la conversion de l'image transmise à Vision coûte près d'un quart du temps : l'image était convertie en RVB puis compressée en PNG au niveau par défaut.
- Optimisation appliquée (27/11/2026) : image transmise en niveaux de gris, PNG sans perte compressé au niveau 1. Sur le poste de développement, la conversion passe de 0,83 s à 0,11 s par page (gain attendu sous macOS : environ 0,6 à 0,9 s par page, soit 20 % du temps). Autre piste, non retenue à ce stade : transmettre l'image non compressée (BMP, 0,016 s), sous réserve de vérifier sa prise en charge par Vision. Gain réel et absence d'effet sur la reconnaissance : à constater par la CI du jalon 7.
