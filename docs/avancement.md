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

## Jalon 6 : Markdown des PDF et des images (26/11/2026)

Fait :
- `markdown_pdf` : conversion par `pymupdf4llm.to_markdown` depuis le PDF consultable, par lots de 50 pages, sortie de la bibliothèque rendue silencieuse, `page_chunks=True`, en-têtes et pieds de page conservés, aucune image exportée, adaptateur `ocr_function` de l'outil (EX-08, EX-40 à EX-43) ;
- repères de page `<!-- page N -->` (variante « TEXTE DOUTEUX » prête pour le jalon 7), entourés de lignes vides, et mention « page sans texte exploitable » (EX-41) ;
- tableaux (EX-44) : tableau simple en Markdown ; tableau natif fusionné ou à double en-tête en HTML produit par l'outil (`colspan`, `rowspan`), toutes les valeurs des tableaux du fichier 6 (dont DPGF et cadre d'honoraires) restituées exactement ; repère « tableau reconnu par OCR » sur les pages reconnues ; `--tableaux md` et `--tableaux html` ;
- calque : chaque mot non final d'une ligne est suivi d'une espace réelle (sans elle, les cellules de tableau issues de l'OCR collaient les mots) ;
- PV-14 : moteur macOS réécrit avec appel direct de Vision et boîte de chaque mot ; mesure en CI ; résultats dans `docs/verifications.md`.

Constats sur PyMuPDF4LLM 1.28.2 (consignés aussi dans `docs/verifications.md`, PV-05) :
- en Markdown, l'extraction d'une cellule de tableau retire les espaces autour de chaque fragment de texte ; le calque écrivant un fragment par mot, les mots étaient collés (« MmeDurand »). Correctif ciblé : une cellule dont tout le texte est invisible (calque OCR) est extraite en texte simple. La version de la bibliothèque étant figée, le correctif est vérifié par les tests à chaque montée de version ;
- une page scannée qui porte aussi du texte visible (mention de dépôt d'une plateforme, fichier 19) n'est plus considérée par la bibliothèque comme une page OCR : l'image pleine page devient une « illustration » qui absorbe le calque, et le Markdown ne contenait que la mention. Repli de PV-05 appliqué aux seules pages reconnues : si le Markdown de la bibliothèque restitue moins de 90 % des mots du calque, ou s'il contient plus de 10 % de mots absents du calque, la page est reprise en texte simple, bloc par bloc, depuis le PDF consultable (journalisé) ;
- sur les tableaux scannés à cellules fusionnées, la bibliothèque coupe les cellules et les nombres (« Total | 40 0 | 00 » pour 40 000) : le même critère fait basculer ces pages en texte simple, précédé du repère « tableau reconnu par OCR » ; les montants restent intacts, la grille est perdue (pages 2 à 4 du fichier 6b) ;
- objectif de recouvrement de EX-40 (98 %) : tenu sur toutes les pages du jeu ; seuil de 90 % retenu pour une page dont un tableau OCR reste en Markdown (cas prévu par le CA de EX-40).

Tests : 149 réussis, 5 sautés sous Windows (module fr-FR du poste de développement).

CI du jalon 6 (run 45897735605), verte sur les quatre plateformes : 149 tests réussis sur les deux Mac, 148 sous Windows (en-US), 142 sous Linux. Pic mémoire 100 / 1 000 pages : Windows 57 / 71 Mo, Mac Intel 58 / 74 Mo, Mac Apple Silicon 68 / 84 Mo. PV-14 levé (voir `docs/verifications.md`).

## Avant le jalon 7 (26/11/2026)

- PV-14 validé par le commanditaire (boîtes Vision par défaut, prorata en repli) ; essai de recette TM-11 ajouté (recherche de montants dans Aperçu sur une DPGF scannée réelle).
- Correctif de PyMuPDF4LLM isolé dans `correctifs.py`, avec contrôle de version, journalisation et tests ; ticket prêt dans `docs/ticket-pymupdf4llm-espaces-cellules.md`.
- Ventilation du temps par page (rendu, reconnaissance, calque) au journal, débit global en fin de lot (EX-57).
- Rapport : nouvelle colonne `pages_texte_simple` (pages du Markdown reprises en texte simple), insérée après `motif_douteux` ; EX-82 mis à jour (15 colonnes). Un rapport existant à 14 colonnes n'est plus relu : les fichiers concernés sont retraités à la relance suivante.

## Jalon 7 : qualité du texte, front matter et avertissements (27/11/2026)

Fait :
- `qualite` : indicateurs de EX-36 (mots inconnus après normalisation des équivalences et des élisions, caractères aberrants, mots fragmentés, mélanges chiffres et lettres hors références et unités, densité) et de EX-35 (confiance moyenne pondérée et part de texte peu sûr sous Vision ; `aucun_texte_reconnu` sur une page non blanche) ; verdict par page, motifs au rapport, nombres seuls au journal ;
- calibrage (EX-76) : `tests/calibrage.py`, tableau dans `docs/calibrage.md` ; zéro erreur de verdict sur le jeu avec le moteur factice et avec `Windows.Media.Ocr` réel ; seuils par défaut fixés aux valeurs de marge maximale : mots inconnus 0,19, caractères aberrants 0,06, mots fragmentés 0,19, densité minimale 0,11 (les autres inchangés) ;
- pas d'OCR d'office sur une couche existante (EX-38) ; `--refaire-ocr` (pages douteuses), `--refaire-ocr=tout` et `--pages` (EX-39) : page remplacée dans la copie par son image rendue à `ocr_dpi` (JPEG qualité 90), reconnue puis réévaluée ;
- front matter (EX-46, section 11.1) conforme au schéma `schema/front-matter-v1.json`, champs dans l'ordre, chaînes libres entre guillemets et énumérations sans guillemets ; bloc d'avertissement (EX-47, paragraphes A, B et C) ; repères de page douteux (EX-41) ; métadonnées (EX-33) ; `_AVERTISSEMENTS.md` régénéré depuis le rapport après chaque fichier (EX-48), avec la commande de reprise pour chaque pièce douteuse ; cohérence des six emplacements vérifiée (EX-49) ;
- PDF réparé partiellement récupérable : reconstruit page par page à l'ouverture (sans quoi le PDF consultable ne se relisait pas) ; une page qui ne se recopie pas est rendue en image puis reconnue ;
- macOS : image transmise à Vision en niveaux de gris et PNG rapide (voir `docs/verifications.md`, temps par page) ;
- test mémoire de lot : seule une hausse de la mémoire entre fichiers est refusée (macOS rend la mémoire de façon différée : 180 puis 146 Mo sur Apple Silicon) ;
- tests : 168 réussis, 6 sautés sous Windows (fr-FR) ; verdicts vérifiés avec le moteur réel (fichier 5 page 2 douteuse, fichiers 2 et 18 sains).

Interprétations et points d'attention :
- seuils calibrés plus sévères que les valeurs de départ du cahier, sur un jeu synthétique très propre : risque de pages signalées à tort sur des documents réels ; recalibrage prévu en recette (TM-08) avec `tests/calibrage.py` ;
- PDF réparé : toutes ses pages sont douteuses ; le bloc d'avertissement ne contient que le paragraphe C (il ne cite pas de pages) ;
- les motifs de toutes les pages douteuses d'un document sont réunis (colonne `motif_douteux`, champ `motifs_douteux`) ;
- `_AVERTISSEMENTS.md` liste, en plus du modèle, la commande `--refaire-ocr` avec le chemin réel de chaque pièce douteuse (REC-04) ;
- `--pages` hors du document : pages ignorées et signalées au journal.

CI du jalon 7 (run 45945692381), verte sur les quatre plateformes (169 tests réussis sur chaque Mac, 166 sous Windows en en-US, 159 sous Linux). Temps de reconnaissance par page sous macOS : 1,48 s (Apple Silicon, moins 52 %) et 2,59 s (Intel, moins 27 %), taux de mots retrouvés inchangés. Mémoire du lot de 10 x 200 pages stable sur toutes les plateformes ; son niveau de départ a monté (160 à 233 Mo selon la plateforme) avec le chargement du lexique de 476 000 formes, une fois par processus.

## Point de reprise (27/11/2026, changement de session)

### État exact

- Jalon 7 terminé, CI verte (run 45945692381 sur le commit `5eb26aa`, poussé). Le jalon 7 n'a pas encore été validé explicitement par le commanditaire.
- Commits locaux non poussés : `1fd4879` (résultats de CI du jalon 7, temps de reconnaissance sous macOS) et le commit qui ajoute cette rubrique. Ils partiront avec le jalon 8.
- Arbre de travail propre ; branche `main`, remote `origin` = `github.com/gie-novea/ocr-md` (public).
- Dernière question posée au commanditaire, sans réponse : « Je lance le jalon 8 (fichiers Office, classeur avec formules en cache) ? ».

### Décisions prises et non encore consignées plus haut

- Distribution (Q10) : la source de distribution est le dépôt GitHub `gie-novea/ocr-md` ; installation par uv depuis l'adresse Git. Cette adresse est celle affichée par `ocr-md --version` (obligation AGPL).
- Outil existant (EX-01) : `C:\Users\Thibaud\Desktop\Outils\Convertisseur MD`. Pour le jalon 8, en reprendre la lecture des classeurs (`data_only`, `read_only`) et des présentations (avec les notes).
- Envois vers le dépôt distant : autorisés depuis le premier passage de la CI ; l'usage est de pousser à chaque jalon. Toute autre action distante reste soumise à accord.
- Identité Git : auteur et committer de chaque commit `Thibaud PROST <311419768+pro-st@users.noreply.github.com>`, réglée par `user.email` local (pas global). L'adresse professionnelle ne doit apparaître dans aucun commit.
- kDrive : le commanditaire créera un dossier de test dédié et ajoutera une exception limitée à ce seul dossier dans `CLAUDE.md` et `settings.json`. D'ici là, ne rien lire sous `F:\`.
- Journal PV-02 : supprimé par le commanditaire ; ne jamais reproduire les chemins ni les noms qu'il contenait.
- Ticket PyMuPDF4LLM : le commanditaire le dépose lui-même ; ne rien publier sur le dépôt de PyMuPDF4LLM.
- PV-14 : pas de mesure supplémentaire demandée.

### Travaux demandés, faits mais non encore confirmés par le commanditaire

- Encadrement du correctif PyMuPDF4LLM (commit `b547ee9`, poussé, CI verte) :
  - module isolé `src/ocr_md/correctifs.py`, appliqué au lancement par `correctifs.appliquer()`, sans copie modifiée de la bibliothèque ;
  - n'agit que si la version installée est 1.28.2 ; sinon il n'est pas appliqué et la raison (`ETAT.raison`) est journalisée ;
  - `tests/test_correctifs.py` échoue si le défaut disparaît (correctif devenu inutile) ou si le correctif n'agit plus ;
  - texte du ticket, en anglais, avec exemple minimal reproductible : `docs/ticket-pymupdf4llm-espaces-cellules.md`.
- Colonne `pages_texte_simple` (commit `b547ee9`) : 15e colonne du rapport, après `motif_douteux` ; EX-82 mis à jour ; un rapport existant à 14 colonnes n'est plus relu (fichiers retraités à la relance).
- Ventilation du temps par page sous Mac et proposition d'optimisation : faite et mesurée (PNG en niveaux de gris, compression rapide) ; résultats dans `docs/verifications.md`.
- Essai de recette TM-11 ajouté au cahier.

### Travaux demandés et non faits

- Jalon 8 (voir prochaine étape).
- Jalon 9 :
  - signaler dans la fenêtre de fin et dans le rapport une sélection qui approche la limite de longueur de la ligne de commande Windows ;
  - vérifier que `uv python install` a réellement réussi (il peut afficher une erreur en réussissant).
- Jalon 10 : performance, guides, `LICENCES-TIERCES.md` généré, `TRACABILITE.md`, fiches de recette ; puis arrêt obligatoire de fin de v1.
- Essais manuels : PV-02 (SendTo, 200 éléments), PV-09 et PV-10 (dossier kDrive de test, à fournir).
- Questions ouvertes : Q14 (PC SODEB sous compte standard, versions de macOS du parc).

### Pièges et constats utiles

- PyMuPDF4LLM 1.28.2 :
  - les cellules de tableau perdent les espaces entre fragments : d'où une espace réelle après chaque mot non final du calque et le correctif de `correctifs.py` ;
  - une page scannée portant du texte visible voit son calque absorbé par l'« illustration » : repli en texte simple si le Markdown garde moins de 90 % des mots du calque ou contient plus de 10 % de mots absents du calque ; pages concernées dans `pages_texte_simple` ;
  - tableaux scannés fusionnés : nombres coupés, même repli ;
  - le HTML de la bibliothèque ne garde pas les fusions : l'outil produit lui-même le HTML des tableaux natifs fusionnés.
- Versions : PyMuPDF, pymupdf4llm et pymupdf-layout figés en 1.28.2 et onnxruntime en 1.23.2 pour garder le Mac Intel ; toute montée de version doit vérifier la publication macOS Intel et relancer `tests/test_correctifs.py`.
- Seuils de qualité : revenus aux valeurs du cahier avant le jalon 8 (voir la rubrique suivante) ; recalibrage en recette (TM-08) avec `tests/calibrage.py`.
- Mémoire : le lexique (476 000 formes) porte la mémoire de base à 160 à 233 Mo ; stable d'un fichier à l'autre. Ne pas assouplir EX-59 : corriger si la marge passe sous 20 %. Le test de lot ne refuse qu'une hausse (macOS rend la mémoire en différé).
- CI Windows : moteur réel en en-US à chaque envoi (seuil de fonctionnement 50 %) ; installation du module fr-FR (environ 15 min), tests réels en français et lot de 20 x 500 pages la nuit, sur les étiquettes `v*` et à la demande. Le module fr-FR reste vérifié sur le poste du commanditaire à chaque jalon.
- WinRT : attendre l'opération par `threading.Event`, pas par `asyncio` (qui ouvre des sockets, interdits pendant les tests).
- Noto Sans n'a pas de glyphe U+FFFD : caractères aberrants du jeu de test en cyrillique.
- openpyxl n'écrit pas de valeurs en cache : le classeur à formules du jalon 8 doit être écrit directement en XML.
- Écriture de code : éviter les heredocs Python avec échappements `\n` dans le shell ; utiliser les outils d'édition de fichiers.

### Prochaine étape : jalon 8 (fichiers Office, EX-45)

- Conversion .docx, .xlsx, .pptx par python-docx, openpyxl et python-pptx ; les traiteurs Office renvoient encore `TraiteurNonRealise(8, ...)`.
- Classeur de test (obligatoire) avec formules et valeurs en cache, XML écrit directement ; une formule sans valeur en cache s'écrit `[formule non calculée : =…]`, jamais une cellule vide.
- Repères `<!-- feuille N : "Nom" -->` et `<!-- diapositive N -->`, plafond `xlsx_lignes_max`, feuilles masquées signalées, notes des diapositives, front matter Office (`pages: null` pour docx et xlsx).
- En fin de jalon : tests verts, mise à jour de ce fichier, commit, envoi avec `1fd4879`, suivi de la CI.

## Avant le jalon 8 (27/11/2026)

Décisions du commanditaire : le calibrage sur un jeu synthétique très propre ne justifie pas d'abaisser les seuils ; plan du jalon 8 validé avec ajustements (voir la rubrique du jalon 8).

Fait :
- seuils (EX-36, EX-76) : pour chaque indicateur, écart entre la page saine la plus défavorable et la page dégradée la plus favorable (parmi celles que l'indicateur déclenche), consigné dans `docs/calibrage.md`. Valeur du cahier retenue quand elle tombe dans l'écart : mots inconnus 0,35, mots fragmentés 0,25, caractères aberrants 0,03 ; densité minimale : 0,2 hors de l'écart (un tableau sain clairsemé est à 0,164), milieu 0,108 retenu (0,11, inchangé) ; mélanges 0,10 et confiance 0,70 inchangés. Toujours zéro erreur de verdict avec le moteur factice et avec `Windows.Media.Ocr`. Calibrage définitif en recette (TM-08) ;
- `docs/calibrage.md` ne contient plus les messages de MuPDF (environ 130 lignes « MuPDF error » dues aux PDF réparés du jeu) : `tests/calibrage.py` les coupe ;
- correctif PyMuPDF4LLM : s'il n'est pas appliqué (version différente), le journal l'inscrit en avertissement et `ocr-md verifier` l'affiche (ligne « [!] Correctifs ») sans changer le code de retour ; test ajouté ;
- rapport : test qu'un rapport aux colonnes d'une version précédente n'est pas relu (fichiers retraités, rapport réécrit) ;
- lexique : déjà chargé à la première recherche d'un mot seulement ; test qu'un lot de PDF natifs ne le charge pas. La mémoire de départ plus haute du test de lot vient de ce que ce lot est fait de pages scannées, qui l'utilisent.

Tests : 171 réussis, 6 sautés sous Windows (fr-FR).
