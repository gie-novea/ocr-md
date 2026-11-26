"""Markdown des PDF, produit par PyMuPDF4LLM à partir du PDF consultable (EX-40 à EX-44).

- Conversion page par page (`page_chunks=True`), en-têtes et pieds de page conservés,
  aucune image exportée ni incorporée, adaptateur `ocr_function` de l'outil (aucune autre
  reconnaissance, aucun autre moteur : EX-08, EX-40).
- Repère `<!-- page N -->` (ou sa variante « TEXTE DOUTEUX ») avant chaque page, toutes
  pages comprises ; `*(page sans texte exploitable)*` pour une page sans texte (EX-41).
- Tableaux (EX-44) : tableau simple en Markdown ; tableau natif à cellules fusionnées ou à
  plusieurs lignes d'en-tête en HTML produit par l'outil (`colspan`, `rowspan`), car le
  rendu HTML de la bibliothèque perd les fusions (PV-13) ; sur une page reconnue par OCR,
  repère « tableau reconnu par OCR » avant chaque tableau.
"""

import contextlib
import html
import io
import re

import pymupdf

from . import correctifs
from .calque import AdaptateurOcr

REPERE_TABLEAU_OCR = ("<!-- tableau reconnu par OCR : correspondance lignes/colonnes non garantie, "
                      "vérifier sur l'original avant de citer un montant -->")
PAGE_SANS_TEXTE = "*(page sans texte exploitable)*"
TAILLE_LOT = 50  # pages converties par appel (mémoire constante sur les gros documents)
# Part minimale des mots du calque d'une page reconnue que le Markdown de la bibliothèque doit
# restituer ; en dessous, repli de PV-05 (texte simple tiré du calque).
COUVERTURE_MIN_PAGE_OCR = 0.90


def repere_page(numero: int, douteuse: bool) -> str:
    if douteuse:
        return f"<!-- page {numero} : TEXTE DOUTEUX, ne pas citer sans vérification sur l'original -->"
    return f"<!-- page {numero} -->"


# ------------------------------------------------------------------------------ tableaux
def _fusions(table) -> bool:
    """Le tableau comporte une cellule fusionnée (position couverte par une fusion)."""
    return any(c is None for ligne in table.rows for c in ligne.cells)


def table_html(page, table) -> str:
    """HTML d'un tableau natif détecté par find_tables, fusions comprises (PV-13)."""
    cellules = sorted({tuple(round(v, 1) for v in c) for c in table.cells if c}, key=lambda c: (c[1], c[0]))
    xs = sorted({c[0] for c in cellules} | {c[2] for c in cellules})
    ys = sorted({c[1] for c in cellules} | {c[3] for c in cellules})
    par_ligne: dict[int, list] = {}
    for c in cellules:
        par_ligne.setdefault(ys.index(c[1]), []).append(c)
    lignes_html = []
    for i in range(len(ys) - 1):
        cases = []
        for c in par_ligne.get(i, []):
            j = xs.index(c[0])
            colspan, rowspan = xs.index(c[2]) - j, ys.index(c[3]) - i
            texte = " ".join(page.get_textbox(pymupdf.Rect(c)).split())
            attributs = (f' colspan="{colspan}"' if colspan > 1 else "") + (f' rowspan="{rowspan}"' if rowspan > 1 else "")
            cases.append(f"<td{attributs}>{html.escape(texte, quote=False)}</td>")
        lignes_html.append("<tr>" + "".join(cases) + "</tr>")
    return "<table>" + "".join(lignes_html) + "</table>"


def _blocs_tableaux(lignes: list[str]) -> list[tuple[int, int]]:
    """Plages [début, fin) des tableaux du Markdown d'une page (lignes « | » ou <table>)."""
    blocs, i = [], 0
    while i < len(lignes):
        if lignes[i].startswith("|"):
            debut = i
            while i < len(lignes) and lignes[i].startswith("|"):
                i += 1
            blocs.append((debut, i))
        elif "<table" in lignes[i]:
            blocs.append((i, i + 1))
            i += 1
        else:
            i += 1
    return blocs


def _remplacer_tableaux(texte: str, rendus: list[str]) -> str:
    lignes = texte.split("\n")
    for (debut, fin), rendu in reversed(list(zip(_blocs_tableaux(lignes), rendus))):
        lignes[debut:fin] = [rendu]
    return "\n".join(lignes)


def _marquer_tableaux_ocr(texte: str) -> str:
    lignes = texte.split("\n")
    for debut, _fin in reversed(_blocs_tableaux(lignes)):
        lignes[debut:debut] = [REPERE_TABLEAU_OCR, ""]
    return "\n".join(lignes)


