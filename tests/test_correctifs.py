"""Correctif de PyMuPDF4LLM (cellules de tableau d'un calque OCR) : module `correctifs`.

Ces tests échouent si le défaut d'origine disparaît (le correctif devient inutile : le
retirer) ou si le correctif n'agit plus (la fonction corrigée a changé).
"""

import importlib.metadata

import pymupdf
import pytest

from ocr_md import correctifs

LIGNES = [["Name", "Role", "Days"], ["Anna Smith", "Lead architect", "42"], ["John Doe", "Fluid engineer", "18"]]


def page_scannee_avec_calque():
    """Exemple minimal du ticket : image d'un tableau réglé, calque invisible, un objet texte
    par mot suivi d'une espace réelle et étiré à sa boîte."""
    x0, y0, w, h, taille = 72, 100, 150, 24, 11
    src = pymupdf.open()
    p = src.new_page()
    for i in range(len(LIGNES) + 1):
        p.draw_line((x0, y0 + i * h), (x0 + 3 * w, y0 + i * h))
    for j in range(4):
        p.draw_line((x0 + j * w, y0), (x0 + j * w, y0 + len(LIGNES) * h))
    positions = []
    for i, ligne in enumerate(LIGNES):
        for j, cellule in enumerate(ligne):
            x = x0 + j * w + 4
            mots = cellule.split()
            for k, mot in enumerate(mots):
                p.insert_text((x, y0 + i * h + 16), mot, fontsize=taille)
                positions.append((x, y0 + i * h + 16, mot + (" " if k < len(mots) - 1 else "")))
                x += pymupdf.get_text_length(mot + " ", fontsize=taille)
    pix = p.get_pixmap(dpi=200)
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_image(page.rect, pixmap=pix)
    for n, (x, y, texte) in enumerate(positions):
        page.insert_text((x, y), texte, fontsize=taille, render_mode=3,
                         morph=(pymupdf.Point(x, y), pymupdf.Matrix(1.0 + 0.01 * (n % 3), 1)))
    return doc


def markdown(doc):
    import pymupdf4llm
    return pymupdf4llm.to_markdown(doc, use_ocr=False)


@pytest.fixture
def sans_correctif():
    correctifs.retirer()
    yield
    correctifs.appliquer()


def test_le_defaut_d_origine_existe_toujours(sans_correctif):
    """Si ce test échoue, PyMuPDF4LLM ne colle plus les mots : retirer le correctif."""
    md = markdown(page_scannee_avec_calque())
    assert "|AnnaSmith|" in md and "|Leadarchitect|" in md, md


def test_le_correctif_rend_les_espaces():
    assert correctifs.appliquer()
    md = markdown(page_scannee_avec_calque())
    assert "|Anna Smith|Lead architect|42|" in md, md
    assert "|John Doe|Fluid engineer|18|" in md, md


def test_correctif_non_applique_si_la_version_differe(sans_correctif, monkeypatch):
    vraie = importlib.metadata.version
    monkeypatch.setattr(importlib.metadata, "version",
                        lambda p: "1.29.0" if p == "pymupdf4llm" else vraie(p))
    assert not correctifs.appliquer()
    assert "non appliqué" in correctifs.ETAT.raison and "1.29.0" in correctifs.ETAT.raison
    from pymupdf4llm.helpers import utils
    assert not getattr(utils.extract_cells, "correctif_ocr_md", False)


def test_correctif_non_applique_signale_au_journal_et_par_verifier(sans_correctif, monkeypatch, tmp_path, capsys):
    from ocr_md import cli, config, traitement
    vraie = importlib.metadata.version
    monkeypatch.setattr(importlib.metadata, "version",
                        lambda p: "1.29.0" if p == "pymupdf4llm" else vraie(p))
    (tmp_path / "P").mkdir()
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), "Texte natif de contrôle.")
    doc.save(tmp_path / "P" / "a.pdf")
    p = config.charger(fichier_utilisateur=tmp_path / "absent.toml")
    traitement.executer(cli.analyser(["--sortie", "pdf", str(tmp_path / "P" / "a.pdf")]), p)
    journal = (tmp_path / "P" / "_OCR" / "ocr_journal.log").read_text(encoding="utf-8")
    assert "WARNING AVERTISSEMENT : correctif des cellules de tableau de PyMuPDF4LLM non appliqué" in journal
    cli.verifier()
    assert "[!] Correctifs : AVERTISSEMENT : correctif des cellules" in capsys.readouterr().out


def test_correctif_applique_au_lancement_et_journalise(tmp_path):
    from ocr_md import cli, config, traitement
    correctifs.retirer()
    (tmp_path / "P").mkdir()
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), "Texte natif de contrôle.")
    doc.save(tmp_path / "P" / "a.pdf")
    p = config.charger(fichier_utilisateur=tmp_path / "absent.toml")
    traitement.executer(cli.analyser(["--sortie", "pdf", str(tmp_path / "P" / "a.pdf")]), p)
    assert correctifs.ETAT.applique
    journal = (tmp_path / "P" / "_OCR" / "ocr_journal.log").read_text(encoding="utf-8")
    assert "correctif des cellules de tableau de PyMuPDF4LLM appliqué" in journal
