"""Documentation générée à partir du code et de l'environnement verrouillé (jalon 10).

- tableau des paramètres du guide administrateur (EX-67, EX-80), depuis `config.DEFINITIONS` ;
- `tests/TRACABILITE.md` (EX-75), depuis les marqueurs `@pytest.mark.exigence("EX-nn")` des
  tests et la liste des exigences du cahier des charges ;
- `LICENCES-TIERCES.md` (EX-78), depuis `uv.lock` (dépendances d'exécution, directes et
  transitives, toutes plateformes) et les métadonnées des paquets installés.

Usage : uv run python outils/documentation.py [--verifier]
Sans option, réécrit les trois documents ; avec --verifier, échoue (code 1) si l'un d'eux
n'est pas à jour (utilisé par les tests).
"""

import ast
import importlib.metadata
import pathlib
import re
import sys
import tomllib

RACINE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "src"))

from ocr_md import config  # noqa: E402

GUIDE_ADMIN = RACINE / "docs" / "guide-administrateur.md"
TRACABILITE = RACINE / "tests" / "TRACABILITE.md"
LICENCES = RACINE / "LICENCES-TIERCES.md"
DEBUT_PARAMETRES, FIN_PARAMETRES = "<!-- debut : tableau des paramètres, généré -->", "<!-- fin : tableau des paramètres -->"

# Exigences vérifiées seulement (ou aussi) par la recette manuelle, avec leur fiche.
MANUELLES = {
    "EX-01": "revue : CHANGELOG, « Reprise de l'existant »", "EX-02": "TM-01, TM-10", "EX-04": "TM-06",
    "EX-06": "TM-01 (Mac Intel)", "EX-13": "TM-02", "EX-15": "TM-02", "EX-16": "TM-03", "EX-17": "TM-03",
    "EX-26": "TM-01", "EX-27": "TM-01", "EX-31": "TM-05, TM-11", "EX-58": "TM-08", "EX-64": "TM-07",
    "EX-65": "TM-07", "EX-68": "TM-01", "EX-69": "TM-01", "EX-70": "TM-02", "EX-71": "TM-04",
    "EX-72": "TM-10", "EX-73": "TM-10", "EX-76": "TM-08", "EX-79": "relecture par un utilisateur",
    "EX-80": "relecture par le référent",
}
HORS_V1 = {"EX-54", "EX-55", "EX-56"}  # mode qualité, v1.1 (section 8.2)


# ------------------------------------------------------------------------------ paramètres
def _valeur(v) -> str:
    if isinstance(v, bool):
        return "vrai" if v else "faux"
    if isinstance(v, float):
        return f"{v:g}".replace(".", ",")
    if isinstance(v, (list, tuple)):
        return "liste vide" if not v else ", ".join(map(str, v))
    return str(v)


def tableau_parametres() -> str:
    lignes = ["| Paramètre | Défaut | Bornes ou valeurs | Description |", "|---|---|---|---|"]
    for d in config.DEFINITIONS:
        if d.choix:
            bornes = ", ".join(d.choix)
        elif d.minimum is not None or d.maximum is not None:
            bornes = f"{_valeur(d.minimum)} à {_valeur(d.maximum)}"
        else:
            bornes = ""
        lignes.append(f"| `{d.nom}` | {_valeur(d.defaut)} | {bornes} | {d.description} |")
    return "\n".join(lignes)


def guide_avec_parametres(texte: str) -> str:
    debut, fin = texte.index(DEBUT_PARAMETRES), texte.index(FIN_PARAMETRES)
    return texte[:debut + len(DEBUT_PARAMETRES)] + "\n\n" + tableau_parametres() + "\n\n" + texte[fin:]


# ------------------------------------------------------------------------------ traçabilité
def exigences_du_cahier() -> list[tuple[str, str]]:
    texte = (RACINE / "docs" / "cahier-des-charges.md").read_text(encoding="utf-8")
    return [(m.group(1), m.group(2)) for m in re.finditer(r"^\*\*(EX-\d\d)\. ([^*]+?)\.?\*\*", texte, re.MULTILINE)]


def marqueurs_des_tests() -> dict[str, list[str]]:
    """EX-nn -> liste « fichier::test » d'après les décorateurs pytest.mark.exigence."""
    resultat: dict[str, list[str]] = {}
    for fichier in sorted((RACINE / "tests").glob("test_*.py")):
        arbre = ast.parse(fichier.read_text(encoding="utf-8"))
        for noeud in ast.walk(arbre):
            if not isinstance(noeud, ast.FunctionDef) or not noeud.name.startswith("test_"):
                continue
            for deco in noeud.decorator_list:
                if (isinstance(deco, ast.Call) and isinstance(deco.func, ast.Attribute)
                        and deco.func.attr == "exigence"):
                    for arg in deco.args:
                        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                            resultat.setdefault(arg.value, []).append(f"{fichier.name}::{noeud.name}")
    return resultat


