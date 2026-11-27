"""Recalibrage des seuils de qualité sur une vérité terrain de recette (TM-08).

Le référent juge à l'œil une vingtaine de pages traitées par ocr-md (« correct », « erreurs
ponctuelles » ou « mauvais ») ; le script relit les mesures de ces pages dans le journal du
dossier `_OCR` (`ocr_journal.log`, rotations comprises) et cherche les seuils qui donnent le
moins d'erreurs de verdict par rapport à ce jugement, avec la marge la plus large.

Deux commandes :
    python tests/recalibrage.py gabarit DOSSIER_OCR [--nombre 20] [--sortie FICHIER.csv]
        gabarit CSV à remplir (fichier relatif, page, verdict), prérempli d'un échantillon de
        pages tiré du journal : pages douteuses par l'image, images médiocres, pages bonnes,
        pages douteuses par le texte ;
    python tests/recalibrage.py calibrer DOSSIER_OCR FICHIER.csv [--ponctuelles neutre|bonne|douteuse]
                                         [--poids-oubli 2] [--config FICHIER]
        seuils proposés, sous forme d'un extrait de fichier de configuration TOML.

Verdicts admis : « correct » (page bonne), « mauvais » (page douteuse) et « erreurs
ponctuelles », neutre par défaut (ni bonne ni douteuse attendue : la page ne compte pas).
Le script s'exécute en local ; il lit des noms de fichiers et des nombres, jamais le texte des
documents. Ses sorties contiennent des noms de fichiers : ne pas les versionner.

Approximations (le journal ne garde pas tout) : la part de texte peu sûr d'Apple Vision n'est
pas journalisée, seule la confiance moyenne est recalculée ; une page est supposée non blanche
pour l'indicateur de densité.
"""

import argparse
import csv
import dataclasses
import pathlib
import random
import re
import sys
import unicodedata

if __package__ in (None, ""):
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from ocr_md import config, qualite  # noqa: E402

NOM_JOURNAL = "ocr_journal.log"
COLONNES_GABARIT = ("fichier", "page", "verdict")
VERDICTS = {"correct": "bonne", "mauvais": "douteuse", "erreurs ponctuelles": "ponctuelles"}

_PREFIXE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} [A-Z]+ (?P<message>.*)$")
_MOTEUR = re.compile(r"^(?P<rel>.+) : OCR par (?P<description>.+?), langue ")
_IMAGE = re.compile(r"^(?P<rel>.+) : page (?P<page>\d+) : image : résolution (?P<res>\S+) dpi, part de gris "
                    r"(?P<gris>\S+), contraste (?P<contraste>[^,]+), bruit (?P<bruit>[\d.]+)")
_TEXTE = re.compile(r"^(?P<rel>.+) : page (?P<page>\d+) : mots (?P<mots>\d+), évaluables (?P<eval>\d+), "
                    r"inconnus (?P<inconnus>[\d.]+), aberrants (?P<aberrants>[\d.]+), fragmentés "
                    r"(?P<fragmentes>[\d.]+), mélanges (?P<melanges>[\d.]+), densité (?P<densite>[\d.]+)"
                    r"(?:, confiance (?P<confiance>[\d.]+))? : (?P<verdict>bonne|douteuse)")


def _nombre(texte: str):
    return None if texte in ("None", "") else float(texte)


@dataclasses.dataclass
class Page:
    fichier: str
    page: int
    origine: str                       # « couche_existante » ou nom du moteur
    indicateurs: qualite.Indicateurs
    confiance: float | None
    image: qualite.QualiteImage | None
    verdict_journal: str


def nom_moteur(description: str) -> str:
    if description.startswith("Apple Vision"):
        return "apple-vision"
    if description.startswith("Windows.Media.Ocr"):
        return "windows-media-ocr"
    return "factice"


def journaux(dossier_ocr: pathlib.Path) -> list[pathlib.Path]:
    """Journal et ses rotations, du plus ancien au plus récent."""
    chemins = [dossier_ocr / f"{NOM_JOURNAL}.{i}" for i in (2, 1)] + [dossier_ocr / NOM_JOURNAL]
    return [c for c in chemins if c.is_file()]


