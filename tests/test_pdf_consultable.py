"""PDF consultable (jalon 4) : classification, OCR des pages-images, calque invisible,
images, métadonnées, PDF temporaire. Moteur OCR factice, réel au niveau 2 (jalon 5)."""

import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import threading

import numpy as np
import pymupdf
import pytest
from PIL import Image

from ocr_md import analyse_pdf, cli, config, plateforme, rapport, traitement
from ocr_md.ocr.factice import MoteurFactice, lire_marqueur
from ocr_md.qualite import forme_comparable
from tests.donnees import fabrication as fab


@pytest.fixture
def parametres(tmp_path):
    f = tmp_path / "essai.toml"
    f.write_text("intervalle_tentatives_s = 0\n", encoding="utf-8")
    return config.charger(f, fichier_utilisateur=tmp_path / "absent.toml")


@pytest.fixture
def jeu(jeu_de_test, tmp_path):
    """Copie du jeu de test dans un dossier parent propre au test."""
    racine, m = jeu_de_test
    copie = tmp_path / "P" / "jeu"
    shutil.copytree(racine, copie)
    return copie, m


def par_chemin(m, chemin):
    return next(f for f in m["fichiers"] if f["chemin"] == chemin)


def lancer(parametres, m, *arguments, moteur=None, arret=None):
    moteur = moteur or MoteurFactice(m["ocr_factice"])
    options = cli.analyser([str(a) for a in arguments])
    bilan = traitement.BilanLot()
    code = traitement.executer(options, parametres, moteur=moteur, arret=arret, bilan=bilan)
    return code, moteur, bilan


def sortie(copie, relatif, suffixe=""):
    """Sortie d'un fichier quand les dossiers du jeu (pdf, images...) sont passés en entrée."""
    return copie / "_OCR" / (relatif + suffixe)


def lignes(copie):
    return {l.chemin_relatif: l for l in rapport.lire(copie / "_OCR").values()}


def pdftotext(chemin):
    if not shutil.which("pdftotext"):
        pytest.skip("pdftotext (Poppler) absent de ce poste")
    return subprocess.run(["pdftotext", "-enc", "UTF-8", str(chemin), "-"], capture_output=True).stdout.decode("utf-8")


# ------------------------------------------------------------------------------ EX-22, EX-23
@pytest.mark.exigence("EX-22")
def test_classification_egale_a_la_verite_terrain(jeu_de_test, parametres):
    racine, m = jeu_de_test
    n = 0
    for f in m["fichiers"]:
        if f["type"] == "pdf" and f.get("categories"):
            obtenu = [a.categorie for a in analyse_pdf.analyser(pymupdf.open(racine / f["chemin"]), parametres)]
            assert obtenu == f["categories"], f["chemin"]
            n += 1
    assert n >= 12


@pytest.mark.exigence("EX-22", "EX-67")
def test_seuils_de_classification_reglables(jeu_de_test, tmp_path):
    racine, _ = jeu_de_test
    doc = pymupdf.open(racine / "pdf/19_mention_plateforme.pdf")
    f = tmp_path / "c.toml"
    f.write_text("densite_texte_ajoute_max = 0.0\ntexte_min_caracteres = 10\n", encoding="utf-8")
    p = config.charger(f, fichier_utilisateur=tmp_path / "absent.toml")
    assert analyse_pdf.analyser_page(doc[0], p).categorie == "couche_existante"


@pytest.mark.exigence("EX-23", "EX-21", "EX-34")
def test_statuts_et_origines(jeu, parametres):
    copie, m = jeu
    code, moteur, _ = lancer(parametres, m, "--sortie", "pdf", copie / "pdf", copie / "images", copie / "erreurs")
    l = lignes(copie)
    attendus = {"pdf/01_natif.pdf": "natif", "pdf/02_scanne.pdf": "ocrise", "pdf/03_mixte.pdf": "mixte",
                "pdf/06_tableaux.pdf": "natif", "pdf/06b_tableaux_scannes.pdf": "ocrise",
                "pdf/18_ligatures.pdf": "ocrise", "pdf/19_mention_plateforme.pdf": "ocrise",
                "pdf/20_couche_saine.pdf": "couche_expediteur", "images/10_trois_trames.tiff": "ocrise",
                "erreurs/13b_tronque_recuperable.pdf": "douteux", "erreurs/13_tronque.pdf": "erreur"}
    for chemin, statut in attendus.items():
        assert l[chemin].statut == statut, chemin
        f = par_chemin(m, chemin)
        if f.get("origine"):
            assert l[chemin].origine_texte == f["origine"], chemin
    assert l["pdf/03_mixte.pdf"].pages_ocr == (4, 5)
    repare = par_chemin(m, "erreurs/13b_tronque_recuperable.pdf")
    assert l["erreurs/13b_tronque_recuperable.pdf"].message == repare["message_attendu"]
    assert l["erreurs/13b_tronque_recuperable.pdf"].pages_douteuses == tuple(repare["pages_douteuses"])
    assert l["erreurs/13b_tronque_recuperable.pdf"].motif_douteux[0] == "pdf_repare"


