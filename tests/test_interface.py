"""Interface et raccourcis (jalon 9) : EX-13, EX-15 à EX-17, EX-70, EX-71 ; sélection proche de
la limite de la ligne de commande (décision du commanditaire du 26/11/2026)."""

import pathlib
import plistlib
import subprocess
import sys
import time

import pymupdf
import pytest

from ocr_md import cli, config, interface, plateforme, raccourcis, rapport, traitement
from ocr_md.suivi import SuiviConsole


def parametres(tmp_path):
    f = tmp_path / "essai.toml"
    f.write_text("intervalle_tentatives_s = 0\n", encoding="utf-8")
    return config.charger(f, fichier_utilisateur=tmp_path / "absent.toml")


def pdf_natif(chemin):
    chemin.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), "Texte natif de contrôle.")
    doc.save(chemin)
    return chemin


@pytest.fixture
def tk_racine():
    tk = pytest.importorskip("tkinter")
    try:
        racine = tk.Tk()
    except tk.TclError:
        pytest.skip("aucun affichage disponible")
    yield racine
    try:
        racine.destroy()
    except tk.TclError:
        pass


def ligne(statut="natif", action="traite"):
    return rapport.LigneRapport("a.pdf", "pdf", statut=statut, action=action, sorties=("a.pdf",))


# ------------------------------------------------------------------------------ fenêtre
@pytest.mark.exigence("EX-16", "EX-17")
def test_fenetre_progression_puis_fin(tk_racine, tmp_path):
    import threading
    bilan = traitement.BilanLot(dossiers_ocr=[tmp_path / "_OCR"])
    vus, lu = {}, threading.Event()

    def executer(arret, suivi):
        suivi.fichier(1, 2, "Lot/A.pdf")
        suivi.page(3, 7)
        lu.wait(10)  # la fin n'arrive qu'une fois la progression relevée par la fenêtre
        bilan.lignes.append(ligne())
        return 0

    f = interface.Fenetre(tk_racine, executer, bilan, fermeture_auto_s=0.3)

    def relever():
        if f.libelle_page.cget("text"):
            vus.update(fichier=f.libelle_fichier.cget("text"), page=f.libelle_page.cget("text"))
            lu.set()
        else:
            tk_racine.after(50, relever)
    tk_racine.after(50, relever)
    tk_racine.after(15000, tk_racine.destroy)  # garde-fou
    tk_racine.mainloop()  # se ferme seule : rien à signaler
    assert vus == {"fichier": "Fichier 1 sur 2 : Lot/A.pdf", "page": "Reconnaissance du texte : page 3 sur 7"}
    assert f.code == 0 and f.termine


@pytest.mark.exigence("EX-17")
def test_annuler_arrete_le_lot(tk_racine):
    bilan = traitement.BilanLot()

    def executer(arret, suivi):
        debut = time.monotonic()
        while not arret.is_set() and time.monotonic() - debut < 10:
            time.sleep(0.05)
        bilan.lignes.append(ligne(action="annule"))
        return 0

    f = interface.Fenetre(tk_racine, executer, bilan, fermeture_auto_s=0.2)
    tk_racine.after(300, f.bouton_annuler.invoke)
    tk_racine.after(3000, tk_racine.destroy)  # garde-fou
    tk_racine.mainloop()
    assert f.arret.is_set() and f.termine
    assert "Fichiers non traités (annulation) : 1" in interface.texte_bilan(bilan)


@pytest.mark.exigence("EX-16")
def test_la_fenetre_de_fin_reste_ouverte_s_il_y_a_des_signalements(tk_racine):
    bilan = traitement.BilanLot(lignes=[ligne("erreur")])
    f = interface.Fenetre(tk_racine, lambda arret, suivi: 1, bilan, fermeture_auto_s=0.1)
    ouverte = {}
    tk_racine.after(1200, lambda: (ouverte.update(v=bool(tk_racine.winfo_exists())), tk_racine.destroy()))
    tk_racine.mainloop()
    assert ouverte == {"v": True} and f.termine


