"""Générateur du jeu de test synthétique d'ocr-md (EX-74).

Fabrique, de façon reproductible (graine fixe), un jeu de documents entièrement
synthétiques et son manifeste `manifeste.json`, vérité terrain des tests : type, nombre de
pages, catégorie attendue de chaque page, texte de référence, mots uniques, pages
douteuses attendues, statut attendu, valeurs des tableaux, phrases sentinelles, et
résultat attendu du moteur OCR factice pour chaque image (clé « ocr_factice »).

Usage :
    python tests/donnees/generer.py [SORTIE] [--graine N] [--volumineux] [--chemin-long]
SORTIE vaut par défaut tests/donnees/jeu (non versionné). --volumineux ajoute le PDF de
1 000 pages (fichier 17) ; --chemin-long ajoute l'arborescence à chemin long (fichier 16).
"""

import argparse
import datetime
import io
import json
import os
import pathlib
import re
import sys
import unicodedata
import zipfile

import pymupdf
from PIL import Image, ImageOps

if __package__ in (None, ""):
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tests.donnees import fabrication as fab  # noqa: E402

from ocr_md.ocr.factice import dessiner_marqueur  # noqa: E402

VERSION_MANIFESTE = 1
DPI = 300
DATE_FIXE = datetime.datetime(2026, 11, 26, 9, 0, 0)
CSS_TABLEAUX = ("table{border-collapse:collapse;margin-bottom:12px} "
                "td,th{border:1px solid black;padding:3px;font-size:9px}")

ORIGINE = {
    "natif": "texte natif du document",
    "ocr": "OCR réalisé par l'outil sur l'ensemble du document",
    "mixte": "mixte : texte natif et OCR réalisé par l'outil",
    "couche": "couche OCR fournie par l'expéditeur, non refaite",
}


def reecrire_zip(source: bytes | None, cible: pathlib.Path, modifications: dict, ajouts: dict) -> None:
    """Écrit un paquet Office (zip) : parties de `source` modifiées par les fonctions de
    `modifications` (texte vers texte), puis parties de `ajouts`. Dates fixes (reproductible)."""
    entrees = {}
    if source is not None:
        with zipfile.ZipFile(io.BytesIO(source)) as z:
            for nom in z.namelist():
                donnees = z.read(nom)
                if nom in modifications:
                    donnees = modifications[nom](donnees.decode("utf-8")).encode("utf-8")
                entrees[nom] = donnees
    for nom, texte in ajouts.items():
        entrees[nom] = texte.encode("utf-8")
    noms = sorted(entrees, key=lambda n: (n != "[Content_Types].xml", n))
    with zipfile.ZipFile(cible, "w", zipfile.ZIP_DEFLATED) as z:
        for nom in noms:
            info = zipfile.ZipInfo(nom, date_time=DATE_FIXE.timetuple()[:6])
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, entrees[nom])