# ------------------------------------------------------------------------------ EX-24
@pytest.mark.exigence("EX-24", "EX-08")
@pytest.mark.parametrize("sortie_demandee", ["pdf", "md", "les-deux"])
def test_ocr_une_seule_fois_par_page_image(jeu, parametres, sortie_demandee):
    copie, m = jeu
    _, moteur, _ = lancer(parametres, m, "--sortie", sortie_demandee, copie / "pdf", copie / "images")
    attendu = sorted(i for f in m["fichiers"] if f["chemin"].startswith(("pdf/", "images/"))
                     for i, c in zip(f.get("id_images") or [], f.get("categories") or []) if c == "image" and i)
    assert sorted(moteur.appels) == attendu


# ------------------------------------------------------------------------------ EX-29, EX-30, EX-31
def rendu(page, dpi=100):
    pix = page.get_pixmap(dpi=dpi)
    return np.frombuffer(pix.samples, np.uint8).astype(int)


def flux_images(doc):
    return sorted(hashlib.sha256(doc.xref_stream_raw(x)).hexdigest() for x in range(1, doc.xref_length())
                  if doc.xref_get_key(x, "Subtype")[1] == "/Image")


@pytest.mark.exigence("EX-29")
def test_contenu_visuel_inchange(jeu, parametres):
    copie, m = jeu
    lancer(parametres, m, "--sortie", "pdf", copie / "pdf", copie / "images")
    for f in m["fichiers"]:
        if f["type"] != "pdf" or not f["chemin"].startswith("pdf/"):
            continue
        avant, apres = pymupdf.open(copie / f["chemin"]), pymupdf.open(sortie(copie, f["chemin"]))
        assert apres.page_count == avant.page_count
        for a, b in zip(avant, apres):
            assert (a.rect, a.rotation) == (b.rect, b.rotation)
            assert np.abs(rendu(a) - rendu(b)).mean() < 0.5, (f["chemin"], a.number)
        assert flux_images(avant) == flux_images(apres), f["chemin"]


@pytest.mark.exigence("EX-30")
def test_calque_invisible_recherche_et_extraction(jeu, parametres):
    copie, m = jeu
    lancer(parametres, m, "--sortie", "pdf", copie / "pdf")
    f = par_chemin(m, "pdf/02_scanne.pdf")
    doc = pymupdf.open(sortie(copie, f["chemin"]))
    texte = pdftotext(sortie(copie, f["chemin"]))
    assert all(forme_comparable(c) in forme_comparable(texte) for c in fab.CARACTERES_EXIGES)
    for n, (page, ident) in enumerate(zip(doc, f["id_images"])):
        verite = {}
        for ligne in m["ocr_factice"][str(ident)]["lignes"]:
            for mot, b in ligne["mots"]:
                verite.setdefault(mot, pymupdf.Rect(b[0] * page.rect.width, b[1] * page.rect.height,
                                                     b[2] * page.rect.width, b[3] * page.rect.height))
        candidats = [mt for mt in verite if len(mt) >= 6 and mt.isalpha()][:5]
        assert len(candidats) == 5
        for mot in candidats:
            trouves = page.search_for(mot)
            v = verite[mot]
            dx, dy = v.width * 0.05, v.height * 0.05
            zone = pymupdf.Rect(v.x0 - dx, v.y0 - dy, v.x1 + dx, v.y1 + dy)
            assert any(zone.contains((r.tl + r.br) / 2) for r in trouves), (n + 1, mot)
        assert f["mots_uniques"][n] in page.get_text()


