"""Traitement des PDF et des images : contrôles d'ouverture (EX-21), classification des
pages, OCR des seules pages-images, calque invisible, PDF consultable (EX-29 à EX-33),
PDF temporaire en sortie Markdown seule (EX-28).

Le Markdown est produit par PyMuPDF4LLM depuis le PDF consultable (module markdown_pdf) ;
le front matter et les avertissements arrivent au jalon 7.
"""

import dataclasses
import io
import logging
import math
import os
import pathlib
import shutil
import sys
import time
import uuid

import pymupdf
from PIL import Image, ImageStat

from .. import analyse_pdf, avertissements, calque, images, markdown_pdf, plateforme, qualite
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
    par_pypdf: bool = False  # MuPDF n'a pas su l'ouvrir : pages récupérées par pypdf

    @property
    def partiellement_recupere(self) -> bool:
        """PDF réparé à l'ouverture dont une partie seulement des pages a un contenu, ou PDF
        dont les pages ont été récupérées par pypdf (toujours signalé)."""
        return self.repare and (self.par_pypdf or self.pages_avec_contenu < self.pages)


def message_repare(info: "InfoPdf") -> str:
    par = " par pypdf" if info.par_pypdf else ""
    return (f"PDF endommagé et réparé : {info.pages_avec_contenu} pages sur {info.pages} récupérées{par}, "
            "contenu possiblement incomplet")


def recuperer_par_pypdf(chemin: pathlib.Path):
    """Dernier recours pour un PDF que MuPDF juge endommagé (recette du 27/11/2026) : pypdf,
    en mode tolérant, relit l'arbre des pages et recopie chaque page lisible dans un PDF neuf,
    ouvert ensuite par MuPDF. Une page illisible devient une page blanche (la numérotation est
    conservée). Renvoie (document, InfoPdf) ou None si rien n'est récupérable."""
    import pypdf
    logging.getLogger("pypdf").setLevel(logging.CRITICAL)  # avertissements de lecture : hors console
    try:
        with open(chemin_systeme(chemin), "rb") as f:
            lecteur = pypdf.PdfReader(io.BytesIO(f.read()), strict=False)
        if lecteur.is_encrypted:
            return None
        total = len(lecteur.pages)
    except Exception:
        return None
    ecrivain = pypdf.PdfWriter()
    recopiees = 0
    for i in range(total):
        try:
            ecrivain.add_page(lecteur.pages[i])
            recopiees += 1
        except Exception:
            ecrivain.add_blank_page(595, 842)
    if not recopiees:
        return None
    try:
        tampon = io.BytesIO()
        ecrivain.write(tampon)
        doc = pymupdf.open(stream=tampon.getvalue(), filetype="pdf")
    except Exception:
        return None
    try:
        avec_contenu = sum(1 for page in doc if not _page_vide(page))
    except Exception:
        doc.close()
        return None
    if not avec_contenu:
        doc.close()
        return None
    return doc, InfoPdf(doc.page_count, False, True, avec_contenu, par_pypdf=True)


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


def reconstruire(doc, dpi: int):
    """Document sain reconstruit page par page à partir d'un PDF réparé à l'ouverture, dont
    l'arbre des pages reste incohérent : sans cela, le PDF consultable enregistré ne se
    relirait pas (conversion Markdown). Une page qui ne se recopie pas est rendue en image
    (elle sera reconnue par OCR) ; si même son rendu échoue, elle devient une page blanche
    de même taille. La numérotation des pages est conservée."""
    neuf = pymupdf.open()
    for i in range(doc.page_count):
        try:
            neuf.insert_pdf(doc, from_page=i, to_page=i)
            continue
        except Exception:
            pass
        try:
            page = doc[i]
            largeur, hauteur = page.rect.width, page.rect.height
            image = page.get_pixmap(dpi=dpi).tobytes("jpeg", jpg_quality=90)
            nouvelle = neuf.new_page(width=largeur, height=hauteur)
            nouvelle.insert_image(nouvelle.rect, stream=image)
        except Exception:
            neuf.new_page(width=595, height=842)
    neuf.set_metadata({k: v for k, v in (doc.metadata or {}).items() if v})
    return neuf


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
    ecart_type: float | None = None          # niveaux de gris de l'image (page non blanche ?)
    qualite_image: object | None = None      # qualite.QualiteImage, mesurée avant l'OCR


