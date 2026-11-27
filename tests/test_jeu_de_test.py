"""Générateur du jeu de test et manifeste (EX-74)."""

import json
import zipfile

import pymupdf
import pytest
from PIL import Image, ImageOps

from ocr_md.ocr.factice import lire_marqueur
from ocr_md.qualite import forme_comparable
from tests.donnees import fabrication as fab
from tests.donnees import generer

STATUTS = {"natif", "ocrise", "mixte", "couche_expediteur", "douteux", "non_pris_en_charge", "erreur"}
CATEGORIES = {"native", "image", "couche_existante", "vide"}


def par_numero(manifeste, numero):
    return [f for f in manifeste["fichiers"] if f["numero"] == numero]


def texte_office(chemin):
    with zipfile.ZipFile(chemin) as z:
        # docProps contient des horodatages posés par les bibliothèques : exclus.
        return "".join(z.read(n).decode("utf-8") for n in sorted(z.namelist())
                       if n.endswith(".xml") and not n.startswith("docProps/"))


@pytest.mark.exigence("EX-74")
def test_contenu_minimal_du_cahier(jeu_de_test):
    _, m = jeu_de_test
    numeros = {f["numero"] for f in m["fichiers"]}
    attendus = {str(n) for n in range(1, 16) if n != 16} | {"6b", "18", "19", "20"}
    assert attendus <= numeros
    assert {f["statut"] for f in m["fichiers"]} == STATUTS  # les sept statuts sont représentés


@pytest.mark.exigence("EX-74")
def test_manifeste_coherent_avec_les_fichiers(jeu_de_test):
    racine, m = jeu_de_test
    ids_references = set()
    for f in m["fichiers"]:
        chemin = racine / f["chemin"]
        assert chemin.is_file(), f["chemin"]
        assert f["statut"] in STATUTS
        if f.get("categories"):
            assert len(f["categories"]) == f["pages"]
            assert set(f["categories"]) <= CATEGORIES
        if f.get("id_images"):
            assert len(f["id_images"]) == f["pages"]
            ids_references |= {i for i in f["id_images"] if i is not None}
        if f["type"] == "pdf" and f["statut"] != "erreur":
            assert pymupdf.open(chemin).page_count == f["pages"]
        assert all(1 <= p <= (f["pages"] or 0) for p in f["pages_douteuses"])
    assert ids_references == {int(k) for k in m["ocr_factice"]}


@pytest.mark.exigence("EX-74", "EX-22")
def test_pages_et_categories(jeu_de_test):
    racine, m = jeu_de_test
    for f in m["fichiers"]:
        if f["type"] != "pdf" or f["statut"] == "erreur" or not f.get("categories"):
            continue
        doc = pymupdf.open(racine / f["chemin"])
        for page, cat, mot in zip(doc, f["categories"], f.get("mots_uniques") or [None] * f["pages"]):
            texte = page.get_text()
            images = page.get_images()
            if cat == "native":
                assert mot in texte and not images
            elif cat == "image":
                assert images and mot not in texte
            elif cat == "couche_existante":
                assert images and len(texte) > 100
            else:
                assert not texte.strip() and not images


@pytest.mark.exigence("EX-74", "EX-36")
def test_couche_degradee_seulement_sur_les_pages_2_et_3(jeu_de_test):
    racine, m = jeu_de_test
    (f,) = par_numero(m, "4")
    doc = pymupdf.open(racine / f["chemin"])
    assert f["pages_douteuses"] == [2, 3] and f["statut"] == "douteux"
    for i, page in enumerate(doc, 1):
        texte = page.get_text()
        assert ("\u0436\u0449" in texte) == (i in (2, 3))  # lettres cyrilliques : caract\u00e8res aberrants
        if i not in (2, 3):
            assert f["mots_uniques"][i - 1] in texte
    (saine,) = par_numero(m, "20")
    assert saine["statut"] == "couche_expediteur" and saine["pages_douteuses"] == []


@pytest.mark.exigence("EX-74", "EX-41", "EX-42")
def test_pdf_natif(jeu_de_test):
    racine, m = jeu_de_test
    (f,) = par_numero(m, "1")
    doc = pymupdf.open(racine / f["chemin"])
    texte = doc[0].get_text()
    assert all(c in texte for c in fab.CARACTERES_EXIGES)
    for page, pied in zip(doc, f["pied_attendu"]):
        assert pied in page.get_text()
    assert f["sentinelles"][0] in doc[4].get_text()


