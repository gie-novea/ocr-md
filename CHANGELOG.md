# Journal des modifications

## [Non publié] : vers 1.0.0

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
- PyMuPDF, pymupdf4llm et pymupdf-layout figés en 1.28.2 (au lieu de 2.x), onnxruntime en 1.23.2, pour conserver le Mac Intel.
- Voir `docs/avancement.md`, rubriques « Écarts au cahier des charges » de chaque jalon.

### Recommandations non suivies
- Aucune à ce jour.
