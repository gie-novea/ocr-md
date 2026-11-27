"""Fichiers Office (jalon 8) : EX-45, EX-44 appliquée aux fichiers Office, front matter (EX-46,
section 11), mention des révisions et commentaires d'un .docx, colonne `revisions_commentaires`
du rapport (EX-82), fichiers endommagés ou protégés (EX-18, EX-60)."""

import datetime
import io
import json
import pathlib
import re
import shutil
import tracemalloc
import zipfile

import jsonschema
import pytest
import yaml

from ocr_md import avertissements, cli, config, inventaire, markdown_office as mo, rapport, traitement
from ocr_md.traiteurs.office import MESSAGE_ILLISIBLE

SCHEMA = json.loads((pathlib.Path(__file__).parents[1] / "schema" / "front-matter-v1.json").read_text(encoding="utf-8"))


def parametres_avec(tmp_path, texte=""):
    f = tmp_path / "essai.toml"
    f.write_text("intervalle_tentatives_s = 0\n" + texte, encoding="utf-8")
    return config.charger(f, fichier_utilisateur=tmp_path / "absent.toml")


def lancer(p, *arguments):
    return traitement.executer(cli.analyser([str(a) for a in arguments]), p)


def lire_md(chemin):
    texte = chemin.read_text(encoding="utf-8")
    assert texte.startswith("---\n")
    fin = texte.index("\n---\n", 4)
    return yaml.safe_load(texte[4:fin]), texte[fin + 5:]


def aplati(texte):
    return " ".join(texte.replace("> ", " ").split())


@pytest.fixture(scope="module")
def office(jeu_de_test, tmp_path_factory):
    """Dossier office du jeu traité une fois : (dossier copie, manifeste, rapport)."""
    racine, m = jeu_de_test
    base = tmp_path_factory.mktemp("office")
    copie = base / "P" / "office"
    shutil.copytree(racine / "office", copie)
    p = config.charger(fichier_utilisateur=base / "absent.toml")
    code = lancer(p, copie)
    fichiers = {f["chemin"]: f for f in m["fichiers"] if f["chemin"].startswith("office/")}
    return copie, fichiers, rapport.lire(copie.parent / "_OCR"), code


def md_de(office, nom):
    copie, *_ = office
    return lire_md(copie.parent / "_OCR" / "office" / f"{nom}.md")


# ------------------------------------------------------------------------------ CA de EX-45
@pytest.mark.exigence("EX-45", "EX-46")
@pytest.mark.parametrize("nom", ["07_memoire.docx", "08_chiffrage.xlsx", "09_presentation.pptx"])
def test_textes_de_la_verite_terrain_et_front_matter(office, nom):
    copie, fichiers, lignes, code = office
    f = fichiers[f"office/{nom}"]
    champs, corps = md_de(office, nom)
    jsonschema.validate(champs, SCHEMA)
    assert champs["pages"] == f["pages"]  # null pour .docx et .xlsx, diapositives pour .pptx
    assert champs["type_source"] == f["type"] and champs["origine_texte"] == "texte natif du document"
    assert champs["moteur_ocr"] == "aucun" and champs["qualite_texte"] == "bonne"
    assert re.fullmatch(r"(python-docx|openpyxl|python-pptx) \S+", champs["moteur_md"])
    for t in f["textes_attendus"]:
        assert t in corps, t
    for t in f.get("textes_absents", []):
        assert t not in corps, t
    l = lignes[f"office/{nom}"]
    assert (l.statut, l.origine_texte, l.sorties) == ("natif", "texte natif du document", (f"{nom}.md",))
    assert code == 0


@pytest.mark.exigence("EX-45")
def test_docx_titres_listes_note_et_zone_de_texte(office):
    _, corps = md_de(office, "07_memoire.docx")
    lignes = corps.splitlines()
    assert "# Mémoire technique du groupement" in lignes and "# 2. Moyens humains" in lignes
    assert "- Visites de chantier hebdomadaires" in lignes and "1. Phase travaux" in lignes
    # Listes à puces et numérotée séparées par une ligne vide (deux listes distinctes)
    i = lignes.index("1. Phase études")
    assert lignes[i - 1] == "" and lignes[i - 2] == "- Comptes rendus sous 48 heures"
    assert "complète.[^1]" in corps and "[^1]: Équipe constituée pour ce marché fictif." in lignes
    # Zone de texte : une seule fois (pas de doublon par sa variante VML), après son ancrage
    zone = "Engagement qualité : visa des plans sous 8 jours."
    assert corps.count(zone) == 1
    ancre, repere = lignes.index("Encadré de synthèse ci-contre."), lignes.index(mo.REPERE_ZONE_TEXTE)
    assert ancre < repere < lignes.index(zone) < lignes.index("# 2. Moyens humains")


