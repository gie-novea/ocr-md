"""Orchestration du traitement d'un lot (section 3.2).

Pour chaque dossier parent des éléments passés en entrée : création du dossier `_OCR`,
nettoyage des temporaires d'une exécution interrompue, journal, puis pour chaque fichier :
règle de relance, contrôles préalables, traitement par le traiteur du type, écriture
atomique des sorties et réécriture du rapport après chaque fichier (EX-61). Un fichier en
erreur n'arrête jamais le lot (EX-60) ; un arrêt demandé laisse les fichiers restants en
« annule » (EX-17).
"""

import dataclasses
import datetime
import os
import shutil
import sys
import threading
import time

from . import __version__, archives, avertissements, correctifs, inventaire, ocr, plateforme, rapport, sorties
from .inventaire import ErreurFichier
from .suivi import Suivi, SuiviConsole
from .traiteurs import Annulation, Contexte, traiteurs_par_defaut

SUCCES, ERREUR_FICHIER, PREREQUIS_MANQUANT = 0, 1, 3
MESSAGE_PDF_OFFICE = "pas de PDF consultable pour ce format : utiliser Convertir en Markdown"
MESSAGE_INTROUVABLE = "fichier ou dossier introuvable"
MESSAGE_ANNULE = "traitement annulé avant la fin de ce fichier"


def _maintenant() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _message_parent_non_inscriptible(parent) -> str:
    return (f"écriture impossible dans « {parent} » : copier le dossier dans un emplacement accessible "
            "en écriture, puis relancer")


def creer_dossier_ocr(dossier_ocr) -> None:
    """Crée le dossier _OCR dans le dossier parent ; OSError si le parent n'est pas
    inscriptible (l'outil n'écrit alors nulle part ailleurs, EX-50)."""
    os.makedirs(sorties.chemin_systeme(dossier_ocr), exist_ok=True)


class FournisseurMoteur:
    """Moteur OCR obtenu à la première page qui en a besoin. S'il est indisponible, les
    fichiers à reconnaître passent en erreur avec le message de EX-71, les autres sont
    traités normalement."""

    def __init__(self, parametres, moteur=None):
        self._parametres = parametres
        self._moteur = moteur
        self._erreur = None
        self.utilise = False
        self.indisponible = False

    def obtenir(self):
        if self._moteur is None and self._erreur is None:
            try:
                self._moteur = ocr.moteur_systeme(self._parametres.langue_ocr, self._parametres.langue_ocr_secondaire)
            except ocr.MoteurIndisponible as e:
                self._erreur = e
        if self._moteur is None:
            self.indisponible = True
            raise ErreurFichier(ocr.message_moteur_absent())
        self.utilise = True
        return self._moteur

    def nom_si_utilise(self) -> str:
        return self._moteur.nom if self._moteur is not None else "aucun"

    @property
    def moteur(self):
        return self._moteur


def nettoyer_dossier_temporaire(age_max_s: float = 6 * 3600) -> None:
    """Supprime les dossiers temporaires d'exécutions précédentes (EX-28), en épargnant
    ceux, récents, d'une exécution peut-être encore en cours."""
    base = plateforme.dossier_temporaire()
    if not base.is_dir():
        return
    for d in base.iterdir():
        try:
            if d.name == f"processus-{os.getpid()}" or time.time() - d.stat().st_mtime > age_max_s:
                shutil.rmtree(d, ignore_errors=True)
        except OSError:
            pass


@dataclasses.dataclass
class BilanLot:
    code: int = SUCCES
    lignes: list = dataclasses.field(default_factory=list)       # lignes traitées pendant ce lancement
    dossiers_ocr: list = dataclasses.field(default_factory=list)
    messages: list = dataclasses.field(default_factory=list)     # erreurs générales (parent non inscriptible)
    # Avertissements du lancement (ligne de commande proche de sa limite) : repris dans le
    # message de chaque ligne du rapport, sans effet sur le code de retour.
    avertissements: list = dataclasses.field(default_factory=list)


