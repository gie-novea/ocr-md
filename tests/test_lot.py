"""Traitement d'un lot : inventaire, dossier miroir, nommage, relance, écritures atomiques,
rapport, journal, robustesse (jalon 3).

Les conversions réelles arrivent aux jalons 4 à 8 : ces tests utilisent un traiteur
d'essai qui recopie la source (« PDF consultable ») et écrit un Markdown minimal.
"""

import csv
import hashlib
import os
import pathlib
import shutil
import threading
import time

import pymupdf
import pytest

from ocr_md import cli, config, inventaire, rapport, sorties, traitement
from ocr_md.inventaire import ErreurFichier
from ocr_md.traiteurs import Annulation, ResultatTraitement
from ocr_md.traiteurs.pdf import MESSAGE_ENDOMMAGE, MESSAGE_PROTEGE, controler_pdf
from tests.donnees import fabrication as fab


# ------------------------------------------------------------------------------ outils
class TraiteurEssai:
    """Recopie la source en guise de PDF consultable et écrit un Markdown d'une ligne.
    `comportements` : nom de fichier -> action spéciale."""

    def __init__(self, comportements=None):
        self.comportements = comportements or {}
        self.appels = []

    def traiter(self, ctx):
        nom = ctx.element.source.name
        self.appels.append(nom)
        action = self.comportements.get(nom)
        if action == "erreur":
            raise ErreurFichier("erreur simulée")
        if action == "exception":
            raise RuntimeError("panne simulée")
        if callable(action):
            action(ctx)
        if "pdf" in ctx.prevues:
            ctx.ecrivain.preparer(ctx.prevues["pdf"], lambda c: shutil.copyfile(ctx.element.source, c))
        if "md" in ctx.prevues:
            ctx.ecrivain.preparer(ctx.prevues["md"], lambda c: pathlib.Path(c).write_text(
                f"<!-- page 1 -->\n\n{ctx.element.relatif}\n", encoding="utf-8"))
        return ResultatTraitement("natif", pages=1, origine="texte natif du document")


def traiteurs(t):
    return {k: t for k in ("pdf", "image", "docx", "xlsx", "pptx")}


@pytest.fixture
def parametres(tmp_path):
    f = tmp_path / "essai.toml"
    f.write_text("intervalle_tentatives_s = 0\ndelai_hydratation_s = 1\n", encoding="utf-8")
    return config.charger(f, fichier_utilisateur=tmp_path / "absent.toml")


def pdf_natif(chemin, mot="MOTESSAI"):
    chemin.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open()
    fab.page_native(doc, fab.LIGNES_REFERENCE, mot_unique=mot)
    doc.save(chemin)
    return chemin


def lancer(parametres, *arguments, traiteur=None, **kw):
    t = traiteur or TraiteurEssai()
    options = cli.analyser([str(a) for a in arguments])
    bilan = traitement.BilanLot()
    code = traitement.executer(options, parametres, traiteurs=traiteurs(t), bilan=bilan, **kw)
    return code, t, bilan


