# Spécification du front matter et de la convention d'avertissement

Document généré par `outils/documentation.py` à partir de la section 11 du cahier des charges (`docs/cahier-des-charges.md`), qui fait foi ; schéma JSON : `schema/front-matter-v1.json`. Destiné au socle des skills qui lisent les sorties d'ocr-md.

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
| `version_regles` | entier | oui | version des règles de verdict et de format ayant produit le fichier (EX-52, décision du commanditaire du 27/11/2026) |
| `moteur_md` | chaîne | oui | `"pymupdf4llm <version>"`, `"docling <version>"`, ou nom et version de la bibliothèque de conversion Office |
| `moteur_ocr` | chaîne | oui | `apple-vision`, `windows-media-ocr`, `aucun` (aucune page reconnue par l'outil) ; en mode qualité, moteur réellement à l'origine du texte |
| `pages_ocr` | liste d'entiers | oui | pages reconnues par l'outil, numérotées à partir de 1, triées ; `[]` si aucune |
| `qualite_texte` | chaîne | oui | `bonne` ou `douteuse` ; `douteuse` dès qu'une page est douteuse |
| `pages_douteuses` | liste d'entiers | oui | pages douteuses, triées ; `[]` si `qualite_texte: bonne` |
| `origine_texte` | chaîne | oui | l'une des valeurs normalisées de la section 11.2 |
| `pages_couche_existante` | liste d'entiers | oui | pages dont le texte vient d'une couche OCR fournie par l'expéditeur et non refaite ; `[]` sinon (ajout du rédacteur) |
| `motifs_douteux` | liste de chaînes | non | présents si `qualite_texte: douteuse` : noms des indicateurs déclencheurs, par exemple `[taux_mots_inconnus, confiance_ocr_faible]` ; `image_faible_qualite` pour une page reconnue par l'outil dont l'image est de faible qualité (EX-35) ; `pdf_repare` pour un PDF réparé à l'ouverture (EX-21) |
| `pages_recuperees` | entier | non | présent seulement avec le motif `pdf_repare` : nombre de pages ayant un contenu après réparation (décision du commanditaire du 26/11/2026) |
| `pages_totales` | entier | non | présent seulement avec le motif `pdf_repare` : nombre de pages du document réparé (décision du commanditaire du 26/11/2026) |
| `qualite_image` | chaîne | non | présent si l'outil a reconnu des pages : `mediocre` dès qu'une page reconnue a une image médiocre (EX-35), `bonne` sinon. Information secondaire, sans incidence sur `qualite_texte` ni bloc d'avertissement (décision du commanditaire, recette du 27/11/2026) |

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

**Mention des révisions et commentaires d'un .docx** (décision du commanditaire du 27/11/2026, EX-45). Un .docx qui contient des révisions non acceptées ou des commentaires reçoit, immédiatement après le front matter, une mention en citation (lignes commençant par `> `). Elle n'est pas un avertissement de qualité : le document garde `qualite_texte: bonne` et le statut `natif`. Selon le cas :

```
> Document contenant des révisions non acceptées et {N} commentaires : texte présenté
> dans son état final (insertions acceptées, suppressions écartées), commentaires non
> repris.
```

```
> Document contenant des révisions non acceptées : texte présenté dans son état final
> (insertions acceptées, suppressions écartées).
```

```
> Document contenant {N} commentaires : commentaires non repris.
```

« commentaires » s'écrit au singulier pour N = 1. La colonne `revisions_commentaires` du rapport (11.6) porte la même information.

### 11.4 Repères dans le corps du Markdown

| Cas | Ligne |
|---|---|
| page de PDF ou d'image, saine | `<!-- page N -->` |
| page douteuse | `<!-- page N : TEXTE DOUTEUX, ne pas citer sans vérification sur l'original -->` |
| page reconnue par l'outil sur une image médiocre (EX-35), non douteuse | `<!-- page N : OCR sur image médiocre (CAUSES) ; vérifier chiffres et références sur l'original -->`, où CAUSES reprend les causes abrégées séparées par des virgules : résolution (`150 dpi`), `flou`, `bruit`, `contraste faible`. Pas de bloc d'avertissement ni de statut douteux. Justification (décision du commanditaire du 27/11/2026) : les pages courtes (RIB, extrait Kbis, attestations) n'atteignent jamais 40 mots évaluables, n'entrent donc pas dans la règle du texte limite, et portent pourtant les chiffres qui comptent |
| feuille de classeur | `<!-- feuille N : "Nom de la feuille" -->` |
| diapositive | `<!-- diapositive N -->`, suivi de la ligne `*(diapositive masquée)*` si la diapositive est masquée |
| zone de texte d'un .docx | `<!-- zone de texte -->`, placé après le paragraphe qui porte la zone (son ancrage), avant le texte de la zone |
| feuilles masquées d'un classeur | `<!-- feuilles masquées -->`, en fin de document, suivi de la phrase `Feuilles masquées du classeur, contenu non repris : "Nom", "Nom".` |
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