def resumer(resultat, confiance_basse: float, ecart_type: float | None = None, qualite_image=None) -> ResumeOcr:
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
        return ResumeOcr(resultat.texte, total, None, None, resultat.angle_texte, ecart_type, qualite_image)
    return ResumeOcr(resultat.texte, total, pondere / total, bas / total, resultat.angle_texte, ecart_type,
                     qualite_image)


def resolution_effective(page) -> int | None:
    """Résolution (dpi) de la plus grande image de la page, calculée sur l'aire (pixels de
    l'image rapportés à la surface occupée), donc indépendante d'une rotation à l'insertion
    (photo redressée selon EXIF) ; None si la page ne porte pas d'image."""
    meilleure, aire = None, 0.0
    for info in page.get_image_info():
        r = pymupdf.Rect(info["bbox"])
        if r.is_empty or not info.get("width") or not info.get("height") or r.get_area() <= aire:
            continue
        aire = r.get_area()
        meilleure = 72 * (info["width"] * info["height"] / aire) ** 0.5
    return None if meilleure is None else int(round(meilleure))


@dataclasses.dataclass
class Traitement:
    """Résultat d'un document : catégories finales, pages reconnues, verdicts de qualité."""
    analyses: list
    categories_finales: list          # « native », « ocr », « couche_existante », « vide »
    pages_ocr: list                   # pages reconnues par l'outil
    motifs: dict                      # page douteuse -> motifs
    refaites: list                    # pages dont l'OCR a été refait (EX-39)
    durees: dict
    images: dict = dataclasses.field(default_factory=dict)  # page reconnue -> qualite.VerdictImage

    @property
    def causes_image(self) -> dict:
        """Pages douteuses par l'image (motif image_faible_qualite) -> causes en clair."""
        return {n: list(v.causes) for n, v in self.images.items() if v.douteuse}

    @property
    def images_mediocres(self) -> dict:
        """Pages reconnues sur une image médiocre mais non douteuses par l'image -> causes
        abrégées, pour le repère léger de la section 11.4."""
        return {n: qualite.causes_abregees(v.causes) for n, v in self.images.items()
                if v.niveau == qualite.IMAGE_MEDIOCRE and not v.douteuse}

    @property
    def qualite_image(self) -> str | None:
        """« mediocre » si au moins une page reconnue a une image médiocre, « bonne » sinon ;
        None si l'outil n'a reconnu aucune page."""
        if not self.images:
            return None
        if any(v.niveau == qualite.IMAGE_MEDIOCRE for v in self.images.values()):
            return qualite.IMAGE_MEDIOCRE
        return qualite.IMAGE_BONNE


def _ecart_type_page(page) -> float:
    pix = page.get_pixmap(dpi=50, colorspace=pymupdf.csGRAY)
    return ImageStat.Stat(Image.frombytes("L", (pix.width, pix.height), pix.samples)).stddev[0]


