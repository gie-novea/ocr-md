"""Chaîne complète avec le moteur OCR réel du système (niveau 2, EX-24 à EX-27, 7.3).

Les PDF consultables produits par l'outil à partir des fichiers 2, 3, 10 et 18 du jeu de
test sont relus par pdftotext et par PyMuPDF : au moins 95 % des mots de référence de chaque
page doivent y figurer en français (équivalences œ/oe, æ/ae, ’/' admises). En en-US (CI
Windows hors passe complète), le seuil est réduit (voir test_moteurs_reels.py).
"""

import shutil
import subprocess

import pymupdf
import pytest

from ocr_md import cli, config, rapport, traitement
from tests.donnees import fabrication as fab
from tests.test_moteurs_reels import LANGUE, SEUIL, moteur_ou_saut, taux_retrouves

FICHIERS = ["pdf/02_scanne.pdf", "pdf/03_mixte.pdf", "pdf/18_ligatures.pdf", "images/10_exif6.jpg",
            "images/10_trois_trames.tiff"]


@pytest.fixture
def parametres(tmp_path):
    f = tmp_path / "essai.toml"
    f.write_text(f'intervalle_tentatives_s = 0\nlangue_ocr = "{LANGUE}"\n', encoding="utf-8")
    return config.charger(f, fichier_utilisateur=tmp_path / "absent.toml")


def texte_pages(chemin):
    if shutil.which("pdftotext"):
        sortie = subprocess.run(["pdftotext", "-enc", "UTF-8", str(chemin), "-"], capture_output=True)
        return sortie.stdout.decode("utf-8").split("\f")
    return [p.get_text() for p in pymupdf.open(chemin)]


