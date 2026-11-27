# Journal des modifications

## [1.0.0rc2] : en préparation, après la recette du 27/11/2026

Seconde version candidate, non étiquetée : l'étiquette `v1.0.0-rc2` sera créée après le retour de la vérité terrain du commanditaire et le recalibrage des seuils. Les scripts d'installation et les guides désignent encore `v1.0.0-rc1`.

### Ajouts
- Archives .zip (EX-83) : extraction dans un dossier de travail du profil, jamais dans la source ; sorties dans `_OCR/…/nom.zip/…` ; garde-fous (taille décompressée bornée par `archive_taille_max_mo`, un niveau d'imbrication, noms cp850 sans indicateur UTF-8, chemins neutralisés, archives et fichiers chiffrés signalés `non_pris_en_charge`) ; fichier 22 du jeu de test.
- Classeurs .xlsm, lus comme des .xlsx (macros ignorées, jamais exécutées) ; fichier 8b du jeu de test.
- PDF que MuPDF juge endommagé : récupération des pages par pypdf avant de conclure à l'erreur (motif `pdf_repare`).
- Information secondaire `qualite_image` (`bonne` ou `mediocre`) au front matter et en colonne du rapport (17 colonnes).
- `tests/recalibrage.py` : gabarit CSV de vérité terrain prérempli depuis le journal, recalibrage des seuils de l'image et du texte sur ce gabarit ; gabarit vide `docs/gabarit-verite-terrain.csv`.
- `tests/perf/ventiler.py` : ventilation du temps de conversion d'un PDF par étape.

### Corrections
- Règle de `qualite_image` : l'image seule ne rend une page douteuse qu'en dessous de 120 dpi (`image_resolution_severe_dpi`) ; une image médiocre ne le fait qu'avec un texte reconnu limite (`mots_inconnus_limite_windows` 0,10, `mots_inconnus_limite_vision` 0,055) ; résolution médiocre sous 200 dpi au lieu de 250. En recette, l'image seule signalait 494 pages sur 700 à tort.
- Fenêtre de fin et journal à la relance : les fichiers signalés et en erreur sont comptés d'après le rapport, y compris les fichiers ignorés car à jour.
- Tableaux natifs : détection par la méthode classique de PyMuPDF, sans relancer le modèle de mise en page déjà appliqué par PyMuPDF4LLM (environ 40 % de temps en moins sur un document riche en tableaux, mêmes tableaux sur le jeu de test).
- Lanceurs Windows : `PSModulePath` vidé avant d'appeler Windows PowerShell, pour que l'installation fonctionne aussi lancée depuis PowerShell 7.

### Écarts au cahier des charges
Aucun : le cahier est mis à jour (EX-16, EX-18, EX-19, EX-21, EX-35, EX-76, EX-82, EX-83, section 7.1, section 11.1).

## [1.0.0rc1] : 27/11/2026, version candidate pour la recette

Version candidate (étiquette `v1.0.0-rc1`, publiée en « pre-release »). La version 1.0.0 suivra la recette et le recalibrage des seuils (TM-08).

### Ajouts
- Jalon 1 : squelette du paquet (`pyproject.toml`, Python 3.12, lanceur sans console `ocr-mdw`), paramètres réglables par fichier TOML, ligne de commande en français avec codes de retour, interface des moteurs OCR et moteurs Windows (`Windows.Media.Ocr`) et macOS (Apple Vision), lexique français embarqué (Grammalecte 7.7, MPL 2.0), tests automatisés, intégration continue GitHub Actions (Windows, macOS Apple Silicon et Intel, Linux).
- Jalon 2 : générateur du jeu de test synthétique et de son manifeste (`tests/donnees/generer.py`), moteur OCR factice instrumenté (`ocr/factice.py`), tests des moteurs réels sur le jeu généré ; équivalence des ligatures typographiques (ﬁ, ﬂ...) dans les comparaisons.
- Jalon 3 : inventaire des entrées, contrôle des signatures, dossier miroir `_OCR`, nommage, règle de relance, écritures atomiques, rapport `ocr_rapport.csv`, journal, contrôles d'ouverture des PDF, annulation et robustesse du lot.
- Jalon 4 : classification des pages, OCR des seules pages-images, calque texte invisible (police Noto Sans embarquée), PDF consultable et métadonnées d'avertissement, conversion des images en PDF, PDF temporaire en sortie Markdown seule, PDF réparés partiellement récupérables, mémoire constante sur les gros documents.
- Jalon 5 : moteurs OCR natifs vérifiés de bout en bout, code de retour 3 lorsque le moteur OCR manque et qu'aucun fichier n'a pu être traité, mémoire rendue entre les fichiers d'un lot, CI Windows en deux passes (en-US à chaque envoi, fr-FR la nuit).
- Jalon 6 : Markdown des PDF et des images par PyMuPDF4LLM, repères de page, en-têtes et pieds conservés, tableaux fusionnés en HTML, repère des tableaux reconnus par OCR, repli en texte simple pour les pages reconnues mal restituées par la bibliothèque, boîtes par mot avec Apple Vision (PV-14).
- Avant le jalon 7 : correctif PyMuPDF4LLM isolé et testé, ticket préparé, ventilation du temps par page, colonne `pages_texte_simple` du rapport.
- Jalon 7 : évaluation de la qualité par page, seuils calibrés, reprise d'OCR (`--refaire-ocr`, `--pages`), front matter et schéma JSON, bloc d'avertissement, `_AVERTISSEMENTS.md`, reconstruction des PDF réparés, conversion plus rapide de l'image transmise à Vision.
- Avant le jalon 8 : seuils de qualité revenus aux valeurs du cahier (calibrage définitif en recette), correctif PyMuPDF4LLM non appliqué signalé au journal et par `verifier`.
- Jalon 8 : Markdown des fichiers .docx, .xlsx et .pptx (titres, listes, tableaux fusionnés, notes de bas de page, zones de texte, révisions en état final et commentaires signalés, valeurs en cache des classeurs et formules non calculées, feuilles et diapositives masquées, commentaires du présentateur) ; colonne `revisions_commentaires` du rapport ; message propre aux fichiers Office protégés par mot de passe.
- Après le jalon 8 : seuils de mots inconnus par origine du texte (couche existante, Windows, Vision), fichier 21 de pages moyennement dégradées, correction linguistique de Vision désactivée (PV-15).
- Jalon 9 : fenêtre de progression et de fin (tkinter) avec annulation, raccourcis « Envoyer vers » et Actions rapides du Finder, contrôle des raccourcis par `verifier`, vérification au premier lancement, signalement des sélections proches de la limite de la ligne de commande Windows, scripts d’installation, de mise à jour et de désinstallation, essai de ces scripts en CI.

### Reprise de l'existant
- Le code de l'outil existant (« Convertisseur MD », PC) a été fourni et lu. Aucun fichier n'en est copié et l'outil livré n'en dépend pas. Éléments de logique repris :
  - test d'écriture réel d'un dossier (sous Windows, `os.access` ignore les ACL) : `plateforme.dossier_inscriptible` ;
  - reconfiguration des flux en UTF-8 au démarrage ;
  - `defusedxml` déclaré pour protéger `openpyxl` des fichiers .xlsx piégés ;
  - lecture des .xlsx en valeurs calculées et en lecture seule, structure de conversion des .pptx (titres, niveaux de puces, tableaux, notes du présentateur) : repris au jalon 8 (`markdown_office`).
- Non repris, car contraires au cahier des charges : installation par droits d'administrateur, Tesseract, OCRmyPDF, pandoc, Ghostscript, écriture à côté de la source, repli sur le Bureau.
- Les mesures de sécurité de l'outil existant qui concernent un lanceur `.bat` (injection par nom de fichier) sont sans objet : les raccourcis d'ocr-md ciblent directement le lanceur `ocr-mdw.exe`, sans interpréteur de commandes.

### Écarts au cahier des charges
Tous décidés ou validés par le commanditaire et reportés dans le cahier ; détail par jalon dans `docs/avancement.md`.
- PyMuPDF, pymupdf4llm et pymupdf-layout figés en 1.28.2 (au lieu de 2.x), onnxruntime en 1.23.2, pour conserver le Mac Intel.
- Jeu de test : fichiers 6b, 13b, 18, 19, 20 et 21 ajoutés au tableau de la section 7.1.
- Tableaux : HTML des tableaux natifs fusionnés produit par l'outil (le rendu HTML de PyMuPDF4LLM perd les fusions) ; repère « tableau reconnu par OCR » sur les pages reconnues.
- Statut `couche_expediteur` ; PDF réparé partiellement récupérable traité et signalé (motif `pdf_repare`) ; relance d'un fichier qui passe en erreur ; code de retour 3 seulement si aucun fichier n'a pu être traité faute de moteur.
- Seuils de qualité : mots inconnus propres à l'origine du texte et limités à la dégradation grossière ; nouvel indicateur `qualite_image` (motif `image_faible_qualite`) pour la dégradation moyenne ; netteté mesurée par la part de gris du trait et non par la variance du laplacien, qui ne sépare pas les pages du jeu ; seuil de contraste limité à la dégradation grossière.
- Apple Vision : correction linguistique désactivée (PV-15) ; boîtes par mot obtenues de Vision (PV-14).
- Fichiers Office : mention des révisions et commentaires, colonne `revisions_commentaires` (rapport à 16 colonnes), message des fichiers Office protégés par mot de passe, valeurs des classeurs en écriture française.
- Distribution : archive de la version publiée sur GitHub (étiquette v1.0.0), installée par uv sans Git, au lieu de l'adresse Git ; installation macOS principale par une ligne à coller dans le Terminal.
- Guide utilisateur macOS : la ligne d'installation est la seconde commande admise, avec l'encadré « Refaire l'OCR » (EX-79).

### Recommandations non suivies
- REC-04 (quatrième entrée de menu « Refaire l'OCR des pages douteuses ») : non réalisée, hors du périmètre décidé ; la commande est donnée par le guide et par `_AVERTISSEMENTS.md`.
- REC-06 (OCR en parallèle) : `processus` borné à 1 en v1 ; le débit mesuré sur le lot type (231 pages par minute sous Windows) ne le justifie pas.
