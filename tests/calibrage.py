"""Calibrage des seuils de qualité (EX-76).

Calcule, pour chaque page reconnue ou à couche OCR d'un dossier de PDF, les indicateurs de
EX-35 et EX-36 et le verdict obtenu avec les seuils en vigueur. Avec le jeu de test (qui
contient un manifeste), compare le verdict à la vérité terrain et donne, par origine du texte
(couche OCR existante ou moteur) et par indicateur, l'écart entre la page saine la plus
défavorable et la page dégradée la plus favorable du manifeste, avec son milieu.

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
    from ocr_md import images
    extensions_images = (".jpg", ".jpeg", ".png", ".tif", ".tiff")
    fichiers = [c for c in dossier.rglob("*") if c.is_file() and c.suffix.lower() in (".pdf",) + extensions_images]
    for chemin in sorted(fichiers):
        relatif = chemin.relative_to(dossier).as_posix()
        if "_OCR" in chemin.parts:
            continue
        try:
            # Images : même conversion en PDF que l'outil (EX-34).
            doc = images.image_vers_pdf(chemin) if chemin.suffix.lower() in extensions_images else pymupdf.open(chemin)
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
            confiance = part_basse = q = None
            if a.categorie == "couche_existante":
                texte = page.get_text()
            else:
                from ocr_md.traiteurs.pdf import resolution_effective, resumer
                pix = page.get_pixmap(dpi=p.ocr_dpi, colorspace=pymupdf.csGRAY)
                image = Image.frombytes("L", (pix.width, pix.height), pix.samples)
                q = qualite.mesurer_image(image, resolution_effective(page))
                resultat = moteur.reconnaitre(image)
                resume = resumer(resultat, p.confiance_basse)
                texte, confiance, part_basse = resume.texte, resume.confiance_moyenne, resume.part_confiance_basse
            surface = page.rect.width * page.rect.height * CM2_PAR_PT2
            ind = qualite.calculer(texte, lexique, surface)
            non_blanche = ecart_type(page) > p.page_blanche_ecart_type_max
            origine = qualite.ORIGINE_COUCHE if a.categorie == "couche_existante" else moteur.nom
            motifs = (qualite.motifs_lexicaux(ind, p, non_blanche, origine)
                      + qualite.motifs_confiance(confiance, part_basse, p))
            v = qualite.verdict_image(q, ind, p, origine)
            if v is not None and v.douteuse:
                motifs.append(qualite.MOTIF_IMAGE)
            lignes.append({
                "fichier": relatif, "page": a.numero, "categorie": a.categorie, "origine": origine,
                "mots": ind.mots, "mots_evaluables": ind.mots_evaluables,
                **{k: round(getattr(ind, k), 4) for k in INDICATEURS},
                "confiance": None if confiance is None else round(confiance, 3),
                "image": None if q is None else {"resolution_dpi": q.resolution_dpi, "part_gris": q.part_gris,
                                                 "contraste": q.contraste, "bruit": q.bruit,
                                                 "niveau": v.niveau},
                "verdict": "douteuse" if motifs else "bonne", "motifs": motifs,
                "attendu": None if not verite else ("douteuse" if a.numero in verite.get("pages_douteuses", []) else "bonne"),
            })
    return lignes


VALEURS_CAHIER = {"taux_mots_inconnus": 0.35, "taux_caracteres_aberrants": 0.03, "taux_mots_fragmentes": 0.25,
                  "taux_melange_chiffres_lettres": 0.10, "densite": 0.2}


def ecarts(lignes: list[dict], p) -> dict[str, list[dict]]:
    """Par origine du texte (couche OCR existante, ou moteur de l'outil) et par indicateur :
    valeur de la page saine la plus défavorable et de la page dégradée la plus favorable. Les
    pages saines et dégradées sont celles que déclare le manifeste (vérité terrain), et non
    celles que déclenchent les seuils en vigueur. Pour les mots inconnus, seules comptent les
    pages d'au moins `mots_evaluables_min` mots évaluables (EX-36)."""
    connues = [l for l in lignes if l["attendu"]]
    resultat = {}
    for origine in sorted({l["origine"] for l in connues}):
        groupe = [l for l in connues if l["origine"] == origine]
        lignes_origine = []
        for ind, cahier in VALEURS_CAHIER.items():
            retenues = [l for l in groupe
                        if ind != "taux_mots_inconnus" or l["mots_evaluables"] >= p.mots_evaluables_min]
            saines = [l for l in retenues if l["attendu"] == "bonne"]
            degradees = [l for l in retenues if l["attendu"] == "douteuse"]
            if ind == "densite":  # seuil « en deçà » : les pages saines sont au-dessus
                pire_saine = min(saines, key=lambda l: l[ind], default=None)
                meilleure_degradee = max(degradees, key=lambda l: l[ind], default=None)
                separe = bool(pire_saine and meilleure_degradee and meilleure_degradee[ind] < pire_saine[ind])
            else:
                pire_saine = max(saines, key=lambda l: l[ind], default=None)
                meilleure_degradee = min(degradees, key=lambda l: l[ind], default=None)
                separe = bool(pire_saine and meilleure_degradee and meilleure_degradee[ind] > pire_saine[ind])
            ligne = {"indicateur": ind, "cahier": cahier, "saine": pire_saine, "degradee": meilleure_degradee,
                     "separe": separe}
            if separe:
                bas, haut = sorted((pire_saine[ind], meilleure_degradee[ind]))
                ligne["dans_l_ecart"] = bas < cahier < haut
                ligne["milieu"] = round((bas + haut) / 2, 3)
            lignes_origine.append(ligne)
        resultat[origine] = lignes_origine
    return resultat


def tableau_ecarts(lignes_ecarts: list[dict]) -> str:
    sortie = ["| indicateur | page saine la plus défavorable | page dégradée la plus favorable | valeur du cahier "
              "| dans l'écart | milieu |", "|---|---|---|---|---|---|"]

    def page(l, ind):
        return f"{l[ind]:.3f} ({l['fichier']} p. {l['page']})" if l else "aucune"
    for e in lignes_ecarts:
        ind = e["indicateur"]
        if e["separe"]:
            dans = "oui" if e["dans_l_ecart"] else "non"
        else:
            dans = "pas d'écart" if e["saine"] and e["degradee"] else ""
        sortie.append(f"| {ind} | {page(e['saine'], ind)} | {page(e['degradee'], ind)} | {e['cahier']} | {dans} "
                      f"| {e.get('milieu', '')} |")
    return "\n".join(sortie)


MESURES_IMAGE = (("resolution_dpi", "image_resolution_min_dpi", "min"), ("part_gris", "image_part_gris_max", "max"),
                 ("contraste", "image_contraste_min", "min"), ("bruit", "image_bruit_max", "max"))


def ecarts_image(lignes: list[dict]) -> list[dict]:
    """Pour chaque mesure de qualite_image (pages reconnues par l'outil, indépendantes du
    moteur) : page saine la plus défavorable, puis page dégradée la plus proche au-delà d'elle
    (les pages dégradées que la mesure ne distingue pas relèvent d'une autre mesure), et milieu."""
    connues = [l for l in lignes if l["attendu"] and l.get("image")]
    resultat = []
    for mesure, parametre, sens in MESURES_IMAGE:
        valeurs = [(l, l["image"][mesure]) for l in connues if l["image"][mesure] is not None]
        saines = [(l, v) for l, v in valeurs if l["attendu"] == "bonne"]
        degradees = [(l, v) for l, v in valeurs if l["attendu"] == "douteuse"]
        if not saines:
            continue
        if sens == "min":  # page douteuse si la mesure est sous le seuil
            pire = min(saines, key=lambda x: x[1])
            au_dela = [x for x in degradees if x[1] < pire[1]]
            proche = max(au_dela, key=lambda x: x[1], default=None)
        else:
            pire = max(saines, key=lambda x: x[1])
            au_dela = [x for x in degradees if x[1] > pire[1]]
            proche = min(au_dela, key=lambda x: x[1], default=None)
        resultat.append({"mesure": mesure, "parametre": parametre, "saine": pire, "degradee": proche,
                         "pages": sorted(f"{l['fichier']} p. {l['page']}" for l, _ in au_dela),
                         "milieu": None if proche is None else round((pire[1] + proche[1]) / 2, 3)})
    return resultat


def tableau_ecarts_image(lignes_ecarts: list[dict]) -> str:
    sortie = ["| mesure | page saine la plus défavorable | page dégradée la plus proche au-delà | milieu "
              "| pages dégradées distinguées |", "|---|---|---|---|---|"]
    for e in lignes_ecarts:
        def page(x):
            return "aucune" if x is None else f"{x[1]} ({x[0]['fichier']} p. {x[0]['page']})"
        sortie.append(f"| {e['mesure']} | {page(e['saine'])} | {page(e['degradee'])} | {e['milieu'] or ''} "
                      f"| {', '.join(e['pages'])} |")
    return "\n".join(sortie)


def tableau(lignes: list[dict]) -> str:
    entete = ["fichier", "page", "origine", "mots", "évaluables", "inconnus", "aberrants", "fragmentés",
              "mélanges", "densité", "confiance", "verdict", "attendu"]
    sortie = ["| " + " | ".join(entete) + " |", "|" + "---|" * len(entete)]
    for l in lignes:
        valeurs = [l["fichier"], l["page"], l["origine"], l["mots"], l["mots_evaluables"]] + \
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
    print("\nQualité de l'image (mesures avant OCR, indépendantes du moteur) :\n")
    for l in lignes:
        if l.get("image"):
            i = l["image"]
            print(f"| {l['fichier']} | {l['page']} | {i['resolution_dpi']} dpi | gris {i['part_gris']} | "
                  f"contraste {i['contraste']} | bruit {i['bruit']} | {l['attendu'] or ''} |")
    print("\nÉcart par mesure de qualite_image :\n")
    print(tableau_ecarts_image(ecarts_image(lignes)))
    resultat = ecarts(lignes, p)
    for origine, lignes_ecarts in resultat.items():
        print(f"\nÉcart par indicateur, origine du texte « {origine} » (pages saines et dégradées du manifeste) :\n")
        print(tableau_ecarts(lignes_ecarts))
    return lignes, erreurs, resultat


if __name__ == "__main__":
    main()
