# Plan de réalisation de ocr-md v1

## Contexte

Le dépôt `C:\dev\gie-novea\ocr-md` ne contient encore que `CLAUDE.md`, `.gitignore` et `docs/cahier-des-charges.md` (v1.0 du 26/11/2026). Aucun commit. Il s'agit de construire la v1 (section 8.1 : EX-01 à EX-82 sauf EX-54 à EX-56). Le développement se fait sur ce PC Windows 11. Il n'y a pas de Mac dans la session : tout ce qui dépend d'Apple Vision sera écrit, testé avec le moteur factice, puis validé par le référent.

Ce que j'ai constaté sur le poste (lecture seule) :
- uv 0.11.21 dans le profil, Python 3.12.10 présent ;
- `pdftotext` disponible (Poppler livré avec Git pour Windows), utilisable pour les critères d'acceptation EX-30 et EX-40 ;
- `OcrEngine.AvailableRecognizerLanguages` renvoie `fr-FR` et `en-US` sous compte standard, et `MaxImageDimension` vaut 10000 (PV-03 et une partie de PV-04 déjà levés pour ce poste).

Les arrêts obligatoires de CLAUDE.md sont repris : arrêt A après ce plan, arrêt B après les essais de faisabilité, arrêt C en fin de v1. Chaque jalon se termine par des tests verts, une mise à jour de `docs/avancement.md` et un commit en français.

## Jalon 0 : essais de faisabilité des points bloquants (aucun code de l'outil)

Les essais vivent dans `essais/pv-xx/` (scripts courts et isolés, hors paquet) ; leurs PDF d'entrée sont fabriqués par le script lui-même, à partir de texte synthétique. Un seul environnement `uv` jetable par essai (`uv run --with ...`), Python 3.12. Résultats consignés dans `docs/avancement.md` et `docs/verifications.md` (résultat, date, versions, décision).

### 0.1 PV-05 : `ocr_function`, point d'entrée et texte invisible
1. Installer la dernière version de PyMuPDF et de PyMuPDF4LLM ; relever les versions et constater (e) : `pymupdf4llm` est-il un paquet vide, `Document.to_markdown` existe-t-il, faut-il importer `pymupdf.layout` (a).
2. Lire le code source livré : greffon RapidOCR (`ocr/rapidocr_api.py` ou équivalent) et la fonction qui décide d'appeler l'OCR, pour établir (b) les conditions d'appel d'une `ocr_function` fournie, (d) le rôle de `pixmap`, `dpi`, `keep_ocr_text` et l'unité des coordonnées.
3. Fabriquer un PDF de 3 pages : page native, page-image avec calque invisible déjà posé (mode de rendu 3, texte connu), page-image sans texte.
4. Appeler `to_markdown(page_chunks=True, ocr_function=f_instrumentée)` : vérifier (c) que le texte invisible de la page 2 est repris, compter les appels de `f` (attendu : 0 pour les pages 1 et 2), observer ce qui se passe pour la page 3, tester `ignore_alpha` et `force_text`, et `use_ocr=False`.
5. Vérifier que l'appel n'essaie jamais Tesseract (aucun binaire installé ; capture des avertissements).
- Décision attendue : point d'entrée retenu, paramètres d'appel figés, ou bascule sur le repli de PV-05 (Markdown simple assemblé depuis le calque pour les pages reconnues).

### 0.2 PV-06 : calque invisible avec police Unicode
1. Choisir une police libre couvrant le français, œ, €, guillemets français, apostrophe typographique (proposition : Noto Sans, licence OFL ; alternative DejaVu Sans).
2. Rendre une page de texte de référence en image 300 dpi avec légère rotation, poser un calque ligne par ligne avec `insert_text(render_mode=3, fontfile=...)`, taille déduite de la hauteur de boîte, étirement horizontal calculé par `get_text_length` (`morph`) ; variante mot par mot sans étirement.
3. Contrôles : (d) `pdftotext` restitue tous les caractères ; `page.search_for` trouve des mots de référence dont le centre tombe dans la boîte agrandie de 10 % ; (c) pages avec `rotation` 90 et 270 et `cropbox` décalée ; (e) poids du fichier avant et après `subset_fonts()` ; rendu à 100 dpi identique avant et après ; flux image identique octet pour octet.
4. Contrôle visuel en mode de rendu 0 rouge, image PNG produite dans le dossier de l'essai.
5. Convention Vision (b) : non testable ici, simple conversion écrite et testée avec boîtes normalisées simulées, à confirmer sur Mac.
- Décision attendue : stratégie ligne ou mot, police retenue, fonction de conversion de repère.

