"""Paramètres réglables par fichier TOML (EX-67)."""

import pytest

from ocr_md import config


def ecrire(tmp_path, texte, nom="c.toml"):
    f = tmp_path / nom
    f.write_text(texte, encoding="utf-8")
    return f


@pytest.mark.exigence("EX-67", "EX-22", "EX-25")
def test_valeurs_par_defaut_du_cahier(tmp_path):
    p = config.charger(fichier_utilisateur=tmp_path / "absent.toml")
    assert (p.texte_min_caracteres, p.image_couverture_min, p.image_presence_min) == (30, 0.80, 0.30)
    assert (p.ocr_dpi, p.langue_ocr, p.langue_ocr_secondaire) == (300, "fr-FR", "en-US")
    assert (p.confiance_moyenne_min, p.confiance_basse, p.part_confiance_basse_max) == (0.70, 0.50, 0.20)
    assert (p.taux_mots_inconnus_max, p.mots_evaluables_min, p.taux_caracteres_aberrants_max) == (0.19, 40, 0.06)
    assert (p.taux_mots_fragmentes_max, p.taux_melange_chiffres_lettres_max) == (0.19, 0.10)
    assert (p.densite_min, p.densite_max, p.xlsx_lignes_max, p.delai_hydratation_s) == (0.11, 60.0, 2000, 120)
    assert p.sources == ()


@pytest.mark.exigence("EX-67")
def test_surcharge_par_profil_puis_par_option(tmp_path):
    profil = ecrire(tmp_path, "ocr_dpi = 200\ntexte_min_caracteres = 10\n", "profil.toml")
    option = ecrire(tmp_path, "ocr_dpi = 400\nimage_couverture_min = 1\n")
    p = config.charger(option, fichier_utilisateur=profil)
    assert p.ocr_dpi == 400  # le fichier --config prime sur celui du profil
    assert p.texte_min_caracteres == 10
    assert p.image_couverture_min == 1.0 and isinstance(p.image_couverture_min, float)
    assert p.sources == (str(profil), str(option))


@pytest.mark.exigence("EX-67")
@pytest.mark.parametrize("texte, message", [
    ("inconnu = 1", "paramètre inconnu : « inconnu »"),
    ("ocr_dpi = \"haut\"", "« ocr_dpi » doit être un entier"),
    ("ocr_dpi = 10", "« ocr_dpi » doit être compris entre 72 et 1200"),
    ("image_couverture_min = 1.5", "doit être compris entre 0 et 1"),
    ("lexique_complementaire = [1, 2]", "doit être une liste de chaînes"),
    ("forcer = true", "paramètre inconnu"),
    ("ocr_dpi = true", "doit être un entier"),
    ("ocr_dpi = = 3", "fichier de configuration illisible"),
])
def test_valeurs_invalides(tmp_path, texte, message):
    with pytest.raises(config.ErreurConfiguration, match=message):
        config.charger(ecrire(tmp_path, texte), fichier_utilisateur=tmp_path / "absent.toml")


@pytest.mark.exigence("EX-67")
def test_chaque_parametre_a_une_description_et_un_defaut_valide():
    for d in config.DEFINITIONS:
        assert d.description
        assert config._valider(d.nom, d.defaut) == d.defaut
