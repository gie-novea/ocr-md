"""Architecture : aiguillage par plateforme, absence de moteur OCR tiers, réseau (EX-03, EX-07, EX-08)."""

import ast
import importlib
import pathlib
import pkgutil
import re
import socket
import tomllib

import pytest

import ocr_md

RACINE_SRC = pathlib.Path(ocr_md.__file__).parent
PROPRES_PLATEFORME = {"winrt", "ocrmac", "Vision", "objc", "Foundation", "Quartz", "AppKit", "win32com", "pythoncom"}
MODULES_AUTORISES = {"ocr/windows.py", "ocr/macos.py"}
AUTORISES_PREFIXE = ("plateforme/",)


def imports_de(fichier):
    arbre = ast.parse(fichier.read_text(encoding="utf-8"))
    for noeud in ast.walk(arbre):
        if isinstance(noeud, ast.Import):
            yield from (a.name.split(".")[0] for a in noeud.names)
        elif isinstance(noeud, ast.ImportFrom) and noeud.module and noeud.level == 0:
            yield noeud.module.split(".")[0]


@pytest.mark.exigence("EX-07")
def test_imports_propres_a_une_plateforme_localises():
    fautifs = []
    for f in RACINE_SRC.rglob("*.py"):
        rel = f.relative_to(RACINE_SRC).as_posix()
        if rel in MODULES_AUTORISES or rel.startswith(AUTORISES_PREFIXE):
            continue
        fautifs += [f"{rel} importe {m}" for m in imports_de(f) if m in PROPRES_PLATEFORME]
    assert not fautifs


@pytest.mark.exigence("EX-07")
def test_tous_les_modules_communs_s_importent_sur_cette_plateforme():
    for info in pkgutil.walk_packages(ocr_md.__path__, "ocr_md."):
        if info.name in ("ocr_md.ocr.windows", "ocr_md.ocr.macos"):
            continue
        importlib.import_module(info.name)


@pytest.mark.exigence("EX-08")
def test_aucun_moteur_ocr_tiers_declare():
    projet = tomllib.loads((RACINE_SRC.parents[1] / "pyproject.toml").read_text(encoding="utf-8"))
    deps = " ".join(projet["project"]["dependencies"]).lower()
    for interdit in ("tesseract", "rapidocr", "easyocr", "opencv", "paddle", "ocrmypdf"):
        assert interdit not in deps
    verrou = (RACINE_SRC.parents[1] / "uv.lock").read_text(encoding="utf-8").lower()
    for interdit in ("name = \"pytesseract\"", "name = \"rapidocr", "name = \"easyocr\"", "name = \"opencv"):
        assert interdit not in verrou


@pytest.mark.exigence("EX-08")
def test_aucun_import_de_moteur_tiers_dans_le_code():
    tiers = {"pytesseract", "tesserocr", "rapidocr", "rapidocr_onnxruntime", "easyocr", "cv2", "paddleocr", "ocrmypdf"}
    for f in RACINE_SRC.rglob("*.py"):
        assert not (set(imports_de(f)) & tiers), f


@pytest.mark.exigence("EX-03")
def test_reseau_neutralise_pendant_les_tests():
    with pytest.raises(RuntimeError, match="EX-03"):
        socket.create_connection(("example.org", 80), timeout=1)
    with pytest.raises(RuntimeError, match="EX-03"):
        socket.socket().connect(("127.0.0.1", 9))


@pytest.mark.exigence("EX-03")
def test_aucune_telemetrie_ni_adresse_reseau_dans_le_code():
    # Les espaces de noms XML des formats Office sont des identifiants, jamais consultés.
    espaces_de_noms = re.compile(r"\{http://schemas\.openxmlformats\.org/[\w./-]+\}")
    for f in RACINE_SRC.rglob("*.py"):
        texte = espaces_de_noms.sub("", f.read_text(encoding="utf-8"))
        assert not set(imports_de(f)) & {"requests", "urllib3", "httpx", "socket", "http"}, f
        assert "http://" not in texte and "https://" not in texte, f


@pytest.mark.exigence("EX-09")
def test_python_3_12_impose():
    projet = tomllib.loads((RACINE_SRC.parents[1] / "pyproject.toml").read_text(encoding="utf-8"))
    assert projet["project"]["requires-python"] == ">=3.12,<3.13"


def test_tkinter_present():
    """PV-11 : tkinter doit exister dans le Python utilisé (géré par uv en CI)."""
    import re
    import tkinter
    version = tkinter.Tcl().eval("info patchlevel")
    print(f"Tcl {version}")
    assert re.match(r"^(8\.6|9\.)", version), version


@pytest.mark.exigence("EX-40")
def test_conversion_markdown_minimale():
    """La conversion Markdown (avec le module de mise en page et onnxruntime) fonctionne
    sur cette plateforme ; détecte une dépendance binaire absente (cas du Mac Intel)."""
    import pymupdf
    import pymupdf4llm
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 100), "Mémoire technique : maîtrise d'œuvre")
    morceaux = pymupdf4llm.to_markdown(doc, page_chunks=True, use_ocr=False)
    assert "Mémoire technique" in morceaux[0]["text"]