@pytest.mark.windows
@pytest.mark.macos
@pytest.mark.exigence("EX-24", "EX-26", "EX-27", "EX-30")
def test_pdf_consultable_avec_le_moteur_reel(jeu_de_test, tmp_path, parametres):
    racine, m = jeu_de_test
    moteur = moteur_ou_saut()
    parent = tmp_path / "P"
    for rel in FICHIERS:
        (parent / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(racine / rel, parent / rel)
    options = cli.analyser(["--sortie", "les-deux", str(parent / "pdf"), str(parent / "images")])
    assert traitement.executer(options, parametres) == 0
    lignes = rapport.lire(parent / "_OCR")
    journal = (parent / "_OCR" / rapport.NOM_JOURNAL).read_text(encoding="utf-8")
    assert moteur.description().split(" (")[0] in journal  # « Apple Vision » ou « Windows.Media.Ocr »
    for rel in FICHIERS:
        f = next(x for x in m["fichiers"] if x["chemin"] == rel)
        nom_pdf = rel if rel.endswith(".pdf") else rel + ".pdf"
        pages = texte_pages(parent / "_OCR" / nom_pdf)
        for n, cat in enumerate(f["categories"]):
            if cat != "image":
                continue
            taux = taux_retrouves([f["texte_reference"][n]], pages[n])
            print(f"{moteur.nom} : {rel} page {n + 1} : {taux:.1%} (PDF consultable)")
            assert taux >= SEUIL, (rel, n + 1, taux)
        assert lignes[rel].pages_ocr == tuple(i + 1 for i, c in enumerate(f["categories"]) if c == "image")
        md = (parent / "_OCR" / (rel + ".md")).read_text(encoding="utf-8")
        assert md.count("<!-- page ") == f["pages"]


@pytest.mark.windows
@pytest.mark.exigence("EX-25")
def test_page_a0_avec_windows_media_ocr(tmp_path, parametres):
    """Page A0 à 300 dpi au-delà de MaxImageDimension : résolution réduite, page reconnue."""
    moteur = moteur_ou_saut()
    source = pymupdf.open()
    page_texte = fab.page_native(source, fab.LIGNES_COURANTES, largeur=2384, hauteur=3370, taille=40)
    jpeg = fab.scanner(page_texte, dpi=150)[0]
    doc = pymupdf.open()
    page = doc.new_page(width=2384, height=3370)
    page.insert_image(page.rect, stream=jpeg)
    (tmp_path / "P").mkdir()
    doc.save(tmp_path / "P" / "a0.pdf")
    options = cli.analyser(["--sortie", "pdf", str(tmp_path / "P" / "a0.pdf")])
    assert traitement.executer(options, parametres) == 0
    journal = (tmp_path / "P" / "_OCR" / rapport.NOM_JOURNAL).read_text(encoding="utf-8")
    assert f"dimension maximale du moteur : {moteur.dimension_max()} px" in journal
    texte = pymupdf.open(tmp_path / "P" / "_OCR" / "a0.pdf")[0].get_text()
    assert taux_retrouves(fab.LIGNES_COURANTES, texte) >= SEUIL


@pytest.mark.windows
@pytest.mark.macos
@pytest.mark.exigence("EX-57")
def test_ventilation_du_temps_par_page(jeu_de_test, tmp_path, parametres):
    """Mesure : rendu, reconnaissance et écriture du calque, par page reconnue (journal)."""
    import re
    racine, _ = jeu_de_test
    moteur_ou_saut()
    parent = tmp_path / "P"
    (parent / "pdf").mkdir(parents=True)
    for rel in ("pdf/02_scanne.pdf", "pdf/18_ligatures.pdf", "pdf/06b_tableaux_scannes.pdf"):
        shutil.copyfile(racine / rel, parent / rel)
    options = cli.analyser(["--sortie", "pdf", str(parent / "pdf")])
    assert traitement.executer(options, parametres) == 0
    journal = (parent / "_OCR" / rapport.NOM_JOURNAL).read_text(encoding="utf-8")
    mesures = [tuple(float(x) for x in m) for m in re.findall(
        r"durée par page reconnue \(\d+ page\(s\)\) : rendu ([\d.]+) s, reconnaissance ([\d.]+) s, calque ([\d.]+) s",
        journal)]
    assert len(mesures) == 3
    rendu, ocr_, calque_ = (sum(m[i] for m in mesures) / 3 for i in range(3))
    total = rendu + ocr_ + calque_
    print(f"ventilation par page ({LANGUE}) : rendu {rendu:.3f} s ({rendu / total:.0%}), "
          f"reconnaissance {ocr_:.3f} s ({ocr_ / total:.0%}), calque {calque_:.3f} s ({calque_ / total:.0%})")
    assert "pages par minute" in journal


@pytest.mark.macos
def test_ventilation_de_la_reconnaissance_vision(jeu_de_test):
    """Sous macOS : part de la conversion de l'image en PNG, de Vision et des boîtes des mots."""
    import time
    from PIL import Image as ImagePIL
    racine, m = jeu_de_test
    moteur = moteur_ou_saut()
    pages = 0
    for rel in ("pdf/02_scanne.pdf", "pdf/18_ligatures.pdf"):
        doc = pymupdf.open(racine / rel)
        for page in doc:
            t0 = time.perf_counter()
            pix = page.get_pixmap(dpi=300, colorspace=pymupdf.csGRAY)
            image = ImagePIL.frombytes("L", (pix.width, pix.height), pix.samples)
            moteur.chronos["rendu"] = moteur.chronos.get("rendu", 0.0) + time.perf_counter() - t0
            moteur.reconnaitre(image)
            pages += 1
    c = {k: v / pages for k, v in moteur.chronos.items()}
    total = sum(c.values())
    print("ventilation Vision par page : " + ", ".join(f"{k} {v:.3f} s ({v / total:.0%})" for k, v in c.items()))


@pytest.mark.windows
@pytest.mark.macos
@pytest.mark.exigence("EX-35", "EX-36")
def test_verdicts_avec_le_moteur_reel(jeu_de_test, tmp_path, parametres):
    """Page illisible du fichier 5 douteuse, fichiers 2 et 18 (ligatures) sains, sous les deux
    moteurs. En en-US (CI Windows hors passe complète), la qualité n'est pas jugée."""
    from tests.test_moteurs_reels import EN_FRANCAIS
    if not EN_FRANCAIS:
        pytest.skip("verdicts jugés en fr-FR seulement (passe complète)")
    racine, _ = jeu_de_test
    moteur_ou_saut()
    parent = tmp_path / "P"
    (parent / "pdf").mkdir(parents=True)
    for rel in ("pdf/02_scanne.pdf", "pdf/05_illisible.pdf", "pdf/18_ligatures.pdf", "pdf/21_moyennement_degrade.pdf"):
        shutil.copyfile(racine / rel, parent / rel)
    traitement.executer(cli.analyser(["--sortie", "pdf", str(parent / "pdf")]), parametres)
    lignes = rapport.lire(parent / "_OCR")
    print({k: (l.statut, l.pages_douteuses, l.motif_douteux) for k, l in lignes.items()})
    assert lignes["pdf/05_illisible.pdf"].pages_douteuses == (2,)
    # Pages moyennement dégradées : douteuses par la qualité de l'image, quel que soit le moteur.
    l21 = lignes["pdf/21_moyennement_degrade.pdf"]
    assert l21.pages_douteuses == (1, 2, 3) and "image_faible_qualite" in l21.motif_douteux
    assert "page 1 (résolution 150 dpi" in l21.message
    assert lignes["pdf/02_scanne.pdf"].pages_douteuses == () and lignes["pdf/02_scanne.pdf"].statut == "ocrise"
    assert lignes["pdf/18_ligatures.pdf"].pages_douteuses == ()
