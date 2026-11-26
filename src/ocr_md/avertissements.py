"""Signalement des textes douteux : métadonnées du PDF consultable (EX-33).

Le front matter, le bloc d'avertissement, les repères de page et `_AVERTISSEMENTS.md`
seront ajoutés au jalon 7.
"""

MARQUE = "ocr-md"


def _liste(pages, sep=","):
    return sep.join(str(p) for p in pages)


def _sans_ancienne_marque(texte: str, debut: str) -> str:
    """Retire un avertissement d'ocr-md déjà présent (PDF déjà passé par l'outil)."""
    return "" if texte.startswith(debut) else texte


def metadonnees_pdf(origine_meta: dict, *, pages_douteuses, pages_ocr, origine: str, moteur: str) -> dict:
    """Métadonnées du PDF consultable : Sujet et Mots-clés d'avertissement, les autres
    métadonnées d'origine (Titre, Auteur) étant conservées."""
    meta = dict(origine_meta)
    sujet = (meta.get("subject") or "").strip()
    mots = (meta.get("keywords") or "").strip()
    if pages_douteuses:
        sujet = _sans_ancienne_marque(sujet, "TEXTE DOUTEUX")
        mots = _sans_ancienne_marque(mots, "qualite_texte=")
        meta["subject"] = (f"TEXTE DOUTEUX pages {_liste(pages_douteuses, ', ')} : ne pas citer ces pages sans "
                           f"vérification sur l'original. {sujet}").rstrip()
        meta["keywords"] = (f"qualite_texte=douteuse; pages_douteuses={_liste(pages_douteuses)}; "
                            f"origine={origine}; {MARQUE} {mots}").rstrip()
    else:
        mots = _sans_ancienne_marque(mots, "qualite_texte=")
        meta["keywords"] = (f"qualite_texte=bonne; pages_ocr={_liste(pages_ocr)}; moteur_ocr={moteur}; "
                            f"{MARQUE} {mots}").rstrip()
    return meta
