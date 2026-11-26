"""Traitement des PDF et des images : contrôles d'ouverture (EX-21), classification des
pages, OCR des seules pages-images, calque invisible, PDF consultable (EX-29 à EX-33),
PDF temporaire en sortie Markdown seule (EX-28).

Le Markdown produit ici est provisoire (texte du PDF consultable avec repères de page) ;
la conversion par PyMuPDF4LLM, le front matter et les avertissements arrivent aux jalons
6 et 7.
"""

import dataclasses
import math
import os
import pathlib
import shutil
import sys
import uuid

import pymupdf
from PIL import Image

from .. import analyse_pdf, avertissements, calque, images, plateforme
from ..inventaire import ErreurFichier
from ..sorties import LONGUEUR_SURE, chemin_systeme
from . import ResultatTraitement, Traiteur

MESSAGE_PROTEGE = "PDF protégé par mot de passe"
MESSAGE_ENDOMMAGE = "PDF endommagé"
MESSAGE_SIGNE = ("la copie produite dans _OCR ne conserve pas la validité de la signature ; "
                 "l'original signé reste la référence")
MOTIF_REPARE = "pdf_repare"

# Les messages de MuPDF ne doivent pas encombrer la console : ils sont relus au besoin.
pymupdf.TOOLS.mupdf_display_errors(False)


@dataclasses.dataclass(frozen=True)
class InfoPdf:
    pages: int
    signe: bool
    repare: bool
    pages_avec_contenu: int

    @property
    def partiellement_recupere(self) -> bool:
        """PDF réparé à l'ouverture dont une partie seulement des pages a un contenu."""
        return self.repare and self.pages_avec_contenu < self.pages


def message_repare(info: "InfoPdf") -> str:
    return (f"PDF endommagé et réparé : {info.pages_avec_contenu} pages sur {info.pages} récupérées, "
            "contenu possiblement incomplet")


def _page_vide(page) -> bool:
    return not page.get_text("text").strip() and not page.get_images() and not page.get_drawings()


def _chemin_long(chemin) -> bool:
    return sys.platform == "win32" and len(os.path.abspath(str(chemin))) >= LONGUEUR_SURE


def ouvrir(chemin: pathlib.Path):
    """Ouvre le PDF en lecture ; lève ErreurFichier « protégé » ou « endommagé ».
    Un chemin long est d'abord recopié sous un chemin court (EX-63)."""
    try:
        if _chemin_long(chemin):
            with open(chemin_systeme(chemin), "rb") as f:
                doc = pymupdf.open(stream=f.read(), filetype="pdf")
        else:
            doc = pymupdf.open(chemin_systeme(chemin), filetype="pdf")
    except Exception:
        raise ErreurFichier(MESSAGE_ENDOMMAGE) from None
    if doc.needs_pass:
        doc.close()
        raise ErreurFichier(MESSAGE_PROTEGE)
    return doc


def controler_document(doc) -> InfoPdf:
    """Endommagé si : aucune page, page illisible, ou document réparé à l'ouverture dont
    aucune page ne contient plus ni texte, ni image, ni dessin (fichier tronqué). Une
    réparation qui laisse au moins une page lisible est admise ; le fichier est signalé
    (motif pdf_repare) si des pages ont été perdues (EX-21)."""
    if doc.page_count == 0:
        raise ErreurFichier(MESSAGE_ENDOMMAGE)
    vides = 0
    for page in doc:
        try:
            vides += _page_vide(page)
        except Exception:
            raise ErreurFichier(MESSAGE_ENDOMMAGE) from None
    if doc.is_repaired and vides == doc.page_count:
        raise ErreurFichier(MESSAGE_ENDOMMAGE)
    return InfoPdf(doc.page_count, doc.get_sigflags() >= 1, doc.is_repaired, doc.page_count - vides)


def controler_pdf(chemin: pathlib.Path) -> InfoPdf:
    doc = ouvrir(chemin)
    try:
        return controler_document(doc)
    finally:
        doc.close()