@pytest.mark.exigence("EX-74", "EX-44")
def test_tableaux(jeu_de_test):
    racine, m = jeu_de_test
    (f,) = par_numero(m, "6")
    doc = pymupdf.open(racine / f["chemin"])
    noms = [f["tableaux"][str(i)][0]["nom"] for i in range(1, 5)]
    assert noms == ["simple", "fusion", "dpgf", "honoraires"]
    for i, page in enumerate(doc, 1):
        texte = page.get_text()
        for valeur in f["tableaux"][str(i)][0]["valeurs"]:
            assert all(forme_comparable(mot) in forme_comparable(texte) for mot in valeur.split())
    assert f["rendu_tableaux_attendu"] == ["markdown", "html", "html", "html"]
    (scan,) = par_numero(m, "6b")
    assert scan["repere_tableau_ocr_attendu"] and scan["categories"] == ["image"] * 4


@pytest.mark.exigence("EX-74", "EX-34")
def test_images(jeu_de_test):
    racine, m = jeu_de_test
    images = par_numero(m, "10")
    chemins = {f["chemin"]: f for f in images}
    assert any(c.endswith(".PNG") for c in chemins)
    jpeg = racine / "images/10_exif6.jpg"
    brute = Image.open(jpeg)
    assert brute.getexif().get(0x0112) == 6
    redressee = ImageOps.exif_transpose(brute)
    assert redressee.height > redressee.width
    assert lire_marqueur(redressee) == chemins["images/10_exif6.jpg"]["id_images"][0]
    tiff = Image.open(racine / "images/10_trois_trames.tiff")
    assert tiff.n_frames == 3
    lus = []
    for k in range(3):
        tiff.seek(k)
        lus.append(lire_marqueur(tiff))
    assert lus == chemins["images/10_trois_trames.tiff"]["id_images"]


@pytest.mark.exigence("EX-74", "EX-19", "EX-21", "EX-62", "EX-64")
def test_fichiers_particuliers(jeu_de_test):
    racine, m = jeu_de_test
    assert len(par_numero(m, "11")) == 3
    formes = {f["forme_unicode"]: f["chemin"] for f in par_numero(m, "12")}
    assert set(formes) == {"NFC", "NFD"} and formes["NFC"] != formes["NFD"]
    assert all((racine / c).is_file() for c in formes.values())
    chiffre = pymupdf.open(racine / "erreurs/13_chiffre.pdf")
    assert chiffre.needs_pass
    with pytest.raises(Exception):
        d = pymupdf.open(racine / "erreurs/13_tronque.pdf")
        [p.get_text() for p in d]
        assert d.page_count == 2 and not d.is_repaired
    assert (racine / "erreurs/14_substitut_1ko.pdf").stat().st_size == 1024


@pytest.mark.exigence("EX-74", "EX-14")
def test_lot_et_exclusions(jeu_de_test):
    racine, m = jeu_de_test
    lot = [f["chemin"] for f in par_numero(m, "15")]
    assert any(c.count("/") >= 4 for c in lot)  # trois niveaux sous « lot »
    assert m["exclus"] and all((racine / c).exists() for c in m["exclus"])
    assert any("/_OCR/" in c for c in m["exclus"])


@pytest.mark.exigence("EX-74")
def test_reproductible(jeu_de_test, tmp_path):
    """Deux exécutions donnent le même manifeste et des fichiers de même contenu textuel."""
    racine, m = jeu_de_test
    m2 = generer.generer(tmp_path / "bis")
    assert json.dumps(m, sort_keys=True) == json.dumps(m2, sort_keys=True)
    for f in m["fichiers"]:
        a, b = racine / f["chemin"], tmp_path / "bis" / f["chemin"]
        if f["type"] == "pdf" and f["statut"] != "erreur":
            assert [p.get_text() for p in pymupdf.open(a)] == [p.get_text() for p in pymupdf.open(b)]
        elif f["type"] in ("docx", "xlsx", "pptx"):
            assert texte_office(a) == texte_office(b)
        elif f["chemin"].endswith(("13_chiffre.pdf", "13_tronque.pdf")):
            # Chiffrement et identifiant aléatoires : la taille varie de quelques octets.
            assert abs(a.stat().st_size - b.stat().st_size) <= 64
        else:
            assert a.read_bytes() == b.read_bytes() or f["type"] == "image"


def test_aucune_donnee_reelle_dans_le_generateur():
    """Garde-fou : le générateur ne lit aucun fichier extérieur au dépôt."""
    import inspect
    source = inspect.getsource(generer)
    for interdit in ("kDrive", "F:\\", "F:/", "open(sys.argv", "Path.home"):
        assert interdit not in source
