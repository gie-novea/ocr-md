"""Qualité du texte et signalement (jalon 7) : EX-33, EX-35 à EX-39, EX-46 à EX-49, EX-66."""

import hashlib
import json
import pathlib
import re
import shutil

import jsonschema
import pymupdf
import pytest
import yaml

from ocr_md import avertissements, cli, config, markdown_pdf, qualite, rapport, traitement
from ocr_md.ocr.factice import MoteurFactice

SCHEMA = json.loads((pathlib.Path(__file__).parents[1] / "schema" / "front-matter-v1.json").read_text(encoding="utf-8"))
REPERE_DOUTEUX = re.compile(r"^<!-- page (\d+) : TEXTE DOUTEUX, ne pas citer sans vérification sur l'original -->$",
                            re.MULTILINE)


def parametres_avec(tmp_path, texte=""):
    f = tmp_path / "essai.toml"
    f.write_text("intervalle_tentatives_s = 0\n" + texte, encoding="utf-8")
    return config.charger(f, fichier_utilisateur=tmp_path / "absent.toml")


@pytest.fixture
def parametres(tmp_path):
    return parametres_avec(tmp_path)


@pytest.fixture
def copie(jeu_de_test, tmp_path):
    racine, m = jeu_de_test
    c = tmp_path / "P" / "jeu"
    for d in ("pdf", "images", "erreurs", "non_pris_en_charge"):
        shutil.copytree(racine / d, c / d)
    return c, m


def moteur_de(m, **kw):
    kw.setdefault("nom", "windows-media-ocr")
    return MoteurFactice(m["ocr_factice"], **kw)


def lancer(p, moteur, *arguments):
    return traitement.executer(cli.analyser([str(a) for a in arguments]), p, moteur=moteur)


def front_matter(texte):
    assert texte.startswith("---\n")
    fin = texte.index("\n---\n", 4)
    return texte[4:fin], texte[fin + 5:]


def lire_md(chemin):
    texte = chemin.read_text(encoding="utf-8")
    brut, reste = front_matter(texte)
    return yaml.safe_load(brut), brut, reste


# ------------------------------------------------------------------------------ verdicts
@pytest.mark.exigence("EX-35", "EX-36", "EX-38", "EX-23")
def test_verdicts_sur_le_jeu(copie, parametres):
    c, m = copie
    moteur = moteur_de(m)
    lancer(parametres, moteur, "--sortie", "pdf", c / "pdf", c / "images")
    lignes = rapport.lire(c / "_OCR")
    for f in m["fichiers"]:
        if f["chemin"] not in lignes or f["statut"] in ("erreur", "non_pris_en_charge"):
            continue
        l = lignes[f["chemin"]]
        assert l.pages_douteuses == tuple(f["pages_douteuses"]), f["chemin"]  # aucun faux positif
        assert l.statut == f["statut"], f["chemin"]
    assert lignes["pdf/04_couche_degradee.pdf"].origine_texte == "couche OCR fournie par l'expéditeur, non refaite"
    assert "taux_mots_inconnus" in lignes["pdf/04_couche_degradee.pdf"].motif_douteux
    assert "confiance_ocr_faible" in lignes["pdf/05_illisible.pdf"].motif_douteux
    # EX-38 : aucune reconnaissance des pages à couche existante, couche conservée
    ids_couche = set(next(x for x in m["fichiers"] if x["numero"] == "4")["id_images"])
    assert not ids_couche & set(moteur.appels)
    assert "жщ" in pymupdf.open(c / "_OCR" / "pdf" / "04_couche_degradee.pdf")[1].get_text()


@pytest.mark.exigence("EX-35")
def test_sans_confiance_la_page_illisible_reste_douteuse(copie, parametres):
    """Comme sous Windows (aucune confiance) : l'heuristique lexicale suffit."""
    c, m = copie
    lancer(parametres, moteur_de(m, avec_confiance=False), "--sortie", "pdf", c / "pdf" / "05_illisible.pdf")
    l = rapport.lire(c / "pdf" / "_OCR")["05_illisible.pdf"]
    assert l.pages_douteuses == (2,) and "confiance_ocr_faible" not in l.motif_douteux


