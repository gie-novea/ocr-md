"""PDF endommagé que MuPDF ne sait pas ouvrir : récupération des pages par pypdf (recette du
27/11/2026, EX-21)."""

import re

import pymupdf
import pytest

from ocr_md import cli, config, rapport, traitement
from ocr_md.traiteurs import pdf


@pytest.fixture
def parametres(tmp_path):
    f = tmp_path / "essai.toml"
    f.write_text("intervalle_tentatives_s = 0\n", encoding="utf-8")
    return config.charger(f, fichier_utilisateur=tmp_path / "absent.toml")


def pdf_compte_faux(chemin):
    """PDF de deux pages natives dont l'arbre des pages annonce 0 page : MuPDF n'en voit
    aucune, pypdf suit les pages réellement listées."""
    doc = pymupdf.open()
    for i in range(2):
        doc.new_page().insert_text((72, 72), f"Bonjour page {i + 1} texte natif", fontsize=12)
    octets = doc.tobytes(garbage=4, deflate=False, no_new_id=True)
    chemin.write_bytes(re.sub(rb"/Count 2", b"/Count 0", octets))


@pytest.mark.exigence("EX-21")
def test_pages_recuperees_par_pypdf(tmp_path, parametres):
    source = tmp_path / "P" / "compte_faux.pdf"
    source.parent.mkdir()
    pdf_compte_faux(source)
    with pytest.raises(Exception):
        pdf.controler_pdf(source)  # MuPDF seul conclut à l'endommagement
    options = cli.analyser(["--sortie", "les-deux", "--sans-interface", str(source)])
    traitement.executer(options, parametres)
    l = rapport.lire(source.parent / "_OCR")["compte_faux.pdf"]
    assert l.statut == "douteux" and "pdf_repare" in l.motif_douteux and l.pages == 2
    assert "2 pages sur 2 récupérées par pypdf" in l.message
    texte = (source.parent / "_OCR" / "compte_faux.pdf.md").read_text(encoding="utf-8")
    assert "Bonjour page 2" in texte and "pages_recuperees: 2" in texte
    assert pymupdf.open(source.parent / "_OCR" / "compte_faux.pdf").page_count == 2


def test_fichier_irrecuperable_reste_en_erreur(tmp_path):
    source = tmp_path / "vide.pdf"
    source.write_bytes(b"%PDF-1.7\n" + b"\0" * 200)
    assert pdf.recuperer_par_pypdf(source) is None
