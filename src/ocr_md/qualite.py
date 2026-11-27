"""Qualité du texte : lexique embarqué, équivalences, indicateurs et verdict par page
(EX-35 à EX-37).

Une page est « douteuse » dès qu'un indicateur franchit son seuil ; tous les seuils sont
des paramètres (config). Les indicateurs ne retiennent que des nombres : aucun texte de
document n'est journalisé.
"""

import dataclasses
import functools
import gzip
import importlib.resources
import re
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


# ------------------------------------------------------------------------------ indicateurs
_ELISION = re.compile(r"^(?:[ldjmnstc]|qu|lorsqu|puisqu|jusqu|quoiqu)'", re.IGNORECASE)
_PONCTUATION_BORDS = ".,;:!?()[]{}«»\"'…-–/\\*"
_FIN_DE_PHRASE = (".", "!", "?", "…", ":")
LETTRES_ISOLEES_ADMISES = {"a", "à", "y", "ô", "A", "À", "Y", "Ô"}
_REFERENCE = re.compile(r"[^\W\d_]+\d+")                       # DC1, RE2020
_NOMBRE_UNITE = re.compile(r"\d+[^\W\d_]{1,5}\d*")              # 12m, 18mois, 25m2
_ORDINAL = re.compile(r"\d+(?:er|re|e|ème|eme|nd|nde)", re.IGNORECASE)


def _lettre_admise(c: str) -> bool:
    """Lettre des alphabets latin ou grec."""
    try:
        nom = unicodedata.name(c)
    except ValueError:
        return False
    return nom.startswith(("LATIN", "GREEK"))


def caractere_aberrant(c: str) -> bool:
    """U+FFFD, zone d'usage privé, caractère de contrôle, ou lettre hors latin et grec."""
    if c == "�":
        return True
    categorie = unicodedata.category(c)
    if categorie in ("Co", "Cc") and c not in "\n\r\t":
        return True
    return categorie.startswith("L") and not _lettre_admise(c)


@dataclasses.dataclass
class Indicateurs:
    mots: int = 0
    mots_evaluables: int = 0
    taux_mots_inconnus: float = 0.0
    taux_caracteres_aberrants: float = 0.0
    taux_mots_fragmentes: float = 0.0
    taux_melange_chiffres_lettres: float = 0.0
    densite: float | None = None


def _melange_chiffres_lettres(mot: str) -> bool:
    """Chiffres et lettres mêlés au milieu du mot (mar0hé, l1eu), hors références (lettres
    puis chiffres), nombres suivis d'une unité et ordinaux."""
    if not (any(c.isdigit() for c in mot) and any(c.isalpha() for c in mot)):
        return False
    return not (_REFERENCE.fullmatch(mot) or _NOMBRE_UNITE.fullmatch(mot) or _ORDINAL.fullmatch(mot))


def calculer(texte: str, lexique: Lexique, surface_cm2: float | None = None) -> Indicateurs:
    """Indicateurs de EX-36 pour le texte d'une page."""
    texte = forme_comparable(texte)
    bruts = texte.split()
    ind = Indicateurs(mots=len(bruts))
    caracteres = [c for c in texte if not c.isspace()]
    if caracteres:
        ind.taux_caracteres_aberrants = sum(map(caractere_aberrant, caracteres)) / len(caracteres)
    if surface_cm2:
        ind.densite = len(caracteres) / surface_cm2
    if not bruts:
        return ind
    fragmentes = melanges = inconnus = evaluables = 0
    debut_de_phrase = True
    for brut in bruts:
        mot = brut.strip(_PONCTUATION_BORDS)
        if len(mot) == 1 and mot.isalpha() and mot not in LETTRES_ISOLEES_ADMISES:
            fragmentes += 1
        if "@" in mot:
            pass  # adresse électronique : exclue
        elif _melange_chiffres_lettres(mot):
            melanges += 1
        else:
            racine = _ELISION.sub("", mot)
            if len(racine) >= 3 and racine.isalpha():
                minuscules = racine.islower()
                initiale = racine[0].isupper() and racine[1:].islower()
                if minuscules or (initiale and debut_de_phrase):
                    evaluables += 1
                    if racine not in lexique:
                        inconnus += 1
        debut_de_phrase = brut.endswith(_FIN_DE_PHRASE)
    ind.mots_evaluables = evaluables
    ind.taux_mots_fragmentes = fragmentes / len(bruts)
    ind.taux_melange_chiffres_lettres = melanges / len(bruts)
    ind.taux_mots_inconnus = inconnus / evaluables if evaluables else 0.0
    return ind