def evaluer_page(page, texte: str, ctx, lexique, resume: ResumeOcr | None = None,
                 images: dict | None = None) -> list[str]:
    """Verdict d'une page (EX-35, EX-36) : liste des motifs, vide si la page est bonne.
    Seuls des nombres sont journalisés."""
    p = ctx.parametres
    surface = page.rect.width * page.rect.height * analyse_pdf.CM2_PAR_PT2
    ind = qualite.calculer(texte, lexique, surface)
    ecart = resume.ecart_type if resume and resume.ecart_type is not None else None
    if ecart is None and (ind.densite is not None and ind.densite < p.densite_min or (resume and not resume.caracteres)):
        ecart = _ecart_type_page(page)
    non_blanche = ecart is not None and ecart > p.page_blanche_ecart_type_max
    origine = qualite.ORIGINE_COUCHE if resume is None else ctx.moteur.nom_si_utilise()
    motifs = qualite.motifs_lexicaux(ind, p, non_blanche, origine)
    if resume is not None:
        if not resume.caracteres and non_blanche:
            motifs.insert(0, "aucun_texte_reconnu")
        motifs += qualite.motifs_confiance(resume.confiance_moyenne, resume.part_confiance_basse, p)
        q = resume.qualite_image
        v = qualite.verdict_image(q, ind, p, origine)
        if v is not None:
            if v.douteuse:
                motifs.append(qualite.MOTIF_IMAGE)
            if images is not None:
                images[page.number + 1] = v
            # Format relu par tests/recalibrage.py : ne pas le modifier sans adapter le script.
            ctx.journal.info(f"{ctx.element.relatif} : page {page.number + 1} : image : résolution "
                             f"{q.resolution_dpi} dpi, part de gris {q.part_gris}, contraste {q.contraste}, "
                             f"bruit {q.bruit} : {v.niveau}" + (f" ({', '.join(v.causes)})" if v.causes else "")
                             + (" : douteuse par l'image" if v.douteuse else ""))
    confiance = "" if resume is None or resume.confiance_moyenne is None else f", confiance {resume.confiance_moyenne:.2f}"
    ctx.journal.info(
        f"{ctx.element.relatif} : page {page.number + 1} : mots {ind.mots}, évaluables {ind.mots_evaluables}, "
        f"inconnus {ind.taux_mots_inconnus:.3f}, aberrants {ind.taux_caracteres_aberrants:.3f}, "
        f"fragmentés {ind.taux_mots_fragmentes:.3f}, mélanges {ind.taux_melange_chiffres_lettres:.3f}, "
        f"densité {ind.densite:.3f}{confiance} : {'douteuse (' + ' '.join(motifs) + ')' if motifs else 'bonne'}")
    return motifs


def remplacer_par_image(doc, index: int, dpi: int) -> None:
    """Remplace la page par son image rendue (EX-39) : la couche texte d'origine ne subsiste
    pas dans la copie. Image en JPEG (qualité 90), dimensions et orientation affichées."""
    page = doc[index]
    largeur, hauteur = page.rect.width, page.rect.height
    image = page.get_pixmap(dpi=dpi).tobytes("jpeg", jpg_quality=90)
    doc.delete_page(index)
    nouvelle = doc.new_page(pno=index, width=largeur, height=hauteur)
    nouvelle.insert_image(nouvelle.rect, stream=image)


def pages_a_refaire(options, categories: dict, motifs: dict, journal, relatif: str) -> set[int]:
    """Pages dont l'OCR est (re)fait à la demande (EX-39). Les pages `image` sont reconnues
    dans tous les cas."""
    if options.refaire_ocr == "douteuses":
        return {n for n, c in categories.items() if c == "couche_existante" and motifs.get(n)}
    if options.refaire_ocr == "tout":
        return {n for n, c in categories.items() if c == "couche_existante"}
    if options.refaire_ocr == "pages":
        hors = [n for n in options.pages if n not in categories]
        if hors:
            journal.avertissement(f"{relatif} : pages demandées hors du document, ignorées : {hors}")
        return {n for n in options.pages if n in categories}
    return set()