def tracabilite() -> str:
    marqueurs = marqueurs_des_tests()
    lignes = ["# Traçabilité : exigences et tests (EX-75)", "",
              "Document généré par `outils/documentation.py` à partir des marqueurs "
              "`@pytest.mark.exigence(\"EX-nn\")` des tests et de la liste des exigences du cahier des "
              "charges ; ne pas le modifier à la main.", "",
              "| Exigence | Intitulé | Tests automatisés | Recette manuelle |", "|---|---|---|---|"]
    sans_test = []
    for code, titre in exigences_du_cahier():
        if code in HORS_V1:
            lignes.append(f"| {code} | {titre} | hors v1 (v1.1) | |")
            continue
        tests = marqueurs.get(code, [])
        manuel = MANUELLES.get(code, "")
        if not tests and not manuel:
            sans_test.append(code)
        rendu = "<br>".join(f"`{t}`" for t in tests) if tests else "aucun"
        lignes.append(f"| {code} | {titre} | {rendu} | {manuel} |")
    lignes += ["", f"Exigences de la v1 sans test automatisé ni fiche de recette : {', '.join(sans_test) or 'aucune'}."]
    return "\n".join(lignes) + "\n"


# ------------------------------------------------------------------------------ licences
# Paquets propres à une autre plateforme que celle de la génération : licence relevée sur
# leur page PyPI (vérifiée à la main lors de la relecture de l'inventaire).
LICENCES_CONNUES = {
    "click": ("BSD-3-Clause", "https://palletsprojects.com/p/click/"),
    "ocrmac": ("MIT", "https://github.com/straussmaximilian/ocrmac"),
    "pyobjc-core": ("MIT", "https://github.com/ronaldoussoren/pyobjc"),
    "pyobjc-framework-cocoa": ("MIT", "https://github.com/ronaldoussoren/pyobjc"),
    "pyobjc-framework-coreml": ("MIT", "https://github.com/ronaldoussoren/pyobjc"),
    "pyobjc-framework-quartz": ("MIT", "https://github.com/ronaldoussoren/pyobjc"),
    "pyobjc-framework-vision": ("MIT", "https://github.com/ronaldoussoren/pyobjc"),
    "winrt-runtime": ("MIT", "https://github.com/pywinrt/pywinrt"),
}
COMPATIBLES_AGPL = ("MIT", "BSD", "Apache", "PSF", "Python Software Foundation", "AGPL", "AFFERO GPL", "MPL", "ISC", "HPND",
                    "LGPL", "Zlib", "Unlicense", "CC0")


def _norme(nom: str) -> str:
    return re.sub(r"[-_.]+", "-", nom).lower()


def dependances_execution() -> list[tuple[str, str, str]]:
    """(nom, version, plateformes) des dépendances d'exécution, directes et transitives."""
    verrou = tomllib.loads((RACINE / "uv.lock").read_text(encoding="utf-8"))
    paquets = {_norme(p["name"]): p for p in verrou["package"]}
    a_voir, vus, marqueurs = [("ocr-md", "")], set(), {}
    while a_voir:
        nom, marqueur = a_voir.pop()
        nom = _norme(nom)
        if nom in vus:
            continue
        vus.add(nom)
        marqueurs[nom] = marqueur
        for dep in paquets[nom].get("dependencies", []):
            a_voir.append((dep["name"], dep.get("marker", "") or marqueur))
    resultat = []
    for nom in sorted(vus - {"ocr-md"}):
        m = marqueurs[nom]
        plateformes = ("macOS" if "darwin" in m else "Windows" if "win32" in m else "Linux" if "linux" in m
                       else "toutes")
        resultat.append((paquets[nom]["name"], paquets[nom]["version"], plateformes))
    return resultat


def _licence_installee(nom: str) -> tuple[str, str] | None:
    try:
        meta = importlib.metadata.metadata(nom)
    except importlib.metadata.PackageNotFoundError:
        return None
    # Ordre : expression SPDX, champ « License » s'il est court (une ligne), classification PyPI
    # (moins précise : une double licence AGPL et commerciale y devient « Other/Proprietary »).
    licence = meta.get("License-Expression") or ""
    texte = (meta.get("License") or "").strip()
    if not licence and texte and len(texte.splitlines()[0]) <= 120:
        licence = texte.splitlines()[0]
    if not licence:
        classes = [c.split("::")[-1].strip() for c in meta.get_all("Classifier") or [] if c.startswith("License ::")]
        licence = " ; ".join(classes)
    adresse = ""
    for entree in meta.get_all("Project-URL") or []:
        cle, _, valeur = entree.partition(",")
        if cle.strip().lower() in ("homepage", "home", "source", "repository", "source code", "documentation"):
            adresse = valeur.strip()
            break
    return licence.strip(), adresse or (meta.get("Home-page") or "")


