# Cahier des charges : outil « OCR + Markdown » pour Mac et PC

| | |
|---|---|
| Commanditaire | GIE NOVEA (Besançon) |
| Premier utilisateur | SODEB (parc mixte Mac et PC Windows) |
| Destinataire du document | Claude Code, qui développe l'outil à partir de ce seul document |
| Version du cahier des charges | 1.0 du 26 novembre 2026 |
| Nom de travail de l'outil | `ocr-md` (proposition du rédacteur ; le nom peut être changé sans incidence sur les exigences) |

## Conventions de lecture

- **Exigence** : formulée avec « doit », numérotée `EX-nn`, suivie d'un critère d'acceptation (CA) vérifiable. Toutes les exigences sont obligatoires pour la phase indiquée en section 8.
- **Recommandation** : formulée avec « devrait », numérotée `REC-nn`. Claude Code peut s'en écarter en le justifiant dans le CHANGELOG.
- **Point à vérifier** : introduit par « À VÉRIFIER », numéroté `PV-nn`, détaillé en section 10 avec la méthode de vérification et le plan de repli. Un fait technique non vérifié n'est jamais une base de conception sans repli.
- **Proposition du rédacteur** : choix qui ne figure pas dans les décisions du commanditaire et que le rédacteur a dû arrêter pour rendre le document exécutable. Ces choix sont signalés par la mention « (proposition) ». Ils sont récapitulés en annexe B.
- **Objectif** : valeur cible de performance ou de qualité, non mesurée à ce jour, à confirmer en recette. Aucun chiffre de performance de ce document n'est un fait établi.
- Les sources web ont été consultées le 26 novembre 2026. Les URL sont citées au fil du texte et regroupées en annexe A.

Claude Code n'a accès ni aux échanges préparatoires ni aux personnes qui les ont menés. En cas de contradiction ou de lacune, il applique dans l'ordre : les exigences, puis les recommandations, puis le choix le plus prudent pour la confidentialité et l'intégrité des originaux, et il consigne sa décision dans le CHANGELOG.

---

## 1. Objet, périmètre, hors périmètre

### 1.1 Objet

Les équipes des membres du GIE NOVEA reçoivent en masse des PDF de tiers : plis de candidatures et d'offres de marchés publics, pièces de dossiers d'aménagement, actes. Une partie de ces PDF est scannée et ne contient aucune couche texte. Claude (claude.ai, Cowork, skills) lit mal ou pas du tout ces documents. La documentation d'Anthropic indique que Claude analyse le texte et les éléments visuels des PDF de 100 pages ou moins, et le texte seul de 101 à 1 000 pages ; les fichiers de projet sont limités à 30 Mo (source : https://support.claude.com/en/articles/8241126-upload-files-to-claude). Au-delà de 100 pages, un PDF sans couche texte est donc inexploitable.

L'outil à développer est un utilitaire de bureau, lancé depuis le menu contextuel de l'Explorateur Windows ou du Finder, qui :

1. analyse chaque PDF page par page (texte natif ou image) ;
2. reconnaît le texte des seules pages-images, une seule fois, avec le moteur OCR du système d'exploitation ;
3. produit, au choix, un PDF consultable (image d'origine et calque texte invisible), un Markdown tiré de ce PDF consultable, ou les deux ;
4. convertit aussi en Markdown les fichiers .docx, .xlsx et .pptx, et traite les images JPEG, PNG et TIFF ;
5. signale les textes de qualité douteuse d'une manière qu'une IA relisant les sorties comprend sans avoir lu le rapport ;
6. produit un rapport de traitement exploitable dans Excel.

### 1.2 Périmètre

- Postes macOS et Windows 10/11, sans droits d'administrateur.
- Traitement local, hors ligne, de fichiers confidentiels.
- Usage aval : les sorties sont données à Claude et aux skills d'analyse `analyse-candidatures-pi` et `analyse-offres-pi`, qui citent leurs constats à la page. Le socle commun de ces skills extrait déjà le texte avec `pdftotext` quand une couche texte existe ; le PDF consultable doit donc être lisible par `pdftotext`, et le front matter des Markdown sera lu par ce socle (champ `qualite_texte` notamment).

### 1.3 Hors périmètre

- Conversion des anciens formats Office (.doc, .xls, .ppt, .pps), des e-mails (.eml, .msg) et de tout autre format : ces fichiers sont **signalés** dans le rapport, jamais convertis, jamais ignorés en silence.
- PDF consultable pour les fichiers .docx, .xlsx, .pptx (Markdown uniquement pour ces formats).
- Correction manuelle de l'OCR, interface d'édition, reconnaissance d'écriture manuscrite garantie.
- Tout traitement serveur, tout envoi de document vers un service externe.
- Linux comme plateforme d'exécution pour les utilisateurs (Linux n'est utilisé que pour les tests automatisés avec un moteur OCR factice, voir section 7).

### 1.4 Alternatives écartées

Les options suivantes ont été examinées et écartées par le commanditaire ; elles ne doivent pas être réintroduites : page web fondée sur Tesseract.js, Stirling-PDF, chaîne serveur n8n, exécutable empaqueté, Tesseract installé sur le système, conversion des anciens formats Office.

### 1.5 Code existant

Un outil de conversion de fichiers en Markdown a déjà été réalisé par Claude Code, pour PC uniquement.

**EX-01. Demande du code existant.** Avant de commencer le développement, Claude Code doit demander à l'utilisateur si le code de l'outil existant de conversion en Markdown est disponible. S'il l'est, Claude Code en reprend la logique utile (conversion des formats Office, gestion des chemins Windows, création des raccourcis) après lecture ; s'il ne l'est pas, le développement se poursuit sans lui. L'outil livré ne doit dépendre d'aucun élément de l'outil existant à l'exécution.
- CA : le CHANGELOG de la version 1.0.0 contient une rubrique « Reprise de l'existant » indiquant si le code a été fourni et, le cas échéant, quels éléments ont été repris ; le dépôt s'installe et passe ses tests sans l'outil existant.

---

## 2. Utilisateurs et contraintes

### 2.1 Utilisateurs

- **Utilisateurs finaux** : chargés d'opérations, assistantes, juristes et acheteurs des SEM et SPL membres. Non développeurs. Ils ne voient jamais de terminal en usage courant.
- **Référent d'installation** : une personne par structure (ou le GIE NOVEA), capable de lancer un script d'installation et de lire un message d'erreur, sans droits d'administrateur.
- **Lecteurs aval** : Claude et les skills d'analyse, qui lisent les sorties sans contexte.

### 2.2 Contraintes

**EX-02. Aucun droit d'administrateur.** L'installation, l'exécution, la mise à jour et la désinstallation de l'outil doivent se faire intégralement dans le profil de l'utilisateur, sans élévation de privilèges, sur macOS et sur Windows 10/11.
- CA : les scripts d'installation, de mise à jour et de désinstallation s'exécutent jusqu'au bout sous un compte standard sans qu'aucune invite d'élévation (UAC, mot de passe administrateur macOS) n'apparaisse ; aucune écriture hors du profil utilisateur (vérifié par relecture des scripts et par le test manuel TM-01).

**EX-03. Confidentialité et absence de télémétrie.** L'outil ne doit émettre aucune requête réseau pendant un traitement, n'envoyer aucun document ni extrait vers un service externe, et ne contenir aucune télémétrie. Les seules connexions admises sont celles de l'installation et de la mise à jour (téléchargement de `uv`, de Python, des paquets) et, pour le mode qualité, le téléchargement initial des modèles (section 4.12).
- CA : un test automatisé exécute un traitement complet du jeu de test avec le réseau neutralisé (connexions sortantes bloquées par un correctif du module `socket`) et réussit ; une recherche dans le code et dans la configuration des dépendances ne montre aucune option de télémétrie active ; le guide administrateur liste exhaustivement les connexions faites à l'installation.

**EX-04. Fonctionnement hors ligne.** Après installation, toutes les fonctions de la v1 doivent fonctionner sans connexion réseau.
- CA : test manuel TM-06 (poste déconnecté du réseau) réussi sur Mac et sur PC.

**EX-05. Intégrité des originaux.** L'outil ne doit jamais modifier, renommer, déplacer ni supprimer un fichier source, et ne doit jamais écrire dans un dossier source. Les fichiers sources sont ouverts en lecture seule.
- CA : un test automatisé calcule l'empreinte SHA-256, la taille et la date de modification de tous les fichiers du jeu de test avant et après un traitement complet (y compris avec `--refaire-ocr` et `--forcer`) et constate qu'elles sont identiques ; aucun fichier nouveau n'apparaît dans les dossiers sources.

**EX-06. Deux plateformes, un seul code.** L'outil doit fonctionner sur macOS et sur Windows 10/11 à partir d'un dépôt unique ; les différences de plateforme sont isolées dans des modules d'aiguillage (section 3.3).
- CA : le même paquet s'installe sur les deux plateformes ; les dépendances propres à une plateforme sont déclarées avec des marqueurs d'environnement (`sys_platform`) ; les tests automatisés passent sur les deux.

---

## 3. Architecture

### 3.1 Principe : le PDF consultable est le pivot

Le commanditaire a arrêté deux décisions qui structurent l'architecture : l'OCR n'est fait **qu'une seule fois**, et le Markdown est produit **à partir du PDF consultable**, pour garantir la cohérence entre les deux sorties. Il a aussi arrêté que le moteur OCR du système est branché sur PyMuPDF4LLM par son paramètre `ocr_function`.

La documentation de PyMuPDF décrit le contrat d'une fonction OCR personnalisée : signature `exec_ocr(page, dpi=300, pixmap=None, language="eng", keep_ocr_text=False)` ; la fonction reconnaît le texte et **l'inscrit sur la page** du document, que PyMuPDF interprète ensuite normalement (source : https://pymupdf.readthedocs.io/en/latest/ocr/index.html). Ce contrat est exactement l'opération qui fabrique le PDF consultable. L'architecture retenue les réunit :

- un **adaptateur OCR natif** unique, conforme à la signature de `ocr_function`, reconnaît une page avec le moteur du système et écrit le calque texte invisible sur cette page ;
- l'outil applique lui-même cet adaptateur aux pages-images pour fabriquer le PDF consultable (étape 3 ci-dessous) ;
- le Markdown est ensuite produit par PyMuPDF4LLM à partir du PDF consultable, en lui passant le même adaptateur comme `ocr_function`. L'adaptateur tient un registre des pages déjà reconnues et ne refait rien pour elles : si PyMuPDF4LLM estime qu'une page doit encore être reconnue, c'est le moteur du système qui est appelé, jamais Tesseract ni un autre moteur.

Cette lecture conjointe des deux décisions est une interprétation du rédacteur (annexe B, point 1).

### 3.2 Chaîne de traitement

```
 Sélection (fichiers, dossiers)            Explorateur "Envoyer vers" / Finder "Actions rapides"
        |
        v
 [1] Inventaire récursif  ---->  formats non pris en charge : ligne de rapport, pas de conversion
        |
        +--> .docx .xlsx .pptx ------------------------------------------+
        |                                                                |
        +--> JPEG PNG TIFF --> [2b] assemblage en PDF image (1 page      |
        |                           par image ou par trame TIFF)         |
        v                                 |                              |
 [2] PDF : analyse page par page  <-------+                              |
     (native / image / couche OCR existante / vide)                      |
        |                                                                |
        v                                                                |
 [3] OCR natif des seules pages-images (une fois)                        |
     macOS : Apple Vision      Windows : Windows.Media.Ocr               |
     + écriture du calque texte invisible                                |
        |                                                                |
        v                                                                |
 [4] Évaluation de la qualité du texte, page par page                    |
     (couche existante : heuristique ; OCR de l'outil : confiance        |
      du moteur si disponible, sinon heuristique)                        |
        |                                                                |
        v                                                                v
 [5] PDF consultable (pivot, métadonnées d'avertissement)      [6b] Conversion Office
        |                                                           vers Markdown
        v                                                                |
 [6] Markdown depuis le PDF consultable                                  |
     (PyMuPDF4LLM par défaut ; Docling en mode qualité, v1.1)            |
        |                                                                |
        +----------------------------+-----------------------------------+
                                     v
 [7] Assemblage : front matter, avertissements, repères de page
                                     |
                                     v
 [8] Écriture dans le dossier miroir _OCR ; ocr_rapport.csv ; _AVERTISSEMENTS.md ; journal
                                     |
                                     v
 [9] Fenêtre ou notification de fin (traités, signalés, en erreur, emplacement)
```

Lorsque seule la sortie Markdown est demandée, le PDF consultable est fabriqué dans un dossier temporaire du profil utilisateur, sert de source au Markdown, puis est supprimé (EX-28).

### 3.3 Modules

| Module (noms indicatifs) | Rôle |
|---|---|
| `cli` | Analyse des arguments, sous-commandes, codes de retour |
| `inventaire` | Parcours récursif, classement par type, regroupement par dossier parent, exclusions |
| `analyse_pdf` | Classification des pages (native, image, couche existante, vide) |
| `ocr/base` | Interface commune du moteur OCR : entrée image, sortie liste de lignes ou de mots avec boîte englobante et confiance éventuelle |
| `ocr/macos` | Moteur Apple Vision |
| `ocr/windows` | Moteur `Windows.Media.Ocr` |
| `ocr/factice` | Moteur de test, déterministe, sans dépendance système |
| `calque` | Écriture du calque texte invisible ; adaptateur conforme à `ocr_function` |
| `qualite` | Heuristiques de texte douteux, seuils, lexique |
| `markdown_pdf` | Conversion PDF vers Markdown (PyMuPDF4LLM ; Docling en v1.1), règle des tableaux |
| `markdown_office` | Conversion .docx, .xlsx, .pptx |
| `images` | Assemblage des images en PDF image |
| `sorties` | Dossier miroir, nommage, règle de relance, écritures atomiques |
| `avertissements` | Front matter, blocs d'avertissement, repères, `_AVERTISSEMENTS.md`, métadonnées PDF |
| `rapport` | `ocr_rapport.csv`, journal |
| `interface` | Fenêtre de progression et de fin, notifications |
| `plateforme` | Création et suppression des raccourcis, vérification des prérequis, détection des fichiers non synchronisés |
| `config` | Paramètres par défaut, fichier de configuration utilisateur |

**EX-07. Aiguillage par plateforme.** Le choix du moteur OCR et des mécanismes d'intégration (raccourcis, notifications) doit se faire à l'exécution selon la plateforme, derrière une interface commune. Aucun module commun ne doit importer inconditionnellement une bibliothèque propre à une plateforme.
- CA : l'import du paquet et l'exécution de la suite de tests avec le moteur factice réussissent sur macOS, Windows et Linux ; les imports de bibliothèques propres à macOS ou à Windows sont localisés dans `ocr/macos`, `ocr/windows` et `plateforme`.

**EX-08. Aucun moteur OCR tiers en v1.** En v1, l'outil ne doit appeler aucun autre moteur OCR que celui du système (Apple Vision, `Windows.Media.Ocr`). Il ne doit ni exiger ni utiliser Tesseract, même s'il est présent sur le poste.
- CA : le paquet v1 ne déclare aucune dépendance à Tesseract, RapidOCR, EasyOCR ou opencv ; un test vérifie que la conversion Markdown d'un PDF scanné n'appelle que l'adaptateur natif (moteur factice instrumenté, compteur d'appels) ; les appels à PyMuPDF4LLM sont faits avec `ocr_function` renseigné ou `use_ocr=False`, jamais avec le moteur par défaut.

### 3.4 Version de Python et dépendances principales

**EX-09. Version de Python figée.** L'outil doit cibler **Python 3.12**, installé et géré par `uv` dans le profil utilisateur, indépendamment de tout Python du système. Justification : la projection `winrt-Windows.Media.Ocr` exige Python 3.11 ou plus (source : https://pypi.org/project/winrt-windows-media-ocr) ; sur Mac Intel, Docling impose PyTorch 2.2.2, qui limite à Python 3.12 au plus (source : https://docling-project.github.io/docling/getting_started/installation/).
- CA : `pyproject.toml` déclare `requires-python = ">=3.12,<3.13"` ; les scripts d'installation passent `--python 3.12` à `uv`.

**EX-10. Versions des dépendances verrouillées.** Toutes les dépendances doivent être verrouillées (fichier `uv.lock` versionné) ; la version de PyMuPDF et de PyMuPDF4LLM effectivement utilisée est consignée dans le guide administrateur et inscrite dans le front matter (`moteur_md`).
- CA : `uv.lock` est présent ; l'installation depuis le dépôt reproduit les mêmes versions sur deux postes ; `ocr-md --version` affiche la version de l'outil, de PyMuPDF, de PyMuPDF4LLM et du moteur OCR.