def executer(options, parametres, *, traiteurs=None, arret: threading.Event | None = None,
             moteur=None, bilan: BilanLot | None = None, suivi=None) -> int:
    traiteurs = traiteurs or traiteurs_par_defaut()
    arret = arret or threading.Event()
    bilan = bilan if bilan is not None else BilanLot()
    suivi = suivi if suivi is not None else (SuiviConsole() if options.sans_interface else Suivi())
    fournisseur = moteur if isinstance(moteur, FournisseurMoteur) else FournisseurMoteur(parametres, moteur)
    correctifs.appliquer()
    nettoyer_dossier_temporaire()
    groupes = inventaire.inventorier(list(options.chemins))
    total = sum(len(g.elements) for g in groupes)
    rang = 0
    try:
        for groupe in groupes:
            rang, total = _traiter_groupe(groupe, options, parametres, traiteurs, arret, fournisseur, bilan, rang,
                                          total, suivi)
    finally:
        shutil.rmtree(plateforme.dossier_temporaire() / f"processus-{os.getpid()}", ignore_errors=True)
    bilan.code = code_de_retour(bilan, fournisseur)
    return bilan.code


def code_de_retour(bilan, fournisseur) -> int:
    """EX-12 : 0 si aucun fichier en erreur ; 3 si le moteur OCR manque et qu'aucun fichier
    n'a pu être traité faute de moteur (aucun fichier pris en charge traité avec succès) ;
    1 dans les autres cas d'erreur."""
    erreurs = [l for l in bilan.lignes if l.statut == "erreur"]
    if not erreurs and not bilan.messages:
        return SUCCES
    if fournisseur.indisponible:
        message = ocr.message_moteur_absent()
        faute_de_moteur = [l for l in erreurs if l.message.startswith(message)]
        reussis = [l for l in bilan.lignes if l.action in ("traite", "ignore_a_jour")
                   and l.statut not in ("erreur", "non_pris_en_charge")]
        if faute_de_moteur and not reussis:
            return PREREQUIS_MANQUANT
    return ERREUR_FICHIER


def _traiter_groupe(groupe, options, parametres, traiteurs, arret, moteur, bilan, rang, total,
                    suivi) -> tuple[int, int]:
    dossier_ocr = groupe.dossier_ocr
    try:
        creer_dossier_ocr(dossier_ocr)
    except OSError:
        message = _message_parent_non_inscriptible(groupe.parent)
        bilan.messages.append(message)
        print(f"ocr-md : {message}", file=sys.stderr)
        return rang + len(groupe.elements), total
    bilan.dossiers_ocr.append(dossier_ocr)
    nettoyes = sorties.nettoyer_temporaires(dossier_ocr)
    journal = rapport.Journal(dossier_ocr)
    try:
        journal.info(f"--- ocr-md {__version__} : début du lot ({len(groupe.elements)} fichier(s) dans ce dossier)")
        journal.info(f"options : sortie={options.sortie} refaire_ocr={options.refaire_ocr} "
                     f"pages={','.join(map(str, options.pages)) or '-'} forcer={options.forcer} "
                     f"tableaux={options.tableaux}")
        journal.info("paramètres : " + " ".join(f"{k}={v}" for k, v in sorted(parametres.valeurs.items())))
        if correctifs.ETAT.applique:
            journal.info(correctifs.ETAT.raison)
        else:
            journal.avertissement(f"AVERTISSEMENT : {correctifs.ETAT.raison}")
        if parametres.sources:
            journal.info("fichiers de configuration lus : " + " ; ".join(parametres.sources))
        if nettoyes:
            journal.info(f"{nettoyes} fichier(s) temporaire(s) d'une exécution interrompue supprimé(s)")
        lignes = rapport.lire(dossier_ocr)
        for relatif in groupe.introuvables:
            ligne = rapport.LigneRapport(relatif, inventaire.type_par_extension(groupe.parent / relatif)[0],
                                         statut="erreur", message=MESSAGE_INTROUVABLE, date_traitement=_maintenant())
            lignes[relatif] = ligne
            bilan.lignes.append(ligne)
        if groupe.introuvables:
            _ecrire_rapports(groupe, lignes, parametres)
        etat = {"rang": rang, "total": total}
        presents: set[str] = set()

        def enregistrer(ligne):
            for avertissement in bilan.avertissements:
                ligne.message = f"{ligne.message} ; {avertissement}" if ligne.message else avertissement
            lignes[ligne.chemin_relatif] = ligne
            bilan.lignes.append(ligne)
            _ecrire_rapports(groupe, lignes, parametres)

        def traiter(element):
            etat["rang"] += 1
            suivi.fichier(etat["rang"], etat["total"], element.relatif)
            presents.add(element.relatif)
            if element.type != "zip":
                enregistrer(_traiter_element(element, lignes.get(element.relatif), options, parametres, traiteurs,
                                             arret, moteur, journal, suivi=suivi))
                return
            developpement, ligne = _developper_archive(element, lignes.get(element.relatif), parametres, arret,
                                                       journal)
            if ligne is not None:
                enregistrer(ligne)
                return
            if lignes.pop(element.relatif, None) is not None:  # ligne d'un échec précédent de l'archive
                _ecrire_rapports(groupe, lignes, parametres)
            try:
                etat["total"] += len(developpement.elements)
                for contenu in developpement.elements:
                    traiter(contenu)
            finally:
                developpement.nettoyer()

        for element in groupe.elements:
            traiter(element)
        rang, total = etat["rang"], etat["total"]
        _signaler_sources_disparues(groupe, lignes, journal, presents)
        b = rapport.bilan(l for l in bilan.lignes if l.chemin_relatif in lignes)
        journal.info(f"fin du lot : {b}")
        faites = [l for l in bilan.lignes if l.action == "traite" and l.duree_s and l.pages]
        if faites:  # EX-57 : débit global
            pages, duree = sum(l.pages for l in faites), sum(l.duree_s for l in faites)
            journal.info(f"débit : {pages} page(s) en {duree:.1f} s, soit {60 * pages / duree:.1f} pages par minute")
    finally:
        journal.fermer()
    return rang, total


