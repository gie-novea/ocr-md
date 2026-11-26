"""Markdown des PDF et des images (jalon 6, EX-08, EX-40 à EX-44). Moteur OCR factice."""

import re
import shutil
import subprocess

import pymupdf
import pytest

from ocr_md import cli, config, markdown_pdf, traitement
from ocr_md.ocr.factice import MoteurFactice
from ocr_md.qualite import forme_comparable

REPERE = re.compile(r"^<!-- page (\d+)( : TEXTE DOUTEUX, ne pas citer sans vérification sur l'original)? -->$")


@pytest.fixture
def parametres(tmp_path):
    f = tmp_path / "essai.toml"
    f.write_text("intervalle_tentatives_s = 0\n", encoding="utf-8")
    return config.charger(f, fichier_utilisateur=tmp_path / "absent.toml")


@pytest.fixture
def traite(jeu_de_test, tmp_path, parametres):
    """Traite (les-deux) les dossiers pdf et images d'une copie du jeu ; renvoie une fonction
    d'accès aux sorties."""
    racine, m = jeu_de_test
    copie = tmp_path / "P" / "jeu"
    for d in ("pdf", "images"):
        shutil.copytree(racine / d, copie / d)
    moteur = MoteurFactice(m["ocr_factice"])
    options = cli.analyser(["--sortie", "les-deux", str(copie / "pdf"), str(copie / "images")])
    assert traitement.executer(options, parametres, moteur=moteur) == 0
    return copie, m, moteur


def md(copie, rel):
    return (copie / "_OCR" / (rel + ".md")).read_text(encoding="utf-8")


def pages_md(texte):
    """Texte de chaque page du Markdown, d'après les repères."""
    morceaux, courant = {}, None
    for ligne in texte.split("\n"):
        r = REPERE.match(ligne)
        if r:
            courant = int(r.group(1))
            morceaux[courant] = []
        elif courant is not None:
            morceaux[courant].append(ligne)
    return {k: "\n".join(v) for k, v in morceaux.items()}


def mots(texte):
    texte = re.sub(r"<[^>]+>", " ", texte)
    texte = re.sub(r"[|*#`_]+|-{3,}", " ", texte)
    return {forme_comparable(m).strip(".,;:!?()«»\"'").lower() for m in texte.split()} - {""}


# ------------------------------------------------------------------------------ EX-41
@pytest.mark.exigence("EX-41")
def test_reperes_de_page(traite):
    copie, m, _ = traite
    for f in m["fichiers"]:
        if f["chemin"].split("/")[0] not in ("pdf", "images") or f["statut"] == "erreur":
            continue
        texte = md(copie, f["chemin"])
        reperes = [int(REPERE.match(l).group(1)) for l in texte.split("\n") if REPERE.match(l)]
        assert reperes == list(range(1, f["pages"] + 1)), f["chemin"]
        assert all(l == "" for l in _voisins_des_reperes(texte)), f["chemin"]
        pages = pages_md(texte)
        for n, mot in enumerate(f.get("mots_uniques") or [], 1):
            if mot and n not in f["pages_douteuses"]:  # pages à couche volontairement dégradée
                assert mot in pages[n], (f["chemin"], n, mot)
                assert all(mot not in pages[k] for k in pages if k != n)


def _voisins_des_reperes(texte):
    lignes = texte.split("\n")
    for i, l in enumerate(lignes):
        if REPERE.match(l):
            yield lignes[i + 1]
            if i:
                yield lignes[i - 1]


@pytest.mark.exigence("EX-41")
def test_page_sans_texte_et_repere_douteux(traite):
    copie, _, _ = traite
    pages = pages_md(md(copie, "pdf/03_mixte.pdf"))
    assert pages[6].strip() == markdown_pdf.PAGE_SANS_TEXTE
    corps = markdown_pdf.convertir(str(copie / "_OCR" / "pdf" / "03_mixte.pdf"), pages_douteuses=[2, 6])
    lignes = corps.split("\n")
    assert "<!-- page 2 : TEXTE DOUTEUX, ne pas citer sans vérification sur l'original -->" in lignes
    i = lignes.index("<!-- page 6 : TEXTE DOUTEUX, ne pas citer sans vérification sur l'original -->")
    assert lignes[i + 2] == markdown_pdf.PAGE_SANS_TEXTE  # les deux mentions (décision du 26/11/2026)