Dépendances pressenties pour la v1 : PyMuPDF et PyMuPDF4LLM (AGPL), Pillow (images, TIFF multipage), `ocrmac` sur macOS, `winrt-Windows.Media.Ocr` et les paquets `winrt-*` associés sur Windows (voir PV-04), une bibliothèque de conversion Office (voir 4.9). À VÉRIFIER (PV-05) : la documentation en ligne indique que, depuis PyMuPDF 2.0, le cœur de PyMuPDF4LLM est intégré à PyMuPDF (`Document.to_markdown()`) et que le paquet `pymupdf4llm` devient un paquet vide requis par PyMuPDF 2.x (sources : https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/api.html ; https://github.com/pymupdf/pymupdf4llm), alors que les éléments préparatoires citaient un README « version 1.28.x ». Claude Code doit constater la situation réelle au moment du développement et s'y adapter ; les exigences de ce document valent quel que soit le point d'entrée (`pymupdf4llm.to_markdown` ou `Document.to_markdown`).

---

## 4. Exigences fonctionnelles

### 4.1 Lancement et ligne de commande

**EX-11. Commande unique.** L'outil doit exposer une seule commande, `ocr-md`, avec l'interface suivante :

```
ocr-md [OPTIONS] CHEMIN [CHEMIN ...]

  --sortie pdf|md|les-deux     sortie demandée (défaut : les-deux)
  --refaire-ocr[=PORTEE]       refaire l'OCR : douteuses (défaut si l'option est
                               donnée sans valeur) | tout
  --pages LISTE                pages visées par --refaire-ocr, numérotées à partir
                               de 1, par exemple 3,4,9-12 ; admis seulement si un
                               seul fichier PDF est passé en entrée
  --qualite                    mode qualité (Docling), v1.1
  --forcer                     retraiter même si les sorties sont à jour
  --tableaux auto|md|html      rendu des tableaux (défaut : auto)
  --sans-interface             aucun affichage graphique ; progression sur la
                               sortie standard
  --config FICHIER             fichier de paramètres (seuils, résolution)
  --version, --aide

Sous-commandes :
  ocr-md verifier              vérifie les prérequis et affiche un diagnostic
  ocr-md raccourcis --creer | --supprimer
```

- CA : `ocr-md --aide` affiche cette interface en français ; chaque option fait l'objet d'au moins un test automatisé ; une option inconnue ou une combinaison invalide (par exemple `--pages` avec deux fichiers) produit un message en français et un code de retour 2 sans rien traiter.

**EX-12. Codes de retour.** La commande doit renvoyer : 0 si tous les fichiers pris en charge ont été traités sans erreur (y compris s'il existe des pièces signalées douteuses ou non prises en charge) ; 1 si au moins un fichier est en erreur ; 2 en cas d'erreur d'usage ; 3 si un prérequis bloquant manque : le moteur OCR est indisponible et **aucun** fichier pris en charge n'a pu être traité faute de moteur ; si d'autres fichiers ont été traités, le code est 1 (voir EX-71) (décision du commanditaire du 26/11/2026).
- CA : tests automatisés des quatre cas.

**EX-13. Trois entrées de menu par plateforme.** L'installation doit créer trois entrées, qui appellent la commande unique avec `--sortie pdf`, `--sortie md` et `--sortie les-deux` :
- Windows, dans le dossier « Envoyer vers » du profil (`%APPDATA%\Microsoft\Windows\SendTo`) : « Rendre lisible (PDF) », « Convertir en Markdown », « Les deux » ;
- macOS, sous forme d'Actions rapides du Finder dans la bibliothèque de l'utilisateur : mêmes libellés.

Afin que les trois entrées restent groupées et identifiables dans des menus qui en contiennent d'autres, les libellés devraient être préfixés de façon identique, par exemple « OCR - Rendre lisible (PDF) », « OCR - Convertir en Markdown », « OCR - Les deux » (REC-01, proposition).
- CA : après installation, les trois entrées sont visibles par clic droit sur un fichier, sur plusieurs fichiers et sur un dossier ; chacune lance la commande avec la bonne valeur de `--sortie` (vérifié dans le journal) ; test manuel TM-02.

**EX-14. Entrées multiples et récursivité.** La commande doit accepter un ou plusieurs fichiers et un ou plusieurs dossiers, mélangés ; les dossiers sont parcourus récursivement. Les dossiers nommés `_OCR`, les fichiers cachés, les fichiers temporaires d'Office (préfixe `~$`), `.DS_Store`, `Thumbs.db` et `desktop.ini` sont exclus du parcours et ne figurent pas au rapport.
- CA : test automatisé avec une arborescence à trois niveaux contenant un dossier `_OCR` issu d'un traitement précédent : aucun fichier de `_OCR` n'est retraité ; tous les autres fichiers apparaissent une fois et une seule dans le rapport.

**EX-15. Raccourcis sans fenêtre de console.** Lancé depuis un raccourci, l'outil ne doit pas ouvrir de fenêtre de terminal. Sous Windows, le raccourci cible un point d'entrée graphique (exécutable de lancement sans console généré à l'installation du paquet) ; sous macOS, l'Action rapide exécute un script shell qui appelle la commande par son chemin absolu.
- CA : tests manuels TM-02 : aucune fenêtre de console n'apparaît ; seule la fenêtre de progression de l'outil est visible.

### 4.2 Retour visuel

**EX-16. Fenêtre de fin.** À la fin de chaque lancement par raccourci, l'outil doit afficher une fenêtre (ou, à défaut, une notification du système) indiquant : le nombre de fichiers traités, le nombre de fichiers signalés (douteux ou non pris en charge), le nombre de fichiers en erreur, le nombre de fichiers ignorés car à jour, et l'emplacement du ou des dossiers `_OCR`, avec un bouton « Ouvrir le dossier ». La fenêtre de fin ne se ferme pas seule lorsqu'il existe des fichiers signalés ou en erreur.
- CA : test manuel TM-03 ; les nombres affichés sont égaux à ceux calculés depuis `ocr_rapport.csv`.

**EX-17. Progression.** Pendant le traitement, l'outil doit afficher la progression : fichier en cours, rang du fichier sur le total, page en cours pendant l'OCR. Un bouton « Annuler » arrête proprement le lot après la page en cours : les sorties achevées sont conservées, aucune sortie partielle ne subsiste (EX-53), le rapport mentionne les fichiers non traités.
- CA : test manuel TM-03 sur un lot de 20 fichiers ; test automatisé de l'annulation (signal d'arrêt injecté) vérifiant l'absence de fichier partiel et la cohérence du rapport.

**REC-02.** L'interface devrait être réalisée avec `tkinter` (bibliothèque standard) pour ne rien ajouter aux dépendances. À VÉRIFIER (PV-11) : disponibilité de `tkinter` dans le Python installé par `uv` sur les deux plateformes. Repli : notification du système en fin de traitement (macOS : `osascript -e 'display notification ...'` ; Windows : notification par l'API WinRT déjà présente pour l'OCR) et progression dans un fichier `_OCR/_EN_COURS.txt` mis à jour à chaque fichier.

### 4.3 Formats d'entrée

**EX-18. Formats pris en charge.** L'outil doit traiter :

| Type | Extensions (insensibles à la casse) | PDF consultable | Markdown |
|---|---|---|---|
| PDF | .pdf | oui | oui |
| Image | .jpg, .jpeg, .png, .tif, .tiff (TIFF multipage compris) | oui | oui |
| Office | .docx, .xlsx, .pptx | non | oui |

Le type est déterminé par l'extension puis confirmé par la signature du fichier (premiers octets) ; en cas de désaccord (par exemple un .pdf qui n'en est pas un), le fichier est mis en `erreur` avec un message explicite.
- CA : un test par extension, dont une extension en majuscules et un TIFF de trois pages ; un faux PDF (fichier texte renommé) est signalé en `erreur` avec le message « le contenu du fichier ne correspond pas à son extension ».

**EX-19. Formats non pris en charge, signalés.** Tout fichier d'un autre format doit donner lieu à une ligne du rapport avec le statut `non_pris_en_charge` et un message adapté :
- .doc, .xls, .ppt, .pps : « ancien format Office : l'enregistrer au format .docx, .xlsx ou .pptx, ou en PDF, puis relancer » ;
- .eml, .msg : « e-mail non pris en charge : enregistrer les pièces jointes et les traiter séparément » ;
- autres : « format non pris en charge ».
Ces fichiers sont comptés dans les « signalés » de la fenêtre de fin et listés dans `_AVERTISSEMENTS.md` (section « Pièces non converties »), afin qu'une IA sache que le dossier `_OCR` est incomplet.
- CA : test automatisé avec un .doc, un .msg et un .zip : trois lignes `non_pris_en_charge`, aucun fichier de sortie, mention dans `_AVERTISSEMENTS.md`, code de retour 0.

**EX-20. Sortie demandée sans objet.** Lorsque la sortie demandée est `pdf` et que le fichier est un .docx, .xlsx ou .pptx, l'outil ne doit rien produire pour ce fichier et l'indiquer au rapport (statut `natif`, colonne `sorties` vide, message « pas de PDF consultable pour ce format : utiliser Convertir en Markdown »). Ce cas est compté dans les « signalés ».
- CA : test automatisé.

**EX-21. PDF protégés, endommagés ou signés.** Un PDF chiffré exigeant un mot de passe à l'ouverture, ou illisible, doit être mis en `erreur` avec un message clair (« PDF protégé par mot de passe », « PDF endommagé ») sans arrêter le lot. Un PDF portant une signature électronique est traité normalement ; le message du rapport précise « la copie produite dans _OCR ne conserve pas la validité de la signature ; l'original signé reste la référence ».

**PDF réparé à l'ouverture** (décision du commanditaire du 26/11/2026). Un PDF endommagé que la bibliothèque répare à l'ouverture est traité ainsi : si aucune page ne contient plus de contenu (texte, image ou dessin), le fichier est en `erreur` avec le message « PDF endommagé » ; si au moins une page est récupérée, le fichier est traité normalement mais signalé : statut `douteux`, toutes ses pages dans `pages_douteuses` (le contenu peut être incomplet partout), motif `pdf_repare`, champs `pages_recuperees` et `pages_totales` du front matter (section 11.1), paragraphe C du bloc d'avertissement (section 11.3), mention dans `_AVERTISSEMENTS.md`, et message du rapport : « PDF endommagé et réparé : N pages sur M récupérées, contenu possiblement incomplet » (N : pages ayant un contenu, M : pages du document réparé). Le jeu de test comporte un PDF tronqué partiellement récupérable (fichier 13b).
- CA : tests automatisés avec un PDF chiffré, un PDF tronqué irrécupérable (`erreur`) et un PDF tronqué partiellement récupérable (`douteux`, motif `pdf_repare`, message du rapport conforme) ; À VÉRIFIER par Claude Code : la détection d'une signature avec PyMuPDF (champs de signature) ; à défaut, le message est omis et la limite est documentée dans le guide.

### 4.4 Analyse des PDF page par page

**EX-22. Classification des pages.** Chaque page de PDF doit être classée dans l'une des catégories suivantes, à partir de paramètres réglables :

| Catégorie | Critère par défaut | Traitement |
|---|---|---|
| `native` | texte extractible d'au moins `texte_min_caracteres` caractères hors espaces (défaut : 30), provenant majoritairement de texte visible | pas d'OCR |
| `couche_existante` | texte extractible suffisant, mais majoritairement en mode de rendu invisible, ou superposé à une image couvrant au moins `image_couverture_min` de la page (défaut : 0,80) | pas d'OCR d'office ; évaluation de qualité (4.7) |
| `image` | texte extractible inférieur à `texte_min_caracteres` et présence d'une ou plusieurs images couvrant au moins `image_presence_min` de la page (défaut : 0,30) | OCR natif |
| `vide` | ni texte suffisant, ni image significative | pas d'OCR ; page conservée |

Une page `native` qui contient en outre une grande image (tampon, plan, photographie) reste `native` : elle n'est pas reconnue en v1 (limite documentée dans le guide).

**Cas des mentions ajoutées par les plateformes (ajout de la relecture).** Les plis téléchargés sur un profil d'acheteur, ou les pièces transmises par certains outils, portent souvent sur une page scannée une mention en texte natif visible ajoutée après coup (horodatage de dépôt, numéro de pli, filigrane, pied de page de la plateforme). Une telle page ne doit être classée ni `native` ni `couche_existante` du seul fait de cette mention. Règle : lorsqu'une image couvre au moins `image_couverture_min` de la page et que le texte extractible, rapporté à la surface de la page, est inférieur à `densite_texte_ajoute_max` (défaut : 0,5 caractère par cm², valeur de départ à calibrer), la page est classée `image` ; l'OCR est appliqué et le texte natif existant est conservé tel quel à côté du calque. Le jeu de test (7.1) comporte un PDF scanné portant une mention d'horodatage en texte natif.
- CA complémentaire : sur ce PDF de test, chaque page est classée `image`, reconnue par l'outil, et la mention d'horodatage figure une seule fois dans le Markdown de la page.
- CA : sur le jeu de test, la classification de chaque page est égale à la vérité terrain du manifeste (section 7.1) ; les trois seuils sont modifiables par le fichier de configuration et un test le démontre.

**EX-23. Statut du document.** Le statut du fichier dans le rapport doit être déduit des pages : `natif` (aucune page reconnue par l'outil), `ocrise` (toutes les pages non vides ont été reconnues par l'outil), `mixte` (une partie seulement), `couche_expediteur` (au moins une page dont le texte provient d'une couche OCR fournie par l'expéditeur et conservée, quelles que soient les autres pages ; ce statut prime sur `natif`, `ocrise` et `mixte`), `douteux` (au moins une page douteuse, quel que soit le reste, y compris un PDF réparé à l'ouverture, voir EX-21 ; ce statut prime sur les quatre précédents). Justification (décision du commanditaire du 26/11/2026) : l'heuristique lexicale ne détecte pas les erreurs sur les chiffres, une couche OCR d'expéditeur n'a donc jamais la fiabilité d'un texte natif ; une telle couche jugée bonne ne donne pas lieu à bloc d'avertissement. Les fichiers Office convertis ont le statut `natif`.
- CA : tests automatisés sur les sept statuts (`natif`, `ocrise`, `mixte`, `couche_expediteur`, `douteux`, `non_pris_en_charge`, `erreur`).

### 4.5 OCR natif

**EX-24. Moteur du système, pages-images seulement, une seule fois.** L'OCR doit être appliqué aux seules pages `image` (et aux pages désignées par `--refaire-ocr`), une seule fois par page et par traitement, avec Apple Vision sur macOS et `Windows.Media.Ocr` sur Windows. Le résultat (texte, boîtes englobantes, confiance éventuelle) est conservé en mémoire pour alimenter à la fois le calque, l'évaluation de qualité et le rapport.
- CA : test avec le moteur factice instrumenté : le nombre d'appels au moteur est égal au nombre de pages `image` du lot, quelle que soit la sortie demandée (`pdf`, `md`, `les-deux`).

**EX-25. Langue et résolution.** La langue de reconnaissance par défaut doit être le français (`fr-FR`), avec l'anglais en langue secondaire lorsque le moteur accepte plusieurs langues. La résolution de rendu des pages pour l'OCR est un paramètre (`ocr_dpi`, défaut : 300). Si l'image rendue dépasse la dimension maximale acceptée par le moteur (propriété `OcrEngine.MaxImageDimension` sous Windows, source : https://learn.microsoft.com/en-us/uwp/api/windows.media.ocr.ocrengine), l'outil réduit la résolution de cette page au plus près de la limite et le consigne dans le journal.
- CA : la langue et la résolution figurent dans le journal de chaque traitement ; test avec une page au format A0 simulée : pas d'erreur, résolution réduite journalisée.

**EX-26. Moteur macOS.** Sur macOS, l'outil doit utiliser le framework Vision d'Apple, par la bibliothèque `ocrmac` (enveloppe de `VNRecognizeTextRequest`, macOS 10.15 ou plus, qui renvoie pour chaque élément le texte, une confiance et une boîte englobante ; source : https://pypi.org/project/ocrmac) ou directement par `pyobjc-framework-Vision`. Le niveau de reconnaissance est `accurate`. Le framework `livetext` n'est pas utilisé par défaut : il n'existe que depuis macOS Sonoma et renvoie une confiance toujours égale à 1 (même source), ce qui priverait l'outil de l'indice de confiance exigé par EX-35.
- CA : sur un Mac, le PDF scanné du jeu de test est reconnu ; le journal mentionne « Apple Vision (accurate) » ; `moteur_ocr` du front matter vaut `apple-vision`.

**EX-27. Moteur Windows.** Sur Windows, l'outil doit utiliser `Windows.Media.Ocr`. La bibliothèque d'accès devrait être la projection PyWinRT `winrt-Windows.Media.Ocr` (REC-03), mieux maintenue que `winocr` à la date de rédaction : dernière publication de `winrt-Windows.Media.Ocr` le 31 octobre 2026, Python 3.11 ou plus (source : https://pypi.org/project/winrt-windows-media-ocr) ; dernière publication de `winocr` (0.0.15) le 25 octobre 2024 (source : https://pypi.org/project/winocr). `winocr` reste le repli si la projection pose une difficulté (PV-04). Le moteur est créé pour le français par `OcrEngine.TryCreateFromLanguage` ; s'il est indisponible, l'outil applique EX-71.
- CA : sur un PC disposant du pack OCR français, le PDF scanné du jeu de test est reconnu ; `moteur_ocr` vaut `windows-media-ocr` ; test manuel TM-04 du cas « pack absent ».

**EX-28. PDF temporaire en sortie Markdown seule.** Lorsque la sortie demandée est `md`, le PDF consultable intermédiaire doit être créé dans un dossier temporaire propre à l'outil dans le profil utilisateur, puis supprimé dès le Markdown écrit, y compris en cas d'erreur ou d'annulation. Au démarrage, l'outil supprime les résidus temporaires de ses exécutions précédentes.
- CA : test automatisé : après un traitement `--sortie md` (réussi, en erreur simulée, annulé), le dossier temporaire de l'outil est vide et `_OCR` ne contient aucun PDF.

### 4.6 PDF consultable

**EX-29. Contenu visuel inchangé.** Le PDF consultable doit être une copie du PDF source à laquelle l'outil ajoute, sur les pages reconnues, un calque texte invisible. Le nombre de pages, leur ordre, leurs dimensions, leur rotation et leur rendu visuel sont inchangés. Les images d'origine ne sont ni recompressées ni rééchantillonnées (sauf pages retraitées par `--refaire-ocr`, EX-39).
- CA : pour chaque PDF du jeu de test, le nombre de pages et les dimensions sont identiques ; le rendu à 100 dpi de chaque page avant et après est identique au pixel près (ou avec un écart moyen inférieur à un seuil de tolérance fixé par le test pour l'anticrénelage) ; les flux d'images des pages non retraitées sont identiques octet pour octet.

**EX-30. Calque texte invisible.** Le texte reconnu doit être inscrit avec PyMuPDF en mode de rendu 3 (la documentation indique que, dans ce mode, les glyphes ne sont ni tracés ni remplis et que le texte devient invisible ; source : https://pymupdf.readthedocs.io/en/latest/shape.html), ligne par ligne ou mot par mot, positionné et mis à l'échelle d'après la boîte englobante renvoyée par le moteur, après conversion du repère de l'image vers le repère de la page (échelle liée à `ocr_dpi`, origine, rotation de la page ; attention : Vision renvoie des coordonnées normalisées dont l'origine est à vérifier, voir PV-06). La police employée doit couvrir tous les caractères du français, y compris é è ê ë à â ù û ü ç î ï ô œ æ, les majuscules accentuées, les guillemets français, l'apostrophe typographique et le symbole € : les polices Base 14 intégrées de PyMuPDF (par exemple `helv`) ne couvrent que les caractères jusqu'à Unicode 256 (source : https://pymupdf.readthedocs.io/en/latest/faq/), ce qui exclut œ et € ; l'outil doit donc embarquer et utiliser une police Unicode sous licence libre, déclarée dans l'inventaire des licences.
- CA : sur le PDF scanné du jeu de test, dont le texte de référence contient tous les caractères listés ci-dessus : (a) `pdftotext` appliqué au PDF consultable restitue ces caractères, les équivalences `œ`/`oe`, `æ`/`ae` et `’`/`'` étant admises, car `Windows.Media.Ocr` produit les secondes formes (décision du commanditaire du 26/11/2026, après l'essai PV-04) ; le texte reconnu n'est pas corrigé ; la capacité du calque à restituer œ, æ et ’ est vérifiée séparément, par un test qui écrit ces caractères dans le calque ; (b) `page.search_for()` de PyMuPDF trouve cinq mots de référence par page, et le centre du rectangle trouvé est à l'intérieur de la boîte du mot dans la vérité terrain, agrandie de 10 % ; (c) le rendu visuel est inchangé (EX-29) ; (d) test manuel TM-05 : la recherche et la sélection du texte fonctionnent dans Aperçu (macOS), dans Adobe Acrobat Reader et dans un navigateur.

**EX-31. Pages natives intactes.** Les pages `native` et `couche_existante` non retraitées ne doivent recevoir aucun calque et leur texte existant ne doit pas être altéré.
- CA : sur le PDF mixte du jeu de test, le texte extrait des pages natives est identique avant et après.

**EX-32. PDF sans page à reconnaître.** Lorsque la sortie `pdf` est demandée pour un PDF dont aucune page n'est reconnue et dont aucune page n'est douteuse, l'outil doit copier le fichier à l'identique dans `_OCR` (copie octet pour octet), afin que le dossier `_OCR` soit complet et utilisable seul.
- CA : empreinte SHA-256 de la copie identique à celle de la source.

**EX-33. Métadonnées d'avertissement.** Le PDF consultable d'un document douteux doit porter, sans modification visuelle :
- dans **Sujet** : `TEXTE DOUTEUX pages 3, 4, 9 : ne pas citer ces pages sans vérification sur l'original. ` suivi du sujet d'origine s'il existait ;
- dans **Mots-clés** : `qualite_texte=douteuse; pages_douteuses=3,4,9; origine=<valeur de origine_texte>; ocr-md` suivi des mots-clés d'origine.
Le PDF consultable d'un document reconnu par l'outil et de bonne qualité porte dans **Mots-clés** : `qualite_texte=bonne; pages_ocr=<liste>; moteur_ocr=<moteur>; ocr-md`. Les autres métadonnées d'origine (Titre, Auteur) sont conservées.
- CA : lecture des métadonnées par PyMuPDF et par `pdfinfo` : valeurs conformes sur le document douteux et sur le document sain du jeu de test.

**EX-34. Images.** Une image (ou chaque trame d'un TIFF multipage) doit devenir une page d'un PDF image, aux dimensions physiques déduites de la résolution déclarée dans le fichier (à défaut : 300 dpi, plafonné au format A3 par mise à l'échelle), l'orientation EXIF étant appliquée. Ce PDF suit ensuite la chaîne commune (OCR, calque, Markdown). L'image n'est pas recompressée lorsqu'elle est en JPEG ; les autres formats sont intégrés sans perte.
- CA : un TIFF de trois trames produit un PDF de trois pages et un Markdown de trois repères de page ; un JPEG avec orientation EXIF 6 est redressé.

### 4.7 Qualité du texte : détection et signalement

**EX-35. Évaluation de l'OCR de l'outil.** Pour chaque page reconnue par l'outil, celui-ci doit calculer un verdict `bonne` ou `douteuse` :
- sur macOS, à partir de l'indice de confiance renvoyé par Vision : la page est douteuse si la confiance moyenne pondérée par la longueur du texte est inférieure à `confiance_moyenne_min` (défaut : 0,70) ou si la part du texte dont la confiance est inférieure à `confiance_basse` (défaut : 0,50) dépasse `part_confiance_basse_max` (défaut : 0,20) ;
- sur Windows, `Windows.Media.Ocr` ne fournit pas d'indice de confiance : la classe `OcrWord` n'expose que `Text` et `BoundingRect` (source : https://learn.microsoft.com/en-us/uwp/api/windows.media.ocr.ocrword). L'outil applique donc l'heuristique lexicale de EX-36 au texte qu'il a lui-même produit ;
- sur les deux plateformes, l'heuristique lexicale de EX-36 est appliquée en complément : une page est douteuse si l'un des deux contrôles le dit.
Une page `image` pour laquelle le moteur ne renvoie aucun texte alors qu'elle n'est pas uniformément blanche (écart type des niveaux de gris supérieur à `page_blanche_ecart_type_max`) est marquée douteuse avec le motif `aucun_texte_reconnu`.
- CA : avec le moteur factice renvoyant des confiances imposées, les verdicts suivent les seuils ; sur la page volontairement illisible du jeu de test (flou et bruit forts), le verdict est `douteuse` sur les deux plateformes.

**EX-36. Heuristique de couche texte douteuse.** Pour chaque page `couche_existante` (et pour l'OCR de l'outil, voir EX-35), l'outil doit calculer les indicateurs suivants et déclarer la page douteuse dès qu'un indicateur franchit son seuil. Tous les seuils sont des paramètres du fichier de configuration ; les valeurs par défaut ci-dessous sont des valeurs de départ, à calibrer sur le jeu de test (EX-76), et non des valeurs validées.

| Indicateur | Définition | Seuil par défaut (page douteuse si) |
|---|---|---|
| `taux_mots_inconnus` | parmi les mots de 3 lettres ou plus, entièrement alphabétiques, en minuscules ou à seule initiale majuscule en début de phrase, part des mots absents du lexique (français, plus une liste complémentaire : anglais courant, sigles et vocabulaire des marchés publics). Les mots tout en majuscules, les mots à initiale majuscule en cours de phrase (noms propres, raisons sociales), les nombres, références et adresses électroniques sont exclus du calcul | supérieur à 0,35, si la page compte au moins 40 mots évaluables |
| `taux_caracteres_aberrants` | part des caractères qui sont U+FFFD, des caractères de zones d'usage privé, des caractères de contrôle, ou des lettres hors alphabets latin et grec, parmi les caractères hors espaces | supérieur à 0,03 |
| `taux_mots_fragmentes` | part des « mots » d'une seule lettre (hors a, à, y, ô, et lettres suivies d'une apostrophe) parmi tous les mots | supérieur à 0,25 |
| `taux_melange_chiffres_lettres` | part des mots mêlant chiffres et lettres au milieu du mot (par exemple `mar0hé`, `l1eu`), hors motifs de référence reconnus (lettres puis chiffres, ou chiffres puis unité) | supérieur à 0,10 |
| `densite_anormale` | nombre de caractères extraits rapporté à la surface de la page en cm², comparé à un intervalle plausible | inférieur à 0,2 alors que la page est couverte d'une image contenant visiblement du texte (page non blanche), ou supérieur à 60 |

Avant la recherche dans le lexique, chaque mot est normalisé : `oe` et `œ`, `ae` et `æ`, `'` et `’` sont tenus pour équivalents (les formes `oeuvre`, `coeur` produites par `Windows.Media.Ocr` ne comptent pas comme mots inconnus) (décision du commanditaire du 26/11/2026, après l'essai PV-04). Cette normalisation ne sert qu'au calcul ; le texte n'est pas modifié.

Le verdict, les indicateurs calculés et le motif (nom du ou des indicateurs déclencheurs) sont journalisés et reportés dans la colonne `motif_douteux` du rapport. Les pages de moins de 40 mots évaluables ne sont jugées que sur les indicateurs autres que `taux_mots_inconnus`.
- CA : sur le PDF à couche OCR volontairement dégradée du jeu de test, toutes les pages dégradées sont déclarées douteuses et aucune page saine du jeu de test ne l'est (objectif de départ : aucun faux positif sur le jeu de test ; à confirmer sur documents réels en recette) ; un test démontre que la modification d'un seuil dans le fichier de configuration change le verdict.

**EX-37. Lexique embarqué.** L'outil doit embarquer son lexique (aucun téléchargement à l'exécution), sous une licence compatible avec la distribution du dépôt, citée dans l'inventaire des licences. À VÉRIFIER (PV-12) : choix de la source du lexique français et de sa licence. Le lexique complémentaire (sigles et vocabulaire métier : DC1, DC2, DUME, CCAP, CCTP, DPGF, BPU, SIRET, Kbis, URSSAF, MOE, AMO, OPC, SPS, etc.) est un fichier texte du dépôt, extensible par le fichier de configuration.
- CA : le lexique est chargé depuis le paquet installé, réseau neutralisé ; l'ajout d'un mot dans le fichier de configuration le fait sortir des « mots inconnus ».

**EX-38. Pas d'OCR d'office sur une couche existante.** Un PDF qui possède déjà une couche texte doit la conserver ; l'outil ne refait pas l'OCR de ces pages sans demande explicite, même si elles sont douteuses : il les **signale** (EX-33, EX-41, EX-46 à EX-49).
- CA : sur le PDF à couche dégradée, sans `--refaire-ocr` : zéro appel au moteur OCR pour ces pages ; le texte de la couche d'origine est conservé ; le document a le statut `douteux` et `origine_texte` vaut « couche OCR fournie par l'expéditeur, non refaite ».

**EX-39. Option `--refaire-ocr`.** Avec `--refaire-ocr` (portée `douteuses`, par défaut), l'outil doit refaire l'OCR des pages `couche_existante` déclarées douteuses de tous les PDF passés en entrée. Avec `--refaire-ocr=tout`, il refait l'OCR de toutes les pages `couche_existante` et `image`. Avec `--pages`, il refait l'OCR des pages listées du fichier unique passé en entrée, quelle que soit leur catégorie (y compris `native`). Pour une page retraitée, la couche texte d'origine ne doit pas subsister dans la copie : la page est remplacée, dans le PDF consultable, par son image rendue à `ocr_dpi` (défaut : 300), sur laquelle est écrit le nouveau calque ; l'original n'est pas touché. `--refaire-ocr` implique le retraitement des fichiers concernés même si leurs sorties sont à jour. Après retraitement, la page est réévaluée (EX-35) : elle peut rester douteuse, avec `origine_texte` mis à jour.
- CA : sur le PDF à couche dégradée : après `--refaire-ocr`, `pdftotext` ne restitue plus le texte dégradé d'origine des pages retraitées mais le texte reconnu par l'outil ; le nombre d'appels au moteur est égal au nombre de pages douteuses ; avec `--pages 2`, seule la page 2 est retraitée ; l'original est inchangé (EX-05).

**REC-04 (proposition).** Les trois entrées de menu décidées ne donnent pas accès à `--refaire-ocr`. En v1, cette option est accessible en ligne de commande ; le guide utilisateur donne la commande à copier, et `_AVERTISSEMENTS.md` la rappelle avec les chemins réels. Une quatrième entrée « Refaire l'OCR des pages douteuses » pourrait être ajoutée ultérieurement ; elle n'est pas dans le périmètre décidé et n'est pas à réaliser sans accord du commanditaire.

### 4.8 Markdown issu des PDF

**EX-40. Markdown produit à partir du PDF consultable.** Le Markdown d'un PDF ou d'une image doit être produit à partir du PDF consultable (définitif ou temporaire) et de lui seul, par PyMuPDF4LLM en v1. Aucun texte ne doit provenir d'une autre reconnaissance que celle inscrite dans le PDF consultable. L'appel passe l'adaptateur natif en `ocr_function` (section 3.1) et n'utilise jamais le moteur OCR par défaut de la bibliothèque. À VÉRIFIER (PV-05) : le texte en mode de rendu invisible est bien repris par la conversion Markdown ; la documentation décrit un paramètre `ignore_alpha` et un paramètre `force_text` dont l'effet sur le texte invisible doit être testé.
- CA : pour chaque PDF du jeu de test, l'ensemble des mots du Markdown d'une page (hors balisage) recouvre au moins 98 % des mots restitués par `pdftotext` pour la même page du PDF consultable, et réciproquement (objectif, à ajuster si la mise en forme des tableaux l'explique) ; le compteur d'appels OCR n'augmente pas pendant la conversion Markdown.

**EX-41. Repères de page.** Le texte de chaque page doit être précédé d'un repère sur une ligne isolée : `<!-- page N -->`, où N est le rang de la page dans le fichier, à partir de 1 (numérotation du lecteur PDF, sans rapport avec la pagination imprimée). Toutes les pages ont un repère, y compris les pages vides, dans l'ordre et sans lacune. Pour une page douteuse, le repère est remplacé par : `<!-- page N : TEXTE DOUTEUX, ne pas citer sans vérification sur l'original -->`. Pour une page sans texte, le repère est suivi de la ligne `*(page sans texte exploitable)*` ; une page douteuse sans texte (motif `aucun_texte_reconnu`) reçoit le repère douteux suivi de cette même ligne. La conversion est faite page par page (paramètre `page_chunks=True` de `to_markdown`, qui renvoie un dictionnaire par page ; source : https://pymupdf.readthedocs.io/en/latest/document.html) afin que l'attribution du texte à la page soit certaine ; le séparateur intégré `page_separators` n'est pas utilisé (il numérote à partir de 0 et se place en fin de page, même source).
- CA : pour un PDF de n pages, le Markdown contient exactement n repères, numérotés de 1 à n dans l'ordre, chacun correspondant à l'expression régulière `^<!-- page (\d+)( : TEXTE DOUTEUX, ne pas citer sans vérification sur l'original)? -->$` ; dans le PDF de test dont chaque page porte un mot unique connu, ce mot se trouve entre le repère N et le repère N+1.

**EX-42. En-têtes et pieds de page conservés.** Les en-têtes et pieds de page répétés doivent être conservés dans le Markdown (paramètres `header` et `footer` laissés à `True`), car ils portent souvent le nom du candidat et la pagination imprimée, utiles à la citation.
- CA : sur le PDF natif du jeu de test, le pied de page « Page x sur y » figure dans le Markdown de chaque page.

**EX-43. Images non exportées.** En v1, les images contenues dans les pages ne doivent être ni exportées en fichiers ni incorporées en base64 dans le Markdown (`write_images=False`, `embed_images=False`).
- CA : aucun fichier image dans `_OCR` ; aucune chaîne `data:image` dans les Markdown.

**EX-44. Règle de rendu des tableaux.** Avec `--tableaux auto` (défaut), la règle est la suivante, appliquée page par page :
1. un tableau est rendu en **tableau Markdown** (syntaxe compatible GitHub) lorsqu'il est simple : aucune cellule fusionnée, une seule ligne d'en-tête ;
2. un tableau est rendu en **HTML**, avec attributs `colspan` et `rowspan`, lorsqu'il comporte au moins une cellule fusionnée (horizontalement ou verticalement) ou plusieurs lignes d'en-tête ;
3. si la page contient à la fois des tableaux simples et des tableaux complexes, toute la page est convertie avec le rendu HTML des tableaux.
`--tableaux md` et `--tableaux html` imposent un rendu unique. La détection des cellules fusionnées s'appuie sur l'analyse des tableaux de PyMuPDF (`page.find_tables()`), qui marque les positions couvertes par une fusion (PV-13 : détection fiable sur les tableaux natifs). Le rendu HTML de PyMuPDF4LLM (`table_output="html"`) ne restituant pas les fusions (PV-13), l'outil produit lui-même le HTML des tableaux natifs, à partir des cellules détectées, et le substitue au rendu de la bibliothèque (décision du commanditaire du 26/11/2026).

**Tableaux des pages reconnues par OCR.** Sur une page reconnue par OCR (par l'outil ou par l'expéditeur), les fusions ne sont pas détectables et la correspondance des lignes et des colonnes n'est pas garantie. Tout tableau détecté sur une telle page est précédé, sur une ligne isolée, du repère `<!-- tableau reconnu par OCR : correspondance lignes/colonnes non garantie, vérifier sur l'original avant de citer un montant -->` ; il est rendu selon la règle ci-dessus, sans garantie sur les fusions (décision du commanditaire du 26/11/2026).
- CA : sur le PDF « tableau fusionné » du jeu de test : la page du tableau simple contient un tableau Markdown (lignes commençant par `|`) et aucune balise `<table>` ; la page du tableau fusionné contient une balise `<table>` avec au moins un attribut `colspan` ou `rowspan`, et toutes les valeurs de cellules de la vérité terrain y figurent ; il en va de même pour la DPGF et le cadre de décomposition des honoraires ; sur le fichier 6b (version scannée), chaque tableau détecté est précédé du repère « tableau reconnu par OCR » et aucun tableau d'une page native n'en porte.

### 4.9 Markdown issu des fichiers Office

**EX-45. Conversion .docx, .xlsx, .pptx.** L'outil doit convertir ces formats en Markdown, hors ligne, sans Microsoft Office ni LibreOffice :
- **.docx** : titres (niveaux de titre du document), paragraphes, listes, tableaux, notes de bas de page si la bibliothèque le permet ; pas de repère de page (un .docx n'a pas de pagination fixe) ;
- **.xlsx** : une section par feuille visible, précédée du repère `<!-- feuille N : "Nom de la feuille" -->`, contenu en tableau (valeurs calculées en cache, pas les formules) ; les feuilles masquées sont listées en fin de document sans leur contenu ; au-delà de `xlsx_lignes_max` lignes par feuille (défaut : 2 000), la feuille est tronquée et une ligne d'avertissement l'indique explicitement ;
- **.pptx** : une section par diapositive, précédée du repère `<!-- diapositive N -->`, titre, textes, tableaux, commentaires du présentateur.
Le choix de la bibliothèque est laissé à Claude Code (REC-05 : reprendre celle de l'outil existant si le code est fourni ; sinon une bibliothèque sous licence permissive, par exemple MarkItDown ou le trio `python-docx`, `openpyxl`, `python-pptx` ; licences et capacités à vérifier lors de l'inventaire des licences). Les tableaux suivent la règle de EX-44 lorsque la bibliothèque donne accès aux fusions.
- CA : sur les trois fichiers Office du jeu de test, tous les textes de la vérité terrain figurent dans le Markdown ; les repères de feuille et de diapositive sont présents et numérotés ; le front matter est conforme (section 11) avec `pages: null` pour .docx et .xlsx, et `origine_texte: "texte natif du document"`.

### 4.10 Front matter et avertissements

La spécification complète (schéma, valeurs, exemples) est en section 11. Les exigences sont les suivantes.

**EX-46. Front matter sur tous les Markdown.** Chaque Markdown produit doit commencer par un front matter YAML conforme au schéma de la section 11.1, que le document soit douteux ou non. Le fichier commence par la ligne `---`, sans marque d'ordre d'octets ni ligne vide avant.
- CA : un test valide le front matter de tous les Markdown du jeu de test contre le schéma JSON livré dans le dépôt (`schema/front-matter-v1.json`) après lecture par un analyseur YAML standard ; les champs obligatoires sont tous présents, dans l'ordre spécifié.

**EX-47. Avertissement en tête des Markdown douteux.** Lorsqu'un document comporte au moins une page douteuse, le front matter doit être suivi du bloc d'avertissement en prose à l'impératif défini en section 11.3, adapté à l'origine du texte et listant les pages concernées.
- CA : sur les documents douteux du jeu de test, le bloc est présent immédiatement après le front matter, cite exactement les pages de `pages_douteuses`, et son texte est celui du modèle correspondant à `origine_texte` ; il est absent des documents sains.

**EX-48. Fichier `_AVERTISSEMENTS.md`.** L'outil doit maintenir, à la racine de chaque dossier `_OCR`, un fichier `_AVERTISSEMENTS.md` conforme à la section 11.5, rédigé pour être compris par une IA sans autre contexte : consigne générale, liste des pièces douteuses avec leurs pages et le motif, liste des pièces non converties, liste des pièces en erreur. Le fichier est régénéré à chaque traitement à partir de `ocr_rapport.csv` ; il existe même s'il n'y a rien à signaler (il l'indique alors explicitement), afin que son absence ne soit jamais interprétée comme une absence de problème.
- CA : après traitement du jeu de test, le fichier liste exactement les pièces dont le statut est `douteux`, `non_pris_en_charge` ou `erreur` dans le rapport ; après traitement d'un dossier ne contenant que des documents sains, il contient la phrase « Aucune pièce de ce dossier n'est signalée. ».

**EX-49. Cohérence des trois niveaux.** Pour un même document, la liste des pages douteuses doit être identique dans le front matter, dans le bloc d'avertissement, dans les repères de page, dans les métadonnées du PDF consultable, dans `_AVERTISSEMENTS.md` et dans `ocr_rapport.csv`.
- CA : un test automatisé extrait la liste de ces six emplacements pour chaque document douteux du jeu de test et vérifie leur égalité.

### 4.11 Emplacement des sorties, nommage, relance

**EX-50. Dossier miroir `_OCR`.** Pour chaque élément passé en entrée (fichier ou dossier), les sorties doivent être écrites dans un dossier nommé `_OCR`, créé dans le **dossier parent** de cet élément, donc à côté de lui :
- pour un dossier `…/Parent/Lot 1/` : sorties dans `…/Parent/_OCR/Lot 1/`, en reproduisant l'arborescence (par exemple un sous-dossier par candidat) ;
- pour un fichier `…/Parent/DC2.pdf` : sorties dans `…/Parent/_OCR/`.
Les éléments d'une même sélection qui ont des parents différents donnent chacun lieu à un dossier `_OCR` dans leur parent respectif. Chaque dossier `_OCR` contient son propre `ocr_rapport.csv`, son `_AVERTISSEMENTS.md` et son journal. Les chemins relatifs inscrits dans le rapport et dans le champ `source` sont relatifs au dossier parent (exemple : `Lot 1/Candidat B/DC2.pdf`), avec la barre oblique `/` comme séparateur sur les deux plateformes. Si le dossier parent n'est pas accessible en écriture, l'outil s'arrête pour cet élément avec un message clair et propose, dans la fenêtre de fin, de relancer après avoir copié le dossier dans un emplacement accessible en écriture ; il n'écrit jamais ailleurs de sa propre initiative.
- CA : tests automatisés des deux cas et du cas « parents différents » ; test du dossier parent en lecture seule (code de retour 1, message explicite, aucune écriture ailleurs).

**EX-51. Nommage des sorties.** Les noms de sortie doivent être déterministes et sans collision :
- PDF consultable d'un PDF : même nom que la source (`DC2.pdf`) ;
- PDF consultable d'une image : nom complet de la source suivi de `.pdf` (`scan.tiff.pdf`) ;
- Markdown : nom complet de la source, extension comprise, suivi de `.md` (`DC2.pdf.md`, `Mémoire.docx.md`), de sorte que `DC2.pdf` et `DC2.docx` ne produisent pas le même fichier.
- CA : un dossier de test contenant `A.pdf`, `A.docx`, `A.png` produit `A.pdf`, `A.pdf.md`, `A.docx.md`, `A.png.pdf`, `A.png.md` sans écrasement.

**EX-52. Règle de relance.** Lors d'une relance, un fichier source doit être **ignoré** si toutes les sorties demandées existent et sont plus récentes que la source (date de modification), sauf si `--forcer` ou `--refaire-ocr` le concerne. Sinon, il est retraité et ses sorties sont écrasées. Justification : sur un lot de 50 à 100 plis, la relance après interruption ou après ajout de pièces ne doit retraiter que le nécessaire ; l'écrasement systématique gaspille le temps d'OCR, et le suffixage multiplie des versions concurrentes que les skills d'analyse ne sauraient départager. Un fichier ignoré conserve sa ligne dans le rapport, avec la colonne `action` à `ignore_a_jour`. Une sortie dont la source a disparu n'est pas supprimée ; elle est mentionnée dans le journal.

**Relance d'un fichier qui passe en erreur** (décision du commanditaire du 26/11/2026). Si le retraitement d'un fichier échoue alors que des sorties d'un traitement précédent existent : elles sont supprimées si la source est plus récente qu'elles (elles ne correspondent plus à la source) ; sinon elles sont conservées, la ligne du rapport porte le statut `erreur`, la colonne `sorties` les énumère et le message se termine par « ; sorties précédentes conservées (traitement du AAAA-MM-JJ HH:MM:SS) ».
- CA : deuxième lancement à l'identique : zéro appel au moteur OCR, toutes les lignes en `ignore_a_jour`, sorties inchangées (dates de modification identiques) ; après modification de la date d'une source, seule celle-ci est retraitée ; avec `--forcer`, tout est retraité.

**EX-53. Écritures atomiques.** Chaque sortie doit être écrite sous un nom temporaire dans le dossier de destination, puis renommée en fin d'écriture. Une interruption (erreur, annulation, arrêt du poste) ne doit laisser aucune sortie tronquée portant un nom définitif.
- CA : test avec interruption simulée pendant l'écriture : aucun fichier définitif partiel ; les fichiers temporaires résiduels sont nettoyés au lancement suivant.

### 4.12 Mode qualité (v1.1)

**EX-54. Mode qualité optionnel avec Docling.** En v1.1, l'option `--qualite` doit produire le Markdown avec Docling (`export_to_markdown()`) à partir du **PDF consultable**, au lieu de PyMuPDF4LLM. Docling est une dépendance optionnelle (extra `[qualite]`), installée seulement sur les postes qui le demandent ; son absence ne doit jamais empêcher le fonctionnement normal. Si `--qualite` est demandé sans que l'extra soit installé, l'outil s'arrête avant tout traitement avec un message indiquant la commande d'installation (code de retour 3).
- CA : le paquet v1.1 installé sans l'extra passe tous les tests de la v1 ; `ocr-md --qualite` sans l'extra renvoie 3 avec le message attendu ; avec l'extra, le Markdown est produit, `moteur_md` vaut `docling <version>` et toutes les exigences de front matter, d'avertissement et de repères de page restent satisfaites.

**EX-55. OCR en mode qualité.** En mode qualité, les pages qui possèdent déjà une couche texte dans le PDF consultable ne doivent pas être reconnues une seconde fois si Docling permet de s'en dispenser (OCR de Docling désactivé ou limité aux zones sans texte). Si la qualité de structure exige que Docling refasse sa propre reconnaissance, les moteurs sont : `OcrMacOptions(lang=["fr-FR", "en-US"], recognition="accurate")` sur macOS et RapidOCR (backend onnxruntime, installable par pip) sur Windows (sources : https://docling-project.github.io/docling/concepts/OCR/ ; https://docling-project.github.io/docling/getting_started/installation/). Dans ce cas, le front matter l'indique (`moteur_ocr` reflète le moteur réellement à l'origine du texte du Markdown) et le guide précise que le texte du Markdown peut différer légèrement de celui du PDF consultable. Ce point constitue une tension avec la décision « OCR une seule fois » ; Claude Code doit privilégier la première solution et documenter le résultat de son essai (PV-07).
- CA : sur le PDF scanné du jeu de test en mode qualité, le journal indique quelle solution est appliquée ; le nombre d'appels au moteur natif n'est pas supérieur à celui du mode normal ; les repères de page sont exacts (les numéros de page sont tirés de la structure de Docling, pas d'une estimation).

**EX-56. Modèles du mode qualité.** Les modèles de Docling sont téléchargés automatiquement à la première utilisation par défaut ; ils peuvent être préchargés par `docling-tools models download` et désignés par `artifacts_path` ou par la variable `DOCLING_ARTIFACTS_PATH` (source : https://docling-project.github.io/docling/usage/advanced_options). L'outil doit précharger les modèles lors de l'installation de l'extra (commande `ocr-md verifier --precharger-modeles`), dans un dossier du profil utilisateur, puis exécuter Docling en désignant ce dossier, sans accès réseau à l'exécution et sans activer les services distants (`enable_remote_services` laissé à sa valeur par défaut, fausse).
- CA : après préchargement, un traitement en mode qualité réussit réseau neutralisé ; le guide administrateur indique le poids constaté de l'installation et des modèles, mesuré par Claude Code (PV-07).

---

## 5. Exigences non fonctionnelles

### 5.1 Performance

Aucune mesure n'existe à ce jour. Les valeurs ci-dessous sont des **objectifs**, à confirmer ou à réviser en recette sur un Mac et un PC représentatifs du parc de la SODEB.

**EX-57. Mesure de la performance.** L'outil doit mesurer et consigner, pour chaque fichier, la durée de traitement (colonne `duree_s` du rapport) et, dans le journal, la durée d'OCR par page et le débit global en pages par minute.
- CA : valeurs présentes et cohérentes (la somme des durées par fichier est inférieure ou égale à la durée totale du lot).

**EX-58. Objectif sur un lot type.** Lot type : 50 plis, 500 pages au total, dont 300 pages scannées au format A4 à 300 dpi. Objectifs (à confirmer en recette, non garantis) : traitement complet en sortie `les-deux` en moins de 20 minutes sur un poste représentatif ; relance sans modification en moins de 30 secondes ; mémoire résidente inférieure à 1,5 Go. Si la recette montre que ces objectifs sont inatteignables, les valeurs mesurées sont consignées dans le guide administrateur et soumises au commanditaire.
- CA : un script `tests/perf/lot_type.py` génère le lot type synthétique, le traite et produit un relevé (durée totale, pages par minute, pic mémoire) ; le relevé des deux plateformes est joint au dossier de recette.

**EX-59. Traitement en flux.** L'outil doit traiter les documents page par page sans charger en mémoire l'ensemble des pages rendues d'un document ; un PDF de 1 000 pages doit être traité sans croissance linéaire de la mémoire.
- CA : test sur un PDF synthétique de 1 000 pages scannées simulées (moteur factice) : le pic mémoire ne dépasse pas le double de celui mesuré sur 100 pages.

**REC-06.** L'OCR de plusieurs fichiers devrait pouvoir être parallélisé (paramètre `processus`, défaut : 1 en v1) une fois vérifié que les moteurs natifs le supportent ; à défaut, le traitement reste séquentiel.

### 5.2 Robustesse

**EX-60. Un fichier en erreur n'arrête jamais le lot.** Toute exception survenant pendant le traitement d'un fichier doit être interceptée, journalisée avec sa trace, traduite en une ligne `erreur` du rapport avec un message en français compréhensible, et le traitement doit passer au fichier suivant. Une erreur sur une page d'un PDF met le fichier entier en `erreur` (pas de sortie partielle présentée comme complète).
- CA : le jeu de test contient un PDF corrompu placé au milieu du lot : tous les autres fichiers sont traités ; code de retour 1 ; la ligne `erreur` contient un message non vide ; aucune sortie n'existe pour le fichier en erreur (pour une relance, voir la règle « Relance d'un fichier qui passe en erreur » de EX-52).

**EX-61. Rapport toujours écrit.** Le rapport, `_AVERTISSEMENTS.md` et le journal doivent être mis à jour même si le lot se termine par une erreur générale ou une annulation ; le rapport est réécrit de façon atomique après chaque fichier, de sorte qu'un arrêt brutal laisse un rapport cohérent avec les sorties présentes.
- CA : test d'arrêt brutal simulé après le troisième fichier : le rapport contient trois lignes à jour.

**EX-62. Chemins accentués, espaces, caractères particuliers.** L'outil doit traiter correctement les chemins contenant des espaces, des accents, des apostrophes, des parenthèses, des esperluettes et des caractères Unicode décomposés (forme NFD produite par macOS) ; les noms sont comparés après normalisation NFC, et les sorties reprennent le nom de la source tel quel.
- CA : le jeu de test contient un dossier `Candidat Été & Fils (n° 2)/Mémoire d'été.pdf` en formes NFC et NFD : traitement réussi sur les deux plateformes ; chemins corrects dans le rapport et dans le champ `source`.

**EX-63. Chemins longs sous Windows.** Sous Windows, l'outil doit traiter les chemins de plus de 260 caractères en entrée et en sortie (le dossier miroir allonge les chemins), en utilisant la forme étendue des chemins (préfixe `\\?\`) dans ses appels au système de fichiers, sans exiger l'activation de la stratégie « chemins longs », qui relève de l'administrateur. Si une bibliothèque tierce ne supporte pas un chemin long, l'outil travaille sur une copie temporaire à chemin court, puis place le résultat à son emplacement final.
- CA : test automatisé Windows avec une arborescence dont le chemin de sortie atteint 300 caractères : traitement réussi, sorties présentes et lisibles.

**EX-64. Fichiers kDrive non synchronisés localement.** Les membres utilisent kDrive (Infomaniak), dont l'option Lite Sync laisse sur le disque des fichiers « en ligne uniquement », déshydratés, d'environ 1 Ko, qui exigent un téléchargement avant d'être pleinement accessibles et ne peuvent pas être ouverts sans connexion (sources : https://www.infomaniak.com/en/support/faq/2562/lite-sync-kdrive-windows ; https://infomaniak.com/en/support/faq/2608/managing-the-lite-sync-option-on-kdrive-macos). L'outil doit :
1. détecter, avant ouverture, qu'un fichier est probablement non disponible localement (PV-09 : attributs de fichier sous Windows, indicateurs de fichier sans données sous macOS) ;
2. tenter alors la lecture avec un délai maximal par fichier (`delai_hydratation_s`, défaut : 120), l'ouverture déclenchant en principe le téléchargement par le client de synchronisation ;
3. en cas d'échec ou de dépassement du délai, mettre le fichier en `erreur` avec le message : « fichier kDrive non disponible sur ce poste (en ligne uniquement) : dans l'Explorateur ou le Finder, clic droit sur le dossier, puis "Toujours conserver sur cet appareil" (ou équivalent), attendre la fin de la synchronisation, puis relancer » ;
4. ne jamais traiter le fichier substitut de 1 Ko comme s'il était le document (contrôle de signature de EX-18).
- CA : test automatisé avec un fichier simulé (substitut de 1 Ko portant l'extension .pdf, lecture bloquante simulée) : statut `erreur`, message ci-dessus, lot poursuivi ; test manuel TM-07 sur un dossier kDrive réel en Lite Sync, sur Mac et sur PC.

**EX-65. Dossier `_OCR` sur un espace synchronisé.** L'outil doit tolérer qu'un fichier de sortie soit momentanément verrouillé par le client de synchronisation ou par un antivirus : trois nouvelles tentatives espacées avant de déclarer l'erreur.
- CA : test avec verrou simulé relâché après deux secondes : écriture réussie.

### 5.3 Journalisation

**EX-66. Journal.** Chaque dossier `_OCR` doit contenir un journal `ocr_journal.log` (UTF-8, ajouts successifs, rotation au-delà de 5 Mo) : date et heure, version de l'outil et des moteurs, options, paramètres effectifs, puis pour chaque fichier la classification des pages, les indicateurs de qualité, les durées, les erreurs avec leur trace. Le journal ne doit contenir **aucun texte extrait des documents** (confidentialité) : seulement des noms de fichiers, des numéros de page, des nombres et des messages techniques.
- CA : après traitement du jeu de test, une recherche des phrases sentinelles contenues dans les documents de test ne trouve aucune occurrence dans le journal.

### 5.4 Configuration

**EX-67. Paramètres réglables.** Tous les seuils et paramètres cités dans ce document (classification, heuristique, confiance, `ocr_dpi`, délais, limites) doivent avoir une valeur par défaut dans le code, et pouvoir être modifiés par un fichier de configuration TOML : fichier du profil utilisateur (emplacement indiqué par `ocr-md verifier`), ou fichier passé par `--config`. Les valeurs effectives sont écrites au journal. Un paramètre inconnu ou une valeur invalide produit une erreur d'usage explicite.
- CA : le guide administrateur contient le tableau complet des paramètres, généré depuis le code ; tests de surcharge et de valeur invalide.

---

## 6. Installation, désinstallation, mise à jour, prérequis

### 6.1 Principe de distribution

**EX-68. Distribution par `uv`, sans exécutable empaqueté.** L'outil doit être distribué comme un paquet Python installé par `uv tool install` dans le profil de l'utilisateur. Aucun exécutable empaqueté (du type PyInstaller) ne doit être produit : un tel exécutable, non signé, se heurterait à Gatekeeper sur macOS et aux faux positifs des antivirus sous Windows.

Faits vérifiés sur `uv` (source : https://docs.astral.sh/uv/getting-started/installation/ ; https://docs.astral.sh/uv/reference/installer/) :
- l'installateur autonome place `uv` dans le profil de l'utilisateur : `~/.local/bin` sur macOS, `%USERPROFILE%\.local\bin` sous Windows (`uv.exe`, `uvx.exe`, `uvw.exe`) ; l'emplacement se change par `UV_INSTALL_DIR` ; `UV_NO_MODIFY_PATH=1` évite la modification des profils de shell ;
- commandes d'installation : `curl -LsSf https://astral.sh/uv/install.sh | sh` (macOS) ; `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"` (Windows) ;
- mise à jour de `uv` : `uv self update` ; désinstallation : suppression des binaires et, au besoin, de `uv cache`, du dossier des Pythons et du dossier des outils.
La documentation ne mentionne aucun besoin de droits d'administrateur et l'emplacement d'installation est dans le profil ; elle ne l'affirme toutefois pas explicitement, et elle ne traite ni d'AppLocker ni des stratégies d'exécution imposées par stratégie de groupe : voir PV-01.
- CA : le dépôt ne contient aucun script de fabrication d'exécutable empaqueté ; l'installation complète réussit sous un compte standard (TM-01).

**EX-69. Scripts d'installation.** Le dépôt doit fournir :
- `installation/installer-windows.cmd` (lançable par double-clic), qui appelle `installer-windows.ps1` avec `-ExecutionPolicy Bypass` pour ce seul processus ;
- `installation/installer-macos.command` (lançable par double-clic).
Chaque script, de façon idempotente : (1) installe `uv` dans le profil s'il est absent ; (2) installe Python 3.12 géré par `uv` ; (3) installe l'outil par `uv tool install` depuis la source de distribution (paquet « wheel » fourni à côté du script, ou adresse du dépôt Git ; la source est un paramètre en tête de script) ; (4) crée les trois raccourcis par `ocr-md raccourcis --creer` ; (5) exécute `ocr-md verifier` et affiche le diagnostic ; (6) affiche un message final en français indiquant le succès ou l'étape en échec. Les scripts ne modifient aucun réglage du système et n'écrivent que dans le profil.
- CA : sur un poste vierge, sous compte standard : double-clic, puis les trois entrées de menu fonctionnent (TM-01, TM-02) ; une seconde exécution du script réussit sans doublon de raccourci.

**EX-70. Création des raccourcis par l'outil.** La sous-commande `ocr-md raccourcis --creer` doit créer les trois entrées, et `--supprimer` les retirer, sans droits d'administrateur :
- **Windows** : trois fichiers `.lnk` dans `%APPDATA%\Microsoft\Windows\SendTo`, dont la cible est le lanceur sans console de l'outil (chemin absolu) suivi de `--sortie …`. Le menu « Envoyer vers » exécute la cible du raccourci en ajoutant le fichier sur la ligne de commande, et conserve les options inscrites dans la cible (source : https://devblogs.microsoft.com/oldnewthing/20170403-00/?p=95885/). À VÉRIFIER (PV-02) : transmission de l'ensemble d'une sélection multiple et longueur maximale de la ligne de commande ;
- **macOS** : trois Actions rapides dans `~/Library/Services` (lots `.workflow`), configurées pour recevoir « fichiers ou dossiers » dans le Finder et exécuter un script shell avec l'entrée transmise « comme arguments » ; le script appelle l'outil par son chemin absolu, car les Actions rapides s'exécutent avec un `PATH` minimal ; `"$@"` transmet tous les éléments sélectionnés (source : https://developer.apple.com/forums/thread/742419). À VÉRIFIER (PV-02) : prise en compte par le Finder d'un lot `.workflow` écrit par script, sans manipulation de l'utilisateur.
- CA : TM-02 sur les deux plateformes : sélection de 1 fichier, de 30 fichiers, de 2 dossiers, d'un mélange ; tous les éléments sélectionnés figurent au rapport ; `--supprimer` retire les trois entrées et elles seules.

**EX-71. Vérification des prérequis.** `ocr-md verifier`, et automatiquement le premier lancement après installation ou mise à jour (puis à chaque lancement pour le contrôle du moteur OCR, qui est rapide), doit contrôler et afficher en clair :

| Contrôle | Message si échec (résumé) |
|---|---|
| Version du système (Windows 10 ou 11 ; macOS 10.15 ou plus) | « système non pris en charge » |
| Moteur OCR disponible pour le français | Windows : « Le module de reconnaissance de texte en français de Windows n'est pas installé sur ce poste. Les PDF déjà lisibles et les fichiers Office restent convertibles ; les PDF scannés et les images ne peuvent pas être traités. Transmettre à votre service informatique la commande suivante, à exécuter en administrateur : `Add-WindowsCapability -Online -Name "Language.OCR~~~fr-FR~0.0.1.0"` » ; macOS : « la reconnaissance de texte en français n'est pas disponible sur cette version de macOS » |
| Écriture possible dans le dossier temporaire et dans le dossier de configuration | message indiquant le dossier |
| Raccourcis présents et pointant vers l'installation courante | « relancer le script d'installation » |
| Mode qualité (si l'extra est installé) : modèles préchargés | commande de préchargement |

Sous Windows, la disponibilité du français est testée **sans droits d'administrateur** par l'API elle-même : `OcrEngine.IsLanguageSupported` ou `OcrEngine.AvailableRecognizerLanguages` (source : https://learn.microsoft.com/en-us/uwp/api/windows.media.ocr.ocrengine), et non par `Get-WindowsCapability -Online`, que la documentation de PowerToys fait exécuter dans un PowerShell administrateur (source : https://learn.microsoft.com/windows/powertoys/text-extractor). Le nom de la fonctionnalité à installer est `Language.OCR~~~fr-FR~0.0.1.0` (source : https://learn.microsoft.com/windows-hardware/manufacture/desktop/features-on-demand-language-fod).

Lorsque le moteur OCR manque, l'outil ne bloque pas tout : il traite les fichiers qui ne nécessitent pas d'OCR, met en `erreur` ceux qui en nécessitent avec le message ci-dessus, et l'affiche dans la fenêtre de fin.
- CA : test automatisé avec moteur simulé indisponible : PDF natifs et fichiers Office traités, PDF scannés en `erreur` avec le message, code de retour 1 ; lot ne contenant que des PDF scannés : tous en `erreur`, code de retour 3 (EX-12) (décision du commanditaire du 26/11/2026) ; TM-04 sur un PC réel.

**EX-72. Mise à jour.** Le dépôt doit fournir `installation/mettre-a-jour-windows.cmd` et `installation/mettre-a-jour-macos.command`, qui réinstallent l'outil dans sa dernière version depuis la source de distribution (`uv tool install --force` ou `uv tool upgrade` selon la source), recréent les raccourcis, relancent `ocr-md verifier` et affichent l'ancienne et la nouvelle version. La mise à jour conserve le fichier de configuration de l'utilisateur. L'outil ne se met jamais à jour seul et ne vérifie pas l'existence de nouvelles versions (EX-03).
- CA : passage d'une version n à n+1 sur un poste : `ocr-md --version` affiche n+1 ; configuration conservée ; raccourcis fonctionnels.

**EX-73. Désinstallation.** Le dépôt doit fournir `installation/desinstaller-windows.cmd` et `installation/desinstaller-macos.command`, qui suppriment les raccourcis, désinstallent l'outil (`uv tool uninstall`), suppriment le dossier temporaire et, après confirmation, le fichier de configuration et les modèles du mode qualité. Ils proposent, sans l'imposer, de désinstaller `uv` et ses Pythons (d'autres outils peuvent en dépendre). Les dossiers `_OCR` produits ne sont jamais touchés.
- CA : après désinstallation, aucune entrée de menu ne subsiste ; aucun fichier de l'outil ne reste dans le profil hors éléments conservés à la demande de l'utilisateur ; les dossiers `_OCR` existants sont intacts.

### 6.2 Prérequis

| Élément | Exigence | État de la vérification |
|---|---|---|
| Windows | Windows 10 ou 11, 64 bits ; pack OCR français présent | Présence par défaut du pack : non établie, PV-03 |
| macOS | 10.15 ou plus pour Vision selon `ocrmac` ; la version minimale effectivement supportée est celle sur laquelle le français est reconnu en niveau `accurate` | PV-08 |
| Processeur Mac | Apple Silicon et Intel | PV-08 |
| Réseau | Nécessaire à l'installation et à la mise à jour seulement (astral.sh, GitHub, PyPI, et Hugging Face pour le mode qualité) ; à préciser dans le guide administrateur pour les pare-feu et serveurs mandataires | Liste à constater par Claude Code |
| Espace disque | À mesurer et à documenter (v1, puis v1.1 avec modèles) | PV-07 |

---

## 7. Tests

### 7.1 Jeu de données synthétique

**EX-74. Générateur du jeu de test.** Claude Code doit écrire un script `tests/donnees/generer.py` qui fabrique, de façon reproductible (graine fixe), un jeu de test entièrement synthétique, sans aucun document réel, accompagné d'un manifeste `manifeste.json` qui constitue la vérité terrain (pour chaque fichier : type, nombre de pages, catégorie attendue de chaque page, texte de référence par page, pages attendues douteuses, statut attendu, valeurs des cellules des tableaux). Contenu minimal :

| N° | Fichier | Contenu | Attendu |
|---|---|---|---|
| 1 | PDF natif, 5 pages | texte français avec tous les caractères accentués, œ, €, pied de page « Page x sur y », un mot unique par page | `natif`, zéro OCR |
| 2 | PDF scanné simulé, 4 pages | pages du n° 1 rendues en image à 300 dpi, légère rotation (1 à 2 degrés), bruit, compression JPEG ; aucune couche texte | `ocrise` |
| 3 | PDF mixte, 6 pages | 3 pages natives, 2 pages-images, 1 page vide | `mixte` |
| 4 | PDF à couche OCR dégradée, 4 pages | image et couche texte invisible volontairement corrompue sur les pages 2 et 3 (substitutions de caractères, mots fragmentés, caractères aberrants) | `douteux`, pages 2 et 3 |
| 5 | PDF scanné illisible, 2 pages | page 2 très floue et bruitée | `douteux`, page 2 (OCR de l'outil) |
| 6 | PDF avec tableaux, au moins 4 pages natives | page 1 : tableau simple ; page 2 : tableau à cellules fusionnées et double en-tête ; page 3 : DPGF (lots et sous-lots fusionnés, quantités, prix unitaires, totaux) ; page 4 : cadre de décomposition des honoraires de maîtrise d'œuvre (missions par cotraitant, en-têtes sur deux niveaux) | Markdown pour la page 1, HTML avec `colspan`/`rowspan` pour les pages 2 à 4 |
| 6b | Version scannée du fichier 6 | pages 1 à 4 rendues en image | `ocrise` ; chaque tableau détecté précédé du repère « tableau reconnu par OCR » |
| 7 | .docx | titres, liste, tableau | `natif` |
| 8 | .xlsx | deux feuilles visibles, une masquée | `natif` |
| 9 | .pptx | trois diapositives, une avec commentaires | `natif` |
| 10 | Images | un JPEG (orientation EXIF 6), un PNG, un TIFF de 3 trames | `ocrise` |
| 11 | Non pris en charge | .doc, .msg, .zip (fichiers factices) | `non_pris_en_charge` |
| 12 | Chemin accentué | `Candidat Été & Fils (n° 2)/Mémoire d'été.pdf`, formes NFC et NFD | traité |
| 13 | PDF corrompu et PDF chiffré | fichier tronqué ; fichier protégé par mot de passe | `erreur` |
| 13b | PDF tronqué partiellement récupérable | fichier tronqué dont la réparation laisse au moins une page lisible et au moins une page perdue | `douteux`, motif `pdf_repare` |
| 14 | Faux PDF de 1 Ko | substitut simulant un fichier non synchronisé | `erreur` |
| 15 | Arborescence de lot | `Lot 1/Candidat A/…`, `Lot 1/Candidat B/…`, trois niveaux, un dossier `_OCR` préexistant | miroir exact |
| 16 | Chemin long (Windows) | chemin de sortie de 300 caractères | traité |
| 17 | PDF volumineux | 1 000 pages scannées simulées (généré à la demande, hors dépôt) | test de mémoire |
| 18 | PDF scanné riche en ligatures, 2 pages | texte courant dense en « maître d'œuvre », « l'œuvre », « cœur », « sœur », « vœu », « Lætitia », « ex æquo », avec apostrophes typographiques | `ocrise`, aucune page douteuse, sous Apple Vision comme sous `Windows.Media.Ocr` |

- CA : `python tests/donnees/generer.py` produit le jeu complet et son manifeste sur les trois systèmes ; deux exécutions donnent des fichiers de même contenu textuel ; aucun document réel ni donnée personnelle dans le dépôt.

### 7.2 Tests automatisés

**EX-75. Suite de tests.** Le dépôt doit contenir une suite `pytest` couvrant chaque exigence dont le critère d'acceptation est automatisable, avec une table de correspondance exigence vers test (`tests/TRACABILITE.md`, générée à partir de marqueurs `@pytest.mark.exigence("EX-nn")`). Trois niveaux :
1. **tests avec moteur factice** (toutes plateformes, y compris Linux) : le moteur factice renvoie le texte et les boîtes du manifeste, avec des confiances imposées ; ils couvrent toute la chaîne hors reconnaissance réelle ;
2. **tests avec moteur réel**, marqués `macos` ou `windows`, exécutés sur la plateforme correspondante : reconnaissance effective des fichiers 2, 3, 5 et 10 ;
3. **tests d'installation** scriptés autant que possible (installation dans un profil temporaire, création et suppression des raccourcis).
- CA : `uv run pytest` réussit sur macOS et sur Windows (niveaux 1 et 2) et sur Linux (niveau 1) ; `tests/TRACABILITE.md` ne laisse aucune exigence automatisable sans test ; les exigences vérifiées seulement par test manuel y sont marquées comme telles.

**EX-76. Calibrage des seuils.** Claude Code doit fournir un script `tests/calibrage.py` qui calcule les indicateurs de EX-35 et EX-36 sur le jeu de test et produit un tableau (par page : indicateurs, verdict, vérité terrain). Les valeurs par défaut des seuils livrés doivent être celles qui donnent zéro erreur de verdict sur le jeu de test, avec la marge la plus large ; elles sont documentées dans le guide administrateur avec ce tableau. Le script doit pouvoir être relancé sur un dossier de documents réels par le référent, en local, pour ajuster les seuils en recette.
- CA : tableau de calibrage présent dans le guide administrateur ; le script s'exécute sur un dossier arbitraire et n'écrit que des nombres (aucun texte de document) dans sa sortie.

### 7.3 Critères d'acceptation globaux

1. Toutes les exigences de la phase ont leur critère d'acceptation satisfait, ou une dérogation motivée acceptée par le commanditaire et inscrite au CHANGELOG.
2. Qualité de reconnaissance (objectif, à confirmer) : sur les PDF scannés propres du jeu de test (fichiers 2, 3 et 10), au moins 95 % des mots de référence de chaque page sont retrouvés dans le PDF consultable (`pdftotext`) et dans le Markdown, sur Mac comme sur PC, la comparaison admettant les équivalences `œ`/`oe`, `æ`/`ae` et `’`/`'` (décision du commanditaire du 26/11/2026, après l'essai PV-04). Cette valeur mesure le bon fonctionnement de la chaîne sur des pages synthétiques propres ; elle ne préjuge pas de la qualité sur des scans réels.
3. Le traitement du jeu de test complet se termine avec le code de retour 1 (présence volontaire de fichiers en erreur), un rapport conforme, et aucun fichier source modifié.
4. Les tests manuels de la section 7.4 sont réussis sur un vrai Mac et un vrai PC, sous compte standard.

### 7.4 Tests manuels sur un vrai Mac et un vrai PC

Claude Code doit livrer ces tests sous forme de fiches à cocher (`docs/recette-manuelle.md`), avec résultat attendu et espace de constat. Ils sont exécutés par le référent, pas par Claude Code.

| N° | Test | Plateformes |
|---|---|---|
| TM-01 | Installation sur poste vierge, compte standard, sans invite d'élévation ; relevé de toute alerte (SmartScreen, antivirus, AppLocker, Gatekeeper, demandes d'autorisation macOS d'accès aux dossiers) | Mac Apple Silicon, Mac Intel si le parc en compte, Windows 10, Windows 11 |
| TM-02 | Les trois entrées de menu : 1 fichier, 30 fichiers, 2 dossiers, mélange ; sous Windows 11, accès à « Envoyer vers » par « Afficher d'autres options » | toutes |
| TM-03 | Progression, annulation, fenêtre de fin, bouton « Ouvrir le dossier » | toutes |
| TM-04 | PC sans pack OCR français : message de EX-71 ; puis, après installation du pack par l'administrateur, traitement réussi | Windows |
| TM-05 | PDF consultable : recherche et sélection de texte accentué dans Aperçu, Adobe Acrobat Reader, navigateur ; copier-coller d'un paragraphe | toutes |
| TM-06 | Traitement complet, poste déconnecté du réseau | toutes |
| TM-07 | Dossier kDrive en Lite Sync avec fichiers « en ligne uniquement » : comportement conforme à EX-64 ; dossier `_OCR` créé dans kDrive et synchronisé sans conflit | toutes |
| TM-08 | Lot réel anonymisé ou non confidentiel de 50 plis : relevé de performance (EX-58), relecture par sondage de 20 pages reconnues, relevé des faux positifs et faux négatifs de « texte douteux » | toutes |
| TM-09 | Dépôt des sorties d'un pli dans Claude : une question posée sur une page douteuse donne une réponse qui mentionne la réserve ; une citation à la page est exacte | une |
| TM-10 | Mise à jour puis désinstallation | toutes |

---

## 8. Phasage

### 8.1 Version 1.0

**Contenu** : toutes les exigences EX-01 à EX-82, à l'exception de EX-54, EX-55 et EX-56 ; moteur Markdown PyMuPDF4LLM ; OCR natif ; PDF consultable ; Markdown ; front matter et avertissements ; rapport ; installation, mise à jour, désinstallation.

L'option `--qualite` existe dès la v1 dans l'interface, et renvoie le message « mode qualité disponible à partir de la version 1.1 » (code de retour 2).

**Ordre de réalisation recommandé** (REC-07), chaque étape se terminant par des tests verts :
1. levée des points à vérifier PV-01 à PV-06, PV-08, PV-09, PV-11 à PV-13 par de courts prototypes, consignés dans `docs/verifications.md` (résultat, date, version, décision) ;
2. générateur du jeu de test et moteur factice ;
3. inventaire, dossier miroir, rapport, règle de relance ;
4. analyse des pages, calque invisible, PDF consultable ;
5. moteurs OCR natifs ;
6. Markdown, repères, tableaux ;
7. qualité, front matter, avertissements ;
8. Office, images ;
9. interface, raccourcis, scripts d'installation ;
10. guides, inventaire des licences, recette.

**Livrables** : ceux de la section 9.

**Critères de recette de la v1** : critères globaux de la section 7.3 ; `docs/verifications.md` complet, chaque point à vérifier étant levé ou assorti du repli mis en œuvre ; guides relus par un utilisateur non technique de la SODEB capable d'installer et d'utiliser l'outil avec le seul guide.

### 8.2 Version 1.1

**Contenu** : EX-54, EX-55, EX-56 (mode qualité Docling, extra `[qualite]`, préchargement des modèles) ; corrections issues de la recette de la v1 ; recalibrage des seuils d'après TM-08.

**Livrables** : paquet 1.1 ; scripts d'installation acceptant un paramètre « avec mode qualité » ; guides mis à jour (quand utiliser le mode qualité, poids, durée) ; relevé comparatif des deux moteurs Markdown sur le jeu de test (fidélité du texte, tableaux, durée).

**Critères de recette de la v1.1** : non-régression complète de la v1 sans l'extra ; critères d'acceptation de EX-54 à EX-56 ; PV-07 levé, avec poids et durées mesurés et documentés ; sur le fichier 6 du jeu de test, le mode qualité restitue toutes les valeurs de cellules du tableau fusionné.

---

## 9. Livrables de Claude Code

**EX-77. Dépôt complet.** Claude Code doit livrer un dépôt Git unique contenant tout le code source, selon l'arborescence indicative suivante :

```
ocr-md/
  README.md                    présentation, installation rapide, licence
  LICENSE                      texte de la licence du projet
  CHANGELOG.md
  LICENCES-TIERCES.md          inventaire des licences des dépendances
  pyproject.toml
  uv.lock
  src/ocr_md/                  modules de la section 3.3
    donnees/                   lexique, police embarquée, modèles d'avertissement
  schema/front-matter-v1.json
  installation/
    installer-windows.cmd  installer-windows.ps1  installer-macos.command
    mettre-a-jour-windows.cmd  mettre-a-jour-macos.command
    desinstaller-windows.cmd  desinstaller-macos.command
  docs/
    guide-utilisateur-windows.md
    guide-utilisateur-macos.md
    guide-administrateur.md
    specification-front-matter.md
    verifications.md
    recette-manuelle.md
  tests/
    donnees/generer.py
    perf/lot_type.py
    calibrage.py
    TRACABILITE.md
```
- CA : l'arborescence livrée contient tous ces éléments ; `uv run pytest` réussit depuis un clone neuf.

**EX-78. Licence et inventaire.** PyMuPDF et PyMuPDF4LLM sont sous licence AGPL (ou licence commerciale) : l'usage interne ne pose pas de difficulté, mais la distribution aux membres impose de fournir le code source. En conséquence : le dépôt doit contenir l'intégralité du code de l'outil ; le fichier LICENSE doit être cohérent avec l'AGPL (le projet est placé sous AGPL-3.0, sauf instruction contraire du commanditaire) ; `LICENCES-TIERCES.md` doit lister chaque dépendance directe et transitive installée, avec sa version, sa licence et l'adresse de son projet, ainsi que la police et le lexique embarqués ; l'inventaire est généré par un script du dépôt à partir de l'environnement verrouillé, puis relu. Les scripts d'installation et le guide indiquent où obtenir le code source correspondant à la version installée.
- CA : inventaire présent, généré, sans dépendance dont la licence est « inconnue » ; aucune dépendance dont la licence est incompatible avec l'AGPL-3.0 ; `ocr-md --version` affiche la licence et l'adresse du code source.

**EX-79. Guide utilisateur.** Claude Code doit livrer un guide par plateforme, d'**une page**, destiné à des non-techniciens : comment lancer les trois actions, où trouver les sorties, comment lire la fenêtre de fin, que faire d'une pièce signalée douteuse, d'une pièce non prise en charge, d'une erreur ; que donner à Claude (le Markdown, ou le PDF consultable, et toujours `_AVERTISSEMENTS.md`). Les emplacements des captures d'écran sont marqués `[CAPTURE : description précise]` ; les captures seront faites par le référent sur des postes réels.
- CA : chaque guide tient sur une page A4 une fois mis en page ; il ne contient aucune commande de terminal, à la seule exception de l'encadré « Refaire l'OCR des pages douteuses » ; au moins quatre emplacements de capture.

**EX-80. Guide administrateur.** Claude Code doit livrer un guide pour le référent : prérequis, installation, mise à jour, désinstallation, connexions réseau de l'installation, emplacements des fichiers dans le profil, tableau des paramètres et seuils, calibrage, diagnostic des erreurs courantes (pack OCR absent, blocage par AppLocker ou antivirus, autorisations macOS, fichiers kDrive non synchronisés, chemins longs), obligations de licence, résultats de `docs/verifications.md`, mesures de performance et de poids.
- CA : chaque message d'erreur émis par l'outil figure dans le guide avec sa cause et son remède (vérifié par un test qui compare la liste des messages du code à celle du guide).

**EX-81. CHANGELOG.** Le dépôt doit contenir un CHANGELOG en français, par version, listant ajouts, corrections, écarts par rapport au présent cahier des charges et recommandations non suivies avec leur justification.
- CA : rubriques « Écarts au cahier des charges » et « Reprise de l'existant » présentes pour la version 1.0.0, même vides.

---

## 10. Risques et points à vérifier

Chaque point indique : ce qui a été vérifié sur le web le 26 novembre 2026, ce qui reste à vérifier, la méthode que Claude Code (ou le référent, pour les essais sur poste réel) doit suivre, et le plan de repli. Les résultats sont consignés dans `docs/verifications.md`.

### PV-01. `uv` sans droits d'administrateur ; PowerShell restreint ; AppLocker

- **Vérifié** : l'installateur autonome place `uv` dans le profil (`~/.local/bin`, `%USERPROFILE%\.local\bin`) ; commande Windows documentée avec `-ExecutionPolicy ByPass` ; `UV_INSTALL_DIR`, `UV_NO_MODIFY_PATH`, `uv self update` (https://docs.astral.sh/uv/getting-started/installation/ ; https://docs.astral.sh/uv/reference/installer/). Un faux positif de Windows Defender sur `uv.exe` a déjà été signalé et traité par Microsoft, puis signalé de nouveau (https://github.com/astral-sh/uv/issues/1587).
- **À VÉRIFIER** : (a) absence effective de toute demande d'élévation sur Windows 10/11 et macOS (la documentation ne l'affirme pas explicitement) ; (b) comportement lorsque la stratégie d'exécution PowerShell est imposée par stratégie de groupe (le paramètre `-ExecutionPolicy Bypass` d'un processus ne prévaut pas nécessairement sur une stratégie de groupe) ; (c) comportement sous AppLocker ou contrôle d'application, qui peut interdire l'exécution de binaires situés dans le profil (`uv.exe`, `python.exe` géré par `uv`, lanceurs de l'outil) ; (d) existence d'une signature de code sur `uv.exe`, utile à une règle d'autorisation par éditeur.
- **Méthode** : TM-01 sur un PC de la SODEB sous compte standard ; relever `Get-ExecutionPolicy -List` et, avec le service informatique, l'existence de règles AppLocker ; `Get-AuthenticodeSignature` sur `uv.exe`.
- **Repli** : (1) si PowerShell est bloqué : installation de `uv` par téléchargement direct de l'archive publiée et extraction dans le profil par le script `.cmd`, sans PowerShell ; (2) si l'exécution depuis le profil est interdite : demande au service informatique d'une règle d'autorisation (par éditeur ou par chemin) pour `uv`, le Python géré et le lanceur, le guide administrateur fournissant la liste exacte des chemins ; à défaut, installation par le service informatique dans un emplacement autorisé au moyen de `UV_INSTALL_DIR` et des variables de dossier de `uv` ; (3) aucun repli ne passe par un exécutable empaqueté.

### PV-02. Raccourcis « Envoyer vers » et Actions rapides ; sélections multiples

- **Vérifié** : « Envoyer vers » exécute la cible du raccourci avec le fichier sur la ligne de commande et conserve les options de la cible (https://devblogs.microsoft.com/oldnewthing/20170403-00/?p=95885/). Une Action rapide recevant « fichiers et dossiers », avec « Exécuter un script shell » et l'entrée « comme arguments », transmet tous les éléments sélectionnés par `"$@"` ; le `PATH` y est minimal, d'où l'usage de chemins absolus ; macOS peut demander l'autorisation d'accéder aux dossiers Bureau, Documents, Téléchargements (https://developer.apple.com/forums/thread/742419).
- **À VÉRIFIER** : (a) Windows : transmission de toute une sélection multiple en un seul lancement et limite de longueur de la ligne de commande (plusieurs dizaines de chemins longs) ; création du `.lnk` sans droits d'administrateur depuis Python ; visibilité sous Windows 11 (menu « Afficher d'autres options ») ; (b) macOS : un lot `.workflow` écrit par script dans `~/Library/Services` est reconnu par le Finder sans intervention (rafraîchissement des services, activation éventuelle dans Réglages Système, rubrique Extensions) ; format exact du lot sur les versions de macOS visées ; comportement des autorisations d'accès aux fichiers pour un processus lancé par une Action rapide, notamment vers un dossier kDrive.
- **Méthode** : prototype de `ocr-md raccourcis --creer` et TM-02 avec 1, 30 et 200 fichiers sélectionnés.
- **Repli** : (1) Windows : si la sélection est tronquée ou refusée, le guide recommande de sélectionner le dossier plutôt que les fichiers, et l'outil détecte un lancement multiple simultané (verrou par dossier `_OCR`) pour fusionner les demandes en un seul traitement ; (2) macOS : si le lot écrit par script n'est pas reconnu, livraison de trois fichiers `.workflow` prêts à l'emploi que l'utilisateur installe par double-clic, ou procédure illustrée de création manuelle dans l'application Raccourcis, décrite dans le guide ; (3) dans tous les cas, la commande reste utilisable par glisser-déposer sur un lanceur placé sur le Bureau.

### PV-03. Pack OCR français de Windows

- **Vérifié** : l'OCR est une fonctionnalité à la demande distincte, `Language.OCR~~~fr-FR~0.0.1.0`, dépendante du composant de base de la langue ; Microsoft recommande aux intégrateurs de la préinstaller pour chaque langue préinstallée, sans indiquer qu'elle est installée automatiquement (https://learn.microsoft.com/windows-hardware/manufacture/desktop/features-on-demand-language-fod). L'installation se fait par `Add-WindowsCapability -Online`, en administrateur (https://pypi.org/project/winocr). La liste des langues reconnues s'obtient par `[Windows.Media.Ocr.OcrEngine]::AvailableRecognizerLanguages` dans Windows PowerShell (pas PowerShell 7), alors que `Get-WindowsCapability -Online` est présenté comme une commande d'administrateur (https://learn.microsoft.com/windows/powertoys/text-extractor).
- **À VÉRIFIER** : présence effective du pack sur les PC de la SODEB installés en français (non garantie par la documentation) ; exécution sans élévation de l'appel `AvailableRecognizerLanguages`.
- **Méthode** : `ocr-md verifier` sur chaque modèle de poste, ou, avant toute installation, dans Windows PowerShell sous compte standard :
  `[Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null; [Windows.Media.Ocr.OcrEngine]::AvailableRecognizerLanguages`
- **Repli** : message de EX-71 avec la commande destinée au service informatique ; l'outil reste utilisable pour les documents sans OCR ; à partir de la v1.1, le mode qualité (RapidOCR, installable sans droits d'administrateur) peut être proposé aux postes dépourvus du pack, sur décision du commanditaire.

### PV-04. `winocr` ou projection officielle ; indice de confiance sous Windows

- **Vérifié** : `winrt-Windows.Media.Ocr` est publié par le projet PyWinRT, dernière version du 31 octobre 2026, Python 3.11 ou plus (https://pypi.org/project/winrt-windows-media-ocr) ; `winocr` est en version 0.0.15 du 25 octobre 2024 et expose `recognize_pil`, avec texte, lignes, mots et rectangles (https://pypi.org/project/winocr). `Windows.Media.Ocr` ne fournit **aucun indice de confiance** : `OcrWord` n'a que `Text` et `BoundingRect` (https://learn.microsoft.com/en-us/uwp/api/windows.media.ocr.ocrword).
- **Décision qui en découle** : projection PyWinRT recommandée (REC-03) ; heuristique lexicale de remplacement exigée sous Windows (EX-35).
- **À VÉRIFIER** : liste exacte des paquets `winrt-*` à installer (runtime, `Windows.Globalization`, `Windows.Graphics.Imaging`, `Windows.Storage.Streams`, `Windows.Foundation`) ; conversion d'une image Pillow en `SoftwareBitmap` ; valeur de `MaxImageDimension` ; prise en compte de `OcrResult.TextAngle` pour les pages inclinées ; fonctionnement dans un processus sans fenêtre.
- **Méthode** : prototype reconnaissant le fichier 2 du jeu de test sur un PC, avec les deux bibliothèques.
- **Repli** : `winocr`, ou la variante `winocrfix` (https://pypi.org/project/winocrfix/), derrière la même interface `ocr/base`.

### PV-05. `ocr_function` de PyMuPDF4LLM ; import de `pymupdf.layout` ; texte invisible

- **Vérifié** : signature documentée `exec_ocr(page, dpi=300, pixmap=None, language="eng", keep_ocr_text=False)` ; la fonction doit inscrire le texte reconnu sur la page, aucune valeur de retour n'est spécifiée ; moteurs intégrés Tesseract et RapidOCR ; sans moteur par défaut installé et sans fonction fournie, le comportement équivaut à `use_ocr=False` (https://pymupdf.readthedocs.io/en/latest/ocr/index.html). Paramètres de `to_markdown` : `ocr_function`, `use_ocr=True`, `force_ocr=False`, `ocr_dpi=150`, `ocr_language='eng'`, `table_output` (`"html"` ou `None`), `page_chunks`, `page_separators` (numérotation à partir de 0), `pages` (à partir de 0), `header`, `footer`, `ignore_alpha`, `force_text` (https://pymupdf.readthedocs.io/en/latest/document.html). Le ticket 4833, qui signalait que l'import de `pymupdf.layout` avant `pymupdf4llm` n'était pas documenté, a été clos le 25 mars 2026 : le mainteneur indique que « Layout » a été fusionné dans la base de PyMuPDF4LLM et que la documentation OCR a été complétée (https://github.com/PyMuPDF/PyMuPDF/issues/4833). La documentation indique aussi que, depuis PyMuPDF 2.0, le cœur de PyMuPDF4LLM est dans `Document.to_markdown()` (https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/api.html).
- **À VÉRIFIER** : (a) dans la version installée, nécessité ou non d'un import explicite de `pymupdf.layout` ; (b) conditions réelles d'appel de `ocr_function` : l'arbre de décision de la documentation cite Tesseract et `opencv-python` parmi les conditions de l'OCR automatique, sans préciser si elles valent pour une fonction fournie ; (c) reprise du texte en mode de rendu invisible par la conversion Markdown ; (d) unité des coordonnées attendues et rôle exact de `pixmap` et de `keep_ocr_text` ; (e) point d'entrée à utiliser (`pymupdf4llm.to_markdown` ou `Document.to_markdown`) et numéro de version, à rapprocher du « README version 1.28.x » cité en préparation.
- **Méthode** : lire le code source du greffon RapidOCR livré (`pymupdf4llm/ocr/rapidocr_api.py`) comme modèle ; prototype avec le moteur factice sur les fichiers 2 et 3 ; test du compteur d'appels.
- **Repli** : l'architecture de la section 3.1 ne dépend pas du déclenchement de `ocr_function` par la bibliothèque, puisque l'outil applique lui-même l'adaptateur avant la conversion ; si (b) échoue, l'appel est fait avec `use_ocr=False` sur le PDF consultable ; si (c) échoue, essayer `ignore_alpha=True`, puis, en dernier recours, assembler pour les seules pages reconnues un Markdown simple à partir du texte du calque (paragraphes dans l'ordre de lecture), les pages natives restant converties par PyMuPDF4LLM.

### PV-06. Écriture du calque invisible avec PyMuPDF

- **Vérifié** : le mode de rendu 3 rend le texte invisible ; `insert_text` et `insert_textbox` acceptent `render_mode`, `fontname`, `fontfile`, `morph`, `rotate` ; les polices issues d'un fichier sont installées en Type0 par défaut (https://pymupdf.readthedocs.io/en/latest/shape.html ; https://pymupdf.readthedocs.io/en/latest/page.html) ; les polices Base 14 ne couvrent que les caractères jusqu'à Unicode 256 et une police Unicode fournie par fichier est recommandée au-delà (https://pymupdf.readthedocs.io/en/latest/faq/). PyMuPDF sait produire lui-même un PDF à couche cachée, mais avec Tesseract (`pdfocr_save`, police GlyphLessFont ; https://pymupdf.readthedocs.io/en/latest/ocr/index.html), ce qui est exclu ici.
- **À VÉRIFIER** : (a) mise à l'échelle d'une ligne pour qu'elle couvre exactement sa boîte (taille de police déduite de la hauteur, étirement horizontal par `morph` ou par calcul de largeur avec `get_text_length` ou `TextWriter`) ; (b) conversion des coordonnées : Vision renvoie des boîtes normalisées (origine et convention à constater), Windows des pixels depuis le coin supérieur gauche pour un angle de texte nul ; (c) pages pivotées (`page.rotation`) et pages dont la boîte de rognage n'est pas à l'origine ; (d) restitution des accents, de œ et de € par `pdftotext` et par la recherche d'Aperçu et d'Acrobat (présence d'une table ToUnicode correcte) ; (e) poids ajouté par l'incorporation de la police (sous-ensemble à l'enregistrement).
- **Méthode** : prototype sur le fichier 2 ; critères (a) à (d) de EX-30 ; contrôle visuel en rendant le calque visible temporairement (mode de rendu 0, couleur rouge) et en le superposant à l'image.
- **Repli** : si l'ajustement fin échoue, écriture mot par mot à la position de la boîte, sans étirement (la recherche et l'extraction restent correctes, seule la surbrillance de sélection est approximative) ; si une police pose un problème d'encodage, changer de police libre.

### PV-07. Docling : poids, premier lancement, téléchargements (v1.1)

- **Vérifié** : les modèles sont téléchargés automatiquement à la première utilisation ; `docling-tools models download` les précharge dans `$HOME/.cache/docling/models` ; `artifacts_path` et `DOCLING_ARTIFACTS_PATH` les désignent ; aucun envoi vers un service distant sans `enable_remote_services=True` (https://docling-project.github.io/docling/usage/advanced_options). Les poids du pipeline PDF proviennent de Hugging Face ; Docling peut fonctionner en environnement isolé ; les formats DOCX et PPTX ne requièrent pas de modèles (https://docling-project.github.io/docling/faq). Docling dépend de PyTorch ; sur Mac Intel, PyTorch n'est plus publié après la version 2.2.2, ce qui impose `torch==2.2.2`, `torchvision==0.17.2`, NumPy inférieur à 2 et Python 3.12 au plus (https://docling-project.github.io/docling/getting_started/installation/ ; https://docling-project.github.io/docling/faq).
- **À VÉRIFIER** : poids sur disque de l'extra (PyTorch compris) et des modèles ; durée du premier lancement ; téléchargement éventuel de modèles par RapidOCR à la première utilisation ; possibilité de désactiver l'OCR de Docling quand la couche texte existe ; exactitude des numéros de page dans la structure exportée ; téléchargement à travers un serveur mandataire d'entreprise (erreurs de certificat décrites dans la FAQ).
- **Méthode** : installation de l'extra dans un environnement neuf, mesure du dossier d'environnement et du dossier de modèles, chronométrage du premier et du deuxième traitement du fichier 6, capture des connexions réseau de la première exécution.
- **Repli** : si le poids ou la durée sont jugés excessifs par le commanditaire, le mode qualité reste réservé à quelques postes ; si Docling ne permet pas de réutiliser la couche texte, appliquer la seconde solution de EX-55 en la documentant ; sur Mac Intel, si l'installation est trop contraignante, le mode qualité est déclaré non supporté sur cette architecture.

### PV-08. Apple Silicon, Intel, versions de macOS

- **Vérifié** : `ocrmac` (1.0.1, 8 janvier 2026) annonce macOS 10.15 ou plus pour Vision et macOS Sonoma pour LiveText ; il s'appuie sur `pyobjc-framework-Vision` et requiert Python 3.9 ou plus ; il accepte `language_preference` et signale une langue non supportée en listant les langues disponibles ; avec LiveText, la confiance vaut toujours 1 (https://pypi.org/project/ocrmac). La page ne dit rien de la compatibilité Intel. Le greffon OCRmyPDF pour Apple Vision juge l'OCR d'Apple nettement plus précis et plus rapide que Tesseract (https://pypi.org/project/ocrmypdf-appleocr/) ; cette appréciation est celle de son auteur et n'a pas été mesurée ici.
- **À VÉRIFIER** : (a) version de macOS à partir de laquelle le français est reconnu au niveau `accurate` (la liste des langues dépend de la version du système) ; (b) fonctionnement sur Mac Intel (roues PyMuPDF et pyobjc pour x86_64, disponibilité de Python 3.12 géré par `uv`) ; (c) convention des boîtes englobantes renvoyées par `ocrmac` ; (d) versions de macOS réellement présentes à la SODEB.
- **Méthode** : sur chaque Mac type, `ocr-md verifier` affiche la version du système, l'architecture et la liste des langues renvoyée par Vision (`supportedRecognitionLanguages`) ; reconnaissance du fichier 2 ; TM-01.
- **Repli** : fixer la version minimale de macOS supportée à la plus ancienne version constatée conforme ; en dessous, l'outil fonctionne sans OCR (documents natifs et Office) avec le message de EX-71 ; si `ocrmac` pose une difficulté, appel direct de Vision par pyobjc.

### PV-09. Fichiers kDrive « en ligne uniquement »

- **Vérifié** : avec Lite Sync, les fichiers non conservés localement sont des substituts déshydratés d'environ 1 Ko, qui nécessitent un chargement et une connexion ; Windows 10 21H2 ou plus et NTFS sont requis côté Windows, macOS 10.15 ou plus côté Mac ; des icônes d'état distinguent « en ligne », « toujours disponible » et « disponible temporairement » (https://www.infomaniak.com/en/support/faq/2562/lite-sync-kdrive-windows ; https://infomaniak.com/en/support/faq/2608/managing-the-lite-sync-option-on-kdrive-macos). La documentation ne précise ni le mécanisme technique, ni si l'ouverture par une application tierce déclenche le téléchargement.
- **À VÉRIFIER** : (a) Windows : attributs portés par un fichier en ligne uniquement (`FILE_ATTRIBUTE_OFFLINE`, `FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS`, `FILE_ATTRIBUTE_RECALL_ON_OPEN`, lisibles par `os.stat().st_file_attributes` sans ouvrir le fichier) ; (b) macOS : indicateur de fichier sans données (`st_flags`, blocs alloués nuls pour une taille non nulle, ou attributs étendus) ; (c) effet d'une ouverture en lecture par Python : téléchargement transparent, blocage, ou erreur ; durée ; (d) taille déclarée du substitut (taille réelle du document ou 1 Ko).
- **Méthode** : TM-07, avec un petit script de diagnostic livré dans `tests/` qui affiche, pour un fichier donné, ses attributs, sa taille déclarée, ses blocs alloués et le résultat d'une lecture de 1 Ko avec délai.
- **Repli** : si aucune détection préalable n'est fiable, s'en tenir au contrôle de signature (EX-18) et au délai de lecture (EX-64), avec le même message ; le guide utilisateur recommande dans tous les cas de rendre le dossier « toujours disponible » avant de lancer un lot.

### PV-10. Client de synchronisation et dossier `_OCR`

- **À VÉRIFIER** : création d'un grand nombre de fichiers dans un dossier kDrive synchronisé pendant le traitement (verrous, conflits, ralentissement) ; comportement des fichiers temporaires renommés (EX-53).
- **Méthode** : TM-07 et TM-08 dans un dossier kDrive.
- **Repli** : écrire les sorties d'un fichier dans le dossier temporaire du profil, puis les déplacer en une fois ; recommander dans le guide de traiter les très gros lots dans un dossier local.

### PV-11. `tkinter` dans le Python géré par `uv`

- **À VÉRIFIER** : présence et bon fonctionnement de `tkinter` sur macOS et Windows avec le Python 3.12 installé par `uv` ; apparence correcte sur écran à haute densité ; absence d'icône parasite dans le Dock.
- **Méthode** : prototype de la fenêtre de progression lancé par les raccourcis.
- **Repli** : celui de REC-02.

### PV-12. Lexique français

- **À VÉRIFIER** : source et licence d'un lexique français de formes fléchies réutilisable et redistribuable avec un projet sous AGPL-3.0 (par exemple un dictionnaire orthographique libre) ; taille ; temps de chargement.
- **Méthode** : examen des licences lors de l'inventaire ; mesure du temps de chargement (objectif : moins d'une seconde).
- **Repli** : lexique réduit aux formes les plus fréquentes, constitué à partir d'une source libre, avec un seuil `taux_mots_inconnus` recalibré en conséquence.

### PV-13. Détection des cellules fusionnées

- **À VÉRIFIER** : capacité de `page.find_tables()` à signaler les cellules fusionnées et les en-têtes multiples ; rendu effectif de `table_output="html"` (attributs `colspan` et `rowspan`) ; comportement sur les tableaux de pages reconnues par OCR (sans traits vectoriels).
- **Méthode** : prototype sur le fichier 6, en version native et en version scannée.
- **Repli** : celui de EX-44.

### Autres risques

| Risque | Conséquence | Mesure |
|---|---|---|
| Évolution des interfaces de PyMuPDF4LLM (fusion dans PyMuPDF 2.x en cours) | rupture lors d'une mise à jour | versions verrouillées (EX-10) ; tests de non-régression avant toute montée de version |
| Faux positifs ou faux négatifs de l'heuristique sur documents réels | avertissements ignorés car trop nombreux, ou pages fausses non signalées | seuils réglables, calibrage (EX-76), relevé en recette (TM-08) |
| Antivirus bloquant le lanceur ou le Python du profil | outil inutilisable | PV-01 ; liste des chemins à autoriser dans le guide administrateur |
| Autorisations macOS d'accès aux dossiers demandées à chaque mise à jour | gêne pour l'utilisateur | constat en TM-01 et TM-10 ; consigne dans le guide |
| Texte manuscrit, tampons, pages très dégradées | reconnaissance incomplète sans que la page soit jugée douteuse | limite documentée dans le guide ; l'avertissement général de `_AVERTISSEMENTS.md` rappelle que toute page issue d'un OCR peut comporter des erreurs |
| Obligations de l'AGPL lors de la distribution aux membres | non-conformité | EX-78 |

---

## 11. Spécification du front matter et de la convention d'avertissement

Cette section est normative. Elle est reprise telle quelle dans `docs/specification-front-matter.md`, document de référence pour le socle des skills d'analyse. Toute évolution du schéma incrémente `version_schema` ; un champ n'est jamais supprimé ni renommé au sein d'une même version.

### 11.1 Schéma du front matter (version 1)

Le front matter est un bloc YAML délimité par deux lignes `---`, en tête de fichier, encodé en UTF-8 sans marque d'ordre d'octets, avec des fins de ligne LF. Les champs apparaissent dans l'ordre du tableau. Les chaînes libres (`source`, `date_conversion`, `outil`, `moteur_md`, `origine_texte`) sont entre guillemets doubles ; les valeurs énumérées (`type_source`, `moteur_ocr`, `qualite_texte` et les éléments de `motifs_douteux`) sont écrites sans guillemets ; `origine_texte`, bien qu'à valeurs normalisées, reste entre guillemets car ses valeurs contiennent des deux-points et des apostrophes (correction du 26/11/2026 par le commanditaire) ; les listes sont en notation en ligne (`[3, 4, 9]`) ; une liste vide s'écrit `[]`.

| Champ | Type | Obligatoire | Valeurs et règles |
|---|---|---|---|
| `version_schema` | entier | oui | `1` (ajout du rédacteur, voir annexe B) |
| `source` | chaîne | oui | chemin du fichier source relatif au dossier parent du dossier `_OCR`, séparateur `/`, par exemple `"Lot 1/Candidat B/DC2.pdf"` |
| `type_source` | chaîne | oui | `pdf`, `image`, `docx`, `xlsx`, `pptx` (ajout du rédacteur) |
| `pages` | entier ou `null` | oui | nombre de pages du PDF ou de trames de l'image ; nombre de diapositives pour un .pptx ; `null` pour .docx et .xlsx |
| `date_conversion` | chaîne | oui | date et heure locales au format ISO 8601 avec décalage horaire, par exemple `"2026-11-26T14:32:05+01:00"` |
| `outil` | chaîne | oui | `"ocr-md <version>"` (ajout du rédacteur) |
| `moteur_md` | chaîne | oui | `"pymupdf4llm <version>"`, `"docling <version>"`, ou nom et version de la bibliothèque de conversion Office |
| `moteur_ocr` | chaîne | oui | `apple-vision`, `windows-media-ocr`, `aucun` (aucune page reconnue par l'outil) ; en mode qualité, moteur réellement à l'origine du texte |
| `pages_ocr` | liste d'entiers | oui | pages reconnues par l'outil, numérotées à partir de 1, triées ; `[]` si aucune |
| `qualite_texte` | chaîne | oui | `bonne` ou `douteuse` ; `douteuse` dès qu'une page est douteuse |
| `pages_douteuses` | liste d'entiers | oui | pages douteuses, triées ; `[]` si `qualite_texte: bonne` |
| `origine_texte` | chaîne | oui | l'une des valeurs normalisées de la section 11.2 |
| `pages_couche_existante` | liste d'entiers | oui | pages dont le texte vient d'une couche OCR fournie par l'expéditeur et non refaite ; `[]` sinon (ajout du rédacteur) |
| `motifs_douteux` | liste de chaînes | non | présents si `qualite_texte: douteuse` : noms des indicateurs déclencheurs, par exemple `[taux_mots_inconnus, confiance_ocr_faible]` ; `pdf_repare` pour un PDF réparé à l'ouverture (EX-21) |
| `pages_recuperees` | entier | non | présent seulement avec le motif `pdf_repare` : nombre de pages ayant un contenu après réparation (décision du commanditaire du 26/11/2026) |
| `pages_totales` | entier | non | présent seulement avec le motif `pdf_repare` : nombre de pages du document réparé (décision du commanditaire du 26/11/2026) |

Règles de cohérence : `pages_douteuses` est inclus dans l'ensemble des pages du document ; `pages_ocr` et `pages_couche_existante` sont disjoints ; `qualite_texte: bonne` équivaut à `pages_douteuses: []`.

**Consigne pour le socle des skills** (à reproduire dans la spécification) : lire `qualite_texte` ; si la valeur est `douteuse`, ne tirer aucun montant, date, référence ou conclusion des pages de `pages_douteuses` sans le signaler « à vérifier sur l'original » ; si `pages_couche_existante` n'est pas vide, traiter les montants, dates et références tirés de ces pages comme moins sûrs qu'un texte natif (l'heuristique ne détecte pas les erreurs sur les chiffres) ; en l'absence de front matter, considérer la qualité comme inconnue.

### 11.2 Valeurs normalisées de `origine_texte`

| Situation | Valeur exacte |
|---|---|
| toutes les pages non vides sont natives | `"texte natif du document"` |
| toutes les pages non vides ont été reconnues par l'outil | `"OCR réalisé par l'outil sur l'ensemble du document"` |
| pages natives et pages reconnues par l'outil | `"mixte : texte natif et OCR réalisé par l'outil"` |
| couche OCR de l'expéditeur conservée (avec ou sans pages natives) | `"couche OCR fournie par l'expéditeur, non refaite"` |
| couche de l'expéditeur conservée sur certaines pages et OCR de l'outil sur d'autres | `"mixte : couche OCR fournie par l'expéditeur et OCR réalisé par l'outil"` |
| fichier Office | `"texte natif du document"` |

Le détail par page est donné par `pages_ocr` et `pages_couche_existante` ; toute page qui ne figure dans aucune de ces deux listes est native ou vide.

Correspondance avec le statut du rapport (EX-23) : les deux valeurs qui mentionnent la « couche OCR fournie par l'expéditeur » correspondent au statut `couche_expediteur` (ou `douteux` si une page est douteuse). Dans le front matter, ce cas se reconnaît à une liste `pages_couche_existante` non vide. Une couche d'expéditeur jugée bonne garde `qualite_texte: bonne` et ne reçoit pas de bloc d'avertissement, mais elle n'a pas la fiabilité d'un texte natif (correction du 26/11/2026 par le commanditaire).

### 11.3 Bloc d'avertissement en tête de Markdown

Présent si et seulement si `qualite_texte: douteuse`. Il suit immédiatement le front matter, après une ligne vide. Il est composé d'un titre fixe et d'un ou deux paragraphes selon l'origine des pages douteuses. Les listes de pages sont écrites en clair (« la page 3 », « les pages 3 et 4 », « les pages 3, 4 et 9 »).

Titre fixe :

```
> **AVERTISSEMENT À L'ATTENTION DE TOUT LECTEUR, HUMAIN OU IA**
```

Paragraphe A, pour les pages douteuses issues d'une couche de l'expéditeur :

```
> Le texte des pages {liste} provient d'une reconnaissance de caractères de
> mauvaise qualité réalisée avant réception. Il peut contenir des chiffres, des
> noms ou des dates erronés. Ne pas utiliser ces pages comme source d'un montant,
> d'une date, d'une référence ou d'une conclusion sans vérification sur le PDF
> d'origine. Signaler toute information tirée de ces pages comme « à vérifier ».
```

Paragraphe B, pour les pages douteuses reconnues par l'outil :

```
> Le texte des pages {liste} a été obtenu par reconnaissance de caractères sur
> des pages difficiles à lire (scan dégradé, manuscrit, tampon ou mise en page
> complexe). Il peut contenir des chiffres, des noms ou des dates erronés, ou être
> incomplet. Ne pas utiliser ces pages comme source d'un montant, d'une date,
> d'une référence ou d'une conclusion sans vérification sur le PDF d'origine.
> Signaler toute information tirée de ces pages comme « à vérifier ».
```

Paragraphe C, pour un PDF réparé à l'ouverture (motif `pdf_repare`, EX-21) (décision du commanditaire du 26/11/2026) :

```
> Ce PDF était endommagé et a été réparé à l'ouverture : {N} pages sur {M} ont été
> récupérées. Son contenu peut être incomplet ou désordonné sur toutes les pages. Ne pas
> utiliser ce document comme source d'un montant, d'une date, d'une référence ou d'une
> conclusion sans vérification sur le PDF d'origine.
```

Si plusieurs origines coexistent, les paragraphes se suivent dans l'ordre C, A, B, séparés par une ligne `>` vide.

### 11.4 Repères dans le corps du Markdown

| Cas | Ligne |
|---|---|
| page de PDF ou d'image, saine | `<!-- page N -->` |
| page douteuse | `<!-- page N : TEXTE DOUTEUX, ne pas citer sans vérification sur l'original -->` |
| feuille de classeur | `<!-- feuille N : "Nom de la feuille" -->` |
| diapositive | `<!-- diapositive N -->` |
| tableau détecté sur une page reconnue par OCR | `<!-- tableau reconnu par OCR : correspondance lignes/colonnes non garantie, vérifier sur l'original avant de citer un montant -->` (placé immédiatement avant le tableau, voir EX-44) |

Chaque repère est seul sur sa ligne, précédé et suivi d'une ligne vide.

### 11.5 Fichier `_AVERTISSEMENTS.md`

Structure imposée (les listes sont triées par chemin) :

```markdown
---
version_schema: 1
type: avertissements
dossier: "_OCR"
date_mise_a_jour: "2026-11-26T14:40:12+01:00"
outil: "ocr-md 1.0.0"
pieces_total: 42
pieces_douteuses: 2
pieces_non_converties: 3
pieces_en_erreur: 1
---

# Avertissements sur les pièces de ce dossier

> **À L'ATTENTION DE TOUT LECTEUR, HUMAIN OU IA**
> Ce dossier contient des versions lisibles (PDF consultables et Markdown) de
> documents reçus de tiers. Lire ce fichier avant d'exploiter les autres.
> 1. Le texte des pages listées ci-dessous comme douteuses peut être faux : ne pas
>    en tirer de montant, de date, de référence ni de conclusion sans vérification
>    sur le document d'origine, et signaler toute information qui en provient
>    comme « à vérifier ».
> 2. Les pièces listées comme non converties ou en erreur existent dans le dossier
>    d'origine mais sont absentes d'ici : ne pas conclure à l'absence d'une pièce
>    dans un pli sans consulter ces listes.
> 3. Toute page obtenue par reconnaissance de caractères, même non signalée, peut
>    comporter des erreurs ponctuelles : en cas d'enjeu, vérifier sur l'original.

## Pièces dont le texte est douteux

| Pièce | Pages douteuses | Origine du texte | Motif |
|---|---|---|---|
| Lot 1/Candidat B/DC2.pdf | 3, 4, 9 | couche OCR fournie par l'expéditeur, non refaite | taux_mots_inconnus |

Pour refaire la reconnaissance des pages douteuses d'une pièce :
`ocr-md --refaire-ocr "<chemin complet de la pièce d'origine>"`

## Pièces non converties (format non pris en charge)

| Pièce | Raison |
|---|---|
| Lot 1/Candidat A/Attestation.doc | ancien format Office : l'enregistrer au format .docx, .xlsx ou .pptx, ou en PDF, puis relancer |

## Pièces en erreur

| Pièce | Erreur |
|---|---|
| Lot 1/Candidat C/Offre.pdf | PDF protégé par mot de passe |
```

Lorsqu'une rubrique est vide, son tableau est remplacé par la phrase « Aucune. ». Lorsque les trois rubriques sont vides, le corps du fichier, après l'encadré, contient la phrase « Aucune pièce de ce dossier n'est signalée. ».

### 11.6 Rapport `ocr_rapport.csv`

**EX-82. Format du rapport.** Le rapport doit être un fichier CSV encodé en **UTF-8 avec marque d'ordre d'octets (BOM)**, séparateur **point-virgule**, fins de ligne CRLF, champs entre guillemets doubles seulement lorsqu'ils contiennent un point-virgule, un guillemet ou un saut de ligne (guillemets internes doublés ; équivalent de `csv.QUOTE_MINIMAL`), décimales avec **virgule**. Justification : un double-clic l'ouvre correctement dans Excel configuré en français (accents, colonnes, nombres). Une ligne d'en-tête, puis une ligne par fichier source, triées par chemin. Les listes de pages sont écrites avec des **espaces** comme séparateurs et sans plages (par exemple `3 4 9`), afin qu'Excel ne les interprète ni comme un nombre décimal ni comme une date. Colonnes, dans cet ordre :

| Colonne | Contenu |
|---|---|
| `chemin_relatif` | identique au champ `source` |
| `type` | `pdf`, `image`, `docx`, `xlsx`, `pptx`, `autre` |
| `pages` | nombre de pages, vide si sans objet |
| `statut` | `natif`, `ocrise`, `mixte`, `couche_expediteur`, `douteux`, `non_pris_en_charge`, `erreur` |
| `pages_ocr` | liste des pages reconnues par l'outil |
| `pages_douteuses` | liste des pages douteuses |
| `motif_douteux` | indicateurs déclencheurs, séparés par des espaces |
| `origine_texte` | valeur de la section 11.2 |
| `sorties` | noms des fichiers produits, séparés par ` \| ` (barre verticale entourée d'espaces) ; vide si aucun |
| `action` | `traite`, `ignore_a_jour`, `annule` |
| `duree_s` | durée du traitement en secondes, une décimale, virgule décimale ; vide si `ignore_a_jour` |
| `date_traitement` | date et heure locales du dernier traitement effectif, format `AAAA-MM-JJ HH:MM:SS` |
| `message` | message d'erreur ou d'information, en français, sur une seule ligne |
| `version_outil` | version de l'outil ayant produit les sorties |

Lors d'une relance portant sur une partie seulement des éléments d'un dossier parent, les lignes des fichiers non concernés sont conservées ; les lignes des fichiers concernés sont remplacées.
- CA : le fichier s'ouvre par double-clic dans Excel en français avec les colonnes séparées et les accents corrects (TM-03) ; relu par le module `csv` de Python avec `delimiter=";"` et `encoding="utf-8-sig"`, il donne les 14 colonnes attendues ; un nom de fichier contenant un point-virgule et un guillemet est restitué intact ; les nombres de la fenêtre de fin se recalculent à partir de ses lignes.

### 11.7 Exemples complets

#### Exemple 1 : document sain (PDF natif)

Fichier `_OCR/Lot 1/Candidat A/Mémoire technique.pdf.md` :

```markdown
---
version_schema: 1
source: "Lot 1/Candidat A/Mémoire technique.pdf"
type_source: pdf
pages: 2
date_conversion: "2026-11-26T14:32:05+01:00"
outil: "ocr-md 1.0.0"
moteur_md: "pymupdf4llm 2.2.0"
moteur_ocr: aucun
pages_ocr: []
qualite_texte: bonne
pages_douteuses: []
origine_texte: "texte natif du document"
pages_couche_existante: []
---

<!-- page 1 -->

# Mémoire technique

## 1. Compréhension de la mission

Le groupement propose une équipe de maîtrise d'œuvre composée de…

<!-- page 2 -->

## 2. Moyens humains

| Intervenant | Fonction | Temps prévu (jours) |
|---|---|---|
| Mme X | Architecte mandataire | 42 |
| M. Y | Ingénieur fluides | 18 |
```

(Les numéros de version de cet exemple sont illustratifs.)

#### Exemple 2 : document douteux (couche OCR de l'expéditeur)

Fichier `_OCR/Lot 1/Candidat B/DC2.pdf.md` (extrait : pages 1 à 4 sur 14) :

```markdown
---
version_schema: 1
source: "Lot 1/Candidat B/DC2.pdf"
type_source: pdf
pages: 14
date_conversion: "2026-11-26T14:33:41+01:00"
outil: "ocr-md 1.0.0"
moteur_md: "pymupdf4llm 2.2.0"
moteur_ocr: aucun
pages_ocr: []
qualite_texte: douteuse
pages_douteuses: [3, 4, 9]
origine_texte: "couche OCR fournie par l'expéditeur, non refaite"
pages_couche_existante: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]
motifs_douteux: [taux_mots_inconnus, taux_melange_chiffres_lettres]
---

> **AVERTISSEMENT À L'ATTENTION DE TOUT LECTEUR, HUMAIN OU IA**
> Le texte des pages 3, 4 et 9 provient d'une reconnaissance de caractères de
> mauvaise qualité réalisée avant réception. Il peut contenir des chiffres, des
> noms ou des dates erronés. Ne pas utiliser ces pages comme source d'un montant,
> d'une date, d'une référence ou d'une conclusion sans vérification sur le PDF
> d'origine. Signaler toute information tirée de ces pages comme « à vérifier ».

<!-- page 1 -->

DC2 : DÉCLARATION DU CANDIDAT INDIVIDUEL OU DU MEMBRE DU GROUPEMENT

<!-- page 2 -->

A - Identification de l'acheteur

<!-- page 3 : TEXTE DOUTEUX, ne pas citer sans vérification sur l'original -->

Chiffre d'affa1res g1obal H T : 1 2S4 0O0 eur0s

<!-- page 4 : TEXTE DOUTEUX, ne pas citer sans vérification sur l'original -->

Eff ectifs m0yens annue1s
```

Métadonnées du PDF consultable correspondant (`_OCR/Lot 1/Candidat B/DC2.pdf`) :

```
Sujet     : TEXTE DOUTEUX pages 3, 4, 9 : ne pas citer ces pages sans vérification sur l'original.
Mots-clés : qualite_texte=douteuse; pages_douteuses=3,4,9; origine=couche OCR fournie par l'expéditeur, non refaite; ocr-md
```

Ligne correspondante de `ocr_rapport.csv` :

```
Lot 1/Candidat B/DC2.pdf;pdf;14;douteux;;3 4 9;taux_mots_inconnus taux_melange_chiffres_lettres;couche OCR fournie par l'expéditeur, non refaite;DC2.pdf | DC2.pdf.md;traite;2,4;2026-11-26 14:33:41;;1.0.0
```

#### Exemple 3 : document mixte (pages natives et pages reconnues par l'outil, dont une douteuse)

Fichier `_OCR/Lot 1/Candidat C/Candidature complète.pdf.md` (6 pages : 1 à 3 natives, 4 et 5 scannées, 6 vide) :

```markdown
---
version_schema: 1
source: "Lot 1/Candidat C/Candidature complète.pdf"
type_source: pdf
pages: 6
date_conversion: "2026-11-26T14:35:02+01:00"
outil: "ocr-md 1.0.0"
moteur_md: "pymupdf4llm 2.2.0"
moteur_ocr: apple-vision
pages_ocr: [4, 5]
qualite_texte: douteuse
pages_douteuses: [5]
origine_texte: "mixte : texte natif et OCR réalisé par l'outil"
pages_couche_existante: []
motifs_douteux: [confiance_ocr_faible]
---

> **AVERTISSEMENT À L'ATTENTION DE TOUT LECTEUR, HUMAIN OU IA**
> Le texte de la page 5 a été obtenu par reconnaissance de caractères sur
> des pages difficiles à lire (scan dégradé, manuscrit, tampon ou mise en page
> complexe). Il peut contenir des chiffres, des noms ou des dates erronés, ou être
> incomplet. Ne pas utiliser ces pages comme source d'un montant, d'une date,
> d'une référence ou d'une conclusion sans vérification sur le PDF d'origine.
> Signaler toute information tirée de ces pages comme « à vérifier ».

<!-- page 1 -->

# Lettre de candidature

<!-- page 2 -->

Présentation du groupement

<!-- page 3 -->

Liste des références

<!-- page 4 -->

ATTESTATION D'ASSURANCE RESPONSABILITÉ CIVILE PROFESSIONNELLE

<!-- page 5 : TEXTE DOUTEUX, ne pas citer sans vérification sur l'original -->

Attestation de régularité fiscale délivrée le

<!-- page 6 -->

*(page sans texte exploitable)*
```

Le même document, lorsque la page 5 est correctement reconnue, porte `qualite_texte: bonne`, `pages_douteuses: []`, n'a ni champ `motifs_douteux` ni bloc d'avertissement, et sa page 5 commence par `<!-- page 5 -->`.

---

## Annexe A. Sources consultées le 26 novembre 2026

| Sujet | URL |
|---|---|
| Limites de lecture des PDF par Claude | https://support.claude.com/en/articles/8241126-upload-files-to-claude |
| `uv` : installation, emplacement, mise à jour, désinstallation | https://docs.astral.sh/uv/getting-started/installation/ |
| `uv` : options de l'installateur | https://docs.astral.sh/uv/reference/installer/ |
| `uv` : faux positif Windows Defender | https://github.com/astral-sh/uv/issues/1587 |
| PyMuPDF4LLM : dépôt | https://github.com/pymupdf/pymupdf4llm |
| PyMuPDF4LLM : documentation | https://pymupdf.readthedocs.io/en/latest/pymupdf4llm |
| PyMuPDF4LLM : API | https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/api.html |
| PyMuPDF : OCR, greffons, signature de la fonction OCR | https://pymupdf.readthedocs.io/en/latest/ocr/index.html |
| PyMuPDF : `Document.to_markdown` | https://pymupdf.readthedocs.io/en/latest/document.html |
| PyMuPDF : `insert_text`, `get_textpage_ocr` | https://pymupdf.readthedocs.io/en/latest/page.html |
| PyMuPDF : modes de rendu du texte | https://pymupdf.readthedocs.io/en/latest/shape.html |
| PyMuPDF : polices et caractères au-delà d'Unicode 256 | https://pymupdf.readthedocs.io/en/latest/faq/ |
| PyMuPDF : ticket sur `pymupdf.layout` | https://github.com/PyMuPDF/PyMuPDF/issues/4833 |
| PyMuPDF4LLM : présentation « layout » (non relue ce jour, citée en préparation) | https://artifex.com/blog/introducing-the-new-pymupdf4llm-now-including-layout |
| Docling : moteurs OCR (non relue ce jour, citée en préparation) | https://docling-project.github.io/docling/concepts/OCR/ |
| Docling : installation | https://docling-project.github.io/docling/getting_started/installation/ |
| Docling : modèles, hors ligne | https://docling-project.github.io/docling/usage/advanced_options |
| Docling : FAQ | https://docling-project.github.io/docling/faq |
| ocrmac | https://pypi.org/project/ocrmac |
| Greffon OCRmyPDF pour Apple Vision (non relue ce jour, citée en préparation) | https://pypi.org/project/ocrmypdf-appleocr/ |
| winocr | https://pypi.org/project/winocr |
| winocrfix (non relue ce jour, citée en préparation) | https://pypi.org/project/winocrfix/ |
| Projection PyWinRT de `Windows.Media.Ocr` | https://pypi.org/project/winrt-windows-media-ocr |
| `OcrWord` (absence d'indice de confiance) | https://learn.microsoft.com/en-us/uwp/api/windows.media.ocr.ocrword |
| `OcrEngine` | https://learn.microsoft.com/en-us/uwp/api/windows.media.ocr.ocrengine |
| Fonctionnalités de langue à la demande (OCR) | https://learn.microsoft.com/windows-hardware/manufacture/desktop/features-on-demand-language-fod |
| PowerToys Text Extractor : commandes de contrôle des langues OCR | https://learn.microsoft.com/windows/powertoys/text-extractor |
| Menu « Envoyer vers » | https://devblogs.microsoft.com/oldnewthing/20170403-00/?p=95885/ |
| Action rapide du Finder avec script shell | https://developer.apple.com/forums/thread/742419 |
| kDrive Lite Sync, Windows | https://www.infomaniak.com/en/support/faq/2562/lite-sync-kdrive-windows |
| kDrive Lite Sync, macOS | https://infomaniak.com/en/support/faq/2608/managing-the-lite-sync-option-on-kdrive-macos |

## Annexe B. Propositions et interprétations du rédacteur

Ces choix ne figurent pas dans les décisions du commanditaire. Ils ont été arrêtés pour rendre le document exécutable et peuvent être révisés sans remettre en cause le reste.

1. **Articulation entre « OCR une seule fois », « Markdown à partir du PDF consultable » et « `ocr_function` »** (section 3.1) : l'adaptateur conforme à `ocr_function` est appliqué par l'outil lui-même pour fabriquer le PDF consultable, puis passé à PyMuPDF4LLM comme garde-fou, sans nouvelle reconnaissance.
2. **Emplacement exact du dossier miroir** (EX-50) : un dossier `_OCR` unique dans le dossier parent de l'élément traité, contenant un sous-dossier au nom du dossier traité ; pour des fichiers sélectionnés isolément, `_OCR` dans leur dossier.
3. **Nommage des sorties** (EX-51) : extension de la source conservée dans le nom du Markdown (`DC2.pdf.md`), pour éviter les collisions.
4. **Champs ajoutés au front matter** au-delà du minimum demandé : `version_schema`, `type_source`, `outil`, `pages_couche_existante`, `motifs_douteux` ; valeurs normalisées de `origine_texte` (section 11.2).
5. **Colonnes ajoutées au rapport** : `motif_douteux`, `origine_texte`, `action`, `date_traitement`, `version_outil`.
6. **Options ajoutées à la commande** : `--forcer`, `--pages`, `--tableaux`, `--sans-interface`, `--config`, sous-commandes `verifier` et `raccourcis` ; portée `douteuses` ou `tout` de `--refaire-ocr`.
7. **Préfixe commun des libellés de menu** (REC-01) et absence de quatrième entrée pour `--refaire-ocr` (REC-04).
8. **Repères propres aux fichiers Office** (`feuille`, `diapositive`) et `pages: null` pour .docx et .xlsx.
9. **Copie à l'identique des PDF natifs sains** dans `_OCR` lorsque la sortie PDF est demandée (EX-32).
10. **Python 3.12 figé** (EX-09) et projection PyWinRT préférée à `winocr` (REC-03), déduits des vérifications.
11. **Valeurs par défaut des seuils et objectifs chiffrés** (EX-22, EX-35, EX-36, EX-58, section 7.3) : valeurs de départ ou objectifs, non mesurés.
12. **Licence du projet** : AGPL-3.0, par cohérence avec PyMuPDF (EX-78).
