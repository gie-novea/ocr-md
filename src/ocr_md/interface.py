"""Interface graphique (EX-16, EX-17, REC-02) : fenêtre de progression, puis fenêtre de fin.

- Progression : fichier en cours, rang sur le total, page en cours pendant l'OCR, barre de
  progression ; bouton « Annuler » (arrêt après la page en cours, EX-17). Fermer la fenêtre
  pendant le traitement vaut annulation.
- Fin : nombres de fichiers traités, signalés, en erreur, ignorés car à jour (et annulés),
  emplacement des dossiers `_OCR`, bouton « Ouvrir le dossier » ; messages généraux (moteur OCR
  absent, dossier parent non inscriptible, sélection proche de la limite de la ligne de
  commande, prérequis manquants au premier lancement). La fenêtre ne se ferme pas seule s'il
  existe des fichiers signalés ou en erreur, ou un message ; sinon, elle se ferme après
  `FERMETURE_AUTO_S` secondes.
- Le traitement tourne dans un fil secondaire ; la fenêtre lit sa progression dans une file.
- Repli si tkinter manque ou si aucun affichage n'est possible : notification du système en
  fin de traitement et fichier `_EN_COURS.txt` dans chaque dossier `_OCR` pendant le lot.
"""

import os
import pathlib
import queue
import subprocess
import sys
import threading

from . import rapport, traitement
from .suivi import Suivi, SuiviFile

TITRE = "ocr-md"
FERMETURE_AUTO_S = 20
NOM_EN_COURS = "_EN_COURS.txt"


# ------------------------------------------------------------------------------ textes
def texte_bilan(bilan: traitement.BilanLot) -> list[str]:
    """Lignes de la fenêtre de fin (EX-16), nombres recalculés depuis les lignes du rapport."""
    b = rapport.bilan(bilan.lignes)
    lignes = [f"Fichiers traités : {b['traites']}",
              f"Fichiers signalés (texte douteux ou format non pris en charge) : {b['signales']}",
              f"Fichiers en erreur : {b['erreurs']}",
              f"Fichiers ignorés car déjà à jour : {b['ignores_a_jour']}"]
    if b["annules"]:
        lignes.append(f"Fichiers non traités (annulation) : {b['annules']}")
    return lignes


def a_signaler(bilan: traitement.BilanLot) -> bool:
    b = rapport.bilan(bilan.lignes)
    return bool(b["signales"] or b["erreurs"] or b["annules"] or bilan.messages or bilan.avertissements)


def messages_generaux(bilan: traitement.BilanLot) -> list[str]:
    """Messages à montrer en fin de lot : ceux du lot (dont les avertissements), et celui du
    moteur OCR absent s'il a mis des fichiers en erreur (EX-71)."""
    from . import ocr
    messages = list(bilan.messages) + list(bilan.avertissements)
    absent = ocr.message_moteur_absent()
    if any(l.statut == "erreur" and l.message.startswith(absent) for l in bilan.lignes):
        messages.append(absent)
    return list(dict.fromkeys(messages))


def ouvrir_dossier(dossier: pathlib.Path) -> None:
    if sys.platform == "win32":
        os.startfile(str(dossier))  # noqa: S606 - Explorateur, aucune commande tierce
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(dossier)])
    else:
        subprocess.Popen(["xdg-open", str(dossier)])


# ------------------------------------------------------------------------------ repli sans tkinter
class SuiviFichierEnCours(Suivi):
    """Repli de REC-02 : progression écrite dans `_EN_COURS.txt` du dossier `_OCR` en cours."""

    def __init__(self, dossiers: list[pathlib.Path]):
        self.dossiers = dossiers
        self.ligne = ""

    def fichier(self, rang, total, relatif):
        self.ligne = f"Fichier {rang} sur {total} : {relatif}"
        self._ecrire(self.ligne)

    def page(self, numero, total):
        self._ecrire(f"{self.ligne}, page {numero} sur {total}")

    def _ecrire(self, texte):
        for d in self.dossiers:
            try:
                if d.is_dir():
                    (d / NOM_EN_COURS).write_text(texte + "\n", encoding="utf-8")
            except OSError:
                pass

    def nettoyer(self):
        for d in self.dossiers:
            try:
                (d / NOM_EN_COURS).unlink(missing_ok=True)
            except OSError:
                pass


def notifier(titre: str, texte: str) -> None:
    """Notification du système, sans console ni dépendance ajoutée."""
    try:
        if sys.platform == "darwin":
            echappe = texte.replace("\\", "\\\\").replace('"', '\\"')
            subprocess.run(["osascript", "-e", f'display notification "{echappe}" with title "{titre}"'],
                           timeout=10, check=False)
        elif sys.platform == "win32":
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, texte, titre, 0x40)
    except Exception:
        pass


def _dossiers_ocr_prevus(options) -> list[pathlib.Path]:
    from . import inventaire
    try:
        return [g.dossier_ocr for g in inventaire.inventorier(list(options.chemins))]
    except Exception:
        return []


def executer_sans_fenetre(options, parametres, bilan, avant=()) -> int:
    suivi = SuiviFichierEnCours(_dossiers_ocr_prevus(options))
    try:
        code = traitement.executer(options, parametres, bilan=bilan, suivi=suivi)
    finally:
        suivi.nettoyer()
    lignes = list(avant) + texte_bilan(bilan) + messages_generaux(bilan)
    lignes += [f"Résultats : {d}" for d in bilan.dossiers_ocr]
    notifier(TITRE, "\n".join(lignes))
    return code


