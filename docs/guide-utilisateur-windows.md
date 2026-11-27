# ocr-md sous Windows : rendre lisibles les pièces d'un pli

**Installer (une fois).** Télécharger l'archive de l'outil indiquée par le référent, l'extraire, puis double-cliquer sur `installation\installer-windows.cmd`. Attendre le message « Installation terminée ». Si Windows affiche un avertissement de sécurité, choisir « Exécuter quand même ».

**Lancer.** Dans l'Explorateur, clic droit sur un dossier (de préférence le dossier du pli entier), ou sur un ou plusieurs fichiers, puis « Envoyer vers » (sous Windows 11 : d'abord « Afficher d'autres options »), puis l'une des trois entrées :

[CAPTURE : menu clic droit de l'Explorateur sous Windows 11, « Afficher d'autres options » ouvert, sous-menu « Envoyer vers » montrant les trois entrées « OCR - … »]

- **OCR - Rendre lisible (PDF)** : un PDF où le texte se sélectionne et se cherche ;
- **OCR - Convertir en Markdown** : un fichier texte pour une IA comme Claude ;
- **OCR - Les deux** : les deux à la fois (conseillé).

Une fenêtre montre le fichier et la page en cours ; « Annuler » arrête proprement après la page en cours.

[CAPTURE : fenêtre de progression, « Fichier 3 sur 12 : … », page en cours, bouton « Annuler »]

**Où sont les résultats.** Dans un dossier `_OCR` créé à côté du dossier traité, qui reprend son arborescence. Les originaux ne sont jamais modifiés. Relancer l'outil ne retraite que les fichiers nouveaux ou modifiés.

**La fenêtre de fin** donne le nombre de fichiers traités, signalés, en erreur et déjà à jour, et un bouton « Ouvrir le dossier ». Elle reste ouverte tant qu'il y a quelque chose à lire.

[CAPTURE : fenêtre de fin avec des fichiers signalés et le bouton « Ouvrir le dossier »]

**Lire `_AVERTISSEMENTS.md` en premier** (à la racine de `_OCR`). Il liste :

- les **pièces douteuses** : le texte de certaines pages peut être faux (scan de mauvaise qualité, tampon, photocopie). Ne citer aucun montant, aucune date ni aucun nom de ces pages sans le vérifier sur l'original ;
- les **pièces non converties** (ancien format Word ou Excel, courriel…) : les ouvrir et les enregistrer en .docx, .xlsx ou PDF, puis relancer ;
- les **pièces en erreur** (PDF protégé par mot de passe, fichier endommagé, fichier kDrive non synchronisé…) : suivre la consigne indiquée, puis relancer.

[CAPTURE : fichier `_AVERTISSEMENTS.md` ouvert, rubrique « Pièces dont le texte est douteux »]

**Que donner à Claude.** Le Markdown (ou, à défaut, le PDF consultable) de chaque pièce utile, et **toujours** `_AVERTISSEMENTS.md` : il dit à Claude quelles pages vérifier.

> **Refaire l'OCR des pages douteuses** (facultatif, si une pièce importante est signalée). Ouvrir le Terminal Windows et taper, en remplaçant le chemin par celui de la pièce d'origine :
> `ocr-md --refaire-ocr "C:\chemin\vers\la pièce.pdf"`
