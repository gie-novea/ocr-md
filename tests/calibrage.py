"""Calibrage des seuils de qualité (EX-76).

Calcule, pour chaque page reconnue ou à couche OCR d'un dossier de PDF, les indicateurs de
EX-35 et EX-36 et le verdict obtenu avec les seuils en vigueur. Avec le jeu de test (qui
contient un manifeste), compare le verdict à la vérité terrain et propose, pour chaque
indicateur, le seuil de marge maximale : milieu entre la plus forte valeur des pages saines
et la plus faible valeur des pages douteuses qui le déclenchent.

La sortie ne contient que des noms de fichiers, des numéros de page et des nombres : aucun
texte de document. Le script peut être lancé par le référent sur un dossier de documents
réels, en local, pour ajuster les seuils en recette.

Usage :
    python tests/calibrage.py [DOSSIER] [--moteur factice|systeme] [--config FICHIER]
DOSSIER vaut par défaut le jeu de test (tests/donnees/jeu, généré s'il manque).
"""

import argparse
import json
import pathlib
import sys

import pymupdf
from PIL import Image, ImageStat

if __package__ in (None, ""):
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from ocr_md import analyse_pdf, config, ocr, qualite  # noqa: E402

INDICATEURS = ("taux_mots_inconnus", "taux_caracteres_aberrants", "taux_mots_fragmentes",
               "taux_melange_chiffres_lettres", "densite")
CM2_PAR_PT2 = (2.54 / 72) ** 2


def ecart_type(page) -> float:
    pix = page.get_pixmap(dpi=50, colorspace=pymupdf.csGRAY)
    return ImageStat.Stat(Image.frombytes("L", (pix.width, pix.height), pix.samples)).stddev[0]


def mesurer(dossier: pathlib.Path, moteur, p) -> list[dict]:
    lexique = qualite.Lexique(p.lexique_complementaire)
    manifeste = {}
    if (dossier / "manifeste.json").is_file():
        m = json.loads((dossier / "manifeste.json").read_text(encoding="utf-8"))
        manifeste = {f["chemin"]: f for f in m["fichiers"]}
    lignes = []
    for chemin in sorted(dossier.rglob("*.pdf")):
        relatif = chemin.relative_to(dossier).as_posix()
        if "_OCR" in chemin.parts:
            continue
        try:
            doc = pymupdf.open(chemin)
            if doc.needs_pass:
                continue
            analyses = analyse_pdf.analyser(doc, p)
        except Exception:
            continue
        verite = manifeste.get(relatif, {})
        for a in analyses:
            if a.categorie not in ("image", "couche_existante"):
                continue
            page = doc[a.numero - 1]
            confiance = part_basse = None
            if a.categorie == "couche_existante":
                texte = page.get_text()
            else:
                pix = page.get_pixmap(dpi=p.ocr_dpi, colorspace=pymupdf.csGRAY)
                resultat = moteur.reconnaitre(Image.frombytes("L", (pix.width, pix.height), pix.samples))
                from ocr_md.traiteurs.pdf import resumer
                resume = resumer(resultat, p.confiance_basse)
                texte, confiance, part_basse = resume.texte, resume.confiance_moyenne, resume.part_confiance_basse
            surface = page.rect.width * page.rect.height * CM2_PAR_PT2
            ind = qualite.calculer(texte, lexique, surface)
            non_blanche = ecart_type(page) > p.page_blanche_ecart_type_max
            motifs = qualite.motifs_lexicaux(ind, p, non_blanche) + qualite.motifs_confiance(confiance, part_basse, p)
            lignes.append({
                "fichier": relatif, "page": a.numero, "categorie": a.categorie,
                "mots": ind.mots, "mots_evaluables": ind.mots_evaluables,
                **{k: round(getattr(ind, k), 4) for k in INDICATEURS},
                "confiance": None if confiance is None else round(confiance, 3),
                "verdict": "douteuse" if motifs else "bonne", "motifs": motifs,
                "attendu": None if not verite else ("douteuse" if a.numero in verite.get("pages_douteuses", []) else "bonne"),
            })
    return lignes