# ------------------------------------------------------------------------------ EX-40, EX-08
@pytest.mark.exigence("EX-40")
def test_markdown_fidele_au_pdf_consultable(traite):
    if not shutil.which("pdftotext"):
        pytest.skip("pdftotext (Poppler) absent de ce poste")
    copie, m, _ = traite
    for f in m["fichiers"]:
        if not f["chemin"].startswith("pdf/") or f["statut"] == "erreur":
            continue
        pdf = copie / "_OCR" / f["chemin"]
        reference = subprocess.run(["pdftotext", "-enc", "UTF-8", str(pdf), "-"],
                                   capture_output=True).stdout.decode("utf-8").split("\f")
        pages = pages_md(md(copie, f["chemin"]))
        for n in range(1, f["pages"] + 1):
            a, b = mots(pages[n]), mots(reference[n - 1])
            if not b:
                continue
            # Objectif de 98 %, ajusté à 90 % pour une page dont un tableau a été reconnu par
            # OCR : la bibliothèque y coupe les cellules fusionnées (« M » / « ontants »),
            # écart prévu par le CA de EX-40 et signalé par le repère de tableau OCR.
            seuil = 0.90 if markdown_pdf.REPERE_TABLEAU_OCR in pages[n] else 0.98
            assert len(a & b) / len(b) >= seuil, (f["chemin"], n, b - a)
            assert len(a & b) / len(a) >= seuil, (f["chemin"], n, a - b)


@pytest.mark.exigence("EX-08", "EX-40", "EX-24")
def test_conversion_markdown_n_appelle_aucun_moteur(traite, monkeypatch):
    """Aucune reconnaissance pendant la conversion : ni le moteur de l'outil, ni Tesseract ou
    RapidOCR (le sélecteur de moteur de la bibliothèque n'est jamais appelé)."""
    from pymupdf4llm.helpers import document_layout
    copie, m, moteur = traite

    def interdit():
        raise AssertionError("sélecteur de moteur OCR de PyMuPDF4LLM appelé")

    monkeypatch.setattr(document_layout, "select_ocr_function", interdit)
    appels_avant = moteur.nombre_appels
    from ocr_md.calque import AdaptateurOcr
    for rel in ("pdf/02_scanne.pdf", "pdf/03_mixte.pdf", "pdf/04_couche_degradee.pdf"):
        adaptateur = AdaptateurOcr()
        markdown_pdf.convertir(str(copie / "_OCR" / rel), adaptateur=adaptateur)
        sans_texte = [p.number + 1 for p in pymupdf.open(copie / "_OCR" / rel) if not p.get_text().strip()]
        assert set(adaptateur.appels) <= set(sans_texte), rel
    assert moteur.nombre_appels == appels_avant


# ------------------------------------------------------------------------------ EX-42, EX-43
@pytest.mark.exigence("EX-42")
def test_pieds_de_page_conserves(traite):
    copie, _, _ = traite
    pages = pages_md(md(copie, "pdf/01_natif.pdf"))
    for n in range(1, 6):
        assert f"Page {n} sur 5" in pages[n]


@pytest.mark.exigence("EX-43")
def test_aucune_image_exportee(traite):
    copie, _, _ = traite
    sorties = list((copie / "_OCR").rglob("*"))
    assert not [p for p in sorties if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".tif", ".tiff")]
    assert all("data:image" not in p.read_text(encoding="utf-8") for p in sorties if p.suffix == ".md")


# ------------------------------------------------------------------------------ EX-44
def cellules_html(texte):
    return [re.sub(r"<[^>]+>", "", c).strip() for c in re.findall(r"<td[^>]*>.*?</td>", texte)]