def lire_journal(dossier_ocr: pathlib.Path) -> dict[tuple[str, int], Page]:
    """Mesures de chaque page évaluée ; pour une page traitée plusieurs fois, la dernière."""
    moteurs: dict[str, str] = {}
    images: dict[tuple[str, int], qualite.QualiteImage] = {}
    pages: dict[tuple[str, int], Page] = {}
    for chemin in journaux(dossier_ocr):
        for ligne in chemin.read_text(encoding="utf-8", errors="replace").splitlines():
            m = _PREFIXE.match(ligne)
            if not m:
                continue
            message = m["message"]
            if (m := _MOTEUR.match(message)):
                moteurs[m["rel"]] = nom_moteur(m["description"])
            elif (m := _IMAGE.match(message)):
                gris, contraste = _nombre(m["gris"]), _nombre(m["contraste"])
                images[(m["rel"], int(m["page"]))] = qualite.QualiteImage(
                    None if m["res"] == "None" else int(m["res"]), gris,
                    None if contraste is None else int(contraste), float(m["bruit"]))
            elif (m := _TEXTE.match(message)):
                cle = (m["rel"], int(m["page"]))
                image = images.pop(cle, None)
                ind = qualite.Indicateurs(
                    mots=int(m["mots"]), mots_evaluables=int(m["eval"]), taux_mots_inconnus=float(m["inconnus"]),
                    taux_caracteres_aberrants=float(m["aberrants"]), taux_mots_fragmentes=float(m["fragmentes"]),
                    taux_melange_chiffres_lettres=float(m["melanges"]), densite=float(m["densite"]))
                origine = moteurs.get(cle[0], "factice") if image is not None else qualite.ORIGINE_COUCHE
                pages[cle] = Page(cle[0], cle[1], origine, ind, _nombre(m["confiance"] or ""), image, m["verdict"])
    return pages


def verdict(page: Page, p) -> tuple[str, str]:
    """Verdict (bonne ou douteuse) et niveau d'image recalculés avec les paramètres `p`."""
    motifs = qualite.motifs_lexicaux(page.indicateurs, p, True, page.origine)
    motifs += qualite.motifs_confiance(page.confiance, None, p)
    v = qualite.verdict_image(page.image, page.indicateurs, p, page.origine)
    if v is not None and v.douteuse:
        motifs.append(qualite.MOTIF_IMAGE)
    return ("douteuse" if motifs else "bonne"), ("" if v is None else v.niveau)


# ------------------------------------------------------------------------------ gabarit
def normaliser_verdict(texte: str) -> str | None:
    t = unicodedata.normalize("NFKD", texte.strip().lower()).encode("ascii", "ignore").decode()
    t = " ".join(t.replace("_", " ").replace("-", " ").split())
    if not t:
        return None
    if t not in VERDICTS:
        raise ValueError(f"verdict inconnu : « {texte} » (admis : correct, erreurs ponctuelles, mauvais)")
    return VERDICTS[t]


def echantillon(pages: dict, nombre: int, graine: int = 0) -> list[Page]:
    """Échantillon équilibré : pages douteuses par l'image, images médiocres non douteuses,
    pages bonnes, pages douteuses par le texte seul ; tirage reproductible."""
    p = config.charger()
    strates: dict[str, list[Page]] = {"image_douteuse": [], "image_mediocre": [], "bonne": [], "texte_douteux": []}
    for page in pages.values():
        v = qualite.verdict_image(page.image, page.indicateurs, p, page.origine)
        if v is not None and v.douteuse:
            strates["image_douteuse"].append(page)
        elif page.verdict_journal == "douteuse":
            strates["texte_douteux"].append(page)
        elif v is not None and v.niveau == qualite.IMAGE_MEDIOCRE:
            strates["image_mediocre"].append(page)
        else:
            strates["bonne"].append(page)
    hasard = random.Random(graine)
    for s in strates.values():
        s.sort(key=lambda x: (x.fichier, x.page))
        hasard.shuffle(s)
    retenues: list[Page] = []
    while len(retenues) < nombre and any(strates.values()):
        for s in strates.values():
            if s and len(retenues) < nombre:
                retenues.append(s.pop())
    return sorted(retenues, key=lambda x: (x.fichier.casefold(), x.page))


def ecrire_gabarit(chemin: pathlib.Path, pages: list[Page]) -> None:
    with open(chemin, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";", lineterminator="\r\n")
        w.writerow(COLONNES_GABARIT)
        for page in pages:
            w.writerow([page.fichier, page.page, ""])


def lire_gabarit(chemin: pathlib.Path) -> dict[tuple[str, int], str]:
    verites = {}
    with open(chemin, encoding="utf-8-sig", newline="") as f:
        lecteur = csv.DictReader(f, delimiter=";")
        manquantes = set(COLONNES_GABARIT) - set(lecteur.fieldnames or ())
        if manquantes:
            raise ValueError(f"colonnes manquantes dans {chemin.name} : {', '.join(sorted(manquantes))}")
        for ligne in lecteur:
            v = normaliser_verdict(ligne["verdict"] or "")
            if v is not None:
                verites[(unicodedata.normalize("NFC", ligne["fichier"].strip()), int(ligne["page"]))] = v
    return verites