def _ecrire_rapports(groupe, lignes, parametres) -> None:
    """Rapport puis _AVERTISSEMENTS.md, régénéré depuis les lignes du rapport (EX-48, EX-61)."""
    rapport.ecrire(groupe.dossier_ocr, lignes, parametres.tentatives_ecriture, parametres.intervalle_tentatives_s)
    avertissements.ecrire_avertissements(groupe.dossier_ocr, groupe.parent, lignes.values(),
                                         parametres.tentatives_ecriture, parametres.intervalle_tentatives_s)


def _signaler_sources_disparues(groupe, lignes, journal, presents) -> None:
    for relatif in lignes:
        if relatif in presents:
            continue
        if not os.path.lexists(sorties.chemin_systeme(groupe.parent / relatif)):
            journal.info(f"source disparue, sorties conservées : {relatif}")


def _developper_archive(element, precedente, parametres, arret, journal):
    """Archive .zip : (développement, None) si son contenu est à traiter ; (None, ligne du
    rapport) si l'archive est annulée, en erreur ou non prise en charge."""
    if arret.is_set():
        ligne = _ligne_precedente_ou_nouvelle(element, precedente)
        ligne.action, ligne.message, ligne.duree_s = "annule", MESSAGE_ANNULE, None
        return None, ligne
    try:
        inventaire.controler(element, parametres.delai_hydratation_s)
        developpement = archives.developper(element, parametres.archive_taille_max_mo, element.profondeur)
    except archives.NonPrisEnCharge as e:
        journal.info(f"{element.relatif} : archive non prise en charge : {e}")
        return None, rapport.LigneRapport(element.relatif, element.type, statut="non_pris_en_charge",
                                          message=str(e), date_traitement=_maintenant())
    except ErreurFichier as e:
        journal.info(f"{element.relatif} : erreur : {e}")
        return None, rapport.LigneRapport(element.relatif, element.type, statut="erreur", message=str(e),
                                          date_traitement=_maintenant())
    except Exception as e:  # EX-60
        journal.erreur(element.relatif, e)
        return None, rapport.LigneRapport(
            element.relatif, element.type, statut="erreur", date_traitement=_maintenant(),
            message=f"erreur inattendue ({type(e).__name__}) : détails dans {rapport.NOM_JOURNAL}")
    journal.info(f"{element.relatif} : archive extraite hors de la source, {len(developpement.elements)} fichier(s)")
    return developpement, None


def _ligne_precedente_ou_nouvelle(element, precedente):
    if precedente is not None:
        return dataclasses.replace(precedente)
    return rapport.LigneRapport(element.relatif, element.type)


