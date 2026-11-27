"""Archives .zip et classeurs .xlsm (recette du 27/11/2026)."""

import os
import shutil
import zipfile

import pytest
import yaml

from ocr_md import archives, avertissements, cli, config, inventaire, plateforme, rapport, traitement


@pytest.fixture
def parametres(tmp_path):
    f = tmp_path / "essai.toml"
    f.write_text("intervalle_tentatives_s = 0\n", encoding="utf-8")
    return config.charger(f, fichier_utilisateur=tmp_path / "absent.toml")


def lancer(p, *arguments):
    bilan = traitement.BilanLot()
    code = traitement.executer(cli.analyser([str(a) for a in arguments]), p, bilan=bilan)
    return code, bilan


@pytest.fixture
def dossier_archives(jeu_de_test, tmp_path):
    racine, m = jeu_de_test
    c = tmp_path / "P" / "archives"
    shutil.copytree(racine / "archives", c)
    return c, m


def empreintes(dossier):
    return {p.relative_to(dossier).as_posix(): p.read_bytes() for p in dossier.rglob("*") if p.is_file()}


@pytest.mark.exigence("EX-83", "EX-19", "EX-50")
def test_archives_extraites_hors_de_la_source_et_contenu_traite(dossier_archives, parametres):
    c, m = dossier_archives
    avant = empreintes(c)
    code, bilan = lancer(parametres, "--sortie", "les-deux", "--sans-interface", c)
    assert empreintes(c) == avant  # rien n'est écrit dans la source, aucune extraction à côté
    assert not any(p.name == "Pièces" for p in c.rglob("*"))
    lignes = rapport.lire(c.parent / "_OCR")
    attendus = m["archives"]
    assert {k: l.statut for k, l in lignes.items()} == attendus
    ocr = c.parent / "_OCR" / "archives"
    # sorties dans l'arborescence _OCR, sous le nom de l'archive ; nom cp850 décodé
    assert (ocr / "22_dossier.zip" / "DC1.pdf").is_file() and (ocr / "22_dossier.zip" / "DC1.pdf.md").is_file()
    assert (ocr / "22_dossier.zip" / "Pièces" / "Mémoire.pdf.md").is_file()
    assert (ocr / "22_dossier.zip" / "annexes.zip" / "Attestation.pdf.md").is_file()
    # garde-fous : remontée et métadonnées du Finder écartées
    assert not (c.parent / "_OCR" / "evasion.pdf").exists() and not any(c.parent.rglob("evasion.pdf*"))
    assert not any("__MACOSX" in k for k in lignes)
    assert lignes["archives/22_chiffree.zip"].message == archives.MESSAGE_CHIFFREE
    assert lignes["archives/22_dossier.zip/secret.pdf"].message == archives.MESSAGE_FICHIER_CHIFFRE
    assert lignes["archives/22_dossier.zip/annexes.zip/profonde.zip"].message == archives.MESSAGE_IMBRICATION
    assert lignes["archives/22_faux.zip"].message == inventaire.MESSAGE_SIGNATURE
    champs = yaml.safe_load((ocr / "22_dossier.zip" / "DC1.pdf.md").read_text(encoding="utf-8").split("---")[1])
    assert champs["source"] == "archives/22_dossier.zip/DC1.pdf"
    # le dossier de travail est supprimé
    assert not (plateforme.dossier_temporaire() / f"processus-{os.getpid()}").exists()
    assert code == traitement.ERREUR_FICHIER  # l'archive « faux » est en erreur
    texte = (c.parent / "_OCR" / avertissements.NOM_AVERTISSEMENTS).read_text(encoding="utf-8")
    assert "archives/22_dossier.zip/ancien.doc" in texte