# ------------------------------------------------------------------------------ recherche des seuils
def _mesure_image(nom):
    return lambda page: None if page.image is None else getattr(page.image, nom)


def _inconnus(origines):
    return lambda page: page.indicateurs.taux_mots_inconnus if page.origine in origines else None


# Paramètre -> mesure de la page sur laquelle il agit.
PARAMETRES = {
    "image_resolution_severe_dpi": _mesure_image("resolution_dpi"),
    "image_resolution_min_dpi": _mesure_image("resolution_dpi"),
    "image_part_gris_max": _mesure_image("part_gris"),
    "image_contraste_min": _mesure_image("contraste"),
    "image_bruit_max": _mesure_image("bruit"),
    "mots_inconnus_limite_windows": _inconnus(("windows-media-ocr", "factice")),
    "mots_inconnus_limite_vision": _inconnus(("apple-vision",)),
    "mots_inconnus_max_windows": _inconnus(("windows-media-ocr", "factice")),
    "mots_inconnus_max_vision": _inconnus(("apple-vision",)),
    "mots_inconnus_max_couche_existante": _inconnus((qualite.ORIGINE_COUCHE,)),
    "confiance_moyenne_min": lambda page: page.confiance,
}


def cout(pages: list[tuple[Page, str]], p, poids_oubli: float) -> float:
    total = 0.0
    for page, attendu in pages:
        obtenu, _ = verdict(page, p)
        if obtenu != attendu:
            total += poids_oubli if attendu == "douteuse" else 1.0
    return total


def candidats(valeurs: list[float], actuelle: float) -> list[float]:
    """Valeur actuelle, milieux entre valeurs observées consécutives, et valeurs juste au-delà
    des extrêmes."""
    v = sorted(set(valeurs))
    c = {actuelle}
    if v:
        c |= {(a + b) / 2 for a, b in zip(v, v[1:])}
        pas = max((v[-1] - v[0]) / 20, 1e-3)
        c |= {v[0] - pas, v[-1] + pas}
    return sorted(x for x in c if x >= 0)


def recalibrer(pages: list[tuple[Page, str]], p, poids_oubli: float = 2.0, passes: int = 3):
    """Descente par coordonnées, puis, s'il reste des erreurs, essai de chaque paire de
    paramètres (deux seuils doivent parfois bouger ensemble : un seuil limite et un seuil de
    dégradation grossière, par exemple), et nouvelle descente pour centrer les valeurs."""
    courant = _descente(pages, p, poids_oubli, passes)
    for _ in range(3):
        base = cout(pages, courant, poids_oubli)
        if base == 0:
            break
        meilleur = (base, None)
        noms = [n for n, mesure in PARAMETRES.items() if any(mesure(pg) is not None for pg, _ in pages)]
        for i, a in enumerate(noms):
            for b in noms[i + 1:]:
                for xa in candidats([x for x in (PARAMETRES[a](pg) for pg, _ in pages) if x is not None],
                                    courant.valeurs[a]):
                    for xb in candidats([x for x in (PARAMETRES[b](pg) for pg, _ in pages) if x is not None],
                                        courant.valeurs[b]):
                        essai = dict(courant.valeurs, **{a: _type(courant.valeurs[a], xa),
                                                         b: _type(courant.valeurs[b], xb)})
                        c = cout(pages, config.Parametres(essai, ()), poids_oubli)
                        if c < meilleur[0]:
                            meilleur = (c, essai)
        if meilleur[1] is None:
            break
        courant = _descente(pages, config.Parametres(meilleur[1], ()), poids_oubli, passes)
    return courant


def _descente(pages, p, poids_oubli: float, passes: int):
    """Pour chaque paramètre, valeur qui minimise le coût ; parmi les valeurs de coût minimal
    contiguës, celle du milieu (marge la plus large)."""
    valeurs = dict(p.valeurs)
    for _ in range(passes):
        for nom, mesure in PARAMETRES.items():
            observees = [x for x in (mesure(page) for page, _ in pages) if x is not None]
            if not observees:
                continue
            essais = candidats(observees, valeurs[nom])
            couts = []
            for x in essais:
                essai = dict(valeurs, **{nom: _type(valeurs[nom], x)})
                couts.append(cout(pages, config.Parametres(essai, ()), poids_oubli))
            meilleur = min(couts)
            # plage contiguë de coût minimal la plus longue, puis son milieu
            plages, debut = [], None
            for i, c in enumerate(couts + [None]):
                if c == meilleur and debut is None:
                    debut = i
                elif c != meilleur and debut is not None:
                    plages.append((debut, i - 1))
                    debut = None
            actuel_optimal = cout(pages, config.Parametres(valeurs, ()), poids_oubli) == meilleur
            if actuel_optimal:
                continue  # la valeur en vigueur est déjà optimale : on ne la déplace pas
            a, b = max(plages, key=lambda x: x[1] - x[0])
            valeurs[nom] = _type(valeurs[nom], (essais[a] + essais[b]) / 2)
    return config.Parametres(valeurs, ())