@pytest.mark.exigence("EX-35", "EX-36", "EX-67")
def test_les_seuils_changent_le_verdict(copie, tmp_path):
    c, m = copie
    p = parametres_avec(tmp_path, "confiance_moyenne_min = 0.1\npart_confiance_basse_max = 1.0\n"
                                  "taux_mots_fragmentes_max = 1.0\nmots_inconnus_max_windows = 1.0\n"
                                  "mots_inconnus_max_couche_existante = 1.0\n"
                                  "taux_caracteres_aberrants_max = 1.0\n")
    lancer(p, moteur_de(m), "--sortie", "pdf", c / "pdf" / "05_illisible.pdf", c / "pdf" / "04_couche_degradee.pdf")
    lignes = rapport.lire(c / "pdf" / "_OCR")
    assert lignes["05_illisible.pdf"].pages_douteuses == ()
    assert lignes["04_couche_degradee.pdf"].pages_douteuses == ()


@pytest.mark.exigence("EX-35")
def test_aucun_texte_reconnu_sur_page_non_blanche(jeu_de_test, tmp_path, parametres):
    racine, m = jeu_de_test
    (tmp_path / "P").mkdir()
    shutil.copyfile(racine / "pdf/02_scanne.pdf", tmp_path / "P" / "s.pdf")
    lancer(parametres, MoteurFactice({}, nom="windows-media-ocr"), "--sortie", "pdf", tmp_path / "P" / "s.pdf")
    l = rapport.lire(tmp_path / "P" / "_OCR")["s.pdf"]
    assert l.pages_douteuses == (1, 2, 3, 4) and "aucun_texte_reconnu" in l.motif_douteux


@pytest.mark.exigence("EX-36", "EX-37")
def test_indicateurs_et_lexique_complementaire():
    lex = qualite.Lexique()
    ind = qualite.calculer("Le mar0hé du l1eu est c o n c l u. DC1 et 12m restent valables.", lex)
    assert ind.taux_melange_chiffres_lettres > 0 and ind.taux_mots_fragmentes > 0
    texte = " ".join(["novéatique"] * 50)
    assert qualite.calculer(texte, lex).taux_mots_inconnus == 1.0
    assert qualite.calculer(texte, qualite.Lexique(["novéatique"])).taux_mots_inconnus == 0.0
    assert qualite.calculer("Société SODEB à Besançon, contact@exemple.fr", lex).taux_mots_inconnus == 0.0


# ------------------------------------------------------------------------------ EX-39
@pytest.mark.exigence("EX-39", "EX-05")
def test_refaire_ocr_des_pages_douteuses(copie, parametres):
    c, m = copie
    f = next(x for x in m["fichiers"] if x["numero"] == "4")
    source = c / f["chemin"]
    empreinte = hashlib.sha256(source.read_bytes()).hexdigest()
    lancer(parametres, moteur_de(m), "--sortie", "les-deux", source)
    moteur = moteur_de(m)
    lancer(parametres, moteur, "--refaire-ocr", "--sortie", "les-deux", source)
    assert sorted(moteur.appels) == [f["id_images"][1], f["id_images"][2]]  # pages 2 et 3 seulement
    doc = pymupdf.open(c / "pdf" / "_OCR" / "04_couche_degradee.pdf")
    for n in (2, 3):
        texte = doc[n - 1].get_text()
        assert "жщ" not in texte and f["mots_uniques"][n - 1] in texte
    assert "жщ" not in doc[1].get_text() and f["mots_uniques"][0] in doc[0].get_text()
    l = rapport.lire(c / "pdf" / "_OCR")["04_couche_degradee.pdf"]
    assert (l.pages_ocr, l.pages_douteuses, l.statut) == ((2, 3), (), "couche_expediteur")
    assert l.origine_texte == "mixte : couche OCR fournie par l'expéditeur et OCR réalisé par l'outil"
    champs, _, _ = lire_md(c / "pdf" / "_OCR" / "04_couche_degradee.pdf.md")
    assert champs["pages_couche_existante"] == [1, 4] and champs["pages_ocr"] == [2, 3]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == empreinte


