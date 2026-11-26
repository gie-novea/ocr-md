"""PV-14 : boîtes par mot avec Apple Vision (boundingBoxForRange) : mesure en CI macOS.

Trois façons d'écrire le calque sont comparées sur les pages des fichiers 2 et 18 :
- « ligne » : une écriture par ligne (comportement des jalons 4 et 5) ;
- « prorata » : mots répartis au prorata des caractères dans la boîte de la ligne ;
- « vision » : boîte de chaque mot fournie par Vision.
Mesures : taux de mots de référence retrouvés dans le texte du calque, part des mots de
référence (4 lettres ou plus) trouvés par search_for au bon endroit (centre dans la boîte
de vérité agrandie de 10 %), critère EX-30 (b) (cinq mots par page), temps par page.
"""

import dataclasses
import time

import pymupdf
import pytest
from PIL import Image

from ocr_md import calque
from tests.test_moteurs_reels import taux_retrouves

FICHIERS = ("pdf/02_scanne.pdf", "pdf/18_ligatures.pdf")


def verite_mots(m, ident, page):
    v = {}
    for ligne in m["ocr_factice"][str(ident)]["lignes"]:
        for mot, b in ligne["mots"]:
            if len(mot) >= 4 and mot.isalpha():
                v.setdefault(mot, pymupdf.Rect(b[0] * page.rect.width, b[1] * page.rect.height,
                                               b[2] * page.rect.width, b[3] * page.rect.height))
    return v


def bien_place(page, mot, verite):
    dx, dy = verite.width * 0.05, verite.height * 0.05
    zone = pymupdf.Rect(verite.x0 - dx, verite.y0 - dy, verite.x1 + dx, verite.y1 + dy)
    return any(zone.contains((r.tl + r.br) / 2) for r in page.search_for(mot))


@pytest.mark.macos
def test_pv14_boites_par_mot_vision(jeu_de_test):
    from ocr_md.ocr import macos
    racine, m = jeu_de_test
    moteurs = {"vision": macos.MoteurMacos(mode="mots"), "prorata": macos.MoteurMacos(mode="prorata")}
    mesures = {k: {"retrouves": [], "places": [], "ex30b": 0, "temps": []} for k in ("ligne", "prorata", "vision")}
    pages = 0
    for chemin in FICHIERS:
        f = next(x for x in m["fichiers"] if x["chemin"] == chemin)
        source = pymupdf.open(racine / chemin)
        for n, ident in enumerate(f["id_images"]):
            pages += 1
            pix = source[n].get_pixmap(dpi=300, colorspace=pymupdf.csGRAY)
            image = Image.frombytes("L", (pix.width, pix.height), pix.samples)
            resultats = {}
            for nom, moteur in moteurs.items():
                debut = time.perf_counter()
                resultats[nom] = moteur.reconnaitre(image)
                mesures[nom]["temps"].append(time.perf_counter() - debut)
            resultats["ligne"] = dataclasses.replace(resultats["prorata"], niveau_mots=False)
            mesures["ligne"]["temps"].append(mesures["prorata"]["temps"][-1])
            for nom, resultat in resultats.items():
                doc = pymupdf.open()
                doc.insert_pdf(source, from_page=n, to_page=n)
                page = doc[0]
                calque.ecrire_calque(page, resultat)
                verite = verite_mots(m, ident, page)
                places = [bien_place(page, mot, v) for mot, v in verite.items()]
                mesures[nom]["retrouves"].append(taux_retrouves([f["texte_reference"][n]], page.get_text()))
                mesures[nom]["places"].append(sum(places) / len(places))
                mesures[nom]["ex30b"] += all(places[:5])
    stats = moteurs["vision"].statistiques
    part_vision = stats["mots_boite_vision"] / max(1, stats["mots_boite_vision"] + stats["mots_prorata"])
    print(f"\nPV-14 : {pages} pages ; mots avec boîte fournie par Vision : {part_vision:.1%}")
    for nom, v in mesures.items():
        print(f"PV-14 {nom:8s}: mots retrouvés {min(v['retrouves']):.1%} à {max(v['retrouves']):.1%} ; "
              f"mots bien placés {sum(v['places']) / pages:.1%} (min {min(v['places']):.1%}) ; "
              f"EX-30 b réussi sur {v['ex30b']}/{pages} pages ; "
              f"temps par page {sum(v['temps']) / pages:.2f} s")
    assert part_vision >= 0.90
    assert mesures["vision"]["ex30b"] == pages
    assert sum(mesures["vision"]["places"]) >= sum(mesures["prorata"]["places"]) - 0.02 * pages