# ------------------------------------------------------------------------------ OCR d'une page
def rendre_page(page, dpi: int, dimension_max: int | None, journal=None):
    """Image en niveaux de gris de la page affichée ; résolution réduite si l'image dépasse
    la dimension maximale du moteur (EX-25)."""
    plus_grand_cote_pt = max(page.rect.width, page.rect.height)
    if dimension_max and plus_grand_cote_pt * dpi / 72 > dimension_max:
        reduit = math.floor(dimension_max * 72 / plus_grand_cote_pt)
        if journal:
            journal.info(f"page {page.number + 1} : résolution réduite de {dpi} à {reduit} dpi "
                         f"(dimension maximale du moteur : {dimension_max} px)")
        dpi = reduit
    pix = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY)
    return Image.frombytes("L", (pix.width, pix.height), pix.samples), dpi


def enregistrer(doc, chemin: str) -> None:
    """Enregistre le PDF consultable sans recompresser les images (EX-29). Un document
    réparé à l'ouverture peut refuser le nettoyage des objets inutilisés (arbre des pages
    incohérent) : il est alors enregistré sans nettoyage."""
    options = dict(deflate=False, deflate_fonts=True, deflate_images=False, no_new_id=True)
    try:
        octets = doc.tobytes(garbage=1, **options)
    except Exception:
        octets = doc.tobytes(garbage=0, **options)
    with open(chemin, "wb") as f:
        f.write(octets)


@dataclasses.dataclass(frozen=True)
class ResumeOcr:
    """Ce que l'évaluation de la qualité (EX-35, EX-36) retient d'une page reconnue. Le
    résultat complet du moteur (mots, boîtes) n'est pas conservé : sur un document de 500
    pages, il occupait environ 40 Ko par page jusqu'à la fin du fichier (EX-59)."""
    texte: str
    caracteres: int                          # caractères hors espaces
    confiance_moyenne: float | None          # pondérée par la longueur du texte
    part_confiance_basse: float | None       # part du texte sous le seuil confiance_basse
    angle_texte: float | None = None


def resumer(resultat, confiance_basse: float) -> ResumeOcr:
    total = pondere = bas = 0
    avec_confiance = False
    for ligne in resultat.lignes:
        for mot in ligne.mots:
            n = sum(1 for c in mot.texte if not c.isspace())
            total += n
            confiance = mot.confiance if mot.confiance is not None else ligne.confiance
            if confiance is not None:
                avec_confiance = True
                pondere += confiance * n
                bas += n if confiance < confiance_basse else 0
    if not avec_confiance or not total:
        return ResumeOcr(resultat.texte, total, None, None, resultat.angle_texte)
    return ResumeOcr(resultat.texte, total, pondere / total, bas / total, resultat.angle_texte)


@dataclasses.dataclass
class Traitement:
    """Résultat d'un document, conservé pour l'évaluation de la qualité (jalon 7)."""
    analyses: list
    categories_finales: list
    pages_ocr: list
    resumes_ocr: dict  # numéro de page -> ResumeOcr


def reconnaitre_pages(doc, ctx) -> Traitement:
    """OCR des seules pages `image`, une seule fois, et écriture du calque (EX-24)."""
    p = ctx.parametres
    analyses = analyse_pdf.analyser(doc, p)
    finales, pages_ocr, resultats = [], [], {}
    for a in analyses:
        ctx.verifier_arret()
        if a.categorie != "image":
            finales.append(a.categorie)
            continue
        moteur = ctx.moteur.obtenir()
        if not pages_ocr:
            ctx.journal.info(f"{ctx.element.relatif} : OCR par {moteur.description()}, langue {p.langue_ocr} "
                             f"(secondaire {p.langue_ocr_secondaire}), {p.ocr_dpi} dpi")
        page = doc[a.numero - 1]
        image, dpi = rendre_page(page, p.ocr_dpi, moteur.dimension_max(), ctx.journal)
        resultat = moteur.reconnaitre(image)
        del image
        # Le cache de MuPDF garde les images décodées : on le vide après chaque page pour
        # que la mémoire ne croisse pas avec le nombre de pages (EX-59).
        pymupdf.TOOLS.store_shrink(100)
        calque.ecrire_calque(page, resultat)
        resultats[a.numero] = resumer(resultat, p.confiance_basse)
        del resultat
        pages_ocr.append(a.numero)
        finales.append("ocr")
    ctx.journal.info(f"{ctx.element.relatif} : pages " + " ".join(f"{a.numero}={a.categorie}" for a in analyses))
    return Traitement(analyses, finales, pages_ocr, resultats)