### 0.3 PV-04 : OCR Windows par `winrt-Windows.Media.Ocr`
1. Installer `winrt-Windows.Media.Ocr` et dresser la liste minimale des paquets `winrt-*` nécessaires (runtime, Foundation, Globalization, Graphics.Imaging, Storage.Streams).
2. Convertir une image Pillow en `SoftwareBitmap` (via `DataWriter` / `InMemoryRandomAccessStream` ou `SoftwareBitmap.create_copy_from_buffer`), créer le moteur par `TryCreateFromLanguage(Language("fr-FR"))`, reconnaître la page rendue de l'essai 0.2.
3. Relever : texte, lignes, mots, `BoundingRect` (pixels, origine haut gauche), `TextAngle` sur la page inclinée, durée par page, respect de `MaxImageDimension` (page A0 simulée), appel asynchrone depuis un script synchrone (asyncio), fonctionnement lancé par `pythonw` (sans console).
4. Taux de mots de référence retrouvés (objectif 95 % de la section 7.3) et bout en bout : OCR Windows, calque de 0.2, Markdown de 0.1.
5. Même essai avec `winocr` pour comparaison, seulement si la projection pose problème.
- Décision attendue : bibliothèque retenue et liste figée des dépendances Windows.

### 0.4 Autres PV levables sur ce poste, dans le même jalon (courts)
- PV-11 : `tkinter` dans le Python 3.12 géré par uv (fenêtre minimale, lancée par `pythonw`).
- PV-13 : `find_tables()` sur un tableau fusionné natif et scanné, et sortie `table_output="html"`.
- PV-12 : choix de la source du lexique (piste : dictionnaire Hunspell fr de Grammalecte, MPL 2.0, ou Lexique 3, CC BY-SA 4.0), taille, temps de chargement.
- PV-02 partie Windows : création d'un `.lnk` dans SendTo depuis Python sans droits, transmission de 30 et 200 fichiers (à tester à la main par vous).
- PV-09 : script de diagnostic des attributs de fichier, à faire tourner par vous sur un dossier kDrive synthétique.
- Hors d'atteinte ici : PV-01 (poste SODEB), PV-08 et partie macOS de PV-02 et PV-06 (Mac), PV-10 (kDrive en charge). Notés « à lever par le référent ».

Livrables du jalon : `essais/`, `docs/verifications.md`, `docs/avancement.md`. Commit « Jalon 0 : essais de faisabilité ». **Arrêt B.**

## Jalons de la v1 (ordre de REC-07, ajusté aux résultats du jalon 0)