class Generateur:
    def __init__(self, racine: pathlib.Path, graine: int):
        self.racine = racine
        self.graine = graine
        self.fichiers = []
        self.ocr_factice = {}
        self.exclus = []
        self._prochain_id = 1

    # -------------------------------------------------------------- outils internes
    def chemin(self, relatif: str) -> pathlib.Path:
        p = self.racine / relatif
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def nouvel_id(self) -> int:
        i = self._prochain_id
        self._prochain_id += 1
        return i

    def enregistrer(self, **entree):
        entree.setdefault("pages_douteuses", [])
        entree.setdefault("sentinelles", [])
        self.fichiers.append(entree)

    def sentinelle(self, n):
        return f"Phrase sentinelle confidentielle numéro {self.graine}-{n:03d}."

    def enregistrer_pdf(self, doc, chemin):
        doc.set_metadata({"producer": "ocr-md jeu de test", "creationDate": "", "modDate": ""})
        doc.save(chemin, garbage=4, deflate=True, no_new_id=True)

    def page_scannee(self, doc, page_source, *, angle=0.0, bruit=4.0, flou=0.0, qualite=80,
                     confiance=0.95, remplacement=None, graine=None):
        """Ajoute au document une page-image issue de page_source ; renvoie son identifiant."""
        ident = self.nouvel_id()
        jpeg, taille, transfo = fab.scanner(page_source, dpi=DPI, angle=angle, bruit=bruit, flou=flou,
                                            qualite_jpeg=qualite, graine=graine or ident, identifiant=ident)
        page = doc.new_page(width=page_source.rect.width, height=page_source.rect.height)
        page.insert_image(page.rect, stream=jpeg)
        self.ocr_factice[str(ident)] = fab.verite_ocr(page_source, DPI, transfo, taille, confiance=confiance,
                                                      angle=-angle if angle else 0.0, remplacement=remplacement)
        return ident, page, transfo, taille

    def document_natif(self, nb_pages, prefixe, total_pied=None, lignes=None):
        """Document natif source (non enregistré) : pages de texte avec mot unique."""
        src = pymupdf.open()
        mots = []
        for i in range(1, nb_pages + 1):
            mot = f"{prefixe}{i:02d}"
            mots.append(mot)
            fab.page_native(src, lignes or (fab.LIGNES_REFERENCE + fab.LIGNES_COURANTES), mot_unique=mot,
                            pied=f"Page {i} sur {total_pied or nb_pages}")
        return src, mots

    # -------------------------------------------------------------- fichiers 1 à 6
    def f01_natif(self):
        doc, mots = self.document_natif(5, "MOTNATIF")
        sent = [self.sentinelle(1)]  # ajoutée en bas de la dernière page
        doc[4].insert_text((72, 760), sent[0], fontname=fab.NOM_POLICE, fontsize=11)
        rel = "pdf/01_natif.pdf"
        self.enregistrer_pdf(doc, self.chemin(rel))
        self.enregistrer(numero="1", chemin=rel, type="pdf", pages=5, statut="natif",
                         origine=ORIGINE["natif"], categories=["native"] * 5,
                         texte_reference=[fab.texte_page(p) for p in doc], mots_uniques=mots,
                         pied_attendu=[f"Page {i} sur 5" for i in range(1, 6)], sentinelles=sent)

    def f02_scanne(self):
        src, mots = self.document_natif(4, "MOTSCAN")
        doc = pymupdf.open()
        ids = []
        for i, p in enumerate(src):
            ident, *_ = self.page_scannee(doc, p, angle=[1.0, -1.5, 2.0, -1.0][i], bruit=6)
            ids.append(ident)
        rel = "pdf/02_scanne.pdf"
        self.enregistrer_pdf(doc, self.chemin(rel))
        self.enregistrer(numero="2", chemin=rel, type="pdf", pages=4, statut="ocrise", origine=ORIGINE["ocr"],
                         categories=["image"] * 4, texte_reference=[fab.texte_page(p) for p in src],
                         mots_uniques=mots, id_images=ids)

    def f03_mixte(self):
        src, mots = self.document_natif(5, "MOTMIXTE", total_pied=6)
        doc = pymupdf.open()
        ids = [None, None, None]
        doc.insert_pdf(src, from_page=0, to_page=2)
        for i in (3, 4):
            ident, *_ = self.page_scannee(doc, src[i])
            ids.append(ident)
        doc.new_page(width=595, height=842)  # page 6 vide
        ids.append(None)
        rel = "pdf/03_mixte.pdf"
        self.enregistrer_pdf(doc, self.chemin(rel))
        self.enregistrer(numero="3", chemin=rel, type="pdf", pages=6, statut="mixte", origine=ORIGINE["mixte"],
                         categories=["native"] * 3 + ["image"] * 2 + ["vide"],
                         texte_reference=[fab.texte_page(src[i]) for i in range(5)] + [""],
                         mots_uniques=mots + [None], id_images=ids)

    def _pdf_a_couche(self, rel, numero, prefixe, pages_degradees, statut):
        src, mots = self.document_natif(len(pages_degradees), prefixe)
        doc = pymupdf.open()
        ids, douteuses = [], []
        for i, p in enumerate(src):
            ident, page, transfo, (w, h) = self.page_scannee(doc, p, angle=0.5, bruit=5)
            ids.append(ident)
            elements = [(t if not pages_degradees[i] else fab.degrader(t, self.graine * 100 + i),
                         fab.boite_transformee(b, transfo))
                        for t, b in self._lignes_px(p)]
            fab.ecrire_calque_invisible(page, elements, w, h)
            if pages_degradees[i]:
                douteuses.append(i + 1)
        self.enregistrer_pdf(doc, self.chemin(rel))
        self.enregistrer(numero=numero, chemin=rel, type="pdf", pages=len(src), statut=statut,
                         origine=ORIGINE["couche"], categories=["couche_existante"] * len(src),
                         texte_reference=[fab.texte_page(p) for p in src], mots_uniques=mots,
                         pages_douteuses=douteuses, id_images=ids)

    @staticmethod
    def _lignes_px(page):
        lignes = {}
        for mot, b, cle in fab.verite_mots(page, DPI):
            lignes.setdefault(cle, []).append((mot, b))
        return [(" ".join(m for m, _ in l),
                 (min(b[0] for _, b in l), min(b[1] for _, b in l), max(b[2] for _, b in l), max(b[3] for _, b in l)))
                for l in lignes.values()]

    def f04_couche_degradee(self):
        self._pdf_a_couche("pdf/04_couche_degradee.pdf", "4", "MOTCOUCHE", [False, True, True, False], "douteux")

    def f20_couche_saine(self):
        self._pdf_a_couche("pdf/20_couche_saine.pdf", "20", "MOTSAINE", [False, False], "couche_expediteur")

    def f05_illisible(self):
        src, mots = self.document_natif(2, "MOTFLOU")
        doc = pymupdf.open()
        ids = []
        ident, *_ = self.page_scannee(doc, src[0])
        ids.append(ident)
        ident, *_ = self.page_scannee(doc, src[1], flou=4.0, bruit=45, qualite=35, confiance=0.30,
                                      remplacement=lambda m: fab.degrader(m, len(m)))
        ids.append(ident)
        rel = "pdf/05_illisible.pdf"
        self.enregistrer_pdf(doc, self.chemin(rel))
        self.enregistrer(numero="5", chemin=rel, type="pdf", pages=2, statut="douteux", origine=ORIGINE["ocr"],
                         categories=["image"] * 2, texte_reference=[fab.texte_page(p) for p in src],
                         mots_uniques=mots, pages_douteuses=[2], id_images=ids)

    def f21_moyennement_degrade(self):
        """Trois pages moyennement dégradées, lisibles en partie, avec montants : scan à 150 dpi
        légèrement flou, tampon superposé au texte, photocopie de photocopie. Elles servent à
        mesurer l'écart réel entre pages saines et dégradées pour chaque moteur (EX-76)."""
        montants = [
            ["Montant des travaux du lot 2 : 48 320,50 € HT, soit 57 984,60 € TTC.",
             "Acompte de 15 % versé à la notification : 7 248,08 € HT."],
            ["Révision des prix : indice BT01 de septembre 2026, coefficient 1,0425.",
             "Pénalité de retard : 250,00 € par jour calendaire, plafonnée à 10 %."],
            ["Honoraires de maîtrise d’œuvre : 96 750,00 € HT pour les missions de base.",
             "Mission complémentaire OPC : 12 900,00 € HT, réglée en six échéances."],
        ]
        lignes_page = [fab.LIGNES_COURANTES + m + fab.LIGNES_REFERENCE[1:4] + fab.LIGNES_REFERENCE[7:8] for m in montants]
        src = pymupdf.open()
        mots = []
        for i, lignes in enumerate(lignes_page, 1):
            mot = f"MOTMOYEN{i:02d}"
            mots.append(mot)
            fab.page_native(src, lignes, mot_unique=mot, pied=f"Page {i} sur 3")
        texte_reference = [fab.texte_page(p) for p in src]
        degrade = lambda graine: (lambda m: fab.degrader_partiellement(m, graine + len(m)))  # noqa: E731
        doc = pymupdf.open()
        ids = []
        # Page 1 : scan à 150 dpi, léger flou, bruit, JPEG médiocre, légère inclinaison.
        ident = self.nouvel_id()
        jpeg, taille, transfo = fab.scanner(src[0], dpi=150, angle=0.8, bruit=22, flou=1.6, qualite_jpeg=30,
                                            graine=ident, identifiant=ident)
        doc.new_page(width=src[0].rect.width, height=src[0].rect.height).insert_image(src[0].rect, stream=jpeg)
        self.ocr_factice[str(ident)] = fab.verite_ocr(src[0], 150, transfo, taille, confiance=0.55, angle=-0.8,
                                                      remplacement=degrade(1))
        ids.append(ident)
        # Page 2 : tampon superposé au texte (sur la source, avant le scan), scan à 300 dpi.
        avec_tampon = pymupdf.open()
        avec_tampon.insert_pdf(src, from_page=1, to_page=1)
        fab.tamponner(avec_tampon[0], "REÇU LE 12 NOV. 2026", (300, 250))
        fab.tamponner(avec_tampon[0], "COPIE CONFORME", (330, 470), taille=30, angle=12)
        # La vérité terrain du moteur factice est celle de la page sans tampon (le tampon n'est
        # pas du texte du document).
        ident = self.nouvel_id()
        jpeg, taille, transfo = fab.scanner(avec_tampon[0], dpi=300, angle=-0.6, bruit=10, qualite_jpeg=80,
                                            graine=ident, identifiant=ident)
        doc.new_page(width=src[1].rect.width, height=src[1].rect.height).insert_image(src[1].rect, stream=jpeg)
        self.ocr_factice[str(ident)] = fab.verite_ocr(src[1], 300, transfo, taille, confiance=0.55, angle=0.6,
                                                      remplacement=degrade(2))
        ids.append(ident)
        # Page 3 : photocopie de photocopie (trois passes), 200 dpi.
        ident = self.nouvel_id()
        pix = src[2].get_pixmap(dpi=200, colorspace=pymupdf.csGRAY)
        img = fab.photocopier(Image.frombytes("L", (pix.width, pix.height), pix.samples), passes=3, graine=ident)
        img = dessiner_marqueur(img, ident)
        tampon = io.BytesIO()
        img.save(tampon, "JPEG", quality=55, dpi=(200, 200))
        doc.new_page(width=src[2].rect.width, height=src[2].rect.height).insert_image(src[2].rect,
                                                                                      stream=tampon.getvalue())
        self.ocr_factice[str(ident)] = fab.verite_ocr(src[2], 200, lambda x, y: (x, y), img.size, confiance=0.55,
                                                      remplacement=degrade(3))
        ids.append(ident)
        rel = "pdf/21_moyennement_degrade.pdf"
        self.enregistrer_pdf(doc, self.chemin(rel))
        self.enregistrer(numero="21", chemin=rel, type="pdf", pages=3, statut="douteux", origine=ORIGINE["ocr"],
                         categories=["image"] * 3, texte_reference=texte_reference, mots_uniques=mots,
                         pages_douteuses=[1, 2, 3], id_images=ids,
                         degradations=["scan 150 dpi, léger flou", "tampon sur le texte", "photocopie de photocopie"],
                         montants=[m for l in montants for m in re.findall(r"\d[\d ]*,\d\d €", " ".join(l))])

    # -------------------------------------------------------------- tableaux
    @staticmethod
    def tableaux_html():
        simple = ("<table><tr><th>Intervenant</th><th>Fonction</th><th>Jours</th></tr>"
                  "<tr><td>Mme Durand</td><td>Architecte</td><td>42</td></tr>"
                  "<tr><td>M. Martin</td><td>Ingénieur fluides</td><td>18</td></tr></table>")
        fusion = ("<table><tr><th rowspan='2'>Lot</th><th colspan='2'>Montants</th><th rowspan='2'>Délai</th></tr>"
                  "<tr><th>Tranche ferme</th><th>Tranche optionnelle</th></tr>"
                  "<tr><td>Gros œuvre</td><td>125 000 €</td><td>30 000 €</td><td rowspan='2'>12 mois</td></tr>"
                  "<tr><td>Charpente</td><td colspan='2'>48 500 € forfait global</td></tr></table>")
        dpgf = ("<table><tr><th>N°</th><th>Désignation</th><th>Unité</th><th>Quantité</th><th>PU HT</th><th>Total HT</th></tr>"
                "<tr><td colspan='6'>Lot 01 : Gros œuvre</td></tr>"
                "<tr><td>1.1</td><td>Terrassements généraux</td><td>m3</td><td>320</td><td>18,50</td><td>5 920,00</td></tr>"
                "<tr><td>1.2</td><td>Béton de fondation</td><td>m3</td><td>85</td><td>165,00</td><td>14 025,00</td></tr>"
                "<tr><td colspan='6'>Lot 02 : Menuiseries extérieures</td></tr>"
                "<tr><td>2.1</td><td>Fenêtres aluminium</td><td>u</td><td>24</td><td>740,00</td><td>17 760,00</td></tr>"
                "<tr><td colspan='5'>Total général HT</td><td>37 705,00</td></tr></table>")
        honoraires = ("<table><tr><th rowspan='2'>Mission</th><th colspan='2'>Architecte mandataire</th>"
                      "<th colspan='2'>BET structure</th><th rowspan='2'>Total € HT</th></tr>"
                      "<tr><th>%</th><th>€ HT</th><th>%</th><th>€ HT</th></tr>"
                      "<tr><td>ESQ</td><td>80</td><td>8 000</td><td>20</td><td>2 000</td><td>10 000</td></tr>"
                      "<tr><td>APD</td><td>70</td><td>14 000</td><td>30</td><td>6 000</td><td>20 000</td></tr>"
                      "<tr><td>DET</td><td>60</td><td>18 000</td><td>40</td><td>12 000</td><td>30 000</td></tr>"
                      "<tr><td>Total</td><td colspan='2'>40 000</td><td colspan='2'>20 000</td><td>60 000</td></tr></table>")
        return [("simple", simple), ("fusion", fusion), ("dpgf", dpgf), ("honoraires", honoraires)]

    @staticmethod
    def valeurs_cellules(html):
        import re
        return [re.sub(r"<[^>]+>", "", c).strip() for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", html)]

    def f06_tableaux(self):
        doc = pymupdf.open()
        tableaux = {}
        rendus = []
        for i, (nom, html) in enumerate(self.tableaux_html(), 1):
            titre = f"<p>Tableau {nom} : pièce MOTTABLEAU{i:02d}</p>"
            fab.page_html(doc, titre + html, CSS_TABLEAUX)
            tableaux[str(i)] = [{"nom": nom, "fusions": nom != "simple", "valeurs": self.valeurs_cellules(html)}]
            rendus.append("html" if nom != "simple" else "markdown")
        rel = "pdf/06_tableaux.pdf"
        self.enregistrer_pdf(doc, self.chemin(rel))
        self.enregistrer(numero="6", chemin=rel, type="pdf", pages=4, statut="natif", origine=ORIGINE["natif"],
                         categories=["native"] * 4, texte_reference=[fab.texte_page(p) for p in doc],
                         mots_uniques=[f"MOTTABLEAU{i:02d}" for i in range(1, 5)], tableaux=tableaux,
                         rendu_tableaux_attendu=rendus)
        # 6b : version scannée
        scan = pymupdf.open()
        ids = [self.page_scannee(scan, p, bruit=3)[0] for p in doc]
        rel = "pdf/06b_tableaux_scannes.pdf"
        self.enregistrer_pdf(scan, self.chemin(rel))
        self.enregistrer(numero="6b", chemin=rel, type="pdf", pages=4, statut="ocrise", origine=ORIGINE["ocr"],
                         categories=["image"] * 4, texte_reference=[fab.texte_page(p) for p in doc],
                         mots_uniques=[f"MOTTABLEAU{i:02d}" for i in range(1, 5)], tableaux=tableaux,
                         repere_tableau_ocr_attendu=True, id_images=ids)

    # -------------------------------------------------------------- 18, 19
    def f18_ligatures(self):
        src, mots = self.document_natif(2, "MOTLIGATURE", lignes=fab.LIGNES_LIGATURES * 2)
        doc = pymupdf.open()
        ids = [self.page_scannee(doc, p, angle=0.7)[0] for p in src]
        rel = "pdf/18_ligatures.pdf"
        self.enregistrer_pdf(doc, self.chemin(rel))
        self.enregistrer(numero="18", chemin=rel, type="pdf", pages=2, statut="ocrise", origine=ORIGINE["ocr"],
                         categories=["image"] * 2, texte_reference=[fab.texte_page(p) for p in src],
                         mots_uniques=mots, id_images=ids)

    def f19_mention_plateforme(self):
        src, mots = self.document_natif(2, "MOTDEPOT")
        doc = pymupdf.open()
        ids = []
        mention = "Pli déposé le 26/11/2026 à 10:42:17 sur la plateforme de dématérialisation, pli n° 0042"
        for p in src:
            ident, page, *_ = self.page_scannee(doc, p)
            ids.append(ident)
            page.insert_font(fontname=fab.NOM_POLICE, fontbuffer=fab.POLICE.buffer)
            page.insert_text((40, 830), mention, fontname=fab.NOM_POLICE, fontsize=6)
        rel = "pdf/19_mention_plateforme.pdf"
        self.enregistrer_pdf(doc, self.chemin(rel))
        self.enregistrer(numero="19", chemin=rel, type="pdf", pages=2, statut="ocrise", origine=ORIGINE["ocr"],
                         categories=["image"] * 2, texte_reference=[fab.texte_page(p) for p in src],
                         mots_uniques=mots, mention_native=mention, id_images=ids)

    # -------------------------------------------------------------- Office
    def f07_docx(self):
        """Mémoire .docx : titres, listes, tableau fusionné, note de bas de page, commentaire,
        révisions non acceptées (insertion et suppression), zone de texte ancrée (forme Word
        moderne avec sa variante VML de repli, qui ne doit être lue qu'une fois)."""
        import docx
        d = docx.Document()
        textes = ["Mémoire technique du groupement", "1. Compréhension de la mission",
                  "Le groupement propose une équipe de maîtrise d’œuvre complète.",
                  "Visites de chantier hebdomadaires", "Comptes rendus sous 48 heures",
                  "Phase études", "Phase travaux",
                  "Le planning détaillé figure en annexe.",
                  "Encadré de synthèse ci-contre.",
                  "2. Moyens humains", "Intervenant", "Mission", "Équipe", "Mme Durand", "Architecte mandataire",
                  "40 %", "Groupement", "M. Martin", "Économiste", "20 %",
                  self.sentinelle(7)]
        note = "Équipe constituée pour ce marché fictif."
        zone = "Engagement qualité : visa des plans sous 8 jours."
        revision = "Délai d’exécution proposé : dix-huit mois."
        commentaire = "Vérifier la date de remise avec le mandataire."
        d.add_heading(textes[0], 0)
        d.add_heading(textes[1], 1)
        d.add_paragraph("@@NOTE@@")
        d.add_paragraph(textes[3], style="List Bullet")
        d.add_paragraph(textes[4], style="List Bullet")
        d.add_paragraph(textes[5], style="List Number")
        d.add_paragraph(textes[6], style="List Number")
        d.add_paragraph("@@COMMENTAIRE@@")
        d.add_paragraph("@@REVISION@@")
        d.add_paragraph("@@ZONE@@")
        d.add_heading(textes[9], 1)
        t = d.add_table(rows=3, cols=4)
        t.style = "Table Grid"
        t.cell(0, 1).merge(t.cell(0, 2))
        t.cell(1, 3).merge(t.cell(2, 3))
        for (r, c), v in zip(((0, 0), (0, 1), (0, 3), (1, 0), (1, 1), (1, 2), (1, 3), (2, 0), (2, 1), (2, 2)),
                             textes[10:20]):
            t.cell(r, c).text = v
        d.add_paragraph(textes[20])
        d.core_properties.created = d.core_properties.modified = DATE_FIXE
        tampon = io.BytesIO()
        d.save(tampon)
        a = 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
        corps_zone = f'<w:txbxContent><w:p><w:r><w:t>{zone}</w:t></w:r></w:p></w:txbxContent>'
        remplacements = {
            "@@NOTE@@": (f'<w:r><w:t>{textes[2]}</w:t></w:r><w:r><w:rPr><w:vertAlign w:val="superscript"/></w:rPr>'
                         '<w:footnoteReference w:id="1"/></w:r>'),
            "@@COMMENTAIRE@@": ('<w:commentRangeStart w:id="0"/>'
                                f'<w:r><w:t>{textes[7]}</w:t></w:r><w:commentRangeEnd w:id="0"/>'
                                '<w:r><w:commentReference w:id="0"/></w:r>'),
            "@@REVISION@@": ('<w:r><w:t xml:space="preserve">Délai d’exécution proposé : </w:t></w:r>'
                             '<w:ins w:id="11" w:author="Relecteur" w:date="2026-11-26T09:00:00Z"><w:r>'
                             '<w:t>dix-huit mois</w:t></w:r></w:ins>'
                             '<w:del w:id="12" w:author="Relecteur" w:date="2026-11-26T09:00:00Z"><w:r>'
                             '<w:delText>vingt-quatre mois</w:delText></w:r></w:del><w:r><w:t>.</w:t></w:r>'),
            "@@ZONE@@": (f'<w:r><w:t>{textes[8]}</w:t></w:r><w:r><mc:AlternateContent><mc:Choice Requires="wps">'
                         '<w:drawing><wp:anchor distT="0" distB="0" distL="114300" distR="114300" simplePos="0" '
                         'relativeHeight="1" behindDoc="0" locked="0" layoutInCell="1" allowOverlap="1">'
                         '<wp:simplePos x="0" y="0"/><wp:positionH relativeFrom="column"><wp:posOffset>3000000'
                         '</wp:posOffset></wp:positionH><wp:positionV relativeFrom="paragraph"><wp:posOffset>0'
                         '</wp:posOffset></wp:positionV><wp:extent cx="2000000" cy="600000"/><wp:wrapSquare '
                         'wrapText="bothSides"/><wp:docPr id="1" name="Zone de texte 1"/><wp:cNvGraphicFramePr/>'
                         f'<a:graphic {a}><a:graphicData uri="http://schemas.microsoft.com/office/word/2010/'
                         'wordprocessingShape"><wps:wsp><wps:cNvSpPr txBox="1"/><wps:spPr><a:xfrm><a:off x="0" '
                         'y="0"/><a:ext cx="2000000" cy="600000"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/>'
                         f'</a:prstGeom></wps:spPr><wps:txbx>{corps_zone}</wps:txbx><wps:bodyPr/></wps:wsp>'
                         '</a:graphicData></a:graphic></wp:anchor></w:drawing></mc:Choice><mc:Fallback><w:pict>'
                         '<v:shape id="Zone1" type="#_x0000_t202" style="position:absolute;width:157pt;height:47pt">'
                         f'<v:textbox>{corps_zone}</v:textbox></v:shape></w:pict></mc:Fallback>'
                         '</mc:AlternateContent></w:r>'),
        }
        w = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
        parties = {
            "word/footnotes.xml": (
                f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:footnotes {w}>'
                '<w:footnote w:type="separator" w:id="-1"><w:p><w:r><w:separator/></w:r></w:p></w:footnote>'
                '<w:footnote w:type="continuationSeparator" w:id="0"><w:p><w:r><w:continuationSeparator/></w:r>'
                '</w:p></w:footnote><w:footnote w:id="1"><w:p><w:r><w:rPr><w:vertAlign w:val="superscript"/>'
                f'</w:rPr><w:footnoteRef/></w:r><w:r><w:t xml:space="preserve"> {note}</w:t></w:r></w:p>'
                '</w:footnote></w:footnotes>'),
            "word/comments.xml": (
                f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:comments {w}>'
                '<w:comment w:id="0" w:author="Relecteur" w:date="2026-11-26T09:00:00Z" w:initials="R"><w:p>'
                f'<w:r><w:t>{commentaire}</w:t></w:r></w:p></w:comment></w:comments>'),
        }
        types = {"word/footnotes.xml": "footnotes", "word/comments.xml": "comments"}

        def document(xml: str) -> str:
            for repere, runs in remplacements.items():
                xml = xml.replace(f"<w:r><w:t>{repere}</w:t></w:r>", runs)
            assert "@@" not in xml
            return xml

        def relations(xml: str) -> str:
            ajout = "".join(f'<Relationship Id="rIdJeu{i}" Type="http://schemas.openxmlformats.org/officeDocument/'
                            f'2006/relationships/{t}" Target="{n.split("/")[-1]}"/>'
                            for i, (n, t) in enumerate(types.items()))
            return xml.replace("</Relationships>", ajout + "</Relationships>")

        def contenus(xml: str) -> str:
            ajout = "".join(f'<Override PartName="/{n}" ContentType="application/vnd.openxmlformats-officedocument.'
                            f'wordprocessingml.{t}+xml"/>' for n, t in types.items())
            return xml.replace("</Types>", ajout + "</Types>")

        rel = "office/07_memoire.docx"
        reecrire_zip(tampon.getvalue(), self.chemin(rel),
                     {"word/document.xml": document, "word/_rels/document.xml.rels": relations,
                      "[Content_Types].xml": contenus}, parties)
        mention = ("Document contenant des révisions non acceptées et 1 commentaire : texte présenté dans son état "
                   "final (insertions acceptées, suppressions écartées), commentaires non repris.")
        self.enregistrer(numero="7", chemin=rel, type="docx", pages=None, statut="natif", origine=ORIGINE["natif"],
                         textes_attendus=textes + [note, zone, revision], sentinelles=[textes[20]],
                         textes_absents=["vingt-quatre mois", commentaire], zone_de_texte=zone,
                         mention_revisions=mention, revisions_commentaires="revisions commentaires=1",
                         titres={"Mémoire technique du groupement": 1, "1. Compréhension de la mission": 1,
                                 "2. Moyens humains": 1})

    def f08_xlsx(self):
        """Classeur écrit directement en XML (openpyxl n'écrit pas de valeurs en cache) :
        formule avec valeur en cache, formule sans valeur, cellules fusionnées, pourcentages,
        artefacts de virgule flottante, date, booléen, erreur, feuille masquée."""
        jour = (datetime.date(2026, 11, 26) - datetime.date(1899, 12, 30)).days
        chaines = ["Récapitulatif des lots", "Lot", "Montant HT", "Délai", "Part", "Gros œuvre", "12 mois",
                   "Charpente", "4 mois", "Total HT", "Total TTC", "Révision", "Date de valeur", "Contrôle",
                   "Ratio", "Poste", "Quantité", "Terrassements", "Fondations", "Taux de TVA", "Prix unitaire"]
        s = {c: i for i, c in enumerate(chaines)}

        def c(ref, chaine=None, v=None, f=None, t=None, style=None):
            attributs = f' r="{ref}"' + (f' s="{style}"' if style else "")
            if chaine is not None:
                return f'<c{attributs} t="s"><v>{s[chaine]}</v></c>'
            contenu = (f"<f>{f}</f>" if f else "") + (f"<v>{v}</v>" if v is not None else "")
            return f'<c{attributs}{f" t=\"{t}\"" if t else ""}>{contenu}</c>'

        def feuille(lignes, fusions=()):
            xml = "".join(f'<row r="{n}">{"".join(cs)}</row>' for n, cs in lignes)
            fus = (f'<mergeCells count="{len(fusions)}">' + "".join(f'<mergeCell ref="{r}"/>' for r in fusions)
                   + "</mergeCells>") if fusions else ""
            return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<worksheet xmlns="http://schemas.'
                    'openxmlformats.org/spreadsheetml/2006/main"><sheetData>' + xml + "</sheetData>" + fus
                    + "</worksheet>")

        synthese = feuille([
            (1, [c("A1", "Récapitulatif des lots")]),
            (2, [c("A2", "Lot"), c("B2", "Montant HT"), c("C2", "Délai"), c("D2", "Part")]),
            (3, [c("A3", "Gros œuvre"), c("B3", v=125000), c("C3", "12 mois"), c("D3", v="0.72", style=1)]),
            (4, [c("A4", "Charpente"), c("B4", v="48500.1"), c("C4", "4 mois"), c("D4", v="0.28", style=1)]),
            (5, [c("A5", "Total HT"), c("B5", f="B3+B4", v="173500.09999999998")]),
            (6, [c("A6", "Total TTC"), c("B6", f="B5*1.2")]),
            (7, [c("A7", "Révision"), c("B7", v="0.30000000000000004"), c("C7", "Ratio"),
                 c("D7", v="0.12345", style=2)]),
            (8, [c("A8", "Date de valeur"), c("B8", v=jour, style=3), c("C8", "Contrôle"), c("D8", v=1, t="b")]),
            (9, [c("A9", "Prix unitaire"), c("B9", v="1234.5600000000002"), c("C9", f="B3/0", v="#DIV/0!", t="e")]),
        ], fusions=["A1:D1"])
        detail = feuille([
            (1, [c("A1", "Poste"), c("B1", "Quantité")]),
            (2, [c("A2", "Terrassements"), c("B2", v=320)]),
            (3, [c("A3", "Fondations"), c("B3", v=85)]),
        ])
        parametres = feuille([(1, [c("A1", "Taux de TVA"), c("B1", v="0.2", style=1)])])
        ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
        nsr = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
        rels = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
        noms = [("Synthèse", "visible"), ("Détail", "visible"), ("Paramètres", "hidden")]
        parties = {
            "[Content_Types].xml": (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Types xmlns="http://schemas.'
                'openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/'
                'vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/'
                'xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-'
                'officedocument.spreadsheetml.sheet.main+xml"/>'
                + "".join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.'
                          'openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in (1, 2, 3))
                + '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.'
                'spreadsheetml.styles+xml"/><Override PartName="/xl/sharedStrings.xml" ContentType="application/'
                'vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/></Types>'),
            "_rels/.rels": (
                f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.'
                f'openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="{rels}/'
                'officeDocument" Target="xl/workbook.xml"/></Relationships>'),
            "xl/workbook.xml": (
                f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<workbook {ns} {nsr}><sheets>'
                + "".join(f'<sheet name="{n}" sheetId="{i}"{"" if e == "visible" else f" state=\"{e}\""} '
                          f'r:id="rId{i}"/>' for i, (n, e) in enumerate(noms, 1))
                + "</sheets></workbook>"),
            "xl/_rels/workbook.xml.rels": (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.'
                'openxmlformats.org/package/2006/relationships">'
                + "".join(f'<Relationship Id="rId{i}" Type="{rels}/worksheet" Target="worksheets/sheet{i}.xml"/>'
                          for i in (1, 2, 3))
                + f'<Relationship Id="rId4" Type="{rels}/styles" Target="styles.xml"/>'
                f'<Relationship Id="rId5" Type="{rels}/sharedStrings" Target="sharedStrings.xml"/>'
                "</Relationships>"),
            "xl/styles.xml": (
                f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<styleSheet {ns}>'
                '<numFmts count="1"><numFmt numFmtId="164" formatCode="0.00\\ %"/></numFmts>'
                '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
                '<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill '
                'patternType="gray125"/></fill></fills><borders count="1"><border><left/><right/><top/><bottom/>'
                '<diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" '
                'borderId="0"/></cellStyleXfs><cellXfs count="4"><xf numFmtId="0" fontId="0" fillId="0" '
                'borderId="0" xfId="0"/><xf numFmtId="9" fontId="0" fillId="0" borderId="0" xfId="0" '
                'applyNumberFormat="1"/><xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" '
                'applyNumberFormat="1"/><xf numFmtId="14" fontId="0" fillId="0" borderId="0" xfId="0" '
                'applyNumberFormat="1"/></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" '
                'builtinId="0"/></cellStyles></styleSheet>'),
            "xl/sharedStrings.xml": (
                f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<sst {ns} count="{len(chaines)}" '
                f'uniqueCount="{len(chaines)}">' + "".join(f"<si><t>{t}</t></si>" for t in chaines) + "</sst>"),
            "xl/worksheets/sheet1.xml": synthese, "xl/worksheets/sheet2.xml": detail,
            "xl/worksheets/sheet3.xml": parametres,
        }
        rel = "office/08_chiffrage.xlsx"
        reecrire_zip(None, self.chemin(rel), {}, parties)
        self.enregistrer(numero="8", chemin=rel, type="xlsx", pages=None, statut="natif", origine=ORIGINE["natif"],
                         feuilles_visibles=["Synthèse", "Détail"], feuilles_masquees=["Paramètres"],
                         textes_attendus=["Récapitulatif des lots", "Gros œuvre", "125000", "12 mois", "48500,1",
                                          "173500,1", "[formule non calculée : =B5*1.2]", "72 %", "28 %",
                                          "0,3", "12,345 %", "2026-11-26", "VRAI", "1234,56", "#DIV/0!",
                                          "Terrassements", "320"],
                         textes_absents=["Taux de TVA", "0,30000000000000004", "1234,5600000000002", "0,72"])

    def f09_pptx(self):
        from pptx import Presentation
        from pptx.util import Inches
        prs = Presentation()
        s1 = prs.slides.add_slide(prs.slide_layouts[0])
        s1.shapes.title.text = "Présentation de l’offre"
        s1.placeholders[1].text = "Groupement fictif Alpha Bêta"
        s2 = prs.slides.add_slide(prs.slide_layouts[1])
        s2.shapes.title.text = "Méthodologie"
        s2.placeholders[1].text = "Diagnostic de l’existant"
        s2.notes_slide.notes_text_frame.text = "Insister sur le planning de la phase études."
        groupe = s2.shapes.add_group_shape()
        groupe.shapes.add_textbox(Inches(1), Inches(5), Inches(3), Inches(0.5)).text_frame.text = "Visa sous 8 jours"
        groupe.shapes.add_textbox(Inches(5), Inches(5), Inches(3), Inches(0.5)).text_frame.text = "Synthèse mensuelle"
        s3 = prs.slides.add_slide(prs.slide_layouts[5])
        s3.shapes.title.text = "Équipe proposée"
        tab = s3.shapes.add_table(3, 3, Inches(1), Inches(2), Inches(6), Inches(1.5)).table
        tab.cell(0, 1).merge(tab.cell(0, 2))
        for (r, c), v in zip(((0, 0), (0, 1), (1, 0), (1, 1), (1, 2), (2, 0), (2, 1), (2, 2)),
                             ["Rôle", "Intervenant et part", "Mandataire", "Mme Durand", "40 %",
                              "Économiste", "M. Martin", "20 %"]):
            tab.cell(r, c).text = v
        s4 = prs.slides.add_slide(prs.slide_layouts[5])
        s4.shapes.title.text = "Annexe masquée"
        s4._element.set("show", "0")
        prs.core_properties.created = prs.core_properties.modified = DATE_FIXE
        rel = "office/09_presentation.pptx"
        prs.save(self.chemin(rel))
        self.enregistrer(numero="9", chemin=rel, type="pptx", pages=4, statut="natif", origine=ORIGINE["natif"],
                         textes_attendus=["Présentation de l’offre", "Groupement fictif Alpha Bêta", "Méthodologie",
                                          "Diagnostic de l’existant", "Insister sur le planning de la phase études.",
                                          "Visa sous 8 jours", "Synthèse mensuelle", "Équipe proposée",
                                          "Intervenant et part", "Mandataire", "Mme Durand", "40 %", "Économiste",
                                          "M. Martin", "Annexe masquée"],
                         diapositives_masquees=[4])

    # -------------------------------------------------------------- images
    def _image_page(self, prefixe):
        src, mots = self.document_natif(1, prefixe)
        ident = self.nouvel_id()
        pix = src[0].get_pixmap(dpi=DPI, colorspace=pymupdf.csGRAY)
        img = dessiner_marqueur(Image.frombytes("L", (pix.width, pix.height), pix.samples), ident)
        self.ocr_factice[str(ident)] = fab.verite_ocr(src[0], DPI, lambda x, y: (x, y), img.size)
        return img, ident, fab.texte_page(src[0]), mots[0]

    def f10_images(self):
        # JPEG à orientation EXIF 6 : stocké tourné d'un quart de tour, à redresser.
        img, ident, texte, mot = self._image_page("MOTJPEG")
        stockee = img.rotate(90, expand=True)
        exif = Image.Exif()
        exif[0x0112] = 6
        rel = "images/10_exif6.jpg"
        stockee.save(self.chemin(rel), "JPEG", quality=85, dpi=(DPI, DPI), exif=exif.tobytes())
        assert ImageOps.exif_transpose(Image.open(self.chemin(rel))).size == img.size
        self.enregistrer(numero="10", chemin=rel, type="image", pages=1, statut="ocrise", origine=ORIGINE["ocr"],
                         categories=["image"], texte_reference=[texte], mots_uniques=[mot], id_images=[ident],
                         orientation_exif=6)
        img, ident, texte, mot = self._image_page("MOTPNG")
        rel = "images/10_page.png"
        img.save(self.chemin(rel), "PNG", dpi=(DPI, DPI))
        self.enregistrer(numero="10", chemin=rel, type="image", pages=1, statut="ocrise", origine=ORIGINE["ocr"],
                         categories=["image"], texte_reference=[texte], mots_uniques=[mot], id_images=[ident])
        img, ident, texte, mot = self._image_page("MOTMAJUSCULE")
        rel = "images/10_extension_majuscules.PNG"
        img.save(self.chemin(rel), "PNG", dpi=(DPI, DPI))
        self.enregistrer(numero="10", chemin=rel, type="image", pages=1, statut="ocrise", origine=ORIGINE["ocr"],
                         categories=["image"], texte_reference=[texte], mots_uniques=[mot], id_images=[ident])
        trames = [self._image_page(f"MOTTRAME{i}") for i in range(1, 4)]
        rel = "images/10_trois_trames.tiff"
        trames[0][0].save(self.chemin(rel), "TIFF", save_all=True, append_images=[t[0] for t in trames[1:]],
                          compression="tiff_deflate", dpi=(DPI, DPI))
        self.enregistrer(numero="10", chemin=rel, type="image", pages=3, statut="ocrise", origine=ORIGINE["ocr"],
                         categories=["image"] * 3, texte_reference=[t[2] for t in trames],
                         mots_uniques=[t[3] for t in trames], id_images=[t[1] for t in trames])

    # -------------------------------------------------------------- non pris en charge, erreurs
    def f11_non_pris_en_charge(self):
        ole = bytes.fromhex("D0CF11E0A1B11AE1") + b"\0" * 504
        for rel, message in (("non_pris_en_charge/ancien.doc", "ancien format Office"),
                             ("non_pris_en_charge/courriel.msg", "e-mail non pris en charge"),):
            self.chemin(rel).write_bytes(ole)
            self.enregistrer(numero="11", chemin=rel, type="autre", pages=None, statut="non_pris_en_charge",
                             message_attendu=message)
        rel = "non_pris_en_charge/archive.zip"
        with zipfile.ZipFile(self.chemin(rel), "w") as z:
            z.writestr(zipfile.ZipInfo("lisez-moi.txt", date_time=(2026, 11, 26, 9, 0, 0)), "Archive fictive.")
        self.enregistrer(numero="11", chemin=rel, type="autre", pages=None, statut="non_pris_en_charge",
                         message_attendu="format non pris en charge")

    def f12_chemins_accentues(self):
        nom_dossier, nom_fichier = "Candidat Été & Fils (n° 2)", "Mémoire d'été.pdf"
        for forme in ("NFC", "NFD"):
            rel = f"chemins/{forme.lower()}/{unicodedata.normalize(forme, nom_dossier)}/{unicodedata.normalize(forme, nom_fichier)}"
            doc, mots = self.document_natif(1, f"MOTACCENT{forme}")
            self.enregistrer_pdf(doc, self.chemin(rel))
            self.enregistrer(numero="12", chemin=rel, type="pdf", pages=1, statut="natif", origine=ORIGINE["natif"],
                             categories=["native"], texte_reference=[fab.texte_page(doc[0])], mots_uniques=mots,
                             forme_unicode=forme)

    def f13_f14_erreurs(self):
        doc, _ = self.document_natif(2, "MOTERREUR")
        octets = doc.tobytes(garbage=4, deflate=True, no_new_id=True)
        rel = "erreurs/13_tronque.pdf"
        self.chemin(rel).write_bytes(octets[: int(len(octets) * 0.6)])
        self.enregistrer(numero="13", chemin=rel, type="pdf", pages=None, statut="erreur", message_attendu="PDF endommagé")
        rel = "erreurs/13_chiffre.pdf"
        doc.save(self.chemin(rel), encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="essai", owner_pw="essai-proprietaire")
        self.enregistrer(numero="13", chemin=rel, type="pdf", pages=None, statut="erreur",
                         message_attendu="PDF protégé par mot de passe")
        # 13b : PDF tronqué partiellement récupérable (police de base, non intégrée, pour que
        # les pages placées avant la coupure restent lisibles après réparation).
        partiel = pymupdf.open()
        for i in range(1, 5):
            p = partiel.new_page()
            p.insert_text((72, 100), f"MOTREPARE{i:02d} Memoire technique, page {i}", fontname="helv", fontsize=12)
            for k in range(30):
                p.insert_text((72, 130 + k * 20), f"Ligne {k} de la page {i} : contenu de controle.",
                              fontname="helv", fontsize=11)
        octets = partiel.tobytes(garbage=4, deflate=True, no_new_id=True)
        tronque = octets[: int(len(octets) * 0.55)]
        repare = pymupdf.open("pdf", tronque)
        recuperees = sum(1 for p in repare if p.get_text().strip())
        assert repare.is_repaired and 1 <= recuperees < repare.page_count, "troncature 13b inadaptée"
        rel = "erreurs/13b_tronque_recuperable.pdf"
        self.chemin(rel).write_bytes(tronque)
        self.enregistrer(numero="13b", chemin=rel, type="pdf", pages=repare.page_count, statut="douteux",
                         pages_douteuses=list(range(1, repare.page_count + 1)), motifs=["pdf_repare"],
                         pages_recuperees=recuperees,
                         message_attendu=f"PDF endommagé et réparé : {recuperees} pages sur {repare.page_count} "
                                         "récupérées, contenu possiblement incomplet")
        rel = "erreurs/14_substitut_1ko.pdf"
        self.chemin(rel).write_bytes(b"\0" * 1024)
        self.enregistrer(numero="14", chemin=rel, type="pdf", pages=None, statut="erreur",
                         message_attendu="le contenu du fichier ne correspond pas à son extension")
        rel = "erreurs/faux_pdf.pdf"
        self.chemin(rel).write_text("Ceci est un fichier texte renommé en .pdf.\n", encoding="utf-8")
        self.enregistrer(numero="EX-18", chemin=rel, type="pdf", pages=None, statut="erreur",
                         message_attendu="le contenu du fichier ne correspond pas à son extension")

    def f15_lot(self):
        def pdf_natif(rel, prefixe):
            doc, mots = self.document_natif(1, prefixe)
            self.enregistrer_pdf(doc, self.chemin(rel))
            self.enregistrer(numero="15", chemin=rel, type="pdf", pages=1, statut="natif", origine=ORIGINE["natif"],
                             categories=["native"], texte_reference=[fab.texte_page(doc[0])], mots_uniques=mots)

        def pdf_scanne(rel, prefixe):
            src, mots = self.document_natif(1, prefixe)
            doc = pymupdf.open()
            ident = self.page_scannee(doc, src[0])[0]
            self.enregistrer_pdf(doc, self.chemin(rel))
            self.enregistrer(numero="15", chemin=rel, type="pdf", pages=1, statut="ocrise", origine=ORIGINE["ocr"],
                             categories=["image"], texte_reference=[fab.texte_page(src[0])], mots_uniques=mots,
                             id_images=[ident])

        pdf_natif("lot/Lot 1/Candidat A/DC1.pdf", "MOTLOTA")
        pdf_scanne("lot/Lot 1/Candidat A/Annexes/Attestation URSSAF.pdf", "MOTLOTANNEXE")
        pdf_natif("lot/Lot 1/Candidat B/Offre/Mémoire technique.pdf", "MOTLOTB")
        pdf_scanne("lot/Lot 1/Candidat B/DC2.pdf", "MOTLOTBDC")
        # Éléments à exclure du parcours (EX-14) : ils ne doivent pas figurer au rapport.
        exclus = {"lot/Lot 1/_OCR/DC1.pdf.md": "ancienne sortie",
                  "lot/Lot 1/Candidat A/_OCR/vieux.pdf": "%PDF-ancienne sortie",
                  "lot/Lot 1/Candidat A/.DS_Store": "", "lot/Lot 1/Candidat B/Thumbs.db": "",
                  "lot/Lot 1/desktop.ini": "", "lot/Lot 1/Candidat B/~$moire technique.docx": "",
                  "lot/Lot 1/Candidat A/.cache cachée.pdf": "%PDF-"}
        for rel, contenu in exclus.items():
            self.chemin(rel).write_text(contenu, encoding="utf-8")
        self.exclus += list(exclus)

    # -------------------------------------------------------------- 16, 17 (à la demande)
    def f16_chemin_long(self, longueur_cible=300):
        segments, total = [], len(str((self.racine / "long" / "_OCR").resolve()))
        while total < longueur_cible:
            seg = f"dossier intermédiaire de profondeur {len(segments) + 1:02d}"
            segments.append(seg)
            total += len(seg) + 1
        rel = "long/" + "/".join(segments) + "/pièce à chemin long.pdf"
        doc, mots = self.document_natif(1, "MOTLONG")
        cible = self.racine / rel
        if os.name == "nt":
            os.makedirs("\\\\?\\" + str(cible.parent.resolve()), exist_ok=True)
            doc.save("\\\\?\\" + str(cible.resolve()))
        else:
            cible.parent.mkdir(parents=True, exist_ok=True)
            self.enregistrer_pdf(doc, cible)
        self.enregistrer(numero="16", chemin=rel, type="pdf", pages=1, statut="natif", origine=ORIGINE["natif"],
                         categories=["native"], texte_reference=[fab.texte_page(doc[0])], mots_uniques=mots,
                         longueur_chemin_sortie_min=longueur_cible)

    def f17_volumineux(self, nb_pages=1000):
        src, _ = self.document_natif(1, "MOTVOLUME")
        pix = src[0].get_pixmap(dpi=100, colorspace=pymupdf.csGRAY)
        doc = pymupdf.open()
        # Une seule image, de même identifiant, sur toutes les pages : la vérité terrain du
        # moteur factice ne grossit pas avec le nombre de pages (mesure mémoire de EX-59).
        ident = self.nouvel_id()
        img = dessiner_marqueur(Image.frombytes("L", (pix.width, pix.height), pix.samples), ident)
        self.ocr_factice[str(ident)] = fab.verite_ocr(src[0], 100, lambda x, y: (x, y), img.size)
        tampon = io.BytesIO()
        img.save(tampon, "JPEG", quality=50)
        for _i in range(nb_pages):
            doc.new_page(width=595, height=842).insert_image(pymupdf.Rect(0, 0, 595, 842), stream=tampon.getvalue())
        rel = f"volumineux/17_{nb_pages}_pages.pdf"
        self.enregistrer_pdf(doc, self.chemin(rel))
        self.enregistrer(numero="17", chemin=rel, type="pdf", pages=nb_pages, statut="ocrise", origine=ORIGINE["ocr"],
                         categories=["image"] * nb_pages, texte_reference=None, mots_uniques=None)

    # -------------------------------------------------------------- ensemble
    def generer(self, volumineux=False, chemin_long=False):
        for f in (self.f01_natif, self.f02_scanne, self.f03_mixte, self.f04_couche_degradee, self.f05_illisible,
                  self.f06_tableaux, self.f07_docx, self.f08_xlsx, self.f09_pptx, self.f10_images,
                  self.f11_non_pris_en_charge, self.f12_chemins_accentues, self.f13_f14_erreurs, self.f15_lot,
                  self.f18_ligatures, self.f19_mention_plateforme, self.f20_couche_saine,
                  self.f21_moyennement_degrade):
            f()
        if chemin_long:
            self.f16_chemin_long()
        if volumineux:
            self.f17_volumineux()
        manifeste = {"version": VERSION_MANIFESTE, "graine": self.graine, "dpi_scans": DPI,
                     "fichiers": self.fichiers, "exclus": self.exclus, "ocr_factice": self.ocr_factice}
        (self.racine / "manifeste.json").write_text(json.dumps(manifeste, ensure_ascii=False, indent=1), encoding="utf-8")
        return manifeste


def generer(racine, graine=2026, volumineux=False, chemin_long=False) -> dict:
    racine = pathlib.Path(racine)
    racine.mkdir(parents=True, exist_ok=True)
    return Generateur(racine, graine).generer(volumineux=volumineux, chemin_long=chemin_long)


def main():
    a = argparse.ArgumentParser(description="Génère le jeu de test synthétique d'ocr-md")
    a.add_argument("sortie", nargs="?", default=str(pathlib.Path(__file__).parent / "jeu"))
    a.add_argument("--graine", type=int, default=2026)
    a.add_argument("--volumineux", action="store_true", help="ajoute le PDF de 1 000 pages (fichier 17)")
    a.add_argument("--chemin-long", action="store_true", help="ajoute le fichier à chemin long (fichier 16)")
    o = a.parse_args()
    m = generer(o.sortie, o.graine, o.volumineux, o.chemin_long)
    print(f"{len(m['fichiers'])} fichiers, {len(m['ocr_factice'])} images, dans {o.sortie}")


if __name__ == "__main__":
    main()
