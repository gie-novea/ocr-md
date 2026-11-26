"""Fonctions de fabrication de PDF synthétiques, communes aux essais.

Elles seront reprises par le générateur du jeu de test (jalon 2). Aucune donnée réelle.
"""

import io
import math
import random

import numpy as np
import pymupdf
from PIL import Image, ImageFilter

POLICE = pymupdf.Font("notos")  # Noto Sans (OFL), paquet pymupdf-fonts

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
CARACTERES_EXIGES = "éèêëàâùûüçîïôœæÉÈÊËÀÂÙÛÜÇÎÏÔŒÆ«»’€"


def page_native(doc, lignes, mot_unique="", largeur=595, hauteur=842, taille=12):
    """Ajoute une page de texte natif visible ; renvoie la page."""
    page = doc.new_page(width=largeur, height=hauteur)
    page.insert_font(fontname="notos", fontbuffer=POLICE.buffer)
    y = 90
    if mot_unique:
        page.insert_text((72, y), mot_unique, fontname="notos", fontsize=taille)
        y += taille * 2
    for ligne in lignes:
        page.insert_text((72, y), ligne, fontname="notos", fontsize=taille)
        y += taille * 2
    return page


def verite_mots(page, dpi):
    """Mots de la page native en pixels à dpi donné : [(texte, (x0,y0,x1,y1), no_ligne)]."""
    f = dpi / 72
    res = []
    for x0, y0, x1, y1, mot, bloc, ligne, _ in page.get_text("words"):
        res.append((mot, (x0 * f, y0 * f, x1 * f, y1 * f), (bloc, ligne)))
    return res


def scanner(page, dpi=300, angle=0.0, bruit=0.0, flou=0.0, qualite_jpeg=85, graine=1):
    """Simule un scan : rendu, rotation (degrés), bruit gaussien, flou, JPEG.

    Renvoie (octets_jpeg, (largeur_px, hauteur_px), transformation) où
    transformation(x, y) envoie un point de l'image droite vers l'image tournée.
    """
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
    tampon = io.BytesIO()
    img.save(tampon, "JPEG", quality=qualite_jpeg, dpi=(dpi, dpi))
    # PIL.rotate tourne dans le sens antihoraire à l'écran (axe y vers le bas).
    t = math.radians(angle)

    def transformation(x, y):
        dx, dy = x - cx, y - cy
        return (cx + dx * math.cos(t) + dy * math.sin(t),
                cy - dx * math.sin(t) + dy * math.cos(t))

    return tampon.getvalue(), (w, h), transformation


def boite_transformee(boite, transformation):
    """Boîte englobante alignée sur les axes d'une boîte après transformation."""
    x0, y0, x1, y1 = boite
    pts = [transformation(x, y) for x, y in ((x0, y0), (x1, y0), (x0, y1), (x1, y1))]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def ocr_simule(page_native_, dpi, transformation, niveau="mot"):
    """Résultat d'OCR simulé, au format de l'interface ocr/base pressentie.

    niveau "mot" : [(texte, boite_px)] ; niveau "ligne" : lignes reconstituées.
    """
    mots = [(m, boite_transformee(b, transformation), l) for m, b, l in verite_mots(page_native_, dpi)]
    if niveau == "mot":
        return [(m, b) for m, b, _ in mots]
    lignes = {}
    for m, b, l in mots:
        lignes.setdefault(l, []).append((m, b))
    res = []
    for elems in lignes.values():
        texte = " ".join(m for m, _ in elems)
        bs = [b for _, b in elems]
        res.append((texte, (min(b[0] for b in bs), min(b[1] for b in bs),
                            max(b[2] for b in bs), max(b[3] for b in bs))))
    return res


def melanger(graine=1):
    return random.Random(graine)
