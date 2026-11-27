# ocr-md sous macOS : rendre lisibles les pièces d'un pli

**Installer (une fois).** Ouvrir le Terminal (Applications, puis Utilitaires), coller la ligne transmise par le référent, appuyer sur Entrée et attendre le message « Installation terminée » :

`cd /tmp && curl -LsSf https://github.com/gie-novea/ocr-md/archive/refs/tags/v1.0.0.zip -o ocr-md.zip && unzip -oq ocr-md.zip && bash ocr-md-1.0.0/installation/installer-macos.command`

En secours : double-cliquer sur `installation/installer-macos.command` dans l'archive extraite ; si macOS refuse (« développeur non identifié »), faire clic droit sur le fichier, puis « Ouvrir », puis « Ouvrir ».

**Lancer.** Dans le Finder, clic droit sur un dossier (de préférence le dossier du pli entier), ou sur un ou plusieurs fichiers, puis « Actions rapides », puis l'une des trois entrées :

[CAPTURE : menu clic droit du Finder, sous-menu « Actions rapides » montrant les trois entrées « OCR - … »]

- **OCR - Rendre lisible (PDF)** : un PDF où le texte se sélectionne et se cherche ;
- **OCR - Convertir en Markdown** : un fichier texte pour une IA comme Claude ;
- **OCR - Les deux** : les deux à la fois (conseillé).

Au premier traitement d'un dossier, macOS peut demander l'autorisation d'y accéder : l'accepter. Une fenêtre montre le fichier et la page en cours ; « Annuler » arrête proprement après la page en cours.

[CAPTURE : fenêtre de progression, « Fichier 3 sur 12 : … », page en cours, bouton « Annuler »]

**Où sont les résultats.** Dans un dossier `_OCR` créé à côté du dossier traité, qui reprend son arborescence. Les originaux ne sont jamais modifiés. Relancer l'outil ne retraite que les fichiers nouveaux ou modifiés.

**La fenêtre de fin** donne le nombre de fichiers traités, signalés, en erreur et déjà à jour, et un bouton « Ouvrir le dossier ». Elle reste ouverte tant qu'il y a quelque chose à lire.

[CAPTURE : fenêtre de fin avec des fichiers signalés et le bouton « Ouvrir le dossier »]

**Lire `_AVERTISSEMENTS.md` en premier** (à la racine de `_OCR`). Il liste les **pièces douteuses** (texte de certaines pages peut-être faux : ne citer aucun montant, aucune date ni aucun nom de ces pages sans vérifier l'original), les **pièces non converties** (à enregistrer en .docx, .xlsx ou PDF, puis relancer) et les **pièces en erreur** (suivre la consigne indiquée, puis relancer).

[CAPTURE : fichier `_AVERTISSEMENTS.md` ouvert dans Aperçu ou TextEdit, rubrique « Pièces dont le texte est douteux »]

**Que donner à Claude.** Le Markdown (ou, à défaut, le PDF consultable) de chaque pièce utile, et **toujours** `_AVERTISSEMENTS.md` : il dit à Claude quelles pages vérifier.

> **Refaire l'OCR des pages douteuses** (facultatif, si une pièce importante est signalée). Dans le Terminal, taper `ocr-md --refaire-ocr ` (avec l'espace final), glisser la pièce d'origine dans la fenêtre, puis appuyer sur Entrée.
