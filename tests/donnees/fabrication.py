"""Fonctions de fabrication de documents synthétiques (reprises de essais/commun et complétées).

Utilisées par le générateur du jeu de test (`generer.py`) et par les tests. Aucune donnée
réelle : textes rédigés pour l'occasion, noms fictifs.
"""

import io
import math
import random

import numpy as np
import pymupdf
from PIL import Image, ImageFilter

from ocr_md.ocr.factice import dessiner_marqueur

POLICE = pymupdf.Font("notos")  # Noto Sans (OFL), paquet pymupdf-fonts
NOM_POLICE = "notos"

# Texte de référence couvrant tous les caractères exigés par EX-30.
LIGNES_REFERENCE = [
    "Mémoire technique : maîtrise d’œuvre de l’opération",
    "Le groupement réalisera l’étude préalable à coût maîtrisé.",
    "Montant forfaitaire : 12 450,00 € HT « clé en main ».",
    "Où sûrement l’ambiguïté naïve du cœur reste à lever.",
    "Noël, aïeul, Lætitia, ex æquo, déçu, bâtir, fenêtre, hôtel.",
    "ÉTÉ À PARIS : ÇA SE RÉSERVE, ÊTRE ÔTÉ, ÈRE ŒUVRE, ÆON, ÎLE, OÙ.",
    "Références : DC1, DC2, DUME, CCAP, CCTP, DPGF et BPU.",
    "Délai d’exécution : 18 mois à compter de l’ordre de service.",
    "CAPHARNAÜM, MAÏS, NOËL, ÂME, FÛT : il achète un pèse-lettre, aigüe.",
]
# Texte courant supplémentaire, pour que chaque page compte plus de 40 mots évaluables.
LIGNES_COURANTES = [
    "Le présent mémoire décrit la méthode proposée pour conduire la mission.",
    "Les réunions de chantier se tiennent chaque semaine en présence du maître d’ouvrage.",
    "Les plans sont transmis sous forme numérique avant chaque phase de validation.",
    "Le planning prévisionnel tient compte des congés et des intempéries habituelles.",
]
# Texte riche en ligatures (fichier 18) : doit rester « bonne » sous les deux moteurs.
LIGNES_LIGATURES = [
    "Le maître d’œuvre assure la direction de l’œuvre et le suivi du chantier.",
    "Au cœur du projet, la sœur du maître d’ouvrage exprime le vœu d’un bâtiment sobre.",
    "Les offres classées ex æquo sont départagées par le maître d’œuvre.",
    "Lætitia, chargée d’opération, vérifie l’œuvre achevée et le nœud des réseaux.",
    "La manœuvre des engins est réglée par l’œil attentif du coordonnateur.",
    "Le maître d’œuvre transmet chaque mois l’état d’avancement de l’œuvre.",
]
CARACTERES_EXIGES = "éèêëàâùûüçîïôœæÉÈÊËÀÂÙÛÜÇÎÏÔŒÆ«»’€"


def page_native(doc, lignes, mot_unique="", largeur=595, hauteur=842, taille=12, pied="", sentinelle=""):
    """Ajoute une page de texte natif visible ; renvoie la page."""
    page = doc.new_page(width=largeur, height=hauteur)
    page.insert_font(fontname=NOM_POLICE, fontbuffer=POLICE.buffer)
    y = 90
    for ligne in ([mot_unique] if mot_unique else []) + list(lignes) + ([sentinelle] if sentinelle else []):
        page.insert_text((72, y), ligne, fontname=NOM_POLICE, fontsize=taille)
        y += taille * 2
    if pied:
        page.insert_text((largeur / 2 - 30, hauteur - 40), pied, fontname=NOM_POLICE, fontsize=9)
    return page


def page_html(doc, html, css, largeur=595, hauteur=842):
    """Ajoute une page dont le contenu est rendu depuis du HTML (tableaux)."""
    page = doc.new_page(width=largeur, height=hauteur)
    page.insert_htmlbox(pymupdf.Rect(50, 70, largeur - 50, hauteur - 60), html, css=css)
    return page


def verite_mots(page, dpi):
    """Mots de la page en pixels à dpi donné : [(texte, (x0,y0,x1,y1), (bloc, ligne))]."""
    f = dpi / 72
    return [(mot, (x0 * f, y0 * f, x1 * f, y1 * f), (bloc, ligne))
            for x0, y0, x1, y1, mot, bloc, ligne, _ in page.get_text("words")]


def texte_page(page):
    """Texte de référence d'une page native (mots séparés par des espaces)."""
    return " ".join(m[4] for m in page.get_text("words"))