def proposer(lignes: list[dict], p) -> dict:
    """Seuil de marge maximale pour chaque indicateur (« au-delà » : page douteuse)."""
    propositions = {}
    connues = [l for l in lignes if l["attendu"]]
    for ind, param in (("taux_mots_inconnus", "taux_mots_inconnus_max"),
                       ("taux_caracteres_aberrants", "taux_caracteres_aberrants_max"),
                       ("taux_mots_fragmentes", "taux_mots_fragmentes_max"),
                       ("taux_melange_chiffres_lettres", "taux_melange_chiffres_lettres_max")):
        saines = [l[ind] for l in connues if l["attendu"] == "bonne"
                  and (ind != "taux_mots_inconnus" or l["mots_evaluables"] >= p.mots_evaluables_min)]
        douteuses = [l[ind] for l in connues if l["attendu"] == "douteuse" and ind in l["motifs"]]
        if saines and douteuses:
            propositions[param] = round((max(saines) + min(douteuses)) / 2, 3)
    # Densité : seuil « en deçà » ; milieu entre la plus forte densité des pages douteuses qui
    # le déclenchent et la plus faible des pages saines (à défaut, moitié de cette dernière).
    saines = [l["densite"] for l in connues if l["attendu"] == "bonne" and l["densite"] is not None]
    basses = [l["densite"] for l in connues if l["attendu"] == "douteuse" and "densite_anormale" in l["motifs"]
              and l["densite"] is not None and l["densite"] < min(saines or [0])]
    if saines and basses:
        propositions["densite_min"] = round((max(basses) + min(saines)) / 2, 3)
    elif saines and min(saines) < p.densite_min:
        propositions["densite_min"] = round(min(saines) / 2, 3)
    return propositions


VALEURS_CAHIER = {"taux_mots_inconnus": 0.35, "taux_caracteres_aberrants": 0.03, "taux_mots_fragmentes": 0.25,
                  "taux_melange_chiffres_lettres": 0.10, "densite": 0.2}
MOTIF = {"taux_mots_inconnus": "taux_mots_inconnus", "taux_caracteres_aberrants": "taux_caracteres_aberrants",
         "taux_mots_fragmentes": "taux_mots_fragmentes", "taux_melange_chiffres_lettres": "taux_melange_chiffres_lettres",
         "densite": "densite_anormale"}


def ecarts(lignes: list[dict], p) -> list[dict]:
    """Pour chaque indicateur : valeur de la page saine la plus défavorable, valeur de la page
    dégradée la plus favorable parmi celles que l'indicateur déclenche (les pages dégradées par
    un autre défaut ne disent rien de cet indicateur), et position de la valeur du cahier."""
    connues = [l for l in lignes if l["attendu"]]
    resultat = []
    for ind, cahier in VALEURS_CAHIER.items():
        saines = [l for l in connues if l["attendu"] == "bonne"
                  and (ind != "taux_mots_inconnus" or l["mots_evaluables"] >= p.mots_evaluables_min)]
        degradees = [l for l in connues if l["attendu"] == "douteuse" and MOTIF[ind] in l["motifs"]]
        if ind == "densite":  # seuil « en deçà » : les pages saines sont au-dessus
            degradees = [l for l in degradees if l["densite"] < p.densite_min]
            pire_saine = min(saines, key=lambda l: l[ind], default=None)
            meilleure_degradee = max(degradees, key=lambda l: l[ind], default=None)
        else:
            pire_saine = max(saines, key=lambda l: l[ind], default=None)
            meilleure_degradee = min(degradees, key=lambda l: l[ind], default=None)
        ligne = {"indicateur": ind, "cahier": cahier, "saine": pire_saine, "degradee": meilleure_degradee}
        if pire_saine and meilleure_degradee:
            bas, haut = sorted((pire_saine[ind], meilleure_degradee[ind]))
            ligne["dans_l_ecart"] = bas < cahier < haut
            ligne["milieu"] = round((bas + haut) / 2, 3)
        resultat.append(ligne)
    return resultat


