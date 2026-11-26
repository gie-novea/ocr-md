"""Ligne de commande d'ocr-md (EX-11, EX-12) : analyse des arguments et codes de retour.

Les messages sont en français. Une option inconnue ou une combinaison invalide produit un
message et le code 2, sans rien traiter.
"""

import argparse
import dataclasses
import pathlib
import re
import sys

from . import ADRESSE_CODE_SOURCE, LICENCE, __version__, config, plateforme

# Codes de retour (EX-12)
SUCCES = 0
ERREUR_FICHIER = 1
ERREUR_USAGE = 2
PREREQUIS_MANQUANT = 3

AIDE = """\
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
"""


class ErreurUsage(Exception):
    """Erreur d'usage : message en français, code de retour 2."""


@dataclasses.dataclass(frozen=True)
class Options:
    chemins: tuple[pathlib.Path, ...]
    sortie: str
    refaire_ocr: str | None  # None, « douteuses », « tout » ou « pages »
    pages: tuple[int, ...]
    forcer: bool
    tableaux: str
    sans_interface: bool
    config: pathlib.Path | None


_TRADUCTIONS = (
    (r"unrecognized arguments: (.*)", "option ou argument inconnu : {0}"),
    (r"argument (\S+): expected one argument", "l'option {0} attend une valeur"),
    (r"argument (\S+): ignored explicit argument '(.*)'", "l'option {0} n'accepte pas de valeur ({1})"),
    (r"argument (\S+): invalid choice: '(.*)' \(choose from (.*)\)", "valeur invalide pour {0} : « {1} » (valeurs admises : {2})"),
    (r"argument (\S+): not allowed with argument (\S+)", "les options {0} et {1} ne peuvent pas être combinées"),
    (r"one of the arguments (.*) is required", "l'une des options suivantes est requise : {0}"),
)


def _traduire(message: str) -> str:
    for motif, modele in _TRADUCTIONS:
        m = re.fullmatch(motif, message)
        if m:
            return modele.format(*(g.replace("'", "") for g in m.groups()))
    return message


class _Analyseur(argparse.ArgumentParser):
    def __init__(self, **kw):
        super().__init__(prog="ocr-md", add_help=False, allow_abbrev=False, **kw)

    def error(self, message):
        raise ErreurUsage(_traduire(message))


def _analyseur_principal() -> _Analyseur:
    a = _Analyseur()
    a.add_argument("chemins", nargs="*")
    a.add_argument("--sortie", choices=("pdf", "md", "les-deux"), default="les-deux")
    a.add_argument("--refaire-ocr", dest="refaire_ocr", choices=("douteuses", "tout"))
    a.add_argument("--pages")
    a.add_argument("--qualite", action="store_true")
    a.add_argument("--forcer", action="store_true")
    a.add_argument("--tableaux", choices=("auto", "md", "html"), default="auto")
    a.add_argument("--sans-interface", dest="sans_interface", action="store_true")
    a.add_argument("--config")
    a.add_argument("--version", action="store_true")
    a.add_argument("--aide", action="store_true")
    return a


def analyser_pages(liste: str) -> tuple[int, ...]:
    """« 3,4,9-12 » -> (3, 4, 9, 10, 11, 12). Pages numérotées à partir de 1."""
    pages = set()
    for morceau in liste.split(","):
        morceau = morceau.strip()
        m = re.fullmatch(r"(\d+)(?:-(\d+))?", morceau)
        if not m:
            raise ErreurUsage(f"liste de pages invalide : « {liste} » (exemple attendu : 3,4,9-12)")
        debut = int(m.group(1))
        fin = int(m.group(2) or debut)
        if debut < 1 or fin < debut:
            raise ErreurUsage(f"plage de pages invalide : « {morceau} » (pages numérotées à partir de 1)")
        pages.update(range(debut, fin + 1))
    return tuple(sorted(pages))


