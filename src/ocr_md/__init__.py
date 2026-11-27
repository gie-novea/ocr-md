"""ocr-md : rend lisibles les PDF scannés et produit un Markdown annoté pour l'analyse par IA.

Copyright (C) 2026 GIE NOVEA. Logiciel libre sous licence GNU AGPL-3.0 (fichier LICENSE).
"""

__version__ = "1.0.0rc2"

# Version des règles (EX-52, décision du commanditaire du 27/11/2026) : incrémentée à chaque
# changement de verdict ou de format de sortie. Inscrite au rapport et au front matter ; un
# fichier dont la ligne du rapport porte une autre version est retraité à la relance. Un
# changement de version de l'outil sans changement des règles ne déclenche rien.
#   1 : version 1.0.0rc1 ;
#   2 : rc2 : règle de qualite_image (image médiocre et texte limite), champ et colonne
#       qualite_image, repère de page d'image médiocre, colonne et champ version_regles,
#       archives .zip, .xlsm, récupération par pypdf.
VERSION_REGLES = 2

LICENCE = "GNU AGPL-3.0"
# Adresse du code source correspondant à la version installée (EX-78) : dépôt public, dont
# l'archive de l'étiquette de la version est la source de distribution (décision du jalon 9).
ADRESSE_CODE_SOURCE = "https://github.com/gie-novea/ocr-md"
