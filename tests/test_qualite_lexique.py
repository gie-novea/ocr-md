"""Lexique embarqué et équivalences œ/oe, æ/ae, ’/' (EX-36, EX-37)."""

import time

import pytest

from ocr_md import qualite


@pytest.mark.exigence("EX-37")
def test_lexique_charge_depuis_le_paquet_sans_reseau():
    debut = time.perf_counter()
    taille = qualite.Lexique.taille()
    assert taille > 400_000
    assert time.perf_counter() - debut < 5  # objectif PV-12 : < 1 s sur un poste de bureau


@pytest.mark.exigence("EX-36", "EX-37")
@pytest.mark.parametrize("mot", ["œuvre", "oeuvre", "cœur", "coeur", "Lætitia", "maître", "d’œuvre",
                                 "l'oeuvre", "Candidature", "DUME", "DPGF", "SIRET"])
def test_mots_connus_y_compris_formes_de_l_ocr_windows(mot):
    lexique = qualite.Lexique()
    cle = mot.split("’")[-1].split("'")[-1]  # l’élision est retirée par l'heuristique (jalon 7)
    assert cle in lexique


@pytest.mark.exigence("EX-37")
def test_complement_par_configuration():
    assert "Novéa" not in qualite.Lexique()
    assert "Novéa" in qualite.Lexique(["novéa"])


@pytest.mark.exigence("EX-36")
def test_forme_comparable():
    assert qualite.forme_comparable("maître d’œuvre, ÆON, ex æquo") == "maître d'oeuvre, AEON, ex aequo"
    assert qualite.forme_comparable("été") == "été"  # NFD -> NFC


@pytest.mark.exigence("EX-37", "EX-78")
def test_avis_de_licence_mpl_conserve():
    import gzip
    import importlib.resources
    f = importlib.resources.files("ocr_md") / "donnees" / "lexique" / "formes-fr.txt.gz"
    with f.open("rb") as brut, gzip.open(brut, "rt", encoding="utf-8") as g:
        entete = g.read(600)
    assert "Mozilla Public" in entete and "MPL v2.0" in entete
    assert (importlib.resources.files("ocr_md") / "donnees" / "lexique" / "LICENCE-MPL-2.0.txt").is_file()