def test_textes_de_la_fenetre_de_fin():
    bilan = traitement.BilanLot(lignes=[ligne(), ligne("douteux"), ligne("erreur"), ligne(action="ignore_a_jour")])
    assert interface.texte_bilan(bilan) == [
        "Fichiers traités : 2", "Fichiers signalés (texte douteux ou format non pris en charge) : 1",
        "Fichiers en erreur : 1", "Fichiers ignorés car déjà à jour : 1"]
    assert interface.a_signaler(bilan)
    assert not interface.a_signaler(traitement.BilanLot(lignes=[ligne()]))


@pytest.mark.exigence("EX-16", "EX-17")
def test_traitement_reel_avec_fenetre(tk_racine, tmp_path):
    tk_racine.destroy()  # la fonction crée sa propre fenêtre
    pdf_natif(tmp_path / "P" / "a.pdf")
    options = cli.analyser([str(tmp_path / "P")])
    code = interface.executer_avec_fenetre(options, parametres(tmp_path), fermeture_auto_s=0.2)
    assert code == 0
    assert (tmp_path / "_OCR" / "P" / "a.pdf.md").is_file()


@pytest.mark.exigence("EX-16")
def test_repli_sans_tkinter(tmp_path, monkeypatch):
    """REC-02 : sans affichage, notification en fin de lot et `_EN_COURS.txt` pendant le lot."""
    import tkinter
    pdf_natif(tmp_path / "P" / "a.pdf")
    notes, en_cours = [], []
    monkeypatch.setattr(tkinter, "Tk", lambda: (_ for _ in ()).throw(tkinter.TclError("pas d'affichage")))
    monkeypatch.setattr(interface, "notifier", lambda titre, texte: notes.append(texte))
    vrai = interface.SuiviFichierEnCours._ecrire

    def ecrire(self, texte):
        vrai(self, texte)
        en_cours.extend(p.read_text(encoding="utf-8") for d in self.dossiers if (p := d / interface.NOM_EN_COURS).exists())
    monkeypatch.setattr(interface.SuiviFichierEnCours, "_ecrire", ecrire)
    code = interface.executer_avec_fenetre(cli.analyser([str(tmp_path / "P")]), parametres(tmp_path))
    assert code == 0 and "Fichiers traités : 1" in notes[0]
    assert en_cours and en_cours[0].startswith("Fichier 1 sur 1 : P/a.pdf")
    assert not (tmp_path / "_OCR" / interface.NOM_EN_COURS).exists()


def test_suivi_console(capsys):
    SuiviConsole().fichier(2, 5, "Lot/B.pdf")
    assert capsys.readouterr().out == "[2/5] Lot/B.pdf\n"


# ------------------------------------------------------------------------------ ligne de commande longue
def test_seuil_de_la_ligne_de_commande():
    assert plateforme.ligne_de_commande_proche_de_la_limite(30000)
    assert not plateforme.ligne_de_commande_proche_de_la_limite(10796)  # 66 dossiers (PV-02)
    assert not plateforme.ligne_de_commande_proche_de_la_limite(None) or sys.platform == "win32"


def test_selection_proche_de_la_limite_signalee(tmp_path, monkeypatch, capsys):
    pdf_natif(tmp_path / "P" / "a.pdf")
    monkeypatch.setattr(plateforme, "ligne_de_commande_proche_de_la_limite", lambda: True)
    code = cli.main(["--sans-interface", "--sortie", "pdf", str(tmp_path / "P")])
    assert code == 0  # avertissement sans effet sur le code de retour
    assert cli.MESSAGE_LIGNE_LONGUE in capsys.readouterr().err
    assert cli.MESSAGE_LIGNE_LONGUE in rapport.lire(tmp_path / "_OCR")["P/a.pdf"].message