@pytest.mark.exigence("EX-30")
def test_calque_restitue_oe_ae_et_apostrophe(tmp_path):
    """Capacité du calque à restituer œ, æ, ’ (le moteur Windows ne les produit pas)."""
    from ocr_md import calque
    from ocr_md.ocr.base import Ligne, Mot, ResultatOcr
    doc = pymupdf.open()
    page = doc.new_page()
    mots = ("d’œuvre", "Lætitia", "€", "«", "»", "ŒUVRE", "Æ")
    r = ResultatOcr((Ligne(tuple(Mot(t, (100 + 120 * i, 100, 200 + 120 * i, 140)) for i, t in enumerate(mots))),),
                    2480, 3508)
    calque.ecrire_calque(page, r)
    doc.subset_fonts()
    doc.save(tmp_path / "c.pdf")
    texte = pdftotext(tmp_path / "c.pdf")
    assert all(t in texte for t in mots)


@pytest.mark.exigence("EX-31")
def test_pages_natives_intactes(jeu, parametres):
    copie, m = jeu
    lancer(parametres, m, "--sortie", "pdf", copie / "pdf")
    avant, apres = pymupdf.open(copie / "pdf/03_mixte.pdf"), pymupdf.open(sortie(copie, "pdf/03_mixte.pdf"))
    for n in (0, 1, 2):
        assert apres[n].get_text() == avant[n].get_text()
    assert not apres[5].get_text().strip()


@pytest.mark.exigence("EX-30")
@pytest.mark.parametrize("rotation", [90, 270])
def test_calque_sur_page_pivotee(tmp_path, parametres, rotation):
    """Page scannée enregistrée couchée avec un drapeau de rotation : le calque suit."""
    from tests.donnees import generer
    g = generer.Generateur(tmp_path / "gen", 7)
    src, mots = g.document_natif(1, "MOTROTATION")
    jpeg, taille, transfo = fab.scanner(src[0], identifiant=4242)
    doc = pymupdf.open()
    page = doc.new_page(width=842, height=595)
    page.set_rotation(rotation)
    page.insert_image(page.rect * page.derotation_matrix, stream=jpeg, rotate=rotation)
    (tmp_path / "P").mkdir()
    doc.save(tmp_path / "P" / "pivote.pdf")
    moteur = MoteurFactice({"4242": fab.verite_ocr(src[0], 300, transfo, taille)})
    options = cli.analyser(["--sortie", "pdf", str(tmp_path / "P" / "pivote.pdf")])
    traitement.executer(options, parametres, moteur=moteur)
    resultat = pymupdf.open(tmp_path / "P" / "_OCR" / "pivote.pdf")[0]
    assert moteur.appels == [4242]
    for mot in ("groupement", "réalisera", "MOTROTATION01"):
        assert resultat.search_for(mot), mot
    assert "MOTROTATION01" in resultat.get_text()


# ------------------------------------------------------------------------------ EX-32, EX-33
@pytest.mark.exigence("EX-32")
def test_pdf_natif_copie_a_l_identique(jeu, parametres):
    copie, m = jeu
    lancer(parametres, m, "--sortie", "pdf", copie / "pdf" / "01_natif.pdf", copie / "pdf" / "20_couche_saine.pdf")
    for nom in ("01_natif.pdf", "20_couche_saine.pdf"):
        a = hashlib.sha256((copie / "pdf" / nom).read_bytes()).hexdigest()
        b = hashlib.sha256((copie / "pdf" / "_OCR" / nom).read_bytes()).hexdigest()
        assert a == b


@pytest.mark.exigence("EX-33")
def test_metadonnees_d_avertissement(jeu, parametres):
    copie, m = jeu
    lancer(parametres, m, "--sortie", "pdf", copie / "pdf" / "02_scanne.pdf", copie / "erreurs")
    sain = pymupdf.open(copie / "pdf" / "_OCR" / "02_scanne.pdf").metadata
    assert sain["keywords"].startswith("qualite_texte=bonne; pages_ocr=1,2,3,4; moteur_ocr=factice; ocr-md")
    douteux = pymupdf.open(copie / "_OCR" / "erreurs" / "13b_tronque_recuperable.pdf").metadata
    assert douteux["subject"].startswith("TEXTE DOUTEUX pages 1, 2, 3, 4 : ne pas citer ces pages sans vérification")
    assert douteux["keywords"].startswith("qualite_texte=douteuse; pages_douteuses=1,2,3,4; origine=")
    if shutil.which("pdfinfo"):
        info = subprocess.run(["pdfinfo", "-enc", "UTF-8", str(copie / "pdf" / "_OCR" / "02_scanne.pdf")],
                              capture_output=True).stdout.decode("utf-8")
        assert "qualite_texte=bonne" in info