| Jalon | Contenu | Exigences principales |
|---|---|---|
| 1 | Squelette : `pyproject.toml` (Python 3.12, marqueurs `sys_platform`, script graphique `ocr-mdw`), `uv.lock`, `src/ocr_md/`, `config` TOML, `cli` complète avec codes de retour, `--qualite` renvoyant 2, CHANGELOG avec « Reprise de l'existant », LICENSE AGPL-3.0, marqueur pytest `exigence`, test réseau neutralisé | EX-01, 07, 09 à 12, 67, 03 |
| 2 | Générateur du jeu de test (`tests/donnees/generer.py`, graine fixe, manifeste) et moteur factice instrumenté | EX-74, 24 (compteur) |
| 3 | Inventaire, signature des fichiers, exclusions, dossier miroir `_OCR`, nommage, relance, écritures atomiques, rapport CSV, journal sans texte, robustesse lot | EX-05, 14, 18 à 21, 50 à 53, 60, 61, 62, 63, 64, 65, 66, 82 |
| 4 | Analyse des pages, calque invisible, PDF consultable, métadonnées, images vers PDF, PDF temporaire | EX-22, 23, 28 à 34, 59 |
| 5 | Moteurs natifs : `ocr/windows` (testé réel ici), `ocr/macos` (testé factice, réel par le référent), aiguillage, `verifier` et indisponibilité du moteur | EX-25 à 27, 71, 08 |
| 6 | Markdown PDF : appel figé au jalon 0, repères de page, en-têtes, tableaux auto/md/html | EX-40 à 44 |
| 7 | Qualité : heuristiques, confiance, lexique, `--refaire-ocr` et `--pages`, front matter, schéma JSON, avertissements, `_AVERTISSEMENTS.md`, cohérence des six emplacements, `tests/calibrage.py` | EX-35 à 39, 46 à 49, 76 |
| 8 | Office : .docx, .xlsx, .pptx (bibliothèque choisie selon EX-01 et REC-05) | EX-45 |
| 9 | Interface tkinter (ou repli), raccourcis SendTo et Actions rapides, scripts d'installation, mise à jour, désinstallation | EX-02, 13, 15 à 17, 68 à 70, 72, 73 |
| 10 | Performance (`tests/perf/lot_type.py`), guides utilisateur et administrateur, `docs/specification-front-matter.md`, `docs/recette-manuelle.md`, `LICENCES-TIERCES.md` généré, `TRACABILITE.md` généré, test messages du code / guide | EX-57, 58, 75, 77 à 81 |

Un commit par jalon ; `docs/avancement.md` mis à jour à chaque fois. **Arrêt C** en fin de jalon 10, avant toute recette sur poste réel.

## Vérification

- Essais : chaque script de `essais/` s'exécute seul et affiche un verdict chiffré (caractères restitués, mots trouvés, appels OCR, durées).
- v1 : `uv run pytest` vert sur ce PC (niveaux 1 et 2 Windows) ; niveau 1 seul attendu sur Linux et niveau 2 macOS à faire tourner par le référent ; traitement complet du jeu de test en code de retour 1 avec sources inchangées (EX-05) ; fiches TM-01 à TM-10 livrées pour la recette.

## Questions sur le cahier des charges

**À trancher avant le jalon 1**
1. EX-01 (obligatoire) : le code de l'outil existant de conversion en Markdown (PC) est-il disponible ? Si oui, où ?
2. Un Mac (Apple Silicon, éventuellement Intel) sera-t-il accessible pour lever PV-06 (b), PV-08 et tester `ocr/macos`, ou tout le volet macOS est-il validé uniquement par le référent en recette ?
3. Suivi : CLAUDE.md demande `docs/avancement.md`, le cahier demande `docs/verifications.md` pour les PV. Je propose de tenir les deux (détail technique des PV dans `verifications.md`, synthèse et renvoi dans `avancement.md`). D'accord ?
4. Les prototypes `essais/` sont-ils à versionner dans le dépôt (ma proposition, hors paquet) ou à garder hors dépôt ?

