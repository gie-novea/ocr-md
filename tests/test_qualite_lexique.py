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
    assert qualite.forme_comparable("ingénieur ﬂuides, ﬁche, eﬀectif") == "ingénieur fluides, fiche, effectif"


@pytest.mark.exigence("EX-37", "EX-78")
def test_avis_de_licence_mpl_conserve():
    import gzip
    import importlib.resources
    f = importlib.resources.files("ocr_md") / "donnees" / "lexique" / "formes-fr.txt.gz"
    with f.open("rb") as brut, gzip.open(brut, "rt", encoding="utf-8") as g:
        entete = g.read(600)
    assert "Mozilla Public" in entete and "MPL v2.0" in entete
    assert (importlib.resources.files("ocr_md") / "donnees" / "lexique" / "LICENCE-MPL-2.0.txt").is_file()


SCRIPT_CHARGEMENT = r'''
import pathlib, sys
import pymupdf
from ocr_md import cli, config, qualite, traitement
racine = pathlib.Path(sys.argv[1])
(racine / "P").mkdir()
for i in range(3):
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), "Texte natif sans évaluation de qualité.")
    doc.save(racine / "P" / f"N{i}.pdf")
p = config.charger(fichier_utilisateur=racine / "absent.toml")
traitement.executer(cli.analyser([str(racine / "P")]), p)
print(qualite._formes_grammalecte.cache_info().currsize)
'''


@pytest.mark.exigence("EX-37", "EX-59")
def test_lexique_non_charge_sans_page_a_evaluer(tmp_path):
    """Le lexique n'est chargé qu'à la première évaluation de qualité : un lot de PDF natifs
    (aucune page reconnue ni couche OCR) ne le charge pas."""
    import pathlib
    import subprocess
    import sys
    r = subprocess.run([sys.executable, "-c", SCRIPT_CHARGEMENT, str(tmp_path)], capture_output=True, text=True,
                       cwd=pathlib.Path(__file__).parents[1], timeout=300)
    assert r.returncode == 0, r.stderr[-3000:]
    assert r.stdout.strip().splitlines()[-1] == "0"


@pytest.mark.exigence("EX-36", "EX-67")
def test_seuil_des_mots_inconnus_selon_l_origine(tmp_path):
    """Seuil propre à l'origine du texte : couche OCR existante, Windows (et tout autre moteur),
    Apple Vision ; chacun réglable dans la configuration."""
    from ocr_md import config
    f = tmp_path / "essai.toml"
    f.write_text("mots_inconnus_max_couche_existante = 0.30\nmots_inconnus_max_windows = 0.40\n"
                 "mots_inconnus_max_vision = 0.10\n", encoding="utf-8")
    p = config.charger(f, fichier_utilisateur=tmp_path / "absent.toml")
    ind = qualite.Indicateurs()
    ind.mots_evaluables, ind.taux_mots_inconnus = 60, 0.20
    assert qualite.seuil_mots_inconnus(p, "couche_existante") == 0.30
    assert "taux_mots_inconnus" in qualite.motifs_lexicaux(ind, p, True, "apple-vision")
    assert "taux_mots_inconnus" not in qualite.motifs_lexicaux(ind, p, True, "windows-media-ocr")
    assert "taux_mots_inconnus" not in qualite.motifs_lexicaux(ind, p, True, "factice")
    ind.taux_mots_inconnus = 0.35
    assert "taux_mots_inconnus" in qualite.motifs_lexicaux(ind, p, True, "couche_existante")
