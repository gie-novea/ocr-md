"""Moteurs OCR réels (niveau 2) : Windows.Media.Ocr sous Windows, Apple Vision sous macOS.

Page synthétique rendue à 300 dpi. Vérifie la reconnaissance (avec les équivalences
œ/oe, æ/ae, ’/' admises), la position des boîtes et, sous macOS, la convention des
coordonnées de Vision (PV-06 b). Le fichier 18 (ligatures) est simulé ici en attendant le
générateur du jalon 2.
"""

import re

import pymupdf
import pytest
from PIL import Image

from ocr_md import ocr, qualite
from tests.donnees import fabrication as fab

DPI = 300


def page_image(lignes, mot_unique="MOTUNIQUE"):
    doc = pymupdf.open()
    page = fab.page_native(doc, lignes, mot_unique=mot_unique)
    pix = page.get_pixmap(dpi=DPI, colorspace=pymupdf.csGRAY)
    return page, Image.frombytes("L", (pix.width, pix.height), pix.samples)


def mots(texte):
    return [re.sub(r"^[^\w€]+|[^\w€]+$", "", qualite.forme_comparable(m)) for m in texte.split()]


def taux_retrouves(reference, lu):
    lus = set(mots(lu))
    ref = [m for m in mots(" ".join(reference)) if m]
    return sum(m in lus for m in ref) / len(ref)


def centre_dans(boite, verite, marge=0.5):
    x, y = (boite[0] + boite[2]) / 2, (boite[1] + boite[3]) / 2
    dx, dy = (verite[2] - verite[0]) * marge, (verite[3] - verite[1]) * marge
    return verite[0] - dx <= x <= verite[2] + dx and verite[1] - dy <= y <= verite[3] + dy


def moteur_ou_saut():
    try:
        return ocr.moteur_systeme()
    except ocr.MoteurIndisponible as e:
        pytest.skip(f"moteur OCR du système indisponible sur ce poste : {e}")


def verifier_reconnaissance(moteur):
    page, image = page_image(fab.LIGNES_REFERENCE)
    resultat = moteur.reconnaitre(image)
    taux = taux_retrouves(fab.LIGNES_REFERENCE, resultat.texte)
    print(f"{moteur.description()} : {taux:.1%} des mots de référence retrouvés")
    assert taux >= 0.95  # objectif 7.3, équivalences admises
    verite = {m: b for m, b, _ in fab.verite_mots(page, DPI)}
    unique = [mt for l in resultat.lignes for mt in l.mots if mt.texte == "MOTUNIQUE"]
    assert unique, "mot unique non reconnu"
    assert centre_dans(unique[0].boite, verite["MOTUNIQUE"])
    return resultat


def verifier_ligatures_reconnues(moteur):
    _, image = page_image(fab.LIGNES_LIGATURES, mot_unique="")
    resultat = moteur.reconnaitre(image)
    taux = taux_retrouves(fab.LIGNES_LIGATURES, resultat.texte)
    print(f"{moteur.description()} : ligatures, {taux:.1%} des mots retrouvés")
    assert taux >= 0.95
    lexique = qualite.Lexique()
    alphabetiques = [m for m in mots(resultat.texte) if len(m) >= 3 and m.isalpha()]
    inconnus = [m for m in alphabetiques if m.split("'")[-1] not in lexique]
    # L'heuristique complète arrive au jalon 7 ; ici, le taux de mots inconnus doit rester
    # très inférieur au seuil de 0,35 malgré « oeuvre », « coeur », etc.
    assert len(inconnus) / len(alphabetiques) < 0.10, inconnus


@pytest.mark.windows
@pytest.mark.exigence("EX-27", "EX-24")
def test_windows_media_ocr_reel():
    moteur = moteur_ou_saut()
    assert moteur.nom == "windows-media-ocr"
    assert "fr-FR" in moteur.langues_disponibles()
    assert moteur.dimension_max() >= 4000
    resultat = verifier_reconnaissance(moteur)
    assert resultat.niveau_mots


@pytest.mark.windows
@pytest.mark.exigence("EX-36")
def test_windows_ligatures_restent_dans_le_lexique():
    verifier_ligatures_reconnues(moteur_ou_saut())


@pytest.mark.macos
@pytest.mark.exigence("EX-26")
def test_apple_vision_reel():
    from ocr_md.ocr import macos
    langues = macos.langues_disponibles()
    print(f"Langues Vision (accurate) : {langues}")
    assert "fr-FR" in langues  # PV-08 a
    moteur = moteur_ou_saut()
    assert moteur.nom == "apple-vision"
    resultat = verifier_reconnaissance(moteur)
    confiances = [l.confiance for l in resultat.lignes]
    assert all(c is not None and 0 <= c <= 1 for c in confiances)


@pytest.mark.macos
@pytest.mark.exigence("EX-30")
def test_apple_vision_convention_des_boites():
    """PV-06 b : établit l'origine des boîtes normalisées de Vision (haut ou bas)."""
    from ocrmac import ocrmac

    from ocr_md.ocr import macos
    page, image = page_image(fab.LIGNES_REFERENCE)
    verite = {m: b for m, b, _ in fab.verite_mots(page, DPI)}
    brut = [r for r in ocrmac.OCR(image.convert("RGB"), recognition_level="accurate",
                                  language_preference=["fr-FR"]).recognize() if "MOTUNIQUE" in r[0]]
    assert brut
    w, h = image.size
    en_bas = macos.boite_en_pixels(brut[0][2], w, h, origine_en_bas=True)
    en_haut = macos.boite_en_pixels(brut[0][2], w, h, origine_en_bas=False)
    print(f"boîte normalisée {brut[0][2]} ; origine en bas -> {en_bas} ; en haut -> {en_haut} ; "
          f"vérité {verite['MOTUNIQUE']}")
    assert centre_dans(en_bas, verite["MOTUNIQUE"]) == macos.ORIGINE_EN_BAS
    assert centre_dans(en_haut, verite["MOTUNIQUE"]) != macos.ORIGINE_EN_BAS


@pytest.mark.macos
@pytest.mark.exigence("EX-36")
def test_apple_vision_ligatures_restent_dans_le_lexique():
    verifier_ligatures_reconnues(moteur_ou_saut())
