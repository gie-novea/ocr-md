"""Signalement des textes douteux (EX-33, EX-46 à EX-49, section 11).

Front matter YAML, bloc d'avertissement en tête du Markdown, métadonnées du PDF
consultable et fichier `_AVERTISSEMENTS.md` d'un dossier `_OCR`. La liste des pages
douteuses est la même partout (EX-49) : elle vient du résultat du traitement du fichier.
"""

import datetime
import pathlib
import textwrap

from . import __version__

MARQUE = "ocr-md"
NOM_AVERTISSEMENTS = "_AVERTISSEMENTS.md"
ORIGINE_COUCHE = "couche OCR fournie par l'expéditeur, non refaite"


# ------------------------------------------------------------------------------ outils
def date_iso() -> str:
    return datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()


def _liste(pages, sep=","):
    return sep.join(str(p) for p in pages)


def pages_en_clair(pages) -> str:
    """« de la page 5 », « des pages 3 et 4 », « des pages 3, 4 et 9 »."""
    pages = list(pages)
    if len(pages) == 1:
        return f"de la page {pages[0]}"
    return "des pages " + ", ".join(map(str, pages[:-1])) + f" et {pages[-1]}"


def _chaine(valeur: str) -> str:
    """Chaîne libre YAML entre guillemets doubles (section 11.1)."""
    return '"' + valeur.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _valeur(valeur, libre: bool) -> str:
    if valeur is None:
        return "null"
    if isinstance(valeur, bool):
        return "true" if valeur else "false"
    if isinstance(valeur, int):
        return str(valeur)
    if isinstance(valeur, (list, tuple)):
        return "[" + ", ".join(_valeur(v, libre) for v in valeur) + "]"
    return _chaine(str(valeur)) if libre else str(valeur)


# Champs dans l'ordre de la section 11.1 ; True : chaîne libre (entre guillemets).
CHAMPS = (("version_schema", False), ("source", True), ("type_source", False), ("pages", False),
          ("date_conversion", True), ("outil", True), ("moteur_md", True), ("moteur_ocr", False),
          ("pages_ocr", False), ("qualite_texte", False), ("pages_douteuses", False), ("origine_texte", True),
          ("pages_couche_existante", False), ("motifs_douteux", False), ("pages_recuperees", False),
          ("pages_totales", False))
FACULTATIFS = {"motifs_douteux", "pages_recuperees", "pages_totales"}


def front_matter(champs: dict) -> str:
    """Bloc YAML délimité par « --- », champs dans l'ordre de la section 11.1."""
    lignes = ["---"]
    for nom, libre in CHAMPS:
        if nom in FACULTATIFS and champs.get(nom) in (None, [], ()):
            continue
        lignes.append(f"{nom}: {_valeur(champs[nom], libre)}")
    lignes.append("---")
    return "\n".join(lignes) + "\n"


def champs_document(*, source: str, type_source: str, pages, moteur_md: str, moteur_ocr: str, pages_ocr,
                    pages_douteuses, origine: str, pages_couche_existante, motifs=(), pages_recuperees=None,
                    pages_totales=None) -> dict:
    return {
        "version_schema": 1, "source": source, "type_source": type_source, "pages": pages,
        "date_conversion": date_iso(), "outil": f"ocr-md {__version__}", "moteur_md": moteur_md,
        "moteur_ocr": moteur_ocr, "pages_ocr": sorted(pages_ocr),
        "qualite_texte": "douteuse" if pages_douteuses else "bonne", "pages_douteuses": sorted(pages_douteuses),
        "origine_texte": origine, "pages_couche_existante": sorted(pages_couche_existante),
        "motifs_douteux": list(motifs) if pages_douteuses else [],
        "pages_recuperees": pages_recuperees, "pages_totales": pages_totales,
    }


# ------------------------------------------------------------------------------ bloc d'avertissement
TITRE = "**AVERTISSEMENT À L'ATTENTION DE TOUT LECTEUR, HUMAIN OU IA**"