def analyser(arguments: list[str]) -> Options | str:
    """Renvoie les options du traitement, ou « aide » / « version »."""
    # --refaire-ocr sans « = » ne prend pas de valeur : le mot suivant est un chemin.
    arguments = ["--refaire-ocr=douteuses" if a == "--refaire-ocr" else a for a in arguments]
    ns = _analyseur_principal().parse_args(arguments)
    if ns.aide:
        return "aide"
    if ns.version:
        return "version"
    if ns.qualite:
        raise ErreurUsage("mode qualité disponible à partir de la version 1.1")
    if not ns.chemins:
        raise ErreurUsage("aucun fichier ni dossier à traiter (ocr-md --aide pour l'usage)")
    chemins = tuple(pathlib.Path(c) for c in ns.chemins)
    pages: tuple[int, ...] = ()
    refaire = ns.refaire_ocr
    if ns.pages is not None:
        if len(chemins) != 1 or chemins[0].suffix.lower() != ".pdf" or chemins[0].is_dir():
            raise ErreurUsage("--pages n'est admis que si un seul fichier PDF est passé en entrée")
        pages = analyser_pages(ns.pages)
        refaire = "pages"  # --pages vise ces pages, quelle que soit la portée (EX-39)
    return Options(chemins, ns.sortie, refaire, pages, ns.forcer, ns.tableaux, ns.sans_interface,
                   pathlib.Path(ns.config) if ns.config else None)


def texte_version() -> str:
    import importlib.metadata as md
    from . import ocr

    def v(paquet):
        try:
            return md.version(paquet)
        except md.PackageNotFoundError:
            return "absent"

    try:
        moteur = ocr.moteur_systeme().description()
    except ocr.MoteurIndisponible as e:
        moteur = f"indisponible ({e})"
    return (f"ocr-md {__version__}\n"
            f"PyMuPDF {v('pymupdf')}\n"
            f"PyMuPDF4LLM {v('pymupdf4llm')}\n"
            f"Moteur OCR : {moteur}\n"
            f"Licence : {LICENCE}\n"
            f"Code source : {ADRESSE_CODE_SOURCE}\n")


def verifier() -> int:
    """Diagnostic des prérequis (EX-71). Les contrôles des raccourcis et du mode qualité
    seront ajoutés avec les fonctions correspondantes."""
    from . import ocr
    lignes, code = [], SUCCES
    ok = plateforme.systeme_pris_en_charge()
    lignes.append(f"[{'OK' if ok else 'X'}] Système : {plateforme.description_systeme()}"
                  + ("" if ok else " : système non pris en charge"))
    if not ok:
        code = PREREQUIS_MANQUANT
    try:
        moteur = ocr.moteur_systeme()
        lignes.append(f"[OK] Moteur OCR : {moteur.description()} ; langues : {', '.join(moteur.langues_disponibles())}")
    except ocr.MoteurIndisponible as e:
        lignes.append(f"[X] Moteur OCR : {e}")
        code = PREREQUIS_MANQUANT
    for nom, dossier in (("Dossier temporaire", plateforme.dossier_temporaire()),
                         ("Dossier de configuration", plateforme.dossier_configuration())):
        if plateforme.dossier_inscriptible(dossier):
            lignes.append(f"[OK] {nom} : {dossier}")
        else:
            lignes.append(f"[X] {nom} : écriture impossible dans {dossier}")
            code = PREREQUIS_MANQUANT
    lignes.append(f"     Fichier de configuration : {plateforme.fichier_configuration()}")
    print("\n".join(lignes))
    return code


def _executer(arguments: list[str]) -> int:
    if arguments and arguments[0] == "verifier":
        if len(arguments) > 1:
            raise ErreurUsage("la sous-commande verifier n'accepte pas d'argument (option --precharger-modeles : v1.1)")
        return verifier()
    if arguments and arguments[0] == "raccourcis":
        reste = arguments[1:]
        if reste not in (["--creer"], ["--supprimer"]):
            raise ErreurUsage("usage : ocr-md raccourcis --creer | --supprimer")
        print("création et suppression des raccourcis : fonction réalisée au jalon 9")
        return ERREUR_USAGE
    resultat = analyser(arguments)
    if resultat == "aide":
        print(AIDE, end="")
        return SUCCES
    if resultat == "version":
        print(texte_version(), end="")
        return SUCCES
    try:
        parametres = config.charger(resultat.config)
    except config.ErreurConfiguration as e:
        raise ErreurUsage(str(e)) from None
    from . import traitement
    return traitement.executer(resultat, parametres)


def main(arguments: list[str] | None = None) -> int:
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    try:
        return _executer(list(sys.argv[1:] if arguments is None else arguments))
    except ErreurUsage as e:
        print(f"ocr-md : erreur d'usage : {e}", file=sys.stderr)
        return ERREUR_USAGE


def main_graphique() -> int:
    """Point d'entrée sans console (raccourcis). La fenêtre de progression viendra au jalon 9."""
    return main()


if __name__ == "__main__":
    sys.exit(main())