def markdown_provisoire(chemin_pdf: str) -> str:
    """Jalon 4 : texte du PDF consultable avec repères de page ; remplacé au jalon 6."""
    doc = pymupdf.open(chemin_pdf)
    morceaux = []
    for page in doc:
        texte = page.get_text().strip()
        morceaux.append(f"<!-- page {page.number + 1} -->\n\n{texte or '*(page sans texte exploitable)*'}\n")
    doc.close()
    return "\n".join(morceaux)


def dossier_temporaire_processus() -> pathlib.Path:
    return plateforme.dossier_temporaire() / f"processus-{os.getpid()}"


class TraiteurPdf(Traiteur):
    """PDF (et, par héritage, images) : PDF consultable et Markdown depuis ce PDF."""

    source_est_pdf = True

    def ouvrir_document(self, ctx):
        doc = ouvrir(ctx.element.source)
        try:
            info = controler_document(doc)
        except ErreurFichier:
            doc.close()
            raise
        return doc, info

    def traiter(self, ctx) -> ResultatTraitement:
        doc, info = self.ouvrir_document(ctx)
        try:
            t = reconnaitre_pages(doc, ctx)
            douteuses, motifs, messages = [], [], []
            if info is not None and info.partiellement_recupere:
                douteuses = list(range(1, doc.page_count + 1))
                motifs.append(MOTIF_REPARE)
                messages.append(message_repare(info))
            if info is not None and info.signe:
                messages.append(MESSAGE_SIGNE)
            statut = analyse_pdf.statut(t.categories_finales, douteuses)
            origine = analyse_pdf.origine(t.categories_finales)
            moteur_nom = ctx.moteur.nom_si_utilise() if t.pages_ocr else "aucun"
            copie_identique = self.source_est_pdf and not t.pages_ocr and not douteuses
            if not copie_identique:
                doc.set_metadata(avertissements.metadonnees_pdf(
                    doc.metadata, pages_douteuses=douteuses, pages_ocr=t.pages_ocr, origine=origine,
                    moteur=moteur_nom))
                if t.pages_ocr:
                    doc.subset_fonts()
            self._ecrire_sorties(doc, ctx, copie_identique)
            return ResultatTraitement(statut, pages=doc.page_count, pages_ocr=tuple(t.pages_ocr),
                                      pages_douteuses=tuple(douteuses), motifs=tuple(motifs), origine=origine,
                                      message=" ; ".join(messages))
        finally:
            doc.close()

    def _ecrire_sorties(self, doc, ctx, copie_identique: bool) -> None:
        source = ctx.element.source

        def produire_pdf(chemin):
            if copie_identique:  # EX-32 : copie octet pour octet
                shutil.copyfile(chemin_systeme(source), chemin)
            else:
                enregistrer(doc, chemin)

        chemin_pdf = None
        if "pdf" in ctx.prevues:
            ctx.ecrivain.preparer(ctx.prevues["pdf"], produire_pdf)
            chemin_pdf = ctx.ecrivain.dernier_temporaire()
        if "md" not in ctx.prevues:
            return
        temporaire = None
        try:
            if chemin_pdf is None:  # EX-28 : PDF consultable intermédiaire, supprimé ensuite
                dossier = dossier_temporaire_processus()
                dossier.mkdir(parents=True, exist_ok=True)
                temporaire = str(dossier / f"{uuid.uuid4().hex}.pdf")
                produire_pdf(temporaire)
                chemin_pdf = temporaire
            ctx.verifier_arret()
            texte = markdown_provisoire(chemin_pdf)
            ctx.ecrivain.preparer(ctx.prevues["md"],
                                  lambda c: open(c, "w", encoding="utf-8", newline="\n").write(texte))
        finally:
            if temporaire:
                try:
                    os.remove(temporaire)
                except OSError:
                    pass


class TraiteurImage(TraiteurPdf):
    """Image : assemblée en PDF image (EX-34), puis traitée comme un PDF."""

    source_est_pdf = False

    def ouvrir_document(self, ctx):
        return images.image_vers_pdf(ctx.element.source), None
