"""Ligne de commande : options, combinaisons invalides, codes de retour (EX-11, EX-12)."""

import pytest

from ocr_md import cli


def lancer(capsys, *arguments):
    code = cli.main(list(arguments))
    sortie = capsys.readouterr()
    return code, sortie.out, sortie.err


@pytest.mark.exigence("EX-11")
def test_aide_en_francais(capsys):
    code, out, _ = lancer(capsys, "--aide")
    assert code == cli.SUCCES
    assert out.startswith("ocr-md [OPTIONS] CHEMIN [CHEMIN ...]")
    for option in ("--sortie", "--refaire-ocr", "--pages", "--qualite", "--forcer", "--tableaux",
                   "--sans-interface", "--config", "ocr-md verifier", "ocr-md raccourcis"):
        assert option in out


@pytest.mark.exigence("EX-10", "EX-78")
def test_version_affiche_versions_licence_et_source(capsys):
    code, out, _ = lancer(capsys, "--version")
    assert code == cli.SUCCES
    for attendu in ("ocr-md ", "PyMuPDF 1.28.2", "PyMuPDF4LLM 1.28.2", "Moteur OCR :", "AGPL-3.0", "Code source :"):
        assert attendu in out


@pytest.mark.exigence("EX-11", "EX-12")
@pytest.mark.parametrize("arguments, extrait", [
    (["--inconnue", "a.pdf"], "option ou argument inconnu : --inconnue"),
    (["--sortie", "docx", "a.pdf"], "valeur invalide pour --sortie"),
    (["--tableaux", "csv", "a.pdf"], "valeur invalide pour --tableaux"),
    (["--refaire-ocr=certaines", "a.pdf"], "valeur invalide pour --refaire-ocr"),
    (["--pages", "3", "a.pdf", "b.pdf"], "--pages n'est admis que si un seul fichier PDF"),
    (["--pages", "3", "a.docx"], "--pages n'est admis que si un seul fichier PDF"),
    (["--pages", "0", "a.pdf"], "plage de pages invalide"),
    (["--pages", "3-x", "a.pdf"], "liste de pages invalide"),
    (["--sortie"], "l'option --sortie attend une valeur"),
    ([], "aucun fichier ni dossier à traiter"),
    (["--sortie", "md"], "aucun fichier ni dossier à traiter"),
    (["verifier", "en-trop"], "n'accepte pas d'argument"),
    (["raccourcis"], "usage : ocr-md raccourcis --creer | --supprimer"),
])
def test_erreurs_d_usage(capsys, arguments, extrait):
    code, out, err = lancer(capsys, *arguments)
    assert code == cli.ERREUR_USAGE
    assert extrait in err
    assert err.startswith("ocr-md : erreur d'usage : ")


@pytest.mark.exigence("EX-11")
def test_qualite_annoncee_pour_la_v1_1(capsys):
    code, _, err = lancer(capsys, "--qualite", "a.pdf")
    assert code == cli.ERREUR_USAGE
    assert "mode qualité disponible à partir de la version 1.1" in err


@pytest.mark.exigence("EX-11")
def test_valeurs_par_defaut():
    o = cli.analyser(["a.pdf"])
    assert (o.sortie, o.refaire_ocr, o.pages, o.forcer, o.tableaux, o.sans_interface, o.config) == \
        ("les-deux", None, (), False, "auto", False, None)


@pytest.mark.exigence("EX-11", "EX-39")
def test_refaire_ocr_sans_valeur_ne_consomme_pas_le_chemin():
    o = cli.analyser(["--refaire-ocr", "dossier"])
    assert o.refaire_ocr == "douteuses"
    assert [str(c) for c in o.chemins] == ["dossier"]
    assert cli.analyser(["--refaire-ocr=tout", "x.pdf"]).refaire_ocr == "tout"


@pytest.mark.exigence("EX-11", "EX-39")
def test_pages_liste_et_plages():
    o = cli.analyser(["--pages", "9-12,3,4,4", "Pli.PDF"])
    assert o.pages == (3, 4, 9, 10, 11, 12)
    assert o.refaire_ocr == "pages"


@pytest.mark.exigence("EX-11")
def test_toutes_les_options_ensemble():
    o = cli.analyser(["--sortie", "pdf", "--forcer", "--tableaux", "html", "--sans-interface",
                      "--config", "c.toml", "a.pdf", "dossier"])
    assert (o.sortie, o.forcer, o.tableaux, o.sans_interface, str(o.config)) == ("pdf", True, "html", True, "c.toml")
    assert len(o.chemins) == 2


@pytest.mark.exigence("EX-67", "EX-12")
def test_config_invalide_donne_une_erreur_d_usage(capsys, tmp_path):
    fichier = tmp_path / "c.toml"
    fichier.write_text("seuil_inexistant = 3\n", encoding="utf-8")
    code, _, err = lancer(capsys, "--config", str(fichier), "a.pdf")
    assert code == cli.ERREUR_USAGE
    assert "paramètre inconnu : « seuil_inexistant »" in err


@pytest.mark.exigence("EX-67", "EX-12")
def test_config_introuvable(capsys, tmp_path):
    code, _, err = lancer(capsys, "--config", str(tmp_path / "absent.toml"), "a.pdf")
    assert code == cli.ERREUR_USAGE
    assert "fichier de configuration introuvable" in err


@pytest.mark.exigence("EX-71")
def test_verifier_affiche_un_diagnostic(capsys):
    code, out, _ = lancer(capsys, "verifier")
    assert code in (cli.SUCCES, cli.PREREQUIS_MANQUANT)
    assert "Système :" in out and "Moteur OCR :" in out and "Dossier temporaire" in out
