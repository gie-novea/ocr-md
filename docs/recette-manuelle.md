# Recette manuelle d'ocr-md (section 7.4)

Fiches exécutées par le référent sur de vrais postes, sous compte standard, avec des documents synthétiques ou non confidentiels (jamais de pli réel confidentiel hors de TM-08). Pour chaque fiche : cocher chaque contrôle, noter le constat (et toute alerte du système, mot pour mot), dater et signer. Les captures du guide utilisateur (`[CAPTURE : …]`) peuvent être faites pendant TM-02 et TM-03.

Postes : ☐ Windows 10 ☐ Windows 11 ☐ Mac Apple Silicon (macOS ……) ☐ Mac Intel (macOS ……), si le parc en compte.

---

## TM-01. Installation sur poste vierge, compte standard

Plateformes : Mac Apple Silicon, Mac Intel si le parc en compte, Windows 10, Windows 11.

1. ☐ Windows : télécharger l'archive de la version candidate (https://github.com/gie-novea/ocr-md/archive/refs/tags/v1.0.0-rc1.zip), l'extraire, double-cliquer sur `installation\installer-windows.cmd`.
2. ☐ macOS : coller la ligne d'installation du guide dans le Terminal ; puis, sur un second poste ou après désinstallation, essayer le secours (double-clic sur le `.command`, clic droit puis « Ouvrir »).
3. ☐ Aucune demande de mot de passe administrateur ni d'élévation.
4. ☐ Message final « Installation terminée » ; diagnostic sans ligne `[X]` (sauf module OCR absent, voir TM-04).
5. ☐ Relever toute alerte : SmartScreen, antivirus, AppLocker, stratégie d'exécution PowerShell, Gatekeeper, demandes d'autorisation de macOS (accès aux dossiers).
6. ☐ Derrière le pare-feu de la SODEB : installation réussie avec les seules adresses de la section 6 du guide administrateur.
7. ☐ Relancer le script : succès, aucun raccourci en double.

Résultat attendu : outil installé dans le profil ; `ocr-md --version` affiche la version, la licence et l'adresse du code source.

Constat : …………………………………………… Date : ………… Visa : …………

## TM-02. Les trois entrées de menu

Plateformes : toutes.

1. ☐ Clic droit sur 1 fichier PDF scanné : « OCR - Les deux » ; sous Windows 11, accès par « Afficher d'autres options », puis « Envoyer vers ».
2. ☐ Sélection de 30 fichiers : chacun figure au rapport.
3. ☐ Sélection de 2 dossiers : tous leurs fichiers figurent au rapport.
4. ☐ Mélange de fichiers et de dossiers.
5. ☐ Windows : sélection de 200 fichiers aux noms longs (PV-02) : comportement noté ; si la sélection approche la limite, le message de la fenêtre de fin s'affiche.
6. ☐ Chaque entrée produit la bonne sortie : PDF seul, Markdown seul, les deux (journal : `options : sortie=…`).
7. ☐ Aucune fenêtre de console ne s'ouvre ; seule la fenêtre de l'outil est visible.
8. ☐ `ocr-md raccourcis --supprimer` retire les trois entrées et elles seules ; `--creer` les rétablit.

Constat : …………………………………………… Date : ………… Visa : …………

## TM-03. Progression, annulation, fenêtre de fin

Plateformes : toutes. Lot de 20 fichiers, dont quelques PDF scannés.

1. ☐ La fenêtre montre le fichier en cours, son rang sur le total et la page en cours pendant l'OCR.
2. ☐ « Annuler » arrête après la page en cours ; aucun fichier partiel dans `_OCR` ; le rapport mentionne les fichiers non traités.
3. ☐ Fenêtre de fin : nombres égaux à ceux du rapport `ocr_rapport.csv` (traités, signalés, en erreur, ignorés car à jour).
4. ☐ « Ouvrir le dossier » ouvre le dossier `_OCR`.
5. ☐ La fenêtre ne se ferme pas seule s'il y a des fichiers signalés ou en erreur.
6. ☐ Le rapport s'ouvre par double-clic dans Excel en français : colonnes séparées, accents corrects.
7. ☐ macOS : relever le comportement de l'icône dans le Dock pendant le traitement.

Constat : …………………………………………… Date : ………… Visa : …………

## TM-04. PC sans module OCR français

Plateforme : Windows.

1. ☐ Sur un poste sans le module : `ocr-md verifier` affiche le message de EX-71 et la commande à transmettre.
2. ☐ Traitement d'un dossier mixte : PDF natifs et fichiers Office traités ; PDF scannés en erreur avec le message ; fenêtre de fin qui l'affiche.
3. ☐ Installation du module par l'administrateur, puis relance : PDF scannés traités.

Constat : …………………………………………… Date : ………… Visa : …………