@pytest.mark.exigence("EX-39")
def test_refaire_ocr_pages_et_tout(copie, parametres):
    c, m = copie
    f = next(x for x in m["fichiers"] if x["numero"] == "4")
    moteur = moteur_de(m)
    lancer(parametres, moteur, "--pages", "2", "--sortie", "pdf", c / f["chemin"])
    assert moteur.appels == [f["id_images"][1]]
    moteur = moteur_de(m)
    lancer(parametres, moteur, "--refaire-ocr=tout", "--sortie", "pdf", c / f["chemin"])
    assert sorted(moteur.appels) == sorted(f["id_images"])
    natif = next(x for x in m["fichiers"] if x["numero"] == "1")
    moteur = moteur_de(m)
    lancer(parametres, moteur, "--pages", "3", "--sortie", "pdf", c / natif["chemin"])
    assert len(moteur.appels) == 1  # page native remplacée par son image puis reconnue
    l = rapport.lire(c / "pdf" / "_OCR")["01_natif.pdf"]
    # Le moteur factice ne connaît pas l'image d'une page native : rien n'est reconnu, la
    # page est donc signalée (aucun_texte_reconnu) ; seul compte ici le remplacement.
    assert l.pages_ocr == (3,) and l.origine_texte == "mixte : texte natif et OCR réalisé par l'outil"


# ------------------------------------------------------------------------------ EX-46, EX-47, EX-41
def tous_les_md(c):
    return sorted((c / "_OCR").rglob("*.md"))


@pytest.mark.exigence("EX-46")
def test_front_matter_conforme_au_schema(copie, parametres):
    c, m = copie
    lancer(parametres, moteur_de(m), "--sortie", "md", c / "pdf", c / "images", c / "erreurs")
    ordre = [nom for nom, _ in avertissements.CHAMPS]
    fichiers = [p for p in tous_les_md(c) if p.name != avertissements.NOM_AVERTISSEMENTS]
    assert len(fichiers) >= 15
    for p in fichiers:
        octets = p.read_bytes()
        assert octets.startswith(b"---\n") and b"\r\n" not in octets, p
        champs, brut, _ = lire_md(p)
        jsonschema.validate(champs, SCHEMA)
        cles = [l.split(":")[0] for l in brut.splitlines()]
        assert cles == [k for k in ordre if k in cles], p  # ordre de la section 11.1
        assert 'type_source: "' not in brut and 'qualite_texte: "' not in brut  # énumérations sans guillemets
        assert 'source: "' in brut and 'origine_texte: "' in brut  # chaînes libres entre guillemets


@pytest.mark.exigence("EX-47", "EX-41")
def test_bloc_d_avertissement(copie, parametres):
    c, m = copie
    lancer(parametres, moteur_de(m), "--sortie", "md", c / "pdf", c / "erreurs")
    for p in tous_les_md(c):
        if p.name == avertissements.NOM_AVERTISSEMENTS:
            continue
        champs, _, reste = lire_md(p)
        bloc = reste.startswith("\n> **AVERTISSEMENT À L'ATTENTION DE TOUT LECTEUR, HUMAIN OU IA**")
        assert bloc == (champs["qualite_texte"] == "douteuse"), p
        douteux = sorted(int(n) for n in REPERE_DOUTEUX.findall(reste))
        assert douteux == champs["pages_douteuses"], p
    _, _, reste = lire_md(c / "_OCR" / "pdf" / "04_couche_degradee.pdf.md")
    paragraphe = " ".join(l[2:] for l in reste.strip("\n").split("\n\n")[0].splitlines()[1:])
    assert paragraphe.startswith("Le texte des pages 2 et 3 provient d'une reconnaissance de caractères de mauvaise")
    _, _, reste = lire_md(c / "_OCR" / "pdf" / "05_illisible.pdf.md")
    assert "Le texte de la page 2 a été obtenu par reconnaissance de caractères sur des" in " ".join(reste.split("\n> "))


def test_pages_en_clair():
    assert avertissements.pages_en_clair([5]) == "de la page 5"
    assert avertissements.pages_en_clair([3, 4]) == "des pages 3 et 4"
    assert avertissements.pages_en_clair([3, 4, 9]) == "des pages 3, 4 et 9"