def _ligne_erreur(element, precedente, prevues, message, debut):
    """Ligne d'un fichier en erreur. Sorties d'un traitement précédent : supprimées si la
    source est plus récente qu'elles, conservées et signalées sinon (EX-52)."""
    existantes = {k: p for k, p in prevues.items() if os.path.exists(sorties.chemin_systeme(p))}
    noms: tuple[str, ...] = ()
    if existantes:
        if sorties.source_plus_recente(element, existantes):
            sorties.supprimer_sorties(existantes)
        else:
            noms = tuple(p.name for p in existantes.values())
            date = precedente.date_traitement if precedente and precedente.date_traitement else                 sorties.date_sorties(existantes)
            message = f"{message} ; sorties précédentes conservées (traitement du {date})"
    return rapport.LigneRapport(element.relatif, element.type, statut="erreur", message=message, sorties=noms,
                                duree_s=time.perf_counter() - debut, date_traitement=_maintenant())


def _traiter_element(element, precedente, options, parametres, traiteurs, arret, moteur, journal, suivi=None):
    if not element.pris_en_charge:
        journal.info(f"{element.relatif} : non pris en charge")
        return rapport.LigneRapport(element.relatif, "autre", statut="non_pris_en_charge", message=element.message,
                                    date_traitement=_maintenant())
    if arret.is_set():
        ligne = _ligne_precedente_ou_nouvelle(element, precedente)
        ligne.action, ligne.message, ligne.duree_s = "annule", MESSAGE_ANNULE, None
        return ligne
    prevues = sorties.sorties_prevues(element, options.sortie)
    if not prevues:  # fichier Office avec --sortie pdf (EX-20)
        return rapport.LigneRapport(element.relatif, element.type, statut="natif", message=MESSAGE_PDF_OFFICE,
                                    origine_texte="texte natif du document", date_traitement=_maintenant())
    concerne = options.forcer or (options.refaire_ocr is not None and element.type in ("pdf", "image"))
    if not concerne and precedente is not None and sorties.a_jour(element, prevues):
        ligne = dataclasses.replace(precedente, action="ignore_a_jour", duree_s=None)
        journal.info(f"{element.relatif} : sorties à jour, ignoré")
        return ligne
    ecrivain = sorties.Ecrivain(parametres.tentatives_ecriture, parametres.intervalle_tentatives_s)
    contexte = Contexte(element, prevues, options, parametres, ecrivain, journal, arret, moteur, suivi)
    debut = time.perf_counter()
    try:
        inventaire.controler(element, parametres.delai_hydratation_s)
        resultat = traiteurs[element.type].traiter(contexte)
        noms = ecrivain.valider()
    except Annulation:
        ecrivain.abandonner()
        ligne = _ligne_precedente_ou_nouvelle(element, precedente)
        ligne.action, ligne.message, ligne.duree_s = "annule", MESSAGE_ANNULE, None
        journal.info(f"{element.relatif} : annulé")
        return ligne
    except ErreurFichier as e:
        ecrivain.abandonner()
        journal.info(f"{element.relatif} : erreur : {e}")
        return _ligne_erreur(element, precedente, prevues, str(e), debut)
    except Exception as e:  # EX-60 : jamais d'arrêt du lot
        ecrivain.abandonner()
        journal.erreur(element.relatif, e)
        message = f"erreur inattendue ({type(e).__name__}) : détails dans {rapport.NOM_JOURNAL}"
        return _ligne_erreur(element, precedente, prevues, message, debut)
    finally:
        ecrivain.abandonner()
    duree = time.perf_counter() - debut
    journal.info(f"{element.relatif} : {resultat.statut}, {resultat.pages} page(s), "
                 f"OCR {list(resultat.pages_ocr)}, douteuses {list(resultat.pages_douteuses)}, {duree:.1f} s")
    return rapport.LigneRapport(
        element.relatif, element.type, pages=resultat.pages, statut=resultat.statut, pages_ocr=resultat.pages_ocr,
        pages_douteuses=resultat.pages_douteuses, motif_douteux=resultat.motifs, qualite_image=resultat.qualite_image,
        pages_texte_simple=resultat.pages_texte_simple,
        revisions_commentaires=resultat.revisions_commentaires, origine_texte=resultat.origine,
        sorties=tuple(noms), duree_s=duree, date_traitement=_maintenant(), message=resultat.message)
