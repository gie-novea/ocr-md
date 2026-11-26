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

## Entre les jalons 1 et 2 (26/11/2026)

- PV-02 : générateur `essais/pv02/generer_lot200.py` (200 fichiers vides aux noms longs, ligne de commande estimée à 30 800 caractères, sous la limite de 32 767) ; le lot produit (`essais/pv02/lot200/`) n'est pas versionné. Le journal du premier essai, qui contenait des chemins réels, a été supprimé par le commanditaire.
- Audit de l'historique avant le premier envoi : aucun nom, chemin ni référence issu du journal PV-02 ; mentions de kDrive uniquement génériques. L'auteur et le committer des trois premiers commits ont été remplacés par l'adresse noreply GitHub du commanditaire (historique local réécrit avant tout envoi) ; `user.email` réglé localement dans ce dépôt.
- Décision pour le jalon 9 : le guide utilisateur recommandera d'envoyer un dossier plutôt qu'une sélection de fichiers. Si une sélection approche la limite de longueur de la ligne de commande Windows, l'outil le signalera dans la fenêtre de fin et dans le rapport, plutôt que de traiter une liste éventuellement tronquée.

## Premier passage de la CI et décision Mac Intel (26/11/2026)

- Résultats détaillés : `docs/verifications.md`, rubrique « Premier passage de la CI GitHub Actions ». PV-06 (b) et PV-08 (a) levés sur macOS Apple Silicon ; défaut de détection de Windows Server corrigé.
- Écart au cahier des charges (décision du commanditaire) : PyMuPDF, pymupdf4llm et pymupdf-layout figés en 1.28.2 sur toutes les plateformes, et onnxruntime en 1.23.2, pour conserver la prise en charge du Mac Intel (PyMuPDF 2.x n'y est plus publié). Le « README version 1.28.x » cité en préparation correspond donc à la version retenue. Toute montée de version future devra vérifier la publication pour macOS Intel.
- Coût constaté : l'installation du module OCR français sur l'image Windows de GitHub prend environ 15 minutes par passage.

## Jalon 2 : jeu de test synthétique et moteur factice (26/11/2026)

Fait :
- `tests/donnees/generer.py` (EX-74) : jeu reproductible (graine 2026), 30 fichiers décrits, 30 images, environ 23 Mo, généré en 14 s, non versionné (`tests/donnees/jeu/`). Contenu : fichiers 1 à 15 du cahier, 6b (tableaux scannés), 18 (ligatures), plus deux fichiers ajoutés : 19 (PDF scanné portant une mention de dépôt en texte natif, EX-22) et 20 (couche OCR d'expéditeur saine, statut `couche_expediteur`) ; les sept statuts sont représentés. Le fichier 6 comporte un tableau simple, un tableau fusionné à double en-tête, une DPGF et un cadre de décomposition des honoraires. Fichiers 16 (chemin long) et 17 (1 000 pages) générés à la demande (`--chemin-long`, `--volumineux`).
- `manifeste.json` : vérité terrain par fichier (type, pages, catégorie de chaque page, texte de référence, mots uniques, pied de page attendu, pages douteuses, statut, origine, valeurs des tableaux, rendu attendu, phrases sentinelles, messages attendus) et, pour chaque image, le résultat attendu du moteur factice (mots, boîtes, confiance).
- `ocr/factice.py` : moteur factice déterministe. Chaque image du jeu porte un marqueur de 18 cases dans sa marge supérieure ; le moteur le lit (à toute résolution, vérifié à 72, 150 et 300 dpi, après redressement EXIF et pour chaque trame d'un TIFF) et renvoie les données du manifeste ; compteur d'appels ; mode sans confiance qui imite Windows ; activable par la variable `OCR_MD_MOTEUR_FACTICE` pour les tests en sous-processus.
- Fonctions de fabrication communes (`tests/donnees/fabrication.py`), reprises des essais.
- Tests : 83 réussis, 4 sautés sous Windows. Sur les fichiers 2, 3, 10 et 18 générés, `Windows.Media.Ocr` retrouve 97,8 % à 100 % des mots de référence par page (avec les équivalences) ; page illisible du fichier 5 : 8,9 %.

Constats :
- le rendu HTML de PyMuPDF produit des ligatures typographiques (« ﬂuides ») ; elles existent aussi dans des PDF réels. `forme_comparable` développe désormais ﬀ, ﬁ, ﬂ, ﬃ, ﬄ, ﬅ et ﬆ (même principe que œ et æ) ;
- la police Noto Sans n'a pas de glyphe pour U+FFFD ni pour la zone d'usage privé : la couche dégradée du fichier 4 utilise des lettres cyrilliques comme caractères aberrants (catégorie prévue par EX-36) ;
- openpyxl n'écrit pas de valeurs calculées en cache : le classeur du fichier 8 ne contient que des valeurs saisies ; le cas « formule avec valeur en cache » sera couvert au jalon 8 par un fichier construit autrement, si nécessaire.

Écarts : fichiers 19 et 20 ajoutés au tableau de 7.1 (non prévus au cahier, nécessaires à EX-22 et EX-23) ; la PDF « faux PDF » (fichier texte renommé, CA de EX-18) est rangée avec les erreurs.

## Jalon 3 : inventaire, dossier miroir, rapport, relance, robustesse (26/11/2026)

Fait :
- `inventaire` : parcours récursif trié, exclusions (dossiers `_OCR`, fichiers cachés y compris par attribut Windows, `~$`, `.DS_Store`, `Thumbs.db`, `desktop.ini`), dédoublonnage des fichiers atteints deux fois, regroupement par dossier parent, type par extension (insensible à la casse) confirmé par la signature (PDF, JPEG, PNG, TIFF, conteneur Office avec son dossier `word/`, `xl/` ou `ppt/`), messages des formats non pris en charge (EX-14, EX-18, EX-19) ; détection des fichiers en ligne uniquement (attributs Windows, `SF_DATALESS` et blocs alloués sous macOS) et lecture avec délai (EX-64) ;
- `sorties` : dossier miroir, nommage, règle de relance, écritures atomiques groupées par fichier (aucune sortie d'un fichier n'est publiée tant que toutes ne sont pas prêtes), nettoyage des temporaires au lancement, nouvelles tentatives sur verrou, forme étendue `\?\` des chemins longs sous Windows (EX-50 à EX-53, EX-63, EX-65) ;
- `rapport` : `ocr_rapport.csv` au format de EX-82, fusion avec le rapport existant, réécriture atomique après chaque fichier ; journal avec rotation à 5 Mo, sans texte de document (EX-61, EX-66, EX-82) ; calcul des nombres de la fenêtre de fin (EX-16) ;
- `traitement` : orchestration du lot, fichier Office avec `--sortie pdf` (EX-20), erreurs isolées (EX-60), annulation (EX-17), parent non inscriptible (EX-50) ;
- `traiteurs` : interface commune ; contrôles d'ouverture des PDF (protégé, endommagé, signé : EX-21, le point « À VÉRIFIER » sur la détection de signature est levé par `get_sigflags`) ; les conversions renvoient « fonction réalisée au jalon N » d'ici leur jalon ;
- tests : 112 réussis, 4 sautés sous Windows (dont le chemin de sortie de 300 caractères, EX-63) ; les exigences du jalon sont vérifiées avec un traiteur d'essai qui recopie la source.

Interprétations et écarts (à valider) :
- EX-05 et EX-50 : pour un fichier sélectionné isolément, le dossier `_OCR` est créé dans son dossier, qui est un dossier source. Je lis EX-05 comme « aucun fichier nouveau dans les dossiers sources, hormis le dossier `_OCR` prévu par EX-50 ». Le test d'intégrité vérifie cela ;
- PDF endommagé (EX-21) : PyMuPDF répare sans erreur un fichier tronqué. Règle retenue : endommagé si l'ouverture échoue, s'il n'y a aucune page, si une page est illisible, ou si le document a été réparé et qu'aucune page ne contient plus ni texte, ni image, ni dessin. Une réparation qui laisse un contenu lisible est admise ;
- un fichier passé en erreur lors d'une relance perd ses anciennes sorties, pour qu'aucune sortie périmée ne subsiste à côté d'une ligne « erreur » ;
- fichier annulé (EX-17) : sa ligne garde les informations de la ligne précédente, s'il y en a une, avec `action` à `annule` ;
- `chemin_relatif` est écrit en forme NFC (EX-62), y compris pour un fichier dont le nom est stocké en NFD ;
- une ligne n'est marquée `ignore_a_jour` que si le rapport en contient déjà une pour ce fichier ; à défaut (rapport supprimé), le fichier est retraité ;
- `--refaire-ocr` rend « concernés » les PDF et les images (portée `tout`) ;
- question : EX-12 prévoit le code 3 quand le moteur OCR manque alors qu'un OCR est nécessaire, mais le CA de EX-71 attend le code 1 dans ce cas (les autres fichiers étant traités). Proposition : code 3 seulement si aucun fichier n'a pu être traité faute de moteur, code 1 sinon. À trancher avant le jalon 5.

Constat : le guillemet droit est interdit dans les noms de fichiers sous Windows ; le CA de EX-82 (nom avec point-virgule et guillemet) est vérifié sur un vrai fichier pour le point-virgule et sur le format CSV pour le guillemet.

Décisions du commanditaire sur les jalons 2 et 3 (26/11/2026) :
- EX-05 : interprétation validée (seul le dossier `_OCR` peut apparaître dans un dossier source) ;
- PDF réparé à l'ouverture : 0 page avec contenu, erreur ; au moins une page récupérée, traitement normal et signalement (motif `pdf_repare`, statut `douteux`, message du rapport) ; cahier mis à jour (EX-21, EX-23, 7.1 fichier 13b, 11.1 champs `pages_recuperees` et `pages_totales`, 11.3 paragraphe C) ;
- relance d'un fichier qui passe en erreur : anciennes sorties supprimées seulement si la source est plus récente ; sinon conservées et signalées dans le rapport ; cahier mis à jour (EX-52, EX-60) ;
- codes de retour : 3 si aucun fichier n'a pu être traité faute de moteur OCR, 1 sinon ; cahier mis à jour (EX-12, EX-71) ; réalisation au jalon 5 ;
- jalon 8 (obligatoire) : classeur de test avec formules et valeurs en cache, écrit directement en XML ; une formule sans valeur en cache s'écrit `[formule non calculée : =…]`.

## Jalon 4 : analyse des pages, calque invisible, PDF consultable (26/11/2026)

Fait :
- `analyse_pdf` : classification des pages d'après le texte tracé (mode de rendu invisible), la surface couverte par les images (union exacte des rectangles) et la densité de texte, règle des mentions ajoutées par les plateformes ; statut du document et `origine_texte` (EX-22, EX-23, section 11.2) ; classification égale à la vérité terrain sur toutes les pages du jeu ;
- `calque` : calque invisible en Noto Sans embarquée (`donnees/polices/`, OFL 1.1), mot par mot ou ligne par ligne, pages pivotées comprises ; adaptateur conforme à `ocr_function` (sans effet, compteur d'appels), utilisé au jalon 6 ;
- `traiteurs/pdf.py` : OCR des seules pages-images, une fois (EX-24), réduction de résolution sous la dimension maximale du moteur avec mention au journal (EX-25), copie à l'identique des PDF sans page reconnue ni douteuse (EX-32), métadonnées d'avertissement (EX-33), enregistrement sans recompression des images (EX-29), PDF temporaire dans le profil en sortie Markdown seule, supprimé dans tous les cas (EX-28), PDF réparé partiellement récupérable ;
- `images` : une page par image ou trame, dimensions d'après la résolution, plafond A3, orientation EXIF ; JPEG intégré sans recompression (rotation à l'insertion) (EX-34) ;
- moteur OCR obtenu à la première page qui en a besoin ; s'il manque, seuls les fichiers à reconnaître passent en erreur avec le message de EX-71 ;
- mémoire (EX-59) : le cache de MuPDF est vidé après chaque page reconnue, le calque d'une page est écrit en un seul flux de contenu (une `Shape`) au lieu d'un flux par mot, et ce flux est compressé dès son écriture (1,3 Ko au lieu d'environ 45 Ko pour 150 mots) ; pic mesuré de 162 Mo pour 100 pages et de 161 Mo pour 1 000 pages (moteur factice renvoyant du texte, 100 dpi). Le premier passage de la CI du jalon 4 avait montré une croissance d'environ 0,1 Mo par page sur Windows et macOS (59 à 149 Mo), due à ces deux causes ;
- CI : Poppler (`pdftotext`, `pdfinfo`) installé sur les quatre plateformes ;
- tests : 135 réussis, 4 sautés sous Windows.

Provisoire : le Markdown est pour l'instant le texte du PDF consultable avec repères de page ; la conversion par PyMuPDF4LLM, les tableaux, le front matter et les avertissements arrivent aux jalons 6 et 7. L'évaluation de la qualité (pages douteuses des fichiers 4 et 5) arrive au jalon 7 : en attendant, le fichier 4 sort en `couche_expediteur` et le fichier 5 en `ocrise`.

Interprétations :
- PDF réparé : le signalement `pdf_repare` ne s'applique que si des pages ont été perdues (N < M) ; un PDF réparé dont toutes les pages ont un contenu est traité normalement, car de nombreux PDF réels sont réparés sans perte à l'ouverture ;
- `doc.subset_fonts()` est appliqué au PDF consultable dès qu'une page a été reconnue : il réduit aussi les polices d'origine non réduites, sans changer leur rendu ni le texte extrait (EX-29 et EX-31 vérifiés) ;
- un PDF réparé refuse parfois le nettoyage des objets inutilisés à l'enregistrement : il est alors enregistré sans nettoyage.

Constat : Tesseract est installé sur le poste de développement (`AppData\Local\Programs\Tesseract-OCR`, dans le `PATH`). L'outil ne l'utilise pas ; le test de EX-08 sur la conversion Markdown (jalon 6) le vérifiera sur ce poste même.

## Avant le jalon 5 : mémoire, CI Windows, PV-06 (b) et PV-08 (26/11/2026)

- Mémoire (EX-59) : cause de la croissance d'environ 55 Ko par page identifiée (résultats complets du moteur conservés jusqu'à la fin du fichier) et corrigée (résumé compact par page) ; nouveau test `tests/test_memoire_lot.py` montrant que la mémoire est rendue entre les fichiers d'un lot ; détail dans `docs/verifications.md`. Le seuil de EX-59 n'a pas été modifié.
- CI : à chaque envoi, moteur factice et moteur Windows réel en en-US (seuil de fonctionnement de 50 %, la qualité en français n'étant pas mesurable sans le module) ; chaque nuit, sur les étiquettes v* et à la demande, installation du module fr-FR, tests réels en français et lot mémoire de 20 fichiers de 500 pages.
- PV-06 (b) et PV-08 (a, b, c) levés avec les résultats de la CI (`docs/verifications.md`).

## Jalon 5 : moteurs OCR natifs (26/11/2026)

Fait :
- moteurs Windows (`Windows.Media.Ocr`, projection PyWinRT) et macOS (Apple Vision par `ocrmac`, niveau « accurate », français et anglais) derrière l'interface commune, choisis à l'exécution ; moteur factice pour les tests (EX-07, EX-26, EX-27) ; aucun moteur tiers (EX-08) ;
- langue et résolution au journal, réduction de résolution sous `MaxImageDimension` (EX-25), vérifiée avec le moteur Windows réel sur une page A0 ;
- `ocr-md verifier` : système, moteur et langues disponibles, dossiers du profil (EX-71 ; contrôle des raccourcis au jalon 9) ;
- moteur indisponible : fichiers à reconnaître en erreur avec le message de EX-71, autres fichiers traités ; code de retour 3 si aucun fichier n'a pu être traité faute de moteur, 1 sinon (EX-12, décision du commanditaire) ;
- tests de bout en bout avec le moteur réel (`tests/test_chaine_reelle.py`) : PDF consultables des fichiers 2, 3, 10 et 18 relus par `pdftotext`.

Vérification sur le poste de développement (module fr-FR, Windows 11) : 97,8 % à 100 % des mots de référence retrouvés par `pdftotext` dans les PDF consultables, page par page ; suite complète : 138 tests réussis, 4 sautés (propres à macOS).

CI du jalon 5 (run 45893116911), verte sur les quatre plateformes : PDF consultables relus par `pdftotext`, Apple Vision 95,6 % à 99,3 % (Mac Intel) et 98,5 % à 100 % (Apple Silicon) ; `Windows.Media.Ocr` en en-US 72,6 % à 93,2 % (passe courante, seuil de fonctionnement). Point d'attention : sur Mac Intel, la page 3 du fichier 2 est à 95,6 %, proche de l'objectif de 95 % (calque par ligne sous Vision).

Remarques :
- sous macOS, Vision ne fournit que des lignes : le calque est écrit ligne par ligne (les boîtes des mots sont estimées au prorata des caractères pour l'évaluation) ; la recherche et l'extraction sont exactes, la surbrillance de sélection d'un mot isolé est approximative (repli prévu par PV-06) ;
- `Windows.Media.Ocr` n'accepte qu'une langue par moteur : la langue secondaire n'est pas utilisée sous Windows.
- TM-04 (poste sans module français, puis installation par l'administrateur) reste un test manuel de recette.