def reconnaitre_pages(doc, ctx) -> Traitement:
    """Évalue les couches existantes, puis reconnaît, une seule fois, les pages `image` et
    les pages à refaire, en écrivant le calque ; évalue chaque page reconnue (EX-24, EX-35
    à EX-39)."""
    p = ctx.parametres
    lexique = qualite.Lexique(p.lexique_complementaire)
    analyses = analyse_pdf.analyser(doc, p)
    categories = {a.numero: a.categorie for a in analyses}
    motifs = {}
    for a in analyses:
        if a.categorie == "couche_existante":
            m = evaluer_page(doc[a.numero - 1], doc[a.numero - 1].get_text(), ctx, lexique)
            if m:
                motifs[a.numero] = m
    refaites = sorted(pages_a_refaire(ctx.options, categories, motifs, ctx.journal, ctx.element.relatif))
    a_reconnaitre = sorted({n for n, c in categories.items() if c == "image"} | set(refaites))
    pages_ocr = []
    verdicts_image: dict = {}
    durees = {"rendu": 0.0, "ocr": 0.0, "calque": 0.0}
    for numero in a_reconnaitre:
        ctx.verifier_arret()
        if ctx.suivi is not None:
            ctx.suivi.page(numero, doc.page_count)
        moteur = ctx.moteur.obtenir()
        if not pages_ocr:
            ctx.journal.info(f"{ctx.element.relatif} : OCR par {moteur.description()}, langue {p.langue_ocr} "
                             f"(secondaire {p.langue_ocr_secondaire}), {p.ocr_dpi} dpi")
        resolution = resolution_effective(doc[numero - 1])  # image d'origine, avant remplacement
        if numero in refaites and categories[numero] != "image":
            remplacer_par_image(doc, numero - 1, p.ocr_dpi)
            motifs.pop(numero, None)
        page = doc[numero - 1]
        t0 = time.perf_counter()
        image, dpi = rendre_page(page, p.ocr_dpi, moteur.dimension_max(), ctx.journal)
        ecart = ImageStat.Stat(image).stddev[0]
        mesure_image = qualite.mesurer_image(image, resolution)
        t1 = time.perf_counter()
        resultat = moteur.reconnaitre(image)
        t2 = time.perf_counter()
        del image
        # Le cache de MuPDF garde les images décodées : on le vide après chaque page pour
        # que la mémoire ne croisse pas avec le nombre de pages (EX-59).
        pymupdf.TOOLS.store_shrink(100)
        calque.ecrire_calque(page, resultat)
        t3 = time.perf_counter()
        durees["rendu"] += t1 - t0
        durees["ocr"] += t2 - t1
        durees["calque"] += t3 - t2
        resume = resumer(resultat, p.confiance_basse, ecart, mesure_image)
        del resultat
        m = evaluer_page(page, resume.texte, ctx, lexique, resume, verdicts_image)
        if m:
            motifs[numero] = m
        categories[numero] = "ocr"
        pages_ocr.append(numero)
    ctx.journal.info(f"{ctx.element.relatif} : pages " + " ".join(f"{a.numero}={a.categorie}" for a in analyses))
    if refaites:
        ctx.journal.info(f"{ctx.element.relatif} : OCR refait pour les pages {refaites}")
    if pages_ocr:  # EX-57 : durée d'OCR par page, ventilée
        n = len(pages_ocr)
        ctx.journal.info(f"{ctx.element.relatif} : durée par page reconnue ({n} page(s)) : rendu "
                         f"{durees['rendu'] / n:.3f} s, reconnaissance {durees['ocr'] / n:.3f} s, "
                         f"calque {durees['calque'] / n:.3f} s")
    finales = [categories[n] for n in sorted(categories)]
    return Traitement(analyses, finales, pages_ocr, motifs, refaites, durees, verdicts_image)


def dossier_temporaire_processus() -> pathlib.Path:
    return plateforme.dossier_temporaire() / f"processus-{os.getpid()}"


def _version(paquet: str) -> str:
    import importlib.metadata
    try:
        return importlib.metadata.version(paquet)
    except importlib.metadata.PackageNotFoundError:
        return "inconnue"