def _type(modele, x):
    return int(round(x)) if isinstance(modele, int) else round(float(x), 4)


# ------------------------------------------------------------------------------ commandes
def commande_gabarit(o) -> int:
    pages = lire_journal(pathlib.Path(o.dossier_ocr))
    if not pages:
        print(f"aucune page évaluée dans le journal de {o.dossier_ocr}", file=sys.stderr)
        return 1
    retenues = echantillon(pages, o.nombre)
    sortie = pathlib.Path(o.sortie)
    ecrire_gabarit(sortie, retenues)
    print(f"{len(retenues)} page(s) à juger dans {sortie} (verdict : correct, erreurs ponctuelles ou mauvais)")
    return 0


def commande_calibrer(o) -> int:
    p = config.charger(o.config)
    pages = lire_journal(pathlib.Path(o.dossier_ocr))
    verites = lire_gabarit(pathlib.Path(o.gabarit))
    jugees, absentes = [], []
    for cle, v in sorted(verites.items()):
        if cle not in pages:
            absentes.append(cle)
            continue
        if v == "ponctuelles":
            if o.ponctuelles == "neutre":
                continue
            v = o.ponctuelles
        jugees.append((pages[cle], v))
    for fichier, page in absentes:
        print(f"absente du journal : {fichier} page {page}")
    if not jugees:
        print("aucune page jugée exploitable", file=sys.stderr)
        return 1
    propose = recalibrer(jugees, p, o.poids_oubli)
    print("| fichier | page | origine | inconnus | résolution | gris | contraste | bruit | confiance | "
          "jugement | verdict actuel | verdict proposé | image proposée |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for page, attendu in jugees:
        i = page.image
        actuel, _ = verdict(page, p)
        nouveau, niveau = verdict(page, propose)
        print(f"| {page.fichier} | {page.page} | {page.origine} | {page.indicateurs.taux_mots_inconnus:.3f} | "
              f"{'' if i is None else i.resolution_dpi} | {'' if i is None else i.part_gris} | "
              f"{'' if i is None else i.contraste} | {'' if i is None else i.bruit} | "
              f"{'' if page.confiance is None else page.confiance} | {attendu} | {actuel} | {nouveau} | {niveau} |")
    erreurs_avant = sum(verdict(pg, p)[0] != a for pg, a in jugees)
    erreurs_apres = sum(verdict(pg, propose)[0] != a for pg, a in jugees)
    print(f"\n{len(jugees)} page(s) jugée(s) ; erreurs de verdict : {erreurs_avant} avec les seuils en vigueur, "
          f"{erreurs_apres} avec les seuils proposés")
    changes = {k: v for k, v in propose.valeurs.items() if k in PARAMETRES and v != p.valeurs[k]}
    if changes:
        print("\nSeuils proposés (extrait de fichier de configuration TOML) :\n")
        for k, v in changes.items():
            print(f"{k} = {v}  # en vigueur : {p.valeurs[k]}")
    else:
        print("\nSeuils en vigueur conservés : aucun changement ne réduit les erreurs.")
    return 0


def main(arguments=None) -> int:
    a = argparse.ArgumentParser(description="Recalibrage des seuils de qualité sur une vérité terrain (TM-08)")
    sous = a.add_subparsers(dest="commande", required=True)
    g = sous.add_parser("gabarit", help="gabarit CSV de vérité terrain, prérempli depuis le journal")
    g.add_argument("dossier_ocr")
    g.add_argument("--nombre", type=int, default=20)
    g.add_argument("--sortie", default="verite-terrain.csv")
    c = sous.add_parser("calibrer", help="seuils proposés à partir du gabarit rempli")
    c.add_argument("dossier_ocr")
    c.add_argument("gabarit")
    c.add_argument("--ponctuelles", choices=("neutre", "bonne", "douteuse"), default="neutre",
                   help="sens donné au verdict « erreurs ponctuelles » (par défaut : la page ne compte pas)")
    c.add_argument("--poids-oubli", type=float, default=2.0,
                   help="coût d'une page « mauvais » jugée bonne, par rapport à une fausse alerte (1)")
    c.add_argument("--config")
    o = a.parse_args(arguments)
    return commande_gabarit(o) if o.commande == "gabarit" else commande_calibrer(o)


if __name__ == "__main__":
    sys.exit(main())