# ------------------------------------------------------------------------------ conversion
def _to_markdown(chemin_pdf: str, pages: list[int], adaptateur, **options) -> list[str]:
    import pymupdf4llm
    correctifs.appliquer()  # idempotent ; normalement déjà fait au lancement du lot
    silence = io.StringIO()
    with contextlib.redirect_stdout(silence), contextlib.redirect_stderr(silence):
        morceaux = pymupdf4llm.to_markdown(
            chemin_pdf, pages=pages, page_chunks=True, ocr_function=adaptateur, ocr_language="fra",
            header=True, footer=True, write_images=False, embed_images=False, show_progress=False, **options)
    return [m["text"] for m in morceaux]


def _mots(texte: str) -> set[str]:
    texte = re.sub(r"<[^>]+>", " ", texte)
    texte = re.sub(r"[|*#`_]+", " ", texte)
    return {m.strip(".,;:!?()«»\"'").lower() for m in texte.split()} - {""}


def texte_simple(page) -> str:
    """Repli de PV-05 : texte de la page, bloc par bloc, dans l'ordre de lecture."""
    blocs = page.get_text("blocks", sort=True)
    return "\n\n".join(" ".join(b[4].split()) for b in blocs if b[6] == 0 and b[4].strip())


def convertir(chemin_pdf: str, *, tableaux: str = "auto", pages_ocr=(), pages_douteuses=(),
              adaptateur: AdaptateurOcr | None = None, arret=None, pages_repli: list | None = None) -> str:
    """Corps du Markdown (repères de page compris, sans front matter).

    pages_ocr : pages dont le texte vient d'une reconnaissance (outil ou expéditeur).
    pages_repli : si fournie, reçoit les pages converties par le repli de PV-05. La
    bibliothèque écarte le texte d'une page scannée qui porte aussi du texte visible (mention
    de dépôt) : l'image pleine page est prise pour une illustration qui absorbe le calque."""
    adaptateur = adaptateur or AdaptateurOcr()
    pages_ocr, pages_douteuses = set(pages_ocr), set(pages_douteuses)
    doc = pymupdf.open(chemin_pdf)
    nombre = doc.page_count
    sortie = []
    for debut in range(0, nombre, TAILLE_LOT):
        if arret is not None:
            arret()
        lot = list(range(debut, min(debut + TAILLE_LOT, nombre)))
        textes = _to_markdown(chemin_pdf, lot, adaptateur)
        for index, texte in zip(lot, textes):
            numero = index + 1
            texte = texte.strip()
            if numero in pages_ocr:
                # Repli si la bibliothèque perd du texte du calque, ou si elle en fabrique des
                # fragments (cellules fusionnées d'un tableau OCR coupées : « 40 0 » | « 00 »).
                calque_mots, md_mots = _mots(doc[index].get_text()), _mots(texte)
                communs = len(md_mots & calque_mots)
                if calque_mots and (communs / len(calque_mots) < COUVERTURE_MIN_PAGE_OCR
                                    or communs / max(1, len(md_mots)) < COUVERTURE_MIN_PAGE_OCR):
                    avait_tableau = bool(_blocs_tableaux(texte.split("\n")))
                    texte = texte_simple(doc[index])
                    if avait_tableau:  # le tableau est restitué en texte : l'avertissement reste dû
                        texte = REPERE_TABLEAU_OCR + "\n\n" + texte
                    if pages_repli is not None:
                        pages_repli.append(numero)
                else:
                    texte = _marquer_tableaux_ocr(texte)
            elif tableaux != "md" and _blocs_tableaux(texte.split("\n")):
                texte = _rendre_tableaux_natifs(doc[index], texte, tableaux, chemin_pdf, index, adaptateur)
            sortie.append(repere_page(numero, numero in pages_douteuses))
            sortie.append(texte if texte else PAGE_SANS_TEXTE)
        pymupdf.TOOLS.store_shrink(100)
    doc.close()
    return "\n\n".join(sortie) + "\n"


def _rendre_tableaux_natifs(page, texte, tableaux, chemin_pdf, index, adaptateur) -> str:
    """Règle de EX-44 pour une page native : HTML de l'outil pour toute la page dès qu'un
    tableau est complexe (ou si --tableaux html), Markdown sinon."""
    trouves = page.find_tables().tables
    complexe = any(_fusions(t) for t in trouves)
    if tableaux == "auto" and not complexe:
        return texte
    blocs = _blocs_tableaux(texte.split("\n"))
    if len(trouves) == len(blocs) and trouves:
        ordonnes = sorted(trouves, key=lambda t: (t.bbox[1], t.bbox[0]))
        return _remplacer_tableaux(texte, [table_html(page, t) for t in ordonnes])
    # Repli de EX-44 : correspondance impossible entre tableaux détectés et rendus ; rendu
    # HTML de la bibliothèque pour toute la page.
    return _to_markdown(chemin_pdf, [index], adaptateur, table_output="html")[0].strip()