def scanner(page, dpi=300, angle=0.0, bruit=0.0, flou=0.0, qualite_jpeg=80, graine=1, identifiant=None):
    """Simule un scan : rendu, rotation (degrés), bruit gaussien, flou, marqueur du moteur
    factice, JPEG. Renvoie (octets_jpeg, (largeur, hauteur), transformation), où
    transformation(x, y) envoie un point de l'image droite vers l'image tournée."""
    pix = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY)
    img = Image.frombytes("L", (pix.width, pix.height), pix.samples)
    w, h = img.size
    cx, cy = w / 2, h / 2
    if angle:
        img = img.rotate(angle, resample=Image.BICUBIC, fillcolor=255, center=(cx, cy))
    if flou:
        img = img.filter(ImageFilter.GaussianBlur(flou))
    if bruit:
        rng = np.random.default_rng(graine)
        a = np.asarray(img, dtype=np.float32) + rng.normal(0, bruit, (h, w))
        img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    if identifiant is not None:
        img = dessiner_marqueur(img, identifiant)
    tampon = io.BytesIO()
    img.save(tampon, "JPEG", quality=qualite_jpeg, dpi=(dpi, dpi))
    t = math.radians(angle)

    def transformation(x, y):
        dx, dy = x - cx, y - cy
        return (cx + dx * math.cos(t) + dy * math.sin(t), cy - dx * math.sin(t) + dy * math.cos(t))

    return tampon.getvalue(), (w, h), transformation


def boite_transformee(boite, transformation):
    x0, y0, x1, y1 = boite
    pts = [transformation(x, y) for x, y in ((x0, y0), (x1, y0), (x0, y1), (x1, y1))]
    return (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts))


def verite_ocr(page_source, dpi, transformation, taille_image, confiance=0.95, angle=None, remplacement=None):
    """Résultat attendu du moteur factice pour une page scannée, au format du manifeste :
    {"lignes": [{"mots": [[texte, [x0,y0,x1,y1] en fractions]], "confiance": c}], "angle": a}.
    `remplacement(texte) -> texte` dégrade le texte (page illisible)."""
    w, h = taille_image
    lignes = {}
    for mot, b, cle in verite_mots(page_source, dpi):
        x0, y0, x1, y1 = boite_transformee(b, transformation)
        texte = remplacement(mot) if remplacement else mot
        lignes.setdefault(cle, []).append([texte, [round(x0 / w, 5), round(y0 / h, 5), round(x1 / w, 5), round(y1 / h, 5)]])
    return {"lignes": [{"mots": mots, "confiance": confiance} for mots in lignes.values()], "angle": angle}


def ecrire_calque_invisible(page, elements, largeur_px, hauteur_px):
    """Calque invisible (mode de rendu 3) ; elements = [(texte, (x0, y0, x1, y1) en pixels)].
    Version simplifiée pour fabriquer les PDF « à couche OCR de l'expéditeur »."""
    page.insert_font(fontname=NOM_POLICE, fontbuffer=POLICE.buffer)
    ech = pymupdf.Matrix(page.rect.width / largeur_px, page.rect.height / hauteur_px)
    for texte, boite in elements:
        if not texte.strip():
            continue
        r = pymupdf.Rect(boite) * ech
        taille = r.height / (POLICE.ascender - POLICE.descender)
        longueur = POLICE.text_length(texte, fontsize=taille)
        base = pymupdf.Point(r.x0, r.y1 + POLICE.descender * taille)
        morph = (base, pymupdf.Matrix(r.width / longueur if longueur else 1, 1))
        page.insert_text(base, texte, fontname=NOM_POLICE, fontsize=taille, render_mode=3, morph=morph)


def degrader(texte, graine):
    """Corrompt un texte comme une mauvaise couche OCR : substitutions de caractères,
    mots fragmentés, caractères aberrants (lettres cyrilliques)."""
    rng = random.Random(graine)
    subst = {"o": "0", "l": "1", "i": "1", "e": "c", "a": "à", "s": "5", "m": "rn", "é": "6"}
    mots = []
    for mot in texte.split():
        tirage = rng.random()
        if tirage < 0.30 and len(mot) > 3:
            mots.append(" ".join(mot))  # fragmentation
        elif tirage < 0.80:
            mots.append("".join(subst.get(c, c) if rng.random() < 0.5 else c for c in mot))
        elif tirage < 0.90:
            # Lettres hors alphabets latin et grec (cyrillique) : la police Noto Sans les
            # possède, alors qu'elle n'a pas de glyphe pour U+FFFD ni pour la zone privée.
            mots.append(mot[: len(mot) // 2] + "жщ" + mot[len(mot) // 2:])
        else:
            mots.append(mot)
    return " ".join(mots)


def melanger(graine=1):
    return random.Random(graine)