@pytest.mark.exigence("EX-45", "EX-82")
def test_docx_revisions_et_commentaires_signales(office):
    copie, fichiers, lignes, _ = office
    f = fichiers["office/07_memoire.docx"]
    champs, corps = md_de(office, "07_memoire.docx")
    texte = (copie.parent / "_OCR" / "office" / "07_memoire.docx.md").read_text(encoding="utf-8")
    apres_front_matter = texte.split("\n---\n", 1)[1].lstrip("\n")
    assert aplati(apres_front_matter.split("\n\n", 1)[0]) == f["mention_revisions"]
    assert "Délai d’exécution proposé : dix-huit mois." in corps and "vingt-quatre mois" not in corps
    l = lignes["office/07_memoire.docx"]
    assert l.revisions_commentaires == f["revisions_commentaires"] == "revisions commentaires=1"
    assert l.statut == "natif" and champs["qualite_texte"] == "bonne"  # pas de statut douteux
    assert lignes["office/09_presentation.pptx"].revisions_commentaires == ""


def test_mention_des_revisions_selon_le_cas():
    assert avertissements.mention_revisions(False, 0) == ""
    assert avertissements.mention_revisions(True, 2).startswith(
        "Document contenant des révisions non acceptées et 2 commentaires : texte présenté")
    assert avertissements.mention_revisions(True, 0) == (
        "Document contenant des révisions non acceptées : texte présenté dans son état final (insertions "
        "acceptées, suppressions écartées).")
    assert avertissements.mention_revisions(False, 1) == "Document contenant 1 commentaire : commentaires non repris."
    assert avertissements.valeur_revisions(False, 3) == "commentaires=3"


@pytest.mark.exigence("EX-45", "EX-44")
def test_xlsx_feuilles_fusions_et_feuille_masquee(office):
    _, corps = md_de(office, "08_chiffrage.xlsx")
    reperes = re.findall(r'^<!-- feuille (\d+) : "([^"]+)" -->$', corps, re.MULTILINE)
    assert reperes == [("1", "Synthèse"), ("2", "Détail")]
    synthese, detail = corps.split('<!-- feuille 2 : "Détail" -->')
    assert '<td colspan="4">Récapitulatif des lots</td>' in synthese
    assert "|Poste|Quantité|" in detail and "<table>" not in detail  # tableau simple : Markdown
    assert detail.rstrip().endswith('Feuilles masquées du classeur, contenu non repris : "Paramètres".')
    assert mo.REPERE_FEUILLES_MASQUEES in detail


@pytest.mark.exigence("EX-45", "EX-44")
def test_pptx_diapositives_groupes_tableau_notes(office):
    _, corps = md_de(office, "09_presentation.pptx")
    assert re.findall(r"^<!-- diapositive (\d+) -->$", corps, re.MULTILINE) == ["1", "2", "3", "4"]
    d2 = corps.split("<!-- diapositive 2 -->")[1].split("<!-- diapositive 3 -->")[0]
    assert d2.index("Visa sous 8 jours") < d2.index("Synthèse mensuelle") < d2.index("Commentaires du présentateur")
    assert '<td colspan="2">Intervenant et part</td>' in corps
    d4 = corps.split("<!-- diapositive 4 -->")[1]
    assert d4.strip().startswith(mo.DIAPOSITIVE_MASQUEE) and "## Annexe masquée" in d4


@pytest.mark.exigence("EX-44")
def test_docx_tableau_fusionne_en_html_ou_force_en_markdown(jeu_de_test, tmp_path):
    racine, _ = jeu_de_test
    source = racine / "office" / "07_memoire.docx"
    auto = mo.convertir_docx(source).corps
    assert '<td colspan="2">Mission</td>' in auto and '<td rowspan="2">Groupement</td>' in auto
    md = mo.convertir_docx(source, tableaux="md").corps
    assert "<table>" not in md and "|Intervenant|Mission||Équipe|" in md
    assert "<table>" in mo.convertir_pptx(racine / "office" / "09_presentation.pptx", tableaux="html").corps