ORIGINE_COUCHE = "couche_existante"


def seuil_mots_inconnus(p, origine: str) -> float:
    """Seuil des mots inconnus selon l'origine du texte (EX-36) : couche OCR existante, ou nom
    du moteur de l'outil (« apple-vision » ; « windows-media-ocr » et tout autre moteur, dont
    le moteur factice, prennent le seuil de Windows)."""
    if origine == ORIGINE_COUCHE:
        return p.mots_inconnus_max_couche_existante
    if origine == "apple-vision":
        return p.mots_inconnus_max_vision
    return p.mots_inconnus_max_windows


def motifs_lexicaux(ind: Indicateurs, p, page_non_blanche: bool, origine: str = ORIGINE_COUCHE) -> list[str]:
    """Indicateurs de EX-36 qui franchissent leur seuil (p : paramètres ; origine : voir
    `seuil_mots_inconnus`)."""
    motifs = []
    if ind.mots_evaluables >= p.mots_evaluables_min and ind.taux_mots_inconnus > seuil_mots_inconnus(p, origine):
        motifs.append("taux_mots_inconnus")
    if ind.taux_caracteres_aberrants > p.taux_caracteres_aberrants_max:
        motifs.append("taux_caracteres_aberrants")
    if ind.taux_mots_fragmentes > p.taux_mots_fragmentes_max:
        motifs.append("taux_mots_fragmentes")
    if ind.taux_melange_chiffres_lettres > p.taux_melange_chiffres_lettres_max:
        motifs.append("taux_melange_chiffres_lettres")
    if ind.densite is not None and ((ind.densite < p.densite_min and page_non_blanche) or ind.densite > p.densite_max):
        motifs.append("densite_anormale")
    return motifs


def motifs_confiance(confiance_moyenne, part_confiance_basse, p) -> list[str]:
    """EX-35, Apple Vision : confiance moyenne pondérée et part de texte peu sûr."""
    if confiance_moyenne is None:
        return []
    if confiance_moyenne < p.confiance_moyenne_min or (part_confiance_basse or 0) > p.part_confiance_basse_max:
        return ["confiance_ocr_faible"]
    return []


# ------------------------------------------------------------------------------ qualité de l'image
# Indicateur `qualite_image` (EX-35, décisions du commanditaire du 27/11/2026, revues en
# recette le 27/11/2026) : calculé sur l'image de la page transmise au moteur, avant l'OCR,
# donc indépendant du moteur. Pillow seul, calcul sur l'histogramme des niveaux de gris.
# L'image seule ne rend la page douteuse qu'en cas de dégradation sévère ; une image
# médiocre n'est qu'une information, sauf si le texte reconnu est lui aussi limite
# (voir `verdict_image`).
MOTIF_IMAGE = "image_faible_qualite"
PART_ENCRE_MIN = 0.002  # en deçà, trop peu de trait pour juger la netteté et le contraste


@dataclasses.dataclass(frozen=True)
class QualiteImage:
    resolution_dpi: int | None   # résolution effective de l'image d'origine de la page
    part_gris: float | None      # part du trait en gris intermédiaires (trait flou ou grisé)
    contraste: int | None        # niveau du papier moins niveau de l'encre
    bruit: float                 # écart type des niveaux de gris du fond (papier)


def _centile(histogramme, part: float) -> int:
    total = sum(histogramme)
    cumul = 0
    for niveau, effectif in enumerate(histogramme):
        cumul += effectif
        if cumul >= part * total:
            return niveau
    return len(histogramme) - 1


