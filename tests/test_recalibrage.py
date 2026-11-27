"""Recalibrage des seuils sur une vérité terrain de recette (EX-76, recette du 27/11/2026)."""

import csv
import shutil

import pytest

from ocr_md import cli, config, qualite, traitement
from ocr_md.ocr.factice import MoteurFactice
from tests import recalibrage


@pytest.fixture
def journal_du_jeu(jeu_de_test, tmp_path):
    """Dossier pdf du jeu traité par le moteur factice : (dossier _OCR, manifeste)."""
    racine, m = jeu_de_test
    c = tmp_path / "P" / "pdf"
    shutil.copytree(racine / "pdf", c)
    f = tmp_path / "essai.toml"
    f.write_text("intervalle_tentatives_s = 0\n", encoding="utf-8")
    p = config.charger(f, fichier_utilisateur=tmp_path / "absent.toml")
    moteur = MoteurFactice(m["ocr_factice"], nom="windows-media-ocr", avec_confiance=False)
    traitement.executer(cli.analyser(["--sortie", "md", "--sans-interface", str(c)]), p, moteur=moteur)
    return tmp_path / "P" / "_OCR", m


@pytest.mark.exigence("EX-76")
def test_journal_relu(journal_du_jeu):
    ocr, _ = journal_du_jeu
    pages = recalibrage.lire_journal(ocr)
    p21 = pages[("pdf/21_moyennement_degrade.pdf", 1)]
    assert p21.image is not None and p21.image.resolution_dpi == 150 and p21.origine == "factice"
    assert p21.verdict_journal == "douteuse"
    assert pages[("pdf/04_couche_degradee.pdf", 3)].origine == "couche_existante"
    # le verdict recalculé avec les seuils en vigueur est celui du journal
    p = config.charger()
    assert all(recalibrage.verdict(page, p)[0] == page.verdict_journal for page in pages.values())


@pytest.mark.exigence("EX-76")
def test_gabarit_puis_recalibrage(journal_du_jeu, tmp_path, capsys):
    ocr, m = journal_du_jeu
    gabarit = tmp_path / "verite.csv"
    assert recalibrage.main(["gabarit", str(ocr), "--nombre", "12", "--sortie", str(gabarit)]) == 0
    with open(gabarit, encoding="utf-8-sig", newline="") as f:
        lignes = list(csv.DictReader(f, delimiter=";"))
    assert len(lignes) == 12 and set(lignes[0]) == {"fichier", "page", "verdict"}
    assert all(l["verdict"] == "" for l in lignes)
    # le référent remplit le gabarit : ici, d'après la vérité terrain du manifeste
    douteuses = {f["chemin"]: set(f["pages_douteuses"]) for f in m["fichiers"]}
    for l in lignes:
        l["verdict"] = "mauvais" if int(l["page"]) in douteuses.get(l["fichier"], ()) else "correct"
    lignes[0]["verdict"] = "erreurs ponctuelles"
    with open(gabarit, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["fichier", "page", "verdict"], delimiter=";")
        w.writeheader()
        w.writerows(lignes)
    capsys.readouterr()
    assert recalibrage.main(["calibrer", str(ocr), str(gabarit)]) == 0
    sortie = capsys.readouterr().out
    assert "11 page(s) jugée(s) ; erreurs de verdict : 0 avec les seuils en vigueur, 0 avec les seuils proposés" in sortie


def page_essai(n, inconnus, resolution=300, gris=0.25):
    ind = qualite.Indicateurs(mots=200, mots_evaluables=100, taux_mots_inconnus=inconnus, densite=1.0)
    return recalibrage.Page(f"essai/{n}.pdf", 1, "windows-media-ocr", ind, None,
                            qualite.QualiteImage(resolution, gris, 255, 1.5), "")


@pytest.mark.exigence("EX-76")
def test_recalibrage_deplace_un_seuil_trop_severe():
    """Cas de la recette : des scans de copieur au texte un peu bruité, jugés corrects, sont
    douteux par la règle de l'image ; le seuil limite remonte entre eux et la page jugée
    mauvaise, et la résolution sévère ne descend pas sous les scans corrects à 100 dpi."""
    jugees = [(page_essai(1, 0.12, gris=0.7), "bonne"), (page_essai(2, 0.14, resolution=150, gris=0.7), "bonne"),
              (page_essai(3, 0.30, gris=0.9), "douteuse"), (page_essai(4, 0.02), "bonne"),
              (page_essai(5, 0.03, resolution=100), "douteuse")]
    p = config.charger()
    assert recalibrage.cout(jugees, p, 2.0) == 2  # pages 1 et 2 signalées à tort
    propose = recalibrage.recalibrer(jugees, p)
    assert all(recalibrage.verdict(pg, propose)[0] == a for pg, a in jugees)
    assert 0.14 < propose.mots_inconnus_limite_windows < 0.30
    assert propose.image_resolution_severe_dpi == p.image_resolution_severe_dpi  # déjà juste


@pytest.mark.parametrize("texte, attendu", [("Correct", "bonne"), ("mauvais ", "douteuse"),
                                            ("Erreurs ponctuelles", "ponctuelles"), ("erreurs_ponctuelles", "ponctuelles"),
                                            ("", None)])
def test_verdicts_admis(texte, attendu):
    assert recalibrage.normaliser_verdict(texte) == attendu
    with pytest.raises(ValueError):
        recalibrage.normaliser_verdict("moyen")