## TM-05. PDF consultable

Plateformes : toutes.

1. ☐ Recherche d'un mot accentué (« maîtrise », « œuvre », « Lætitia ») dans Aperçu, Adobe Acrobat Reader, un navigateur : trouvé et surligné au bon endroit.
2. ☐ Sélection et copier-coller d'un paragraphe : texte correct, mots séparés.
3. ☐ Aspect visuel identique à l'original.

Constat : …………………………………………… Date : ………… Visa : …………

## TM-06. Poste déconnecté du réseau

Plateformes : toutes.

1. ☐ Couper le réseau (Wi-Fi et câble), traiter un dossier mixte : traitement complet, résultats identiques à ceux d'un poste connecté.

Constat : …………………………………………… Date : ………… Visa : …………

## TM-07. Dossier kDrive en Lite Sync

Plateformes : toutes. Dossier kDrive de test, fichiers synthétiques seulement.

1. ☐ Fichiers « en ligne uniquement » : téléchargés à la lecture, ou mis en erreur avec le message de EX-64 après `delai_hydratation_s` ; le lot continue.
2. ☐ Dossier `_OCR` créé dans kDrive et synchronisé sans conflit ni doublon ; relance sans erreur de verrouillage.

Constat : …………………………………………… Date : ………… Visa : …………

## TM-08. Lot réel de 50 plis : performance et qualité

Plateformes : toutes. Lot anonymisé ou non confidentiel.

1. ☐ Performance (EX-58) : durée totale, pages par minute, durée de la relance, mémoire maximale (Gestionnaire des tâches ou Moniteur d'activité). Objectifs : moins de 20 minutes, relance en moins de 30 secondes, moins de 1,5 Go. Pour un relevé chiffré comparable : `uv run python tests/perf/lot_type.py` depuis une copie du dépôt.
2. ☐ Sur un vrai Mac (Apple Silicon, et Intel si le parc en compte) : durée totale et mémoire maximale du même lot (Moniteur d'activité, colonne « Mémoire » du processus Python d'ocr-md), à comparer aux relevés de l'intégration continue (Apple Silicon : 8 min 36 s et 714 Mo ; Intel : 13 min 55 s et 530 Mo, sur le lot type).
   Durée : ………… Mémoire maximale : ………… Modèle et macOS : …………
3. ☐ Mémoire vive des Mac du parc : relever pour chaque modèle si elle est de 8 Go ou plus (la mémoire maximale de l'outil atteint 0,7 Go sur le lot type ; un Mac à 8 Go reste confortable si peu d'applications sont ouvertes, un Mac à moins de 8 Go est à essayer en priorité).
   Modèles et mémoire : ……………………………………
4. ☐ Relecture par sondage de 20 pages reconnues : texte conforme ; montants exacts.
5. ☐ Faux positifs (pages saines signalées douteuses) et faux négatifs (pages fausses non signalées) : relevés page par page avec le motif. Priorité : seuils de confiance de Vision, de résolution de l'image (scans à 200 dpi), de bruit et de netteté, de mots inconnus.
6. ☐ Calibrage : `uv run python tests/calibrage.py DOSSIER --moteur systeme` sur un dossier local des pages relues ; proposer les seuils ajustés au commanditaire (guide administrateur, section 9).

Constat : …………………………………………… Date : ………… Visa : …………

## TM-09. Dépôt des sorties dans Claude

Plateforme : une.

1. ☐ Déposer dans Claude le Markdown d'un pli et `_AVERTISSEMENTS.md`.
2. ☐ Question portant sur une page douteuse : la réponse mentionne la réserve (texte à vérifier).
3. ☐ Demande de citation avec le numéro de page : citation exacte, page exacte.

Constat : …………………………………………… Date : ………… Visa : …………

## TM-10. Mise à jour puis désinstallation

Plateformes : toutes.

1. ☐ Avec une version n installée et un fichier de configuration personnalisé : `mettre-a-jour-…` affiche l'ancienne et la nouvelle version ; `ocr-md --version` affiche n+1 ; configuration conservée ; raccourcis fonctionnels.
2. ☐ `desinstaller-…` : aucune entrée de menu ne subsiste ; aucun fichier de l'outil dans le profil hors éléments conservés à la demande ; dossiers `_OCR` intacts ; `uv` conservé si on le demande.

Constat : …………………………………………… Date : ………… Visa : …………

## TM-11. DPGF scannée réelle dans Aperçu

Plateforme : Mac. DPGF non confidentielle ou anonymisée.

1. ☐ PDF consultable ouvert dans Aperçu : recherche de plusieurs montants, avec et sans espace des milliers, avec virgule décimale ; chaque montant est trouvé et surligné à son emplacement.

Constat : …………………………………………… Date : ………… Visa : …………