**Divergences internes au cahier**
5. Section 11.1 : « les chaînes sont entre guillemets doubles », mais les exemples 11.7 écrivent `type_source: pdf` et `qualite_texte: bonne` sans guillemets. Lequel fait foi ? (Proposition : guillemets partout, sauf si le socle des skills compare déjà la forme brute.)
6. EX-23 : un PDF dont toutes les pages sont `couche_existante` et de bonne qualité aurait le statut `natif` (« aucune page reconnue par l'outil »), alors que `origine_texte` indique une couche OCR de l'expéditeur. Est-ce voulu, ou faut-il un statut distinct ?
7. EX-82, exemple de ligne CSV : le champ `pdf` n'est pas entre guillemets alors que `chemin_relatif` l'est ; je comprends que seuls les champs contenant `;`, `"` ou saut de ligne sont mis entre guillemets, mais l'exemple met aussi entre guillemets `origine_texte` sans `;`. Règle stricte, ou guillemets systématiques sur les champs texte ?
8. REC-07 et section 8.1 placent la levée des PV dans `docs/verifications.md` avant le jeu de test ; or les essais ont besoin de PDF synthétiques. Je les fabrique dans chaque essai, puis le vrai générateur arrive au jalon 2. Acceptable ?
9. EX-41 : une page `image` où le moteur ne trouve rien et qui est douteuse (`aucun_texte_reconnu`) cumule-t-elle le repère douteux et la ligne `*(page sans texte exploitable)*` ? (Proposition : oui, les deux.)

**Décisions de distribution et de licence**
10. EX-69 et EX-78 : source de distribution (wheel à côté du script, ou dépôt Git) et adresse publique du code source à afficher dans `ocr-md --version` (obligation AGPL). Un dépôt existe-t-il déjà (GitHub, Infomaniak) ?
11. EX-78 : la licence AGPL-3.0 du projet est-elle confirmée par le commanditaire ?
12. Police embarquée : Noto Sans (OFL) vous convient-elle ? Lexique : une licence CC BY-SA 4.0 (Lexique 3) ou MPL 2.0 (Grammalecte) est-elle acceptable pour la distribution aux membres ?
13. EX-45 : à défaut de code existant, préférez-vous MarkItDown (une dépendance, rendu moins maîtrisé, accès aux fusions incertain) ou le trio `python-docx`, `openpyxl`, `python-pptx` (plus de code, contrôle des repères et des fusions) ? Je recommande le trio.

**Points de recette à organiser de votre côté**
14. Accès à un PC SODEB sous compte standard (PV-01 : stratégie d'exécution PowerShell, AppLocker) et liste des versions de macOS du parc (PV-08 d).
15. Un dossier kDrive de test en Lite Sync, avec fichiers synthétiques uniquement, pour PV-09 et PV-10.

## Réponses du commanditaire (26/11/2026)

1. Outil existant : réponse à compléter (le message contenait encore le gabarit « [chemin, ou introuvable] »). Sans effet sur le jalon 0 ; à trancher avant le jalon 1.
2. Pas de Mac. Une CI GitHub Actions (macOS et Windows) exécutant les tests, y compris l'OCR Apple Vision réel sur macOS, est mise en place dès le jalon 1. Le reste du volet macOS est validé en recette à la SODEB.
3. Deux fichiers : `docs/avancement.md` renvoie à `docs/verifications.md` sans le dupliquer.
4. Les essais sont versionnés dans `essais/`, hors paquet.
5. Front matter : chaînes libres entre guillemets, valeurs énumérées sans guillemets. Section 11.1 du cahier corrigée.
6. Nouveau statut `couche_expediteur`, distinct de `natif` (EX-23, EX-82, section 11.2 corrigés). Pas de bloc d'avertissement si la couche est jugée bonne.
7. CSV : guillemets seulement si nécessaire (`QUOTE_MINIMAL`). Exemple du cahier corrigé.
8. Les fonctions de fabrication des essais seront reprises par le générateur du jalon 2.
9. Page douteuse sans texte : repère douteux et ligne « page sans texte exploitable ». EX-41 précisé.
10. Source de distribution : réponse à compléter (choix entre dépôt public github.com/gie-novea/ocr-md et wheel sur partage kDrive). À trancher avant le jalon 9.
11. AGPL-3.0 confirmée.
12. Noto Sans (OFL) acceptée ; lexique sous CC BY-SA 4.0 ou MPL 2.0, au mieux de la couverture du français ; licences dans l'inventaire.
13. Office : `python-docx`, `openpyxl`, `python-pptx`.
14. PC SODEB et versions de macOS : réponse à compléter. En attendant, les tests « compte standard » se font sur un compte local du PC de développement.
15. Un dossier kDrive de test dédié sera fourni avec une exception limitée dans CLAUDE.md et settings.json. Rien d'autre n'est lu sous F:\.
