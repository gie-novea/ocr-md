# ocr-md : consignes permanentes

- Spécification de référence : docs/cahier-des-charges.md. En cas de doute, elle prime ; toute
  divergence se signale avant d'être codée.
- Langue : français pour le code commenté, les messages, la documentation et les commits.
  Aucun tiret cadratin dans les textes produits.
- Périmètre : v1 uniquement (section 8.1). Ne rien commencer de la v1.1 (Docling) sans accord.
- Données : uniquement le jeu de test synthétique (section 7.1). Ne jamais lire, copier ni
  versionner de vrais plis ; ne jamais lire F:\kDrive.
- Avancement : tenir docs/avancement.md à jour à chaque fin de jalon (fait, reste à faire,
  points PV tranchés avec leur résultat, écarts au cahier des charges).
- Points à vérifier (PV-xx) : les traiter par un essai minimal et isolé avant de coder la
  fonctionnalité qui en dépend ; consigner le résultat dans docs/avancement.md.
- Arrêts obligatoires : après le plan, après les essais de faisabilité, en fin de v1.
- Commits : un par jalon, message en français.