def licences() -> str:
    lignes = ["# Licences tierces", "",
              "Inventaire généré par `outils/documentation.py` à partir de `uv.lock` (dépendances "
              "d'exécution de l'outil, directes et transitives, toutes plateformes) et des métadonnées "
              "des paquets ; relu à chaque génération. L'outil est distribué sous AGPL-3.0 (fichier "
              "`LICENSE`), licence imposée par PyMuPDF et PyMuPDF4LLM ; le code source de chaque "
              "version est disponible à l'adresse affichée par `ocr-md --version`.", "",
              "## Paquets Python", "",
              "| Paquet | Version | Plateformes | Licence | Projet |", "|---|---|---|---|---|"]
    inconnues = []
    for nom, version, plateformes in dependances_execution():
        trouve = _licence_installee(nom) or LICENCES_CONNUES.get(_norme(nom))
        if trouve is None and _norme(nom).startswith("pyobjc-framework-"):
            trouve = ("MIT", "https://github.com/ronaldoussoren/pyobjc")
        if trouve is None and _norme(nom).startswith("winrt-"):
            trouve = ("MIT", "https://github.com/pywinrt/pywinrt")
        licence, adresse = trouve if trouve else ("inconnue", "")
        if not licence or not any(c.lower() in licence.lower() for c in COMPATIBLES_AGPL):
            inconnues.append(nom)
        lignes.append(f"| {nom} | {version} | {plateformes} | {licence or 'inconnue'} | {adresse} |")
    lignes += ["", "## Données embarquées", "",
               "| Élément | Version | Licence | Source |", "|---|---|---|---|",
               "| Lexique français de Grammalecte (`src/ocr_md/donnees/lexique/formes-fr.txt.gz`) | 7.7 | "
               "MPL-2.0 (texte : `src/ocr_md/donnees/lexique/LICENCE-MPL-2.0.txt`) | https://grammalecte.net |",
               "| Police Noto Sans (`src/ocr_md/donnees/polices/NotoSans-Regular.ttf`) | 2.x | OFL-1.1 (texte : "
               "`src/ocr_md/donnees/polices/LICENCE-OFL-1.1.txt`) | https://notofonts.github.io |", "",
               f"Licences à vérifier (inconnues ou hors de la liste des licences compatibles avec l'AGPL-3.0) : "
               f"{', '.join(inconnues) or 'aucune'}."]
    return "\n".join(lignes) + "\n"


# ------------------------------------------------------------------------------ front matter
SPECIFICATION = RACINE / "docs" / "specification-front-matter.md"


def specification_front_matter() -> str:
    """Section 11 du cahier des charges (front matter, avertissements, repères, rapport),
    reprise telle quelle pour le socle des skills."""
    texte = (RACINE / "docs" / "cahier-des-charges.md").read_text(encoding="utf-8")
    debut = texte.index("## 11. ")
    fin = texte.find("\n## ", debut + 1)
    section = texte[debut:fin if fin != -1 else len(texte)].rstrip()
    corps = section.split("\n", 1)[1].lstrip()  # sans le titre « ## 11. … »
    return ("# Spécification du front matter et de la convention d'avertissement\n\n"
            "Document généré par `outils/documentation.py` à partir de la section 11 du cahier des charges "
            "(`docs/cahier-des-charges.md`), qui fait foi ; schéma JSON : `schema/front-matter-v1.json`. "
            "Destiné au socle des skills qui lisent les sorties d'ocr-md.\n\n" + corps + "\n")


# ------------------------------------------------------------------------------ commande
def documents() -> dict[pathlib.Path, str]:
    return {GUIDE_ADMIN: guide_avec_parametres(GUIDE_ADMIN.read_text(encoding="utf-8")),
            TRACABILITE: tracabilite(), LICENCES: licences(), SPECIFICATION: specification_front_matter()}


def main(arguments=None) -> int:
    verifier = "--verifier" in (arguments if arguments is not None else sys.argv[1:])
    perimes = []
    for chemin, contenu in documents().items():
        actuel = chemin.read_text(encoding="utf-8") if chemin.exists() else ""
        if chemin == LICENCES and verifier and sys.platform != "win32":
            # L'inventaire est généré sous Windows : ailleurs, les métadonnées des paquets propres à
            # une plateforme diffèrent ; seuls les paquets et leurs versions sont comparés.
            def paquets(texte):
                return re.findall(r"^\| ([^|]+) \| ([^|]+) \| ([^|]+) \|", texte, re.MULTILINE)
            actuel, contenu = paquets(actuel), paquets(contenu)
        if actuel != contenu:
            perimes.append(chemin.relative_to(RACINE).as_posix())
            if not verifier:
                if chemin == LICENCES and sys.platform != "win32":
                    print("LICENCES-TIERCES.md se génère sous Windows : non réécrit")
                    continue
                chemin.write_text(contenu, encoding="utf-8", newline="\n")
    if verifier and perimes:
        print("documents à régénérer (uv run python outils/documentation.py) : " + ", ".join(perimes))
        return 1
    print("documents à jour" if not perimes else "documents régénérés : " + ", ".join(perimes))
    return 0


if __name__ == "__main__":
    sys.exit(main())