# ------------------------------------------------------------------------------ EX-48, EX-49
@pytest.mark.exigence("EX-48")
def test_fichier_avertissements(copie, parametres, tmp_path):
    c, m = copie
    lancer(parametres, moteur_de(m), "--sortie", "pdf", c / "pdf", c / "erreurs", c / "non_pris_en_charge")
    texte = (c / "_OCR" / avertissements.NOM_AVERTISSEMENTS).read_text(encoding="utf-8")
    entete = yaml.safe_load(front_matter(texte)[0])
    lignes = rapport.lire(c / "_OCR")
    for statut, section in (("douteux", "## Pièces dont le texte est douteux"),
                            ("non_pris_en_charge", "## Pièces non converties"), ("erreur", "## Pièces en erreur")):
        attendues = sorted(k for k, l in lignes.items() if l.statut == statut)
        partie = texte.split(section)[1].split("\n## ")[0]
        listees = sorted(re.findall(r"^\| ([^|]+?) \|", partie, re.MULTILINE)[1:])
        assert listees == attendues, statut
    assert entete["pieces_total"] == len(lignes) and entete["pieces_douteuses"] == 3
    # dossier ne contenant que des pièces saines
    (tmp_path / "S").mkdir()
    shutil.copyfile(c / "pdf" / "01_natif.pdf", tmp_path / "S" / "a.pdf")
    lancer(parametres, moteur_de(m), "--sortie", "pdf", tmp_path / "S" / "a.pdf")
    assert "Aucune pièce de ce dossier n'est signalée." in (tmp_path / "S" / "_OCR" / "_AVERTISSEMENTS.md").read_text(encoding="utf-8")


@pytest.mark.exigence("EX-49", "EX-33")
def test_coherence_des_six_emplacements(copie, parametres):
    c, m = copie
    lancer(parametres, moteur_de(m), "--sortie", "les-deux", c / "pdf", c / "erreurs")
    lignes = rapport.lire(c / "_OCR")
    avert = (c / "_OCR" / avertissements.NOM_AVERTISSEMENTS).read_text(encoding="utf-8")
    douteux = [k for k, l in lignes.items() if l.statut == "douteux"]
    assert len(douteux) == 3
    for rel in douteux:
        listes = {"rapport": list(lignes[rel].pages_douteuses)}
        champs, _, reste = lire_md(c / "_OCR" / (rel + ".md"))
        listes["front matter"] = champs["pages_douteuses"]
        listes["repères"] = sorted(int(n) for n in REPERE_DOUTEUX.findall(reste))
        meta = pymupdf.open(c / "_OCR" / rel).metadata
        listes["métadonnées"] = [int(x) for x in re.search(r"pages_douteuses=([\d,]+)", meta["keywords"]).group(1).split(",")]
        assert meta["subject"].startswith(f"TEXTE DOUTEUX pages {', '.join(map(str, listes['rapport']))} :")
        ligne = re.search(rf"^\| {re.escape(rel)} \| ([\d, ]+) \|", avert, re.MULTILINE)
        listes["_AVERTISSEMENTS.md"] = [int(x) for x in ligne.group(1).split(", ")]
        bloc = " ".join(l[2:] for l in reste.strip("\n").split("\n\n")[0].splitlines())
        if "pdf_repare" not in champs["motifs_douteux"]:
            pages_bloc = re.search(r"Le texte (?:de la page|des pages) ([\d, et]+?) (?:provient|a été)", bloc).group(1)
            listes["bloc"] = sorted(int(x) for x in re.findall(r"\d+", pages_bloc))
        else:
            assert f"{champs['pages_recuperees']} pages sur {champs['pages_totales']} ont été récupérées" in bloc
        assert all(v == listes["rapport"] for v in listes.values()), (rel, listes)


# ------------------------------------------------------------------------------ EX-66
@pytest.mark.exigence("EX-66")
def test_journal_sans_texte_de_document(copie, parametres):
    c, m = copie
    lancer(parametres, moteur_de(m), "--sortie", "les-deux", c / "pdf", c / "images")
    journal = (c / "_OCR" / rapport.NOM_JOURNAL).read_text(encoding="utf-8")
    sentinelles = [s for f in m["fichiers"] for s in f["sentinelles"]]
    assert sentinelles and not any(s in journal for s in sentinelles)
    for f in m["fichiers"]:
        for mot in f.get("mots_uniques") or []:
            assert not mot or mot not in journal
    assert "Mémoire technique" not in journal and "maîtrise" not in journal