@pytest.mark.exigence("EX-33")
def test_metadonnees_d_origine_conservees():
    from ocr_md.avertissements import metadonnees_pdf
    meta = metadonnees_pdf({"title": "Offre", "author": "Candidat", "subject": "DC2", "keywords": "marché"},
                           pages_douteuses=[3, 4, 9], pages_ocr=[], origine="couche OCR fournie par l'expéditeur, non refaite",
                           moteur="aucun")
    assert (meta["title"], meta["author"]) == ("Offre", "Candidat")
    assert meta["subject"] == "TEXTE DOUTEUX pages 3, 4, 9 : ne pas citer ces pages sans vérification sur l'original. DC2"
    assert meta["keywords"] == ("qualite_texte=douteuse; pages_douteuses=3,4,9; "
                                "origine=couche OCR fournie par l'expéditeur, non refaite; ocr-md marché")


# ------------------------------------------------------------------------------ EX-34
@pytest.mark.exigence("EX-34")
def test_images_en_pdf(jeu, parametres):
    copie, m = jeu
    lancer(parametres, m, copie / "images")
    tiff = pymupdf.open(copie / "_OCR" / "images" / "10_trois_trames.tiff.pdf")
    assert tiff.page_count == 3
    md = (copie / "_OCR" / "images" / "10_trois_trames.tiff.md").read_text(encoding="utf-8")
    assert [l for l in md.splitlines() if l.startswith("<!-- page ")] == [f"<!-- page {i} -->" for i in (1, 2, 3)]
    jpeg = pymupdf.open(copie / "_OCR" / "images" / "10_exif6.jpg.pdf")
    page = jpeg[0]
    assert page.rect.height > page.rect.width  # redressé
    pix = page.get_pixmap(dpi=100, colorspace=pymupdf.csGRAY)
    ident = par_chemin(m, "images/10_exif6.jpg")["id_images"][0]
    assert lire_marqueur(Image.frombytes("L", (pix.width, pix.height), pix.samples)) == ident
    (xref,) = [x[0] for x in page.get_images()]
    assert jpeg.xref_stream_raw(xref) == (copie / "images" / "10_exif6.jpg").read_bytes()  # non recompressé
    assert abs(page.rect.width - 2480 / 300 * 72) < 1  # dimensions déduites de 300 dpi


# ------------------------------------------------------------------------------ EX-25, EX-28
@pytest.mark.exigence("EX-25")
def test_page_a0_resolution_reduite(tmp_path, parametres):
    class MoteurLimite(MoteurFactice):
        def dimension_max(self):
            return 10000
    doc = pymupdf.open()
    page = doc.new_page(width=2384, height=3370)  # A0
    page.insert_image(page.rect, stream=fab.scanner(fab.page_native(pymupdf.open(), ["A0"]), dpi=50)[0])
    (tmp_path / "P").mkdir()
    doc.save(tmp_path / "P" / "a0.pdf")
    moteur = MoteurLimite({})
    options = cli.analyser(["--sortie", "pdf", str(tmp_path / "P" / "a0.pdf")])
    assert traitement.executer(options, parametres, moteur=moteur) == 0
    journal = (tmp_path / "P" / "_OCR" / rapport.NOM_JOURNAL).read_text(encoding="utf-8")
    assert "résolution réduite de 300 à 213 dpi" in journal
    assert "langue fr-FR" in journal and "300 dpi" in journal


