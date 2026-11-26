"""Qualité du texte : normalisation des équivalences et lexique embarqué (EX-36, EX-37).

Les indicateurs de EX-35 et EX-36 seront ajoutés au jalon 7. Ce module ne contient pour
l'instant que les briques utilisées dès le jalon 1 (lexique, équivalences).
"""

import functools
import gzip
import importlib.resources
import unicodedata

# Équivalences admises (décision du commanditaire du 26/11/2026, après PV-04) :
# Windows.Media.Ocr produit « oe », « ae » et l'apostrophe droite. Elles servent aux
# comparaisons et à la recherche dans le lexique ; le texte reconnu n'est jamais modifié.
_EQUIVALENCES = str.maketrans({"’": "'", "ʼ": "'", "‘": "'"})
# Ligatures linguistiques (œ, æ) et ligatures typographiques (ﬁ, ﬂ...) que produisent
# certains PDF à l'extraction du texte.
_LIGATURES = (("œ", "oe"), ("Œ", "OE"), ("æ", "ae"), ("Æ", "AE"), ("ﬀ", "ff"), ("ﬁ", "fi"),
              ("ﬂ", "fl"), ("ﬃ", "ffi"), ("ﬄ", "ffl"), ("ﬅ", "st"), ("ﬆ", "st"))


def forme_comparable(texte: str) -> str:
    """Forme normalisée pour comparer deux textes : NFC, apostrophes droites, ligatures
    développées (œ -> oe, æ -> ae, ﬁ -> fi)."""
    t = unicodedata.normalize("NFC", texte).translate(_EQUIVALENCES)
    for lig, dev in _LIGATURES:
        t = t.replace(lig, dev)
    return t


@functools.lru_cache(maxsize=1)
def _formes_grammalecte() -> frozenset[str]:
    ressource = importlib.resources.files("ocr_md") / "donnees" / "lexique" / "formes-fr.txt.gz"
    with ressource.open("rb") as brut, gzip.open(brut, "rt", encoding="utf-8") as f:
        return frozenset(forme_comparable(l).lower() for l in f.read().splitlines() if l and not l.startswith("#"))


@functools.lru_cache(maxsize=1)
def _formes_complementaires_depot() -> frozenset[str]:
    ressource = importlib.resources.files("ocr_md") / "donnees" / "lexique" / "complementaire.txt"
    lignes = ressource.read_text(encoding="utf-8").splitlines()
    return frozenset(forme_comparable(l.strip()).lower() for l in lignes if l.strip() and not l.startswith("#"))


class Lexique:
    """Lexique français (Grammalecte, MPL 2.0) + lexique complémentaire du dépôt + mots du
    fichier de configuration. Recherche insensible à la casse et aux équivalences."""

    def __init__(self, complement: list[str] | tuple[str, ...] = ()):
        self._ajouts = frozenset(forme_comparable(m).lower() for m in complement)

    def __contains__(self, mot: str) -> bool:
        cle = forme_comparable(mot).lower()
        return cle in _formes_grammalecte() or cle in _formes_complementaires_depot() or cle in self._ajouts

    @staticmethod
    def taille() -> int:
        return len(_formes_grammalecte())