def tableau_ecarts(lignes_ecarts: list[dict]) -> str:
    sortie = ["| indicateur | page saine la plus défavorable | page dégradée la plus favorable | valeur du cahier | dans l'écart | milieu |",
              "|---|---|---|---|---|---|"]
    def page(l, ind):
        return f"{l[ind]:.3f} ({l['fichier']} p. {l['page']})" if l else "aucune"
    for e in lignes_ecarts:
        ind = e["indicateur"]
        dans = "" if "dans_l_ecart" not in e else ("oui" if e["dans_l_ecart"] else "non")
        sortie.append(f"| {ind} | {page(e['saine'], ind)} | {page(e['degradee'], ind)} | {e['cahier']} | {dans} | {e.get('milieu', '')} |")
    return "\n".join(sortie)


def tableau(lignes: list[dict]) -> str:
    entete = ["fichier", "page", "catégorie", "mots", "évaluables", "inconnus", "aberrants", "fragmentés",
              "mélanges", "densité", "confiance", "verdict", "attendu"]
    sortie = ["| " + " | ".join(entete) + " |", "|" + "---|" * len(entete)]
    for l in lignes:
        valeurs = [l["fichier"], l["page"], l["categorie"], l["mots"], l["mots_evaluables"]] + \
            [f"{l[k]:.3f}" for k in INDICATEURS] + [l["confiance"] if l["confiance"] is not None else "",
                                                     l["verdict"], l["attendu"] or ""]
        sortie.append("| " + " | ".join(str(v) for v in valeurs) + " |")
    return "\n".join(sortie)


def main(arguments=None):
    a = argparse.ArgumentParser(description="Calibrage des seuils de qualité d'ocr-md (EX-76)")
    a.add_argument("dossier", nargs="?")
    a.add_argument("--moteur", choices=("factice", "systeme"), default="factice")
    a.add_argument("--config")
    o = a.parse_args(arguments)
    # Messages de MuPDF (PDF réparés du jeu) : hors de la sortie, qui ne contient que le tableau.
    pymupdf.TOOLS.mupdf_display_errors(False)
    pymupdf.TOOLS.mupdf_display_warnings(False)
    p = config.charger(o.config)
    if o.dossier:
        dossier = pathlib.Path(o.dossier)
    else:
        dossier = pathlib.Path(__file__).parent / "donnees" / "jeu"
        if not (dossier / "manifeste.json").is_file():
            from tests.donnees import generer
            generer.generer(dossier)
    if o.moteur == "factice" and (dossier / "manifeste.json").is_file():
        from ocr_md.ocr.factice import MoteurFactice
        moteur = MoteurFactice.depuis_manifeste(dossier / "manifeste.json")
    else:
        moteur = ocr.moteur_systeme(p.langue_ocr, p.langue_ocr_secondaire)
    lignes = mesurer(dossier, moteur, p)
    print(tableau(lignes))
    erreurs = [l for l in lignes if l["attendu"] and l["verdict"] != l["attendu"]]
    print(f"\n{len(lignes)} page(s) mesurée(s) ; erreurs de verdict par rapport à la vérité terrain : {len(erreurs)}")
    for l in erreurs:
        print(f"  {l['fichier']} page {l['page']} : {l['verdict']} au lieu de {l['attendu']} ({' '.join(l['motifs'])})")
    print("\nÉcart par indicateur (pages dégradées : celles que l'indicateur déclenche) :\n")
    print(tableau_ecarts(ecarts(lignes, p)))
    propositions = proposer(lignes, p)
    if propositions:
        print("\nseuils de marge maximale (pour information) : " + ", ".join(f"{k} = {v}" for k, v in propositions.items()))
    return lignes, erreurs, propositions


if __name__ == "__main__":
    main()