@pytest.mark.exigence("EX-44")
def test_regle_des_tableaux_auto(traite):
    copie, m, _ = traite
    f = next(x for x in m["fichiers"] if x["numero"] == "6")
    pages = pages_md(md(copie, "pdf/06_tableaux.pdf"))
    assert "<table" not in pages[1] and any(l.startswith("|") for l in pages[1].split("\n"))
    for n in (2, 3, 4):
        assert "<table" in pages[n] and ("colspan" in pages[n] or "rowspan" in pages[n]), n
        assert not any(l.startswith("|") for l in pages[n].split("\n"))
        assert cellules_html(pages[n]) == f["tableaux"][str(n)][0]["valeurs"], n
    assert markdown_pdf.REPERE_TABLEAU_OCR not in md(copie, "pdf/06_tableaux.pdf")


@pytest.mark.exigence("EX-44")
def test_tableaux_des_pages_ocr_signales(traite):
    copie, _, _ = traite
    texte = md(copie, "pdf/06b_tableaux_scannes.pdf")
    pages = pages_md(texte)
    for n in range(1, 5):
        lignes = pages[n].strip().split("\n")
        debuts = [i for i, l in enumerate(lignes) if l.startswith("|") and (i == 0 or not lignes[i - 1].startswith("|"))]
        if debuts:  # tableau restitué en Markdown : repère juste avant
            for i in debuts:
                assert lignes[i - 2] == markdown_pdf.REPERE_TABLEAU_OCR, n
        else:  # page restituée en texte simple (repli de PV-05) : repère en tête de page
            assert lignes[0] == markdown_pdf.REPERE_TABLEAU_OCR, n
    assert "|Mme Durand|" in pages[1]  # espaces conservés dans les cellules issues de l'OCR
    # Aucun montant coupé en deux cellules (« 40 0 » | « 00 ») sur le cadre d'honoraires scanné.
    assert "40 000" in pages[4] and "|40 0|" not in pages[4]


@pytest.mark.exigence("EX-22", "EX-40")
def test_page_scannee_avec_mention_de_depot(traite):
    """La page porte une mention de dépôt en texte visible : le texte reconnu est restitué
    (repli de PV-05) et la mention figure une seule fois."""
    copie, m, _ = traite
    f = next(x for x in m["fichiers"] if x["numero"] == "19")
    pages = pages_md(md(copie, f["chemin"]))
    for n in (1, 2):
        assert f["mots_uniques"][n - 1] in pages[n]
        assert pages[n].count(f["mention_native"]) == 1
    journal = (copie / "_OCR" / "ocr_journal.log").read_text(encoding="utf-8")
    assert "repli de PV-05" in journal
    from ocr_md import rapport
    lignes = rapport.lire(copie / "_OCR")
    assert lignes["pdf/19_mention_plateforme.pdf"].pages_texte_simple == (1, 2)
    assert lignes["pdf/06b_tableaux_scannes.pdf"].pages_texte_simple == (2, 3, 4)
    assert lignes["pdf/02_scanne.pdf"].pages_texte_simple == ()


@pytest.mark.exigence("EX-44", "EX-11")
@pytest.mark.parametrize("rendu", ["md", "html"])
def test_tableaux_rendu_impose(jeu_de_test, tmp_path, parametres, rendu):
    racine, m = jeu_de_test
    (tmp_path / "P").mkdir()
    shutil.copyfile(racine / "pdf/06_tableaux.pdf", tmp_path / "P" / "t.pdf")
    options = cli.analyser(["--sortie", "md", "--tableaux", rendu, str(tmp_path / "P" / "t.pdf")])
    assert traitement.executer(options, parametres, moteur=MoteurFactice({})) == 0
    pages = pages_md((tmp_path / "P" / "_OCR" / "t.pdf.md").read_text(encoding="utf-8"))
    if rendu == "md":
        assert all("<table" not in pages[n] for n in pages)
    else:
        assert all("<table" in pages[n] for n in pages)