# ------------------------------------------------------------------------------ premier lancement
@pytest.mark.exigence("EX-71")
def test_verification_au_premier_lancement_seulement(tmp_path, monkeypatch):
    monkeypatch.setattr(plateforme, "dossier_configuration", lambda: tmp_path / "conf")
    monkeypatch.setattr(cli, "controles", lambda: [("OK", "Système : essai"), ("!", "Raccourcis : absents")])
    assert cli.verification_premier_lancement() == ["Prérequis : Raccourcis : absents"]
    assert cli.verification_premier_lancement() == []  # même version : pas de nouveau contrôle


# ------------------------------------------------------------------------------ raccourcis
@pytest.fixture
def dossier_raccourcis(tmp_path, monkeypatch):
    if sys.platform not in ("win32", "darwin"):
        pytest.skip("raccourcis sous Windows et macOS seulement")
    d = tmp_path / "raccourcis"
    monkeypatch.setattr(raccourcis, "dossier_raccourcis", lambda: d)
    cible = tmp_path / ("ocr-mdw.exe" if sys.platform == "win32" else "ocr-md")
    cible.write_bytes(b"")
    monkeypatch.setattr(raccourcis, "lanceur", lambda: cible)
    if sys.platform == "darwin":
        monkeypatch.setattr(raccourcis, "_actualiser_services", lambda: None)
    return d, cible


@pytest.mark.exigence("EX-13", "EX-15", "EX-70", "EX-71")
def test_raccourcis_crees_relus_recrees_et_retires(dossier_raccourcis):
    d, cible = dossier_raccourcis
    (d).mkdir()
    (d / "Autre raccourci.txt").write_text("à conserver", encoding="utf-8")
    raccourcis.creer()
    raccourcis.creer()  # seconde installation : pas de doublon
    noms = sorted(p.name for p in d.iterdir())
    extension = ".lnk" if sys.platform == "win32" else ".workflow"
    assert noms == sorted(["Autre raccourci.txt"] + [libelle + extension for _, libelle in raccourcis.ENTREES])
    assert raccourcis.etat()[0]
    for sortie, libelle in raccourcis.ENTREES:
        chemin = d / f"{libelle}{extension}"
        if sys.platform == "win32":
            assert raccourcis.lire_lnk(chemin) == (str(cible), f"--sortie {sortie}")
        else:
            assert raccourcis.lire_workflow(chemin) == f'"{cible}" --sortie {sortie} "$@"\n'
            for plist in ("Info.plist", "document.wflow"):
                assert subprocess.run(["plutil", "-lint", str(chemin / "Contents" / plist)]).returncode == 0
            with open(chemin / "Contents" / "Info.plist", "rb") as f:
                service = plistlib.load(f)["NSServices"][0]
            assert service["NSMenuItem"]["default"] == libelle and service["NSSendFileTypes"] == ["public.item"]
    retires = raccourcis.supprimer()
    assert len(retires) == 3 and [p.name for p in d.iterdir()] == ["Autre raccourci.txt"]
    assert not raccourcis.etat()[0]


def test_raccourci_pointant_ailleurs_detecte(dossier_raccourcis, monkeypatch, tmp_path):
    d, cible = dossier_raccourcis
    raccourcis.creer()
    autre = tmp_path / "ancienne" / cible.name
    autre.parent.mkdir()
    autre.write_bytes(b"")
    monkeypatch.setattr(raccourcis, "lanceur", lambda: autre)
    ok, message = raccourcis.etat()
    assert not ok and "ne pointe pas vers l'installation courante" in message


def test_sous_commande_raccourcis(dossier_raccourcis, capsys):
    assert cli.main(["raccourcis", "--creer"]) == 0
    assert capsys.readouterr().out.count("raccourci créé") == 3
    assert cli.main(["raccourcis", "--supprimer"]) == 0
    assert capsys.readouterr().out.count("raccourci retiré") == 3