@pytest.mark.exigence("EX-83", "EX-52")
def test_relance_d_une_archive_a_jour(dossier_archives, parametres):
    c, _ = dossier_archives
    lancer(parametres, "--sortie", "md", "--sans-interface", c)
    _, bilan = lancer(parametres, "--sortie", "md", "--sans-interface", c)
    actions = {l.chemin_relatif: l.action for l in bilan.lignes if l.statut == "natif"}
    assert actions and set(actions.values()) == {"ignore_a_jour"}
    os.utime(c / "22_dossier.zip")  # archive modifiée : son contenu est retraité
    _, bilan = lancer(parametres, "--sortie", "md", "--sans-interface", c)
    assert {l.action for l in bilan.lignes if l.chemin_relatif.startswith("archives/22_dossier.zip/")
            and l.statut == "natif"} == {"traite"}


@pytest.mark.exigence("EX-83")
def test_taille_decompressee_bornee(tmp_path, parametres):
    source = tmp_path / "P" / "gros.zip"
    source.parent.mkdir()
    with zipfile.ZipFile(source, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("zeros.pdf", b"\0" * (3 * 1024 * 1024))
    f = tmp_path / "petit.toml"
    f.write_text("intervalle_tentatives_s = 0\narchive_taille_max_mo = 2\n", encoding="utf-8")
    p = config.charger(f, fichier_utilisateur=tmp_path / "absent.toml")
    lancer(p, "--sans-interface", source)
    l = rapport.lire(source.parent / "_OCR")["gros.zip"]
    assert l.statut == "non_pris_en_charge" and l.message.startswith("archive trop volumineuse")


@pytest.mark.exigence("EX-83")
def test_archive_qui_ment_sur_ses_tailles(tmp_path):
    source = tmp_path / "menteuse.zip"
    with zipfile.ZipFile(source, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("a.pdf", b"%PDF-" + b"\0" * 100000)
    octets = bytearray(source.read_bytes())
    # taille décompressée annoncée ramenée à 10 octets dans l'en-tête local et le répertoire central
    vraie = (100005).to_bytes(4, "little")
    i = octets.find(vraie)
    while i != -1:
        octets[i:i + 4] = (10).to_bytes(4, "little")
        i = octets.find(vraie, i + 4)
    source.write_bytes(bytes(octets))
    element = inventaire.Element(source, tmp_path, "menteuse.zip", "zip")
    with pytest.raises(inventaire.ErreurFichier):
        archives.developper(element, 2048).nettoyer()


@pytest.mark.exigence("EX-83")
@pytest.mark.parametrize("nom, attendu", [
    ("../../x.pdf", None), ("dossier/", None), ("__MACOSX/._a.pdf", None), (".DS_Store", None),
    ("C:/Windows/a.pdf", ("Windows", "a.pdf")), ("a:b?.pdf", ("a_b_.pdf",)), ("d\\e.pdf", ("d", "e.pdf")),
])
def test_chemins_neutralises(nom, attendu):
    assert archives.chemin_sur(nom) == attendu


@pytest.mark.exigence("EX-83")
def test_nom_utf8_sans_indicateur():
    info = zipfile.ZipInfo("x")
    info.filename = "Mémoire.pdf".encode("utf-8").decode("cp437")
    assert archives.nom_decode(info) == "Mémoire.pdf"


@pytest.mark.exigence("EX-18", "EX-45")
def test_classeur_a_macros_lu_comme_un_xlsx(jeu_de_test, tmp_path, parametres):
    racine, m = jeu_de_test
    f = next(x for x in m["fichiers"] if x["numero"] == "8b")
    source = tmp_path / "P" / "08b_macros.xlsm"
    source.parent.mkdir()
    shutil.copyfile(racine / f["chemin"], source)
    lancer(parametres, "--sans-interface", source)
    l = rapport.lire(source.parent / "_OCR")["08b_macros.xlsm"]
    assert (l.type, l.statut, l.sorties) == ("xlsx", "natif", ("08b_macros.xlsm.md",))
    texte = (source.parent / "_OCR" / "08b_macros.xlsm.md").read_text(encoding="utf-8")
    for t in f["textes_attendus"]:
        assert t in texte
    for t in f["textes_absents"]:
        assert t not in texte