def lignes_csv(dossier_ocr):
    with open(dossier_ocr / rapport.NOM_RAPPORT, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def empreintes(racine):
    res = {}
    for p in sorted(racine.rglob("*")):
        if "_OCR" in p.parts:
            continue
        if p.is_file():
            st = p.stat()
            res[p.relative_to(racine).as_posix()] = (hashlib.sha256(p.read_bytes()).hexdigest(), st.st_size, st.st_mtime_ns)
        else:
            res[p.relative_to(racine).as_posix()] = "dossier"
    return res


@pytest.fixture
def lot(tmp_path):
    """Parent/Lot 1/Candidat A/DC1.pdf, Candidat A/Annexes/Attestation.pdf, Candidat B/DC2.pdf,
    plus un dossier _OCR préexistant et des fichiers à exclure."""
    parent = tmp_path / "Parent"
    racine = parent / "Lot 1"
    pdf_natif(racine / "Candidat A" / "DC1.pdf", "MOTA")
    pdf_natif(racine / "Candidat A" / "Annexes" / "Attestation.pdf", "MOTANNEXE")
    pdf_natif(racine / "Candidat B" / "DC2.pdf", "MOTB")
    (racine / "_OCR").mkdir()
    (racine / "_OCR" / "ancien.pdf").write_bytes(b"%PDF-1.4 ancienne sortie")
    for nom in (".DS_Store", "Thumbs.db", "desktop.ini", "~$brouillon.docx", ".cache.pdf"):
        (racine / "Candidat A" / nom).write_bytes(b"x")
    return parent, racine


# ------------------------------------------------------------------------------ EX-14, EX-50
@pytest.mark.exigence("EX-14", "EX-50")
def test_dossier_miroir_et_exclusions(lot, parametres):
    parent, racine = lot
    code, t, _ = lancer(parametres, racine)
    assert code == 0
    ocr = parent / "_OCR"
    assert (ocr / "Lot 1" / "Candidat A" / "DC1.pdf").is_file()
    assert (ocr / "Lot 1" / "Candidat A" / "Annexes" / "Attestation.pdf.md").is_file()
    assert (ocr / "Lot 1" / "Candidat B" / "DC2.pdf").is_file()
    chemins = [l["chemin_relatif"] for l in lignes_csv(ocr)]
    assert chemins == ["Lot 1/Candidat A/Annexes/Attestation.pdf", "Lot 1/Candidat A/DC1.pdf", "Lot 1/Candidat B/DC2.pdf"]
    assert sorted(t.appels) == ["Attestation.pdf", "DC1.pdf", "DC2.pdf"]
    assert (ocr / rapport.NOM_JOURNAL).is_file()


@pytest.mark.exigence("EX-14")
def test_chaque_fichier_une_seule_fois_meme_selectionne_deux_fois(lot, parametres):
    parent, racine = lot
    code, t, _ = lancer(parametres, racine, racine / "Candidat B" / "DC2.pdf")
    assert sorted(t.appels) == ["Attestation.pdf", "DC1.pdf", "DC2.pdf"]


@pytest.mark.exigence("EX-50")
def test_fichier_isole_et_parents_differents(tmp_path, parametres):
    a = pdf_natif(tmp_path / "X" / "DC2.pdf")
    b = pdf_natif(tmp_path / "Y" / "sous" / "Offre.pdf")
    code, _, bilan = lancer(parametres, a, b)
    assert code == 0
    assert (tmp_path / "X" / "_OCR" / "DC2.pdf").is_file()
    assert (tmp_path / "Y" / "sous" / "_OCR" / "Offre.pdf.md").is_file()
    assert [l["chemin_relatif"] for l in lignes_csv(tmp_path / "X" / "_OCR")] == ["DC2.pdf"]
    assert len(bilan.dossiers_ocr) == 2


@pytest.mark.exigence("EX-50", "EX-12")
def test_parent_non_inscriptible(tmp_path, parametres, monkeypatch, capsys):
    a = pdf_natif(tmp_path / "Lecture seule" / "DC2.pdf")
    avant = empreintes(tmp_path)

    def refuser(dossier):
        raise PermissionError("accès refusé")

    monkeypatch.setattr(traitement, "creer_dossier_ocr", refuser)
    code, t, bilan = lancer(parametres, a)
    assert code == 1 and t.appels == []
    assert "écriture impossible" in capsys.readouterr().err
    assert empreintes(tmp_path) == avant  # aucune écriture ailleurs


# ------------------------------------------------------------------------------ EX-51, EX-20
@pytest.mark.exigence("EX-51", "EX-18")
def test_nommage_sans_collision(tmp_path, parametres):
    d = tmp_path / "P" / "D"
    pdf_natif(d / "A.pdf")
    shutil.copyfile(pathlib.Path(__file__).parent / "donnees" / "fabrication.py", d / "ignore.txt")
    import docx
    docx.Document().save(d / "A.docx")
    from PIL import Image
    Image.new("L", (100, 100), 255).save(d / "A.png")
    code, _, _ = lancer(parametres, d)
    noms = sorted(p.name for p in (tmp_path / "P" / "_OCR" / "D").iterdir())
    assert noms == ["A.docx.md", "A.pdf", "A.pdf.md", "A.png.md", "A.png.pdf"]


@pytest.mark.exigence("EX-20", "EX-16")
def test_office_avec_sortie_pdf(tmp_path, parametres):
    import docx
    d = tmp_path / "P" / "D"
    d.mkdir(parents=True)
    docx.Document().save(d / "Memoire.docx")
    code, t, bilan = lancer(parametres, "--sortie", "pdf", d)
    assert code == 0 and t.appels == []
    (l,) = lignes_csv(tmp_path / "P" / "_OCR")
    assert (l["statut"], l["sorties"]) == ("natif", "")
    assert l["message"] == "pas de PDF consultable pour ce format : utiliser Convertir en Markdown"
    assert rapport.bilan(bilan.lignes)["signales"] == 1


# ------------------------------------------------------------------------------ EX-18, EX-19, EX-21
@pytest.mark.exigence("EX-18", "EX-19")
def test_types_signatures_et_formats_non_pris_en_charge(jeu_de_test, tmp_path, parametres):
    racine, m = jeu_de_test
    for dossier in ("non_pris_en_charge", "erreurs", "images"):
        shutil.copytree(racine / dossier, tmp_path / "P" / dossier)
    code, t, _ = lancer(parametres, tmp_path / "P" / "non_pris_en_charge")
    assert code == 0  # EX-19 : non pris en charge, code 0
    lignes = {l["chemin_relatif"]: l for l in lignes_csv(tmp_path / "P" / "_OCR")}
    assert {l["statut"] for l in lignes.values()} == {"non_pris_en_charge"}
    assert lignes["non_pris_en_charge/ancien.doc"]["message"].startswith("ancien format Office")
    assert lignes["non_pris_en_charge/courriel.msg"]["message"].startswith("e-mail non pris en charge")
    assert lignes["non_pris_en_charge/archive.zip"]["message"] == "format non pris en charge"
    assert not list((tmp_path / "P" / "_OCR" / "non_pris_en_charge").glob("*")) if (tmp_path / "P" / "_OCR" / "non_pris_en_charge").exists() else True
    code, t, _ = lancer(parametres, tmp_path / "P" / "erreurs", tmp_path / "P" / "images")
    lignes = {l["chemin_relatif"]: l for l in lignes_csv(tmp_path / "P" / "_OCR")}
    for nom in ("erreurs/faux_pdf.pdf", "erreurs/14_substitut_1ko.pdf"):
        assert lignes[nom]["statut"] == "erreur"
        assert lignes[nom]["message"] == "le contenu du fichier ne correspond pas à son extension"
    assert lignes["images/10_extension_majuscules.PNG"]["type"] == "image"
    assert lignes["images/10_extension_majuscules.PNG"]["statut"] == "natif"  # traité


@pytest.mark.exigence("EX-21")
def test_pdf_protege_endommage_et_sain(jeu_de_test):
    racine, _ = jeu_de_test
    with pytest.raises(ErreurFichier, match=MESSAGE_PROTEGE):
        controler_pdf(racine / "erreurs/13_chiffre.pdf")
    with pytest.raises(ErreurFichier, match=MESSAGE_ENDOMMAGE):
        controler_pdf(racine / "erreurs/13_tronque.pdf")
    info = controler_pdf(racine / "pdf/01_natif.pdf")
    assert info.pages == 5 and not info.signe


@pytest.mark.exigence("EX-21")
def test_pdf_signe_detecte(tmp_path):
    doc = pymupdf.open()
    page = doc.new_page()
    w = pymupdf.Widget()
    w.field_type = pymupdf.PDF_WIDGET_TYPE_SIGNATURE
    w.field_name = "Signature1"
    w.rect = pymupdf.Rect(100, 100, 300, 150)
    page.add_widget(w)
    doc.save(tmp_path / "signe.pdf")
    assert controler_pdf(tmp_path / "signe.pdf").signe


# ------------------------------------------------------------------------------ EX-52
@pytest.mark.exigence("EX-52")
def test_relance(lot, parametres):
    parent, racine = lot
    lancer(parametres, racine)
    ocr = parent / "_OCR" / "Lot 1"
    dates = {p: p.stat().st_mtime_ns for p in ocr.rglob("*") if p.is_file()}
    code, t, _ = lancer(parametres, racine)
    assert t.appels == []
    assert {l["action"] for l in lignes_csv(parent / "_OCR")} == {"ignore_a_jour"}
    assert {l["duree_s"] for l in lignes_csv(parent / "_OCR")} == {""}
    assert {p: p.stat().st_mtime_ns for p in dates} == dates
    source = racine / "Candidat B" / "DC2.pdf"
    os.utime(source, (time.time() + 10, time.time() + 10))
    _, t, _ = lancer(parametres, racine)
    assert t.appels == ["DC2.pdf"]
    _, t, _ = lancer(parametres, "--forcer", racine)
    assert sorted(t.appels) == ["Attestation.pdf", "DC1.pdf", "DC2.pdf"]
    _, t, _ = lancer(parametres, "--refaire-ocr", racine)
    assert len(t.appels) == 3


@pytest.mark.exigence("EX-52", "EX-82")
def test_relance_partielle_conserve_les_autres_lignes(lot, parametres):
    parent, racine = lot
    lancer(parametres, racine)
    _, t, _ = lancer(parametres, "--forcer", racine / "Candidat B")
    lignes = lignes_csv(parent / "Lot 1" / "_OCR")
    assert [l["chemin_relatif"] for l in lignes] == ["Candidat B/DC2.pdf"]
    # le rapport du parent « Parent/_OCR » est intact
    assert len(lignes_csv(parent / "_OCR")) == 3


# ------------------------------------------------------------------------------ EX-53, EX-65
@pytest.mark.exigence("EX-53", "EX-60")
def test_interruption_pendant_l_ecriture(lot, parametres):
    parent, racine = lot

    def ecriture_tronquee(ctx):
        def producteur(chemin):
            pathlib.Path(chemin).write_bytes(b"%PDF-debut")
            raise OSError("disque plein simulé")
        ctx.ecrivain.preparer(ctx.prevues["pdf"], producteur)

    code, _, _ = lancer(parametres, racine, traiteur=TraiteurEssai({"DC2.pdf": ecriture_tronquee}))
    assert code == 1
    dossier = parent / "_OCR" / "Lot 1" / "Candidat B"
    assert not dossier.exists() or not list(dossier.iterdir())
    assert not [p for p in (parent / "_OCR").rglob("*") if sorties.MARQUE_TEMPORAIRE in p.name]


@pytest.mark.exigence("EX-53")
def test_temporaires_residuels_nettoyes_au_lancement(lot, parametres):
    parent, racine = lot
    residu = parent / "_OCR" / "Lot 1" / f"DC1.pdf{sorties.MARQUE_TEMPORAIRE}999"
    residu.parent.mkdir(parents=True)
    residu.write_bytes(b"partiel")
    lancer(parametres, racine)
    assert not residu.exists()


@pytest.mark.exigence("EX-65")
def test_verrou_momentane_puis_relache(tmp_path, parametres):
    essais = []

    def producteur(chemin):
        essais.append(1)
        if len(essais) <= 2:
            raise PermissionError("fichier verrouillé")
        pathlib.Path(chemin).write_text("ok", encoding="utf-8")

    cible = tmp_path / "_OCR" / "sortie.md"
    sorties.ecrire_atomique(cible, producteur, tentatives=3, intervalle_s=0)
    assert cible.read_text(encoding="utf-8") == "ok" and len(essais) == 3
    with pytest.raises(PermissionError):
        sorties.ecrire_atomique(tmp_path / "_OCR" / "b.md", lambda c: (_ for _ in ()).throw(PermissionError()),
                                tentatives=3, intervalle_s=0)


# ------------------------------------------------------------------------------ EX-60, EX-61, EX-17
@pytest.mark.exigence("EX-60", "EX-12")
def test_un_fichier_en_erreur_n_arrete_pas_le_lot(lot, parametres):
    parent, racine = lot
    t = TraiteurEssai({"DC1.pdf": "exception", "Attestation.pdf": "erreur"})
    code, t, _ = lancer(parametres, racine, traiteur=t)
    assert code == 1 and sorted(t.appels) == ["Attestation.pdf", "DC1.pdf", "DC2.pdf"]
    lignes = {l["chemin_relatif"]: l for l in lignes_csv(parent / "_OCR")}
    assert lignes["Lot 1/Candidat A/DC1.pdf"]["statut"] == "erreur"
    assert "ocr_journal.log" in lignes["Lot 1/Candidat A/DC1.pdf"]["message"]
    assert lignes["Lot 1/Candidat A/Annexes/Attestation.pdf"]["message"] == "erreur simulée"
    assert not (parent / "_OCR" / "Lot 1" / "Candidat A" / "DC1.pdf").exists()
    assert (parent / "_OCR" / "Lot 1" / "Candidat B" / "DC2.pdf").exists()
    journal = (parent / "_OCR" / rapport.NOM_JOURNAL).read_text(encoding="utf-8")
    assert "RuntimeError" in journal and "Traceback" in journal


@pytest.mark.exigence("EX-52", "EX-60")
def test_erreur_en_relance_conserve_les_sorties_si_source_inchangee(lot, parametres):
    parent, racine = lot
    lancer(parametres, racine)
    sortie = parent / "_OCR" / "Lot 1" / "Candidat B" / "DC2.pdf"
    date = {l["chemin_relatif"]: l for l in lignes_csv(parent / "_OCR")}["Lot 1/Candidat B/DC2.pdf"]["date_traitement"]
    lancer(parametres, "--forcer", racine, traiteur=TraiteurEssai({"DC2.pdf": "erreur"}))
    assert sortie.exists()
    ligne = {l["chemin_relatif"]: l for l in lignes_csv(parent / "_OCR")}["Lot 1/Candidat B/DC2.pdf"]
    assert ligne["statut"] == "erreur"
    assert ligne["message"] == f"erreur simulée ; sorties précédentes conservées (traitement du {date})"
    assert ligne["sorties"] == "DC2.pdf | DC2.pdf.md"


@pytest.mark.exigence("EX-52", "EX-60")
def test_erreur_en_relance_supprime_les_sorties_si_source_plus_recente(lot, parametres):
    parent, racine = lot
    lancer(parametres, racine)
    source = racine / "Candidat B" / "DC2.pdf"
    os.utime(source, (time.time() + 60, time.time() + 60))
    lancer(parametres, racine, traiteur=TraiteurEssai({"DC2.pdf": "erreur"}))
    assert not (parent / "_OCR" / "Lot 1" / "Candidat B" / "DC2.pdf").exists()
    ligne = {l["chemin_relatif"]: l for l in lignes_csv(parent / "_OCR")}["Lot 1/Candidat B/DC2.pdf"]
    assert (ligne["message"], ligne["sorties"]) == ("erreur simulée", "")


@pytest.mark.exigence("EX-61")
def test_arret_brutal_apres_le_troisieme_fichier(tmp_path, parametres):
    d = tmp_path / "P" / "D"
    for i in range(1, 6):
        pdf_natif(d / f"F{i}.pdf")

    def arret_brutal(ctx):
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        lancer(parametres, d, traiteur=TraiteurEssai({"F4.pdf": arret_brutal}))
    lignes = lignes_csv(tmp_path / "P" / "_OCR")
    assert [l["chemin_relatif"] for l in lignes] == ["D/F1.pdf", "D/F2.pdf", "D/F3.pdf"]
    assert not (tmp_path / "P" / "_OCR" / "D" / "F4.pdf").exists()


@pytest.mark.exigence("EX-17")
def test_annulation(tmp_path, parametres):
    d = tmp_path / "P" / "D"
    for i in range(1, 5):
        pdf_natif(d / f"F{i}.pdf")
    arret = threading.Event()

    def annuler_pendant(ctx):
        arret.set()
        ctx.verifier_arret()  # le traiteur vérifie l'arrêt entre deux pages

    code, t, bilan = lancer(parametres, d, traiteur=TraiteurEssai({"F2.pdf": annuler_pendant}), arret=arret)
    lignes = {l["chemin_relatif"]: l for l in lignes_csv(tmp_path / "P" / "_OCR")}
    assert lignes["D/F1.pdf"]["action"] == "traite"
    assert [lignes[f"D/F{i}.pdf"]["action"] for i in (2, 3, 4)] == ["annule"] * 3
    assert sorted(p.name for p in (tmp_path / "P" / "_OCR" / "D").iterdir()) == ["F1.pdf", "F1.pdf.md"]
    assert t.appels == ["F1.pdf", "F2.pdf"]
    assert rapport.bilan(bilan.lignes)["annules"] == 3


# ------------------------------------------------------------------------------ EX-62, EX-63, EX-64
@pytest.mark.exigence("EX-62")
def test_chemins_accentues_nfc_et_nfd(jeu_de_test, tmp_path, parametres):
    racine, _ = jeu_de_test
    shutil.copytree(racine / "chemins", tmp_path / "P" / "chemins")
    code, t, _ = lancer(parametres, tmp_path / "P" / "chemins")
    assert code == 0 and len(t.appels) == 2
    relatifs = [l["chemin_relatif"] for l in lignes_csv(tmp_path / "P" / "_OCR")]
    import unicodedata
    assert relatifs == [f"chemins/{f}/Candidat Été & Fils (n° 2)/Mémoire d'été.pdf" for f in ("nfc", "nfd")]
    assert all(unicodedata.is_normalized("NFC", r) for r in relatifs)
    for f in ("nfc", "nfd"):
        sortie = next((tmp_path / "P" / "_OCR" / "chemins" / f).rglob("*.pdf.md"))
        assert unicodedata.normalize("NFC", sortie.name) == "Mémoire d'été.pdf.md"


@pytest.mark.windows
@pytest.mark.exigence("EX-63")
def test_chemin_long_windows(tmp_path, parametres):
    from tests.donnees import generer
    g = generer.Generateur(tmp_path / "P", 2026)
    g.f16_chemin_long(longueur_cible=300)
    code, t, _ = lancer(parametres, tmp_path / "P" / "long")
    assert code == 0 and len(t.appels) == 1
    sortie = next(iter(l for l in lignes_csv(tmp_path / "P" / "_OCR")))
    chemin_md = tmp_path / "P" / "_OCR" / pathlib.PurePosixPath(sortie["chemin_relatif"]).parent / "pièce à chemin long.pdf.md"
    assert len(str(chemin_md)) >= 300
    assert os.path.isfile(sorties.chemin_systeme(chemin_md))


@pytest.mark.exigence("EX-64")
def test_fichier_kdrive_non_disponible(tmp_path, parametres, monkeypatch):
    d = tmp_path / "P" / "D"
    pdf_natif(d / "A.pdf")
    (d / "B.pdf").write_bytes(b"\0" * 1024)  # substitut de 1 Ko
    pdf_natif(d / "C.pdf")
    monkeypatch.setattr(inventaire, "probablement_en_ligne", lambda p: p.name == "B.pdf")
    vrai_lecteur = inventaire._lire_debut

    def lecture_bloquante(chemin, taille=2048):
        if chemin.name == "B.pdf":
            time.sleep(5)
        return vrai_lecteur(chemin, taille)

    monkeypatch.setattr(inventaire, "_lire_debut", lecture_bloquante)
    debut = time.perf_counter()
    code, t, _ = lancer(parametres, d)
    assert time.perf_counter() - debut < 4.5  # délai de 1 s, lot poursuivi
    lignes = {l["chemin_relatif"]: l for l in lignes_csv(tmp_path / "P" / "_OCR")}
    assert lignes["D/B.pdf"]["statut"] == "erreur"
    assert lignes["D/B.pdf"]["message"] == inventaire.MESSAGE_KDRIVE
    assert sorted(t.appels) == ["A.pdf", "C.pdf"] and code == 1


# ------------------------------------------------------------------------------ EX-82, EX-66, EX-05
@pytest.mark.exigence("EX-82")
def test_format_du_rapport(tmp_path, parametres):
    d = tmp_path / "P" / "D"
    pdf_natif(d / "Offre; « finale ».pdf")  # le guillemet droit est interdit sous Windows
    pdf_natif(d / "Simple.pdf")
    lancer(parametres, d)
    brut = (tmp_path / "P" / "_OCR" / rapport.NOM_RAPPORT).read_bytes()
    assert brut.startswith(b"\xef\xbb\xbf") and b"\r\n" in brut and b"\n" not in brut.replace(b"\r\n", b"")
    lignes = lignes_csv(tmp_path / "P" / "_OCR")
    assert list(lignes[0].keys()) == list(rapport.COLONNES) and len(rapport.COLONNES) == 15
    assert lignes[0]["chemin_relatif"] == "D/Offre; « finale ».pdf"
    assert "," in lignes[0]["duree_s"] or lignes[0]["duree_s"] == "0,0"
    assert lignes[1]["sorties"] == "Simple.pdf | Simple.pdf.md"
    texte = brut.decode("utf-8-sig").splitlines()
    assert texte[2].startswith("D/Simple.pdf;pdf;1;natif;")  # pas de guillemets inutiles


@pytest.mark.exigence("EX-82")
def test_point_virgule_et_guillemet_restitues(tmp_path):
    """Nom avec « ; » et « " » (possible sous macOS) : restitué intact par le module csv."""
    nom = 'D/Offre; "finale".pdf'
    rapport.ecrire(tmp_path, {nom: rapport.LigneRapport(nom, "pdf", statut="natif")}, 0, 0)
    assert lignes_csv(tmp_path)[0]["chemin_relatif"] == nom
    assert rapport.lire(tmp_path)[nom].statut == "natif"


@pytest.mark.exigence("EX-82")
def test_aller_retour_des_listes_de_pages():
    l = rapport.LigneRapport("a.pdf", "pdf", pages=12, statut="douteux", pages_douteuses=(3, 4, 9),
                             motif_douteux=("taux_mots_inconnus", "confiance_ocr_faible"), duree_s=2.44)
    v = dict(zip(rapport.COLONNES, l.vers_csv()))
    assert (v["pages_douteuses"], v["duree_s"]) == ("3 4 9", "2,4")
    assert rapport.LigneRapport.depuis_csv(v).pages_douteuses == (3, 4, 9)


@pytest.mark.exigence("EX-66", "EX-67")
def test_journal(lot, parametres):
    parent, racine = lot
    lancer(parametres, racine)
    journal = (parent / "_OCR" / rapport.NOM_JOURNAL).read_text(encoding="utf-8")
    assert "ocr-md 0.1.0" in journal and "options : sortie=les-deux" in journal
    assert "paramètres : " in journal and "ocr_dpi=300" in journal
    assert "Mémoire technique" not in journal and "MOTA" not in journal  # aucun texte de document


@pytest.mark.exigence("EX-05")
@pytest.mark.parametrize("options", [[], ["--forcer"], ["--refaire-ocr=tout"], ["--sortie", "md"]])
def test_integrite_des_originaux(jeu_de_test, tmp_path, parametres, options):
    racine, _ = jeu_de_test
    copie = tmp_path / "P" / "jeu"
    shutil.copytree(racine, copie)
    avant = empreintes(copie)
    lancer(parametres, *options, copie)
    lancer(parametres, *options, copie)
    assert empreintes(copie) == avant
    # seuls les dossiers _OCR sont créés, dans le parent et dans aucun dossier source
    assert [p.name for p in (tmp_path / "P").iterdir()] == ["_OCR", "jeu"] or \
        sorted(p.name for p in (tmp_path / "P").iterdir()) == ["_OCR", "jeu"]
