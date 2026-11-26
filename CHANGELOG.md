# Journal des modifications

## [Non publié] : vers 1.0.0

### Ajouts
- Jalon 1 : squelette du paquet (`pyproject.toml`, Python 3.12, lanceur sans console `ocr-mdw`), paramètres réglables par fichier TOML, ligne de commande en français avec codes de retour, interface des moteurs OCR et moteurs Windows (`Windows.Media.Ocr`) et macOS (Apple Vision), lexique français embarqué (Grammalecte 7.7, MPL 2.0), tests automatisés, intégration continue GitHub Actions (Windows, macOS Apple Silicon et Intel, Linux).

### Reprise de l'existant
- Le code de l'outil existant (« Convertisseur MD », PC) a été fourni et lu. Aucun fichier n'en est copié et l'outil livré n'en dépend pas. Éléments de logique repris :
  - test d'écriture réel d'un dossier (sous Windows, `os.access` ignore les ACL) : `plateforme.dossier_inscriptible` ;
  - reconfiguration des flux en UTF-8 au démarrage ;
  - `defusedxml` déclaré pour protéger `openpyxl` des fichiers .xlsx piégés ;
  - à reprendre au jalon 8 : lecture des .xlsx en valeurs calculées et en lecture seule, structure de conversion des .pptx (titres, niveaux de puces, tableaux, notes du présentateur).
- Non repris, car contraires au cahier des charges : installation par droits d'administrateur, Tesseract, OCRmyPDF, pandoc, Ghostscript, écriture à côté de la source, repli sur le Bureau.
- Les mesures de sécurité de l'outil existant qui concernent un lanceur `.bat` (injection par nom de fichier) sont sans objet : les raccourcis d'ocr-md ciblent directement le lanceur `ocr-mdw.exe`, sans interpréteur de commandes.

### Écarts au cahier des charges
- Voir `docs/avancement.md`, rubriques « Écarts au cahier des charges » de chaque jalon.

### Recommandations non suivies
- Aucune à ce jour.
