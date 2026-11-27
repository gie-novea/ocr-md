"""Livrables du jalon 10 : arborescence (EX-77), documents générés à jour (EX-67, EX-75, EX-78),
messages de l'outil présents dans le guide administrateur (EX-80), guides utilisateur
(EX-79), CHANGELOG (EX-81), script de performance (EX-58)."""

import importlib.util
import json
import pathlib
import re
import subprocess
import sys

import pytest

RACINE = pathlib.Path(__file__).resolve().parents[1]


def charger(nom, chemin):
    spec = importlib.util.spec_from_file_location(nom, chemin)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.exigence("EX-77")
def test_arborescence_livree():
    attendus = ["README.md", "LICENSE", "CHANGELOG.md", "LICENCES-TIERCES.md", "pyproject.toml", "uv.lock",
                "src/ocr_md/donnees", "schema/front-matter-v1.json",
                "installation/installer-windows.cmd", "installation/installer-windows.ps1",
                "installation/installer-macos.command", "installation/mettre-a-jour-windows.cmd",
                "installation/mettre-a-jour-macos.command", "installation/desinstaller-windows.cmd",
                "installation/desinstaller-macos.command", "docs/guide-utilisateur-windows.md",
                "docs/guide-utilisateur-macos.md", "docs/guide-administrateur.md",
                "docs/specification-front-matter.md", "docs/verifications.md", "docs/recette-manuelle.md",
                "tests/donnees/generer.py", "tests/perf/lot_type.py", "tests/calibrage.py", "tests/TRACABILITE.md"]
    manquants = [a for a in attendus if not (RACINE / a).exists()]
    assert not manquants, manquants
    assert not list(RACINE.rglob("*.spec")), "aucun script d'exécutable empaqueté (EX-68)"


@pytest.mark.exigence("EX-67", "EX-75", "EX-78", "EX-80")
def test_documents_generes_a_jour(capsys):
    """Tableau des paramètres du guide, TRACABILITE.md, LICENCES-TIERCES.md, spécification du
    front matter : identiques à ce que produit `outils/documentation.py`."""
    documentation = charger("documentation", RACINE / "outils" / "documentation.py")
    assert documentation.main(["--verifier"]) == 0, capsys.readouterr().out


@pytest.mark.exigence("EX-75")
def test_toute_exigence_a_un_test_ou_une_fiche():
    texte = (RACINE / "tests" / "TRACABILITE.md").read_text(encoding="utf-8")
    assert "sans test automatisé ni fiche de recette : aucune." in texte


@pytest.mark.exigence("EX-78")
def test_licences_toutes_connues_et_compatibles():
    texte = (RACINE / "LICENCES-TIERCES.md").read_text(encoding="utf-8")
    assert "compatibles avec l'AGPL-3.0) : aucune." in texte
    assert "| pymupdf | 1.28.2 |" in texte and "Grammalecte" in texte and "Noto Sans" in texte


@pytest.mark.exigence("EX-80")
def test_chaque_message_figure_dans_le_guide_administrateur():
    messages = charger("messages", RACINE / "outils" / "messages.py").messages()
    guide = (RACINE / "docs" / "guide-administrateur.md").read_text(encoding="utf-8")
    absents = [m for m in messages if m not in guide]
    assert len(messages) >= 35 and not absents, absents


@pytest.mark.exigence("EX-79")
@pytest.mark.parametrize("plateforme", ["windows", "macos"])
def test_guides_utilisateur(plateforme):
    texte = (RACINE / "docs" / f"guide-utilisateur-{plateforme}.md").read_text(encoding="utf-8")
    assert texte.count("[CAPTURE :") >= 4
    assert len(texte.split()) <= 650  # une page A4 une fois mis en page
    for sujet in ("_OCR", "_AVERTISSEMENTS.md", "fenêtre de fin", "douteuses", "non converties", "en erreur",
                  "Claude", "Refaire l'OCR des pages douteuses"):
        assert sujet.lower() in texte.lower(), sujet
    # Commandes : seulement l'encadré « Refaire l'OCR » et, sous macOS, la ligne d'installation
    # (décision du commanditaire du 27/11/2026).
    commandes = re.findall(r"`[^`]*(?:ocr-md|curl)[^`]*`", texte)
    autorisees = [c for c in commandes if "--refaire-ocr" in c or (plateforme == "macos" and "curl -LsSf" in c)]
    assert commandes == autorisees, commandes


@pytest.mark.exigence("EX-81")
def test_changelog():
    texte = (RACINE / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "### Écarts au cahier des charges" in texte and "### Reprise de l'existant" in texte


@pytest.mark.exigence("EX-58", "EX-57")
def test_script_du_lot_type(tmp_path):
    r = subprocess.run([sys.executable, str(RACINE / "tests" / "perf" / "lot_type.py"), str(tmp_path),
                        "--moteur", "factice", "--plis", "2"], capture_output=True, text=True, cwd=RACINE,
                       timeout=600)
    assert r.returncode == 0, r.stderr[-2000:]
    releve = json.loads((tmp_path / "releve.json").read_text(encoding="utf-8"))
    assert releve["pages"] == 20 and releve["pages_scannees"] == 12 and releve["code"] == 0
    assert releve["fichiers_ignores_a_jour"] == 4 and releve["relance_s"] < releve["duree_s"]
    assert releve["pic_memoire_mo"] > 0 and releve["pages_par_minute"] > 0