def mesurer_image(image, resolution_dpi: int | None = None) -> QualiteImage:
    """Mesures d'une image en niveaux de gris (PIL, mode « L ») :
    - papier : 90e centile des niveaux ; encre : 10e centile des pixels plus sombres que le
      papier de 40 niveaux ou plus ; contraste = papier - encre ;
    - part de gris : parmi les pixels de trait (sous 190), part de ceux qui ne sont pas
      vraiment sombres (60 à 189) ; un trait net est surtout noir, un trait flou, pâle ou
      recouvert d'un tampon est surtout gris ;
    - bruit : écart type des pixels du fond (à moins de 40 niveaux du papier)."""
    if image.mode != "L":
        image = image.convert("L")
    h = image.histogram()
    total = sum(h)
    papier = _centile(h, 0.90)
    sombres = h[:max(papier - 40, 1)]
    trait = sum(h[:190])
    if sum(sombres) >= PART_ENCRE_MIN * total and trait:
        contraste = papier - _centile(sombres, 0.10)
        part_gris = sum(h[60:190]) / trait
    else:
        contraste = part_gris = None
    fond = [(v, k) for v, k in enumerate(h) if v >= papier - 40 and k]
    n = sum(k for _, k in fond)
    moyenne = sum(v * k for v, k in fond) / n
    bruit = (sum(k * (v - moyenne) ** 2 for v, k in fond) / n) ** 0.5
    return QualiteImage(resolution_dpi, None if part_gris is None else round(part_gris, 4), contraste,
                        round(bruit, 3))


def causes_image(q: QualiteImage | None, p) -> list[str]:
    """Causes d'une image médiocre, en clair ; liste vide si l'image est bonne."""
    if q is None:
        return []
    causes = []
    if q.resolution_dpi is not None and q.resolution_dpi < p.image_resolution_min_dpi:
        causes.append(f"résolution {q.resolution_dpi} dpi")
    if q.part_gris is not None and q.part_gris > p.image_part_gris_max:
        causes.append("image floue ou trait grisé")
    if q.contraste is not None and q.contraste < p.image_contraste_min:
        causes.append("contraste faible")
    if q.bruit > p.image_bruit_max:
        causes.append("image bruitée")
    return causes


IMAGE_BONNE, IMAGE_MEDIOCRE = "bonne", "mediocre"


def seuil_mots_inconnus_limite(p, origine: str) -> float:
    """Seuil « limite » des mots inconnus pour une page reconnue par l'outil : au-delà, une
    image médiocre rend la page douteuse (règle de recette, 27/11/2026)."""
    return p.mots_inconnus_limite_vision if origine == "apple-vision" else p.mots_inconnus_limite_windows


@dataclasses.dataclass(frozen=True)
class VerdictImage:
    niveau: str             # « bonne » ou « mediocre » (information secondaire, sans avertissement)
    douteuse: bool          # l'image rend la page douteuse (motif image_faible_qualite)
    causes: tuple[str, ...]  # causes en clair de l'image médiocre (et « texte reconnu limite »)


def verdict_image(q: QualiteImage | None, ind: Indicateurs, p, origine: str) -> VerdictImage | None:
    """Règle de qualite_image (recette du 27/11/2026) :
    - l'image est « médiocre » dès qu'une mesure franchit son seuil (résolution, part de gris,
      contraste, bruit) : information secondaire du front matter et du rapport, sans bloc
      d'avertissement ;
    - l'image seule ne rend la page douteuse qu'en cas de dégradation sévère : résolution
      inférieure à `image_resolution_severe_dpi` ;
    - sinon, une image médiocre ne rend la page douteuse que si le texte reconnu est lui aussi
      limite : taux de mots inconnus supérieur au seuil limite du moteur, sur une page d'au
      moins `mots_evaluables_min` mots évaluables.
    None si la page n'a pas été reconnue par l'outil (pas d'image mesurée)."""
    if q is None:
        return None
    causes = causes_image(q, p)
    severe = q.resolution_dpi is not None and q.resolution_dpi < p.image_resolution_severe_dpi
    limite = (ind.mots_evaluables >= p.mots_evaluables_min
              and ind.taux_mots_inconnus > seuil_mots_inconnus_limite(p, origine))
    douteuse = severe or (bool(causes) and limite)
    if douteuse and limite and not severe:
        causes = causes + ["texte reconnu limite"]
    return VerdictImage(IMAGE_MEDIOCRE if causes or severe else IMAGE_BONNE, douteuse, tuple(causes))