class TraiteurPdf(Traiteur):
    """PDF (et, par héritage, images) : PDF consultable et Markdown depuis ce PDF."""

    source_est_pdf = True
    type_source = "pdf"

    def ouvrir_document(self, ctx):
        try:
            doc = ouvrir(ctx.element.source)
            try:
                info = controler_document(doc)
            except ErreurFichier:
                doc.close()
                raise
        except ErreurFichier as e:
            if str(e) != MESSAGE_ENDOMMAGE:
                raise
            recupere = recuperer_par_pypdf(ctx.element.source)
            if recupere is None:
                raise
            ctx.journal.info(f"{ctx.element.relatif} : PDF illisible par MuPDF, {recupere[1].pages_avec_contenu} "
                             f"page(s) sur {recupere[1].pages} récupérée(s) par pypdf")
            return recupere
        if info.repare:
            sain = reconstruire(doc, ctx.parametres.ocr_dpi)
            doc.close()
            ctx.journal.info(f"{ctx.element.relatif} : PDF réparé à l'ouverture, reconstruit page par page")
            return sain, info
        return doc, info

    def traiter(self, ctx) -> ResultatTraitement:
        doc, info = self.ouvrir_document(ctx)
        try:
            t = reconnaitre_pages(doc, ctx)
            repare = info is not None and info.partiellement_recupere
            motifs = []
            for n in sorted(t.motifs):
                motifs += [m for m in t.motifs[n] if m not in motifs]
            douteuses = sorted(t.motifs)
            messages = []
            if repare:
                douteuses = list(range(1, doc.page_count + 1))
                motifs.insert(0, MOTIF_REPARE)
                messages.append(message_repare(info))
            if info is not None and info.signe:
                messages.append(MESSAGE_SIGNE)
            causes = t.causes_image
            if causes:  # motif image_faible_qualite : causes en clair au rapport
                messages.append("image de faible qualité : " + " ; ".join(
                    f"page {n} ({', '.join(c)})" for n, c in sorted(causes.items())))
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
            couche = [n for n, c in enumerate(t.categories_finales, 1) if c == "couche_existante"]
            pages_reconnues = sorted(set(t.pages_ocr) | set(couche))
            champs = avertissements.champs_document(
                source=ctx.element.relatif, type_source=self.type_source, pages=doc.page_count,
                moteur_md=f"pymupdf4llm {_version('pymupdf4llm')}", moteur_ocr=moteur_nom, pages_ocr=t.pages_ocr,
                pages_douteuses=douteuses, origine=origine, pages_couche_existante=couche, motifs=motifs,
                pages_recuperees=info.pages_avec_contenu if repare else None,
                pages_totales=info.pages if repare else None, qualite_image=t.qualite_image)
            entete = {
                "champs": champs,
                "pages_couche_douteuses": [] if repare else [n for n in douteuses if n in couche],
                "pages_outil_douteuses": [] if repare else [n for n in douteuses if n in t.pages_ocr],
                "repare": (info.pages_avec_contenu, info.pages) if repare else None,
                "images_mediocres": {n: c for n, c in t.images_mediocres.items() if n not in douteuses and c},
            }
            adaptateur = calque.AdaptateurOcr()
            repli: list[int] = []
            self._ecrire_sorties(doc, ctx, copie_identique, pages_reconnues, douteuses, adaptateur, repli, entete)
            if adaptateur.appels:
                ctx.journal.info(f"{ctx.element.relatif} : conversion Markdown, adaptateur OCR appelé sans "
                                 f"reconnaissance pour les pages {adaptateur.appels}")
            return ResultatTraitement(statut, pages=doc.page_count, pages_ocr=tuple(t.pages_ocr),
                                      pages_douteuses=tuple(douteuses), motifs=tuple(motifs), origine=origine,
                                      pages_texte_simple=tuple(repli), qualite_image=t.qualite_image or "",
                                      message=" ; ".join(messages))
        finally:
            doc.close()

    def _ecrire_sorties(self, doc, ctx, copie_identique: bool, pages_reconnues, douteuses, adaptateur, repli,
                        entete) -> None:
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
            corps = markdown_pdf.convertir(chemin_pdf, tableaux=ctx.options.tableaux, pages_ocr=pages_reconnues,
                                           pages_douteuses=douteuses, adaptateur=adaptateur,
                                           images_mediocres=entete["images_mediocres"],
                                           arret=ctx.verifier_arret, pages_repli=repli)
            if repli:
                ctx.journal.info(f"{ctx.element.relatif} : Markdown en texte simple (repli de PV-05) pour les "
                                 f"pages {repli}")
            texte = avertissements.document_markdown(
                entete["champs"], corps, pages_couche_douteuses=entete["pages_couche_douteuses"],
                pages_outil_douteuses=entete["pages_outil_douteuses"], repare=entete["repare"])
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
    type_source = "image"

    def ouvrir_document(self, ctx):
        return images.image_vers_pdf(ctx.element.source), None