@pytest.mark.exigence("EX-28")
@pytest.mark.parametrize("cas", ["reussi", "erreur", "annule"])
def test_pdf_temporaire_supprime_en_sortie_md(jeu, parametres, cas):
    copie, m = jeu
    arret = threading.Event()

    class MoteurPiege(MoteurFactice):
        def reconnaitre(self, image):
            if cas == "erreur":
                raise RuntimeError("panne simulée")
            if cas == "annule":
                arret.set()
            return super().reconnaitre(image)

    lancer(parametres, m, "--sortie", "md", copie / "pdf" / "02_scanne.pdf", moteur=MoteurPiege(m["ocr_factice"]),
           arret=arret)
    temporaire = plateforme.dossier_temporaire()
    assert not temporaire.exists() or not any(temporaire.iterdir())
    assert not list((copie / "pdf" / "_OCR").glob("*.pdf")) if (copie / "pdf" / "_OCR").exists() else True
    if cas == "reussi":
        assert (copie / "pdf" / "_OCR" / "02_scanne.pdf.md").is_file()


@pytest.mark.exigence("EX-71", "EX-12")
def test_moteur_indisponible(jeu, parametres, monkeypatch):
    from ocr_md import ocr
    copie, m = jeu

    def absent(*a, **k):
        raise ocr.MoteurIndisponible("absent")

    monkeypatch.setattr(ocr, "moteur_systeme", absent)
    options = cli.analyser(["--sortie", "pdf", str(copie / "pdf" / "01_natif.pdf"), str(copie / "pdf" / "02_scanne.pdf")])
    assert traitement.executer(options, parametres) == 1
    l = rapport.lire(copie / "pdf" / "_OCR")
    assert l["01_natif.pdf"].statut == "natif"
    assert l["02_scanne.pdf"].statut == "erreur" and l["02_scanne.pdf"].message == ocr.message_moteur_absent()
    # Lot ne contenant que des fichiers à reconnaître : aucun n'a pu être traité, code 3 (EX-12).
    options = cli.analyser(["--forcer", "--sortie", "pdf", str(copie / "pdf" / "02_scanne.pdf"),
                            str(copie / "pdf" / "18_ligatures.pdf"), str(copie / "non_pris_en_charge")])
    assert traitement.executer(options, parametres) == 3
    options = cli.analyser(["--forcer", "--sortie", "pdf", str(copie / "pdf" / "02_scanne.pdf"),
                            str(copie / "pdf" / "01_natif.pdf")])
    assert traitement.executer(options, parametres) == 1


# ------------------------------------------------------------------------------ EX-59
@pytest.mark.exigence("EX-59")
def test_memoire_en_flux(tmp_path):
    """Pic mémoire pour 1 000 pages au plus le double de celui pour 100 pages."""
    from tests.donnees import generer
    script = tmp_path / "mesure.py"
    script.write_text(
        "import sys, os, json\n"
        "from ocr_md import cli\n"
        "code = cli.main(sys.argv[1:])\n"
        "try:\n"
        "    import psutil\n"
        "    i = psutil.Process().memory_info()\n"
        "    pic = getattr(i, 'peak_wset', None) or i.rss\n"
        "except ImportError:\n"
        "    pic = 0\n"
        "if os.name != 'nt':\n"
        "    import resource\n"
        "    pic = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == 'darwin' else 1024)\n"
        "print(json.dumps({'code': code, 'pic': pic}))\n", encoding="utf-8")
    config_essai = tmp_path / "c.toml"
    config_essai.write_text("ocr_dpi = 100\n", encoding="utf-8")
    pics = {}
    for n in (100, 1000):
        g = generer.Generateur(tmp_path / f"jeu{n}", 1)
        g.f17_volumineux(nb_pages=n)
        manifeste = tmp_path / f"jeu{n}" / "manifeste.json"
        manifeste.write_text(json.dumps({"ocr_factice": g.ocr_factice}), encoding="utf-8")
        env = dict(os.environ, OCR_MD_MOTEUR_FACTICE=str(manifeste))
        r = subprocess.run([sys.executable, str(script), "--sortie", "pdf", "--sans-interface", "--config",
                            str(config_essai), str(tmp_path / f"jeu{n}" / "volumineux")],
                           capture_output=True, text=True, env=env, cwd=pathlib.Path(__file__).parents[1])
        resultat = json.loads(r.stdout.strip().splitlines()[-1])
        assert resultat["code"] == 0, r.stderr[-2000:]
        pics[n] = resultat["pic"]
    print(f"pic mémoire : 100 pages {pics[100] / 2**20:.0f} Mo, 1 000 pages {pics[1000] / 2**20:.0f} Mo")
    assert pics[1000] <= 2 * pics[100]