def _paragraphe(texte: str) -> list[str]:
    return ["> " + l for l in textwrap.wrap(texte, width=82)]


def bloc_avertissement(pages_couche, pages_outil, repare: tuple[int, int] | None = None) -> str:
    """Bloc de la section 11.3 : titre, puis paragraphes C, A, B selon l'origine."""
    paragraphes = []
    if repare:
        n, m = repare
        paragraphes.append(_paragraphe(
            f"Ce PDF était endommagé et a été réparé à l'ouverture : {n} pages sur {m} ont été récupérées. "
            "Son contenu peut être incomplet ou désordonné sur toutes les pages. Ne pas utiliser ce document "
            "comme source d'un montant, d'une date, d'une référence ou d'une conclusion sans vérification sur "
            "le PDF d'origine."))
    if pages_couche:
        paragraphes.append(_paragraphe(
            f"Le texte {pages_en_clair(pages_couche)} provient d'une reconnaissance de caractères de mauvaise "
            "qualité réalisée avant réception. Il peut contenir des chiffres, des noms ou des dates erronés. Ne "
            "pas utiliser ces pages comme source d'un montant, d'une date, d'une référence ou d'une conclusion "
            "sans vérification sur le PDF d'origine. Signaler toute information tirée de ces pages comme « à "
            "vérifier »."))
    if pages_outil:
        paragraphes.append(_paragraphe(
            f"Le texte {pages_en_clair(pages_outil)} a été obtenu par reconnaissance de caractères sur des "
            "pages difficiles à lire (scan dégradé, manuscrit, tampon ou mise en page complexe). Il peut "
            "contenir des chiffres, des noms ou des dates erronés, ou être incomplet. Ne pas utiliser ces pages "
            "comme source d'un montant, d'une date, d'une référence ou d'une conclusion sans vérification sur le "
            "PDF d'origine. Signaler toute information tirée de ces pages comme « à vérifier »."))
    lignes = ["> " + TITRE]
    for i, p in enumerate(paragraphes):
        if i:
            lignes.append(">")
        lignes += p
    return "\n".join(lignes) + "\n"


def mention_revisions(revisions: bool, commentaires: int) -> str:
    """Mention de tête d'un .docx à révisions non acceptées ou à commentaires (section 11.3,
    décision du commanditaire du 27/11/2026) ; chaîne vide sinon."""
    nombre = f"{commentaires} commentaire{'s' if commentaires > 1 else ''}"
    if revisions and commentaires:
        return (f"Document contenant des révisions non acceptées et {nombre} : texte présenté dans son état final "
                "(insertions acceptées, suppressions écartées), commentaires non repris.")
    if revisions:
        return ("Document contenant des révisions non acceptées : texte présenté dans son état final (insertions "
                "acceptées, suppressions écartées).")
    if commentaires:
        return f"Document contenant {nombre} : commentaires non repris."
    return ""


def valeur_revisions(revisions: bool, commentaires: int) -> str:
    """Colonne `revisions_commentaires` du rapport : « revisions », « commentaires=N », les deux
    séparés par une espace, ou vide."""
    return " ".join((["revisions"] if revisions else []) + ([f"commentaires={commentaires}"] if commentaires else []))


def document_markdown(champs: dict, corps: str, *, pages_couche_douteuses=(), pages_outil_douteuses=(),
                      repare=None, mention: str = "") -> str:
    """Front matter, bloc d'avertissement si le document est douteux, mention des révisions
    et commentaires d'un .docx s'il y a lieu, puis le corps."""
    texte = front_matter(champs) + "\n"
    if champs["qualite_texte"] == "douteuse":
        texte += bloc_avertissement(pages_couche_douteuses, pages_outil_douteuses, repare) + "\n"
    if mention:
        texte += "\n".join(_paragraphe(mention)) + "\n\n"
    return texte + corps


# ------------------------------------------------------------------------------ métadonnées PDF
def _sans_ancienne_marque(texte: str, debut: str) -> str:
    """Retire un avertissement d'ocr-md déjà présent (PDF déjà passé par l'outil)."""
    return "" if texte.startswith(debut) else texte


