"""Moteur OCR factice instrumenté (section 3.3, EX-24, EX-75)."""

import pymupdf
import pytest
from PIL import Image

from ocr_md import ocr
from ocr_md.ocr.factice import MoteurFactice, dessiner_marqueur, lire_marqueur


def rendu(chemin, n, dpi):
    pix = pymupdf.open(chemin)[n].get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY)
    return Image.frombytes("L", (pix.width, pix.height), pix.samples)


@pytest.mark.parametrize("ident", [0, 1, 255, 4097, 65535])
def test_marqueur_aller_retour(ident):
    img = dessiner_marqueur(Image.new("L", (2480, 3508), 255), ident)
    assert lire_marqueur(img) == ident
    assert lire_marqueur(img.resize((595, 842))) == ident  # 72 dpi
    assert lire_marqueur(Image.new("L", (2480, 3508), 255)) is None


@pytest.mark.exigence("EX-24", "EX-75")
def test_factice_restitue_le_manifeste_et_compte_les_appels(jeu_de_test):
    racine, m = jeu_de_test
    f = next(x for x in m["fichiers"] if x["numero"] == "2")
    moteur = MoteurFactice(m["ocr_factice"])
    for n, ident in enumerate(f["id_images"]):
        for dpi in (150, 300):
            r = moteur.reconnaitre(rendu(racine / f["chemin"], n, dpi))
            assert f["mots_uniques"][n] in r.texte
            assert r.largeur == round(595 * dpi / 72) or abs(r.largeur - 595 * dpi / 72) < 2
            assert all(0 <= mt.boite[0] < mt.boite[2] <= r.largeur for l in r.lignes for mt in l.mots)
            assert all(mt.confiance == 0.95 for l in r.lignes for mt in l.mots)
    assert moteur.nombre_appels == 2 * len(f["id_images"])
    assert moteur.appels == [i for i in f["id_images"] for _ in (150, 300)]


@pytest.mark.exigence("EX-35", "EX-75")
def test_factice_confiance_imposee_et_mode_sans_confiance(jeu_de_test):
    racine, m = jeu_de_test
    f = next(x for x in m["fichiers"] if x["numero"] == "5")
    avec = MoteurFactice(m["ocr_factice"]).reconnaitre(rendu(racine / f["chemin"], 1, 150))
    assert {l.confiance for l in avec.lignes} == {0.30}
    assert "Mémoire technique" not in avec.texte and "MOTFLOU02" in avec.texte  # texte dégradé
    sans = MoteurFactice(m["ocr_factice"], avec_confiance=False).reconnaitre(rendu(racine / f["chemin"], 1, 150))
    assert {mt.confiance for l in sans.lignes for mt in l.mots} == {None}


@pytest.mark.exigence("EX-75")
def test_image_inconnue_donne_un_resultat_vide_mais_compte(jeu_de_test):
    _, m = jeu_de_test
    moteur = MoteurFactice(m["ocr_factice"])
    r = moteur.reconnaitre(Image.new("L", (1000, 1400), 255))
    assert r.lignes == () and moteur.appels == [None]


@pytest.mark.exigence("EX-07", "EX-75")
def test_moteur_factice_par_variable_d_environnement(jeu_de_test, monkeypatch):
    racine, _ = jeu_de_test
    monkeypatch.setenv("OCR_MD_MOTEUR_FACTICE", str(racine / "manifeste.json"))
    moteur = ocr.moteur_systeme()
    assert isinstance(moteur, MoteurFactice) and moteur.avec_confiance
    monkeypatch.setenv("OCR_MD_MOTEUR_FACTICE_SANS_CONFIANCE", "1")
    assert not ocr.moteur_systeme().avec_confiance