# ------------------------------------------------------------------------------ valeurs des classeurs
@pytest.mark.exigence("EX-45")
@pytest.mark.parametrize("valeur, format_nombre, attendu", [
    (125000, "General", "125000"), (48500.1, "General", "48500,1"), (0.30000000000000004, "General", "0,3"),
    (1234.5600000000002, "General", "1234,56"), (173500.09999999998, "General", "173500,1"),
    (12345678.91, "General", "12345678,91"), (-0.5, "General", "-0,5"), (1e-7, "General", "0,0000001"),
    (2.5e15, "General", "2500000000000000"), (0.2, "0%", "20 %"), (0.12345, "0.00\\ %", "12,345 %"),
    (1, "0%", "100 %"), (True, "General", "VRAI"), (False, "General", "FAUX"), ("#DIV/0!", "General", "#DIV/0!"),
    (datetime.datetime(2026, 11, 26), "dd/mm/yyyy", "2026-11-26"),
    (datetime.datetime(2026, 11, 26, 14, 30), "dd/mm/yyyy hh:mm", "2026-11-26 14:30:00"),
    (datetime.time(8, 15), "hh:mm", "08:15:00"), (None, "General", ""),
])
def test_valeurs_de_cellule(valeur, format_nombre, attendu):
    assert mo.valeur_cellule(valeur, format_nombre) == attendu


def test_formule_sans_valeur_en_cache():
    assert mo.valeur_cellule(None, "General", "=SOMME(A1:A3)") == "[formule non calculée : =SOMME(A1:A3)]"
    assert mo.valeur_cellule(None, "General", "texte") == ""


def classeur(chemin, nb_lignes, colonnes=3):
    import openpyxl
    wb = openpyxl.Workbook(write_only=True)
    ws = wb.create_sheet("Grand")
    for i in range(1, nb_lignes + 1):
        ws.append([f"Ligne {i}"] + [i * k + 0.25 for k in range(1, colonnes)])
    wb.save(chemin)
    return chemin


@pytest.mark.exigence("EX-45")
def test_feuille_tronquee_au_dela_de_xlsx_lignes_max(tmp_path):
    (tmp_path / "P").mkdir()
    classeur(tmp_path / "P" / "grand.xlsx", 30)
    p = parametres_avec(tmp_path, "xlsx_lignes_max = 10\n")
    lancer(p, tmp_path / "P" / "grand.xlsx")
    _, corps = lire_md(tmp_path / "P" / "_OCR" / "grand.xlsx.md")
    assert "|Ligne 10|" in corps and "Ligne 11" not in corps
    assert "*(feuille tronquée : seules les 10 premières lignes sur 30 sont reprises" in corps


@pytest.mark.exigence("EX-59")
def test_memoire_bornee_sur_un_gros_classeur(tmp_path):
    """Lecture en continu : 60 000 lignes, plafond de 2 000 ; la mémoire Python allouée
    pendant la conversion reste faible et indépendante du nombre de lignes lues."""
    chemin = classeur(tmp_path / "gros.xlsx", 60000, colonnes=5)
    tracemalloc.start()
    try:
        r = mo.convertir_xlsx(chemin, lignes_max=2000)
        _, pic = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert "seules les 2000 premières lignes sur 60000" in r.corps
    assert pic < 40 * 2**20, pic / 2**20


# ------------------------------------------------------------------------------ fichiers abîmés
@pytest.mark.exigence("EX-60", "EX-18")
def test_docx_endommage_et_office_protege(tmp_path, jeu_de_test):
    racine, _ = jeu_de_test
    d = tmp_path / "P"
    d.mkdir()
    tampon = io.BytesIO()
    with zipfile.ZipFile(racine / "office" / "07_memoire.docx") as z, zipfile.ZipFile(tampon, "w") as sortie:
        for nom in z.namelist():
            sortie.writestr(nom, b"<w:document" if nom == "word/document.xml" else z.read(nom))
    (d / "abime.docx").write_bytes(tampon.getvalue())
    cfb = inventaire.ENTETE_CFB + bytes(504) + "EncryptedPackage".encode("utf-16-le") + bytes(512)
    (d / "protege.xlsx").write_bytes(cfb)
    shutil.copyfile(racine / "office" / "09_presentation.pptx", d / "sain.pptx")
    code = lancer(parametres_avec(tmp_path), d)
    lignes = rapport.lire(tmp_path / "_OCR")
    assert (lignes["P/abime.docx"].statut, lignes["P/abime.docx"].message) == ("erreur", MESSAGE_ILLISIBLE)
    assert lignes["P/protege.xlsx"].message == inventaire.MESSAGE_OFFICE_PROTEGE
    assert lignes["P/sain.pptx"].statut == "natif" and code == 1
    assert not (tmp_path / "_OCR" / "P" / "abime.docx.md").exists()
    assert "abime.docx : XMLSyntaxError" in (tmp_path / "_OCR" / rapport.NOM_JOURNAL).read_text(encoding="utf-8")