def metadonnees_pdf(origine_meta: dict, *, pages_douteuses, pages_ocr, origine: str, moteur: str) -> dict:
    """Métadonnées du PDF consultable (EX-33) : Sujet et Mots-clés d'avertissement, les
    autres métadonnées d'origine (Titre, Auteur) étant conservées."""
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


# ------------------------------------------------------------------------------ _AVERTISSEMENTS.md
ENCADRE = """> **À L'ATTENTION DE TOUT LECTEUR, HUMAIN OU IA**
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
"""


def _cellule(texte: str) -> str:
    return " ".join(texte.split()).replace("|", "\\|")


def contenu_avertissements(lignes, parent: pathlib.Path) -> str:
    """Contenu de `_AVERTISSEMENTS.md` (section 11.5) d'après les lignes du rapport."""
    lignes = sorted(lignes, key=lambda l: l.chemin_relatif.casefold())
    douteuses = [l for l in lignes if l.statut == "douteux"]
    non_converties = [l for l in lignes if l.statut == "non_pris_en_charge"]
    erreurs = [l for l in lignes if l.statut == "erreur"]
    sortie = ["---", "version_schema: 1", "type: avertissements", 'dossier: "_OCR"',
              f"date_mise_a_jour: {_chaine(date_iso())}", f"outil: {_chaine('ocr-md ' + __version__)}",
              f"pieces_total: {len(lignes)}", f"pieces_douteuses: {len(douteuses)}",
              f"pieces_non_converties: {len(non_converties)}", f"pieces_en_erreur: {len(erreurs)}", "---", "",
              "# Avertissements sur les pièces de ce dossier", "", ENCADRE]
    if not (douteuses or non_converties or erreurs):
        sortie.append("Aucune pièce de ce dossier n'est signalée.")
        return "\n".join(sortie) + "\n"
    sortie += ["## Pièces dont le texte est douteux", ""]
    if douteuses:
        sortie += ["| Pièce | Pages douteuses | Origine du texte | Motif |", "|---|---|---|---|"]
        for l in douteuses:
            sortie.append(f"| {_cellule(l.chemin_relatif)} | {_liste(l.pages_douteuses, ', ')} | "
                          f"{_cellule(l.origine_texte)} | {_cellule(' '.join(l.motif_douteux))} |")
        sortie += ["", "Pour refaire la reconnaissance des pages douteuses d'une pièce :",
                   '`ocr-md --refaire-ocr "<chemin complet de la pièce d\'origine>"`', "", "Soit, pour ce dossier :", ""]
        sortie += [f'- `ocr-md --refaire-ocr "{parent / l.chemin_relatif}"`' for l in douteuses]
    else:
        sortie.append("Aucune.")
    sortie += ["", "## Pièces non converties (format non pris en charge)", ""]
    if non_converties:
        sortie += ["| Pièce | Raison |", "|---|---|"]
        sortie += [f"| {_cellule(l.chemin_relatif)} | {_cellule(l.message)} |" for l in non_converties]
    else:
        sortie.append("Aucune.")
    sortie += ["", "## Pièces en erreur", ""]
    if erreurs:
        sortie += ["| Pièce | Erreur |", "|---|---|"]
        sortie += [f"| {_cellule(l.chemin_relatif)} | {_cellule(l.message)} |" for l in erreurs]
    else:
        sortie.append("Aucune.")
    return "\n".join(sortie) + "\n"


def ecrire_avertissements(dossier_ocr: pathlib.Path, parent: pathlib.Path, lignes, tentatives=3,
                          intervalle_s=1.0) -> None:
    from .sorties import ecrire_atomique
    texte = contenu_avertissements(lignes, parent)
    ecrire_atomique(dossier_ocr / NOM_AVERTISSEMENTS,
                    lambda c: open(c, "w", encoding="utf-8", newline="\n").write(texte), tentatives, intervalle_s)