# ------------------------------------------------------------------------------ fenêtre
class Fenetre:
    """Fenêtre de progression puis de fin. `executer` est la fonction de traitement, appelée
    dans un fil secondaire avec (arret, suivi) ; elle renvoie le code de retour."""

    def __init__(self, racine, executer, bilan: traitement.BilanLot, avant=(), fermeture_auto_s=FERMETURE_AUTO_S):
        import tkinter as tk
        from tkinter import ttk
        self.tk, self.ttk = tk, ttk
        self.racine = racine
        self.bilan = bilan
        self.avant = list(avant)
        self.fermeture_auto_s = fermeture_auto_s
        self.file: queue.Queue = queue.Queue()
        self.arret = threading.Event()
        self.code: int | None = None
        self.erreur: BaseException | None = None
        self.termine = False
        racine.title(TITRE)
        racine.minsize(460, 0)
        racine.protocol("WM_DELETE_WINDOW", self._fermer)
        self.cadre = ttk.Frame(racine, padding=16)
        self.cadre.pack(fill="both", expand=True)
        self.libelle_fichier = ttk.Label(self.cadre, text="Préparation du traitement...", wraplength=430)
        self.libelle_fichier.pack(anchor="w")
        self.libelle_page = ttk.Label(self.cadre, text="")
        self.libelle_page.pack(anchor="w", pady=(4, 8))
        self.barre = ttk.Progressbar(self.cadre, length=430, mode="determinate")
        self.barre.pack(fill="x")
        self.bouton_annuler = ttk.Button(self.cadre, text="Annuler", command=self.annuler)
        self.bouton_annuler.pack(anchor="e", pady=(12, 0))
        self.fil = threading.Thread(target=self._travailler, args=(executer,), daemon=True)
        self.fil.start()
        racine.after(100, self._lire_file)

    # Fil secondaire
    def _travailler(self, executer):
        try:
            self.code = executer(self.arret, SuiviFile(self.file))
        except BaseException as e:  # noqa: BLE001 - montré dans la fenêtre de fin
            self.erreur = e
            self.code = traitement.ERREUR_FICHIER
        self.file.put(("fin",))

    # Fil de la fenêtre
    def _lire_file(self):
        try:
            while True:
                evenement = self.file.get_nowait()
                if evenement[0] == "fichier":
                    _, rang, total, relatif = evenement
                    self.libelle_fichier.config(text=f"Fichier {rang} sur {total} : {relatif}")
                    self.libelle_page.config(text="")
                    self.barre.config(maximum=total, value=rang - 1)
                elif evenement[0] == "page":
                    _, numero, total = evenement
                    self.libelle_page.config(text=f"Reconnaissance du texte : page {numero} sur {total}")
                elif evenement[0] == "fin":
                    self.afficher_fin()
                    return
        except queue.Empty:
            pass
        self.racine.after(100, self._lire_file)

    def annuler(self):
        self.arret.set()
        self.bouton_annuler.config(state="disabled")
        self.libelle_page.config(text="Annulation demandée : arrêt après la page en cours...")

    def _fermer(self):
        if self.termine:
            self.racine.destroy()
        else:
            self.annuler()

    def afficher_fin(self):
        ttk = self.ttk
        self.termine = True
        for enfant in self.cadre.winfo_children():
            enfant.destroy()
        lignes = self.avant + texte_bilan(self.bilan)
        titre = "Traitement terminé" if not self.arret.is_set() else "Traitement annulé"
        ttk.Label(self.cadre, text=titre, font=("TkDefaultFont", 11, "bold")).pack(anchor="w", pady=(0, 8))
        for l in lignes:
            ttk.Label(self.cadre, text=l, wraplength=520, justify="left").pack(anchor="w")
        messages = messages_generaux(self.bilan)
        if self.erreur is not None:
            messages.append(f"Erreur inattendue : {type(self.erreur).__name__} (détails dans le journal)")
        for m in messages:
            ttk.Label(self.cadre, text=m, wraplength=520, justify="left", foreground="#a00000").pack(anchor="w",
                                                                                                    pady=(8, 0))
        if self.bilan.dossiers_ocr:
            ttk.Label(self.cadre, text="Résultats :").pack(anchor="w", pady=(10, 0))
            for d in dict.fromkeys(self.bilan.dossiers_ocr):
                ligne = ttk.Frame(self.cadre)
                ligne.pack(fill="x", pady=2)
                ttk.Label(ligne, text=str(d), wraplength=400, justify="left").pack(side="left")
                ttk.Button(ligne, text="Ouvrir le dossier", command=lambda d=d: ouvrir_dossier(d)).pack(side="right")
        ttk.Button(self.cadre, text="Fermer", command=self.racine.destroy).pack(anchor="e", pady=(12, 0))
        self.racine.lift()
        if not a_signaler(self.bilan) and self.erreur is None and self.fermeture_auto_s is not None:
            self.racine.after(int(self.fermeture_auto_s * 1000), self.racine.destroy)


def executer_avec_fenetre(options, parametres, bilan=None, avant=(), fermeture_auto_s=FERMETURE_AUTO_S) -> int:
    """Traitement avec fenêtre ; repli sans fenêtre si tkinter ou l'affichage manque."""
    bilan = bilan if bilan is not None else traitement.BilanLot()
    try:
        import tkinter as tk
        racine = tk.Tk()
    except Exception:  # tkinter absent, aucun affichage (session sans écran)
        return executer_sans_fenetre(options, parametres, bilan, avant)

    def executer(arret, suivi):
        return traitement.executer(options, parametres, arret=arret, bilan=bilan, suivi=suivi)

    fenetre = Fenetre(racine, executer, bilan, avant, fermeture_auto_s)
    racine.mainloop()
    fenetre.arret.set()
    fenetre.fil.join()
    return fenetre.code if fenetre.code is not None else traitement.ERREUR_FICHIER
