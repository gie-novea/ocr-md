"""Markdown des fichiers Office (EX-45) : .docx, .xlsx, .pptx, hors ligne, sans Microsoft
Office ni LibreOffice, par python-docx, openpyxl et python-pptx (trio retenu au plan v1 ;
l'outil existant passait par pandoc pour les .docx, que l'outil n'emploie pas).

- .docx : titres (styles de titre et niveaux hiérarchiques), paragraphes, listes à puces et
  numérotées, tableaux, notes de bas de page et de fin. Révisions non acceptées : texte
  présenté dans son état final (insertions retenues, suppressions écartées) ; commentaires
  non repris ; les deux sont comptés pour la mention de tête et le rapport. Zones de texte :
  à leur point d'ancrage (après le paragraphe qui les porte), précédées d'un repère ; la
  variante VML de repli d'une forme moderne n'est pas lue (sinon le texte serait doublé).
- .xlsx : une section par feuille visible, repère `<!-- feuille N : "Nom" -->`, valeurs en
  cache (jamais les formules) ; formule sans valeur en cache : `[formule non calculée : =…]` ;
  feuilles masquées listées en fin de document sans leur contenu ; au-delà de
  `xlsx_lignes_max` lignes, feuille tronquée avec une ligne d'avertissement. Nombres :
  virgule décimale, 12 chiffres significatifs (artefacts de virgule flottante retirés sans
  perte des centimes), pourcentage si le format de la cellule en est un ; dates ISO ;
  booléens VRAI et FAUX ; erreurs telles quelles.
- .pptx : une section par diapositive, repère `<!-- diapositive N -->`, titre, textes (formes
  groupées comprises, de haut en bas puis de gauche à droite), tableaux, commentaires du
  présentateur ; diapositive masquée convertie et signalée.
- Tableaux (EX-44) : Markdown s'ils sont simples, HTML (`colspan`, `rowspan`) s'ils ont une
  cellule fusionnée ou plusieurs lignes d'en-tête ; un tableau complexe fait passer en HTML
  tous les tableaux de son unité (document .docx, feuille, diapositive), comme la page d'un PDF.
"""

import dataclasses
import datetime
import decimal
import html
import importlib.metadata
import itertools
import re
import warnings
import zipfile

REPERE_ZONE_TEXTE = "<!-- zone de texte -->"
REPERE_FEUILLES_MASQUEES = "<!-- feuilles masquées -->"
DIAPOSITIVE_MASQUEE = "*(diapositive masquée)*"
FEUILLE_VIDE = "*(feuille vide)*"
CHIFFRES_SIGNIFICATIFS = 12


@dataclasses.dataclass
class ResultatOffice:
    corps: str
    pages: int | None
    moteur_md: str
    revisions: bool = False
    commentaires: int = 0


def _version(paquet: str) -> str:
    try:
        return importlib.metadata.version(paquet)
    except importlib.metadata.PackageNotFoundError:  # pragma: no cover - dépendance obligatoire
        return "inconnue"


def _sans_arret():
    pass


# ------------------------------------------------------------------------------ tableaux
@dataclasses.dataclass
class Case:
    texte: str
    colspan: int = 1
    rowspan: int = 1


@dataclasses.dataclass
class Tableau:
    grille: list  # lignes de Case ou None (position couverte par une fusion)
    lignes_entete: int = 1

    def complexe(self) -> bool:
        return self.lignes_entete > 1 or any(c is None or c.colspan > 1 or c.rowspan > 1
                                             for ligne in self.grille for c in ligne)


def _cellule_md(texte: str) -> str:
    return "<br>".join(l.strip() for l in texte.replace("|", "\\|").split("\n"))


def tableau_markdown(t: Tableau) -> str:
    largeur = max(len(l) for l in t.grille)
    lignes = [[_cellule_md(c.texte) if c else "" for c in l] + [""] * (largeur - len(l)) for l in t.grille]
    sortie = ["|" + "|".join(lignes[0]) + "|", "|" + "---|" * largeur]
    sortie += ["|" + "|".join(l) + "|" for l in lignes[1:]]
    return "\n".join(sortie)


def tableau_html(t: Tableau) -> str:
    lignes = []
    for ligne in t.grille:
        cases = []
        for c in ligne:
            if c is None:
                continue
            attributs = (f' colspan="{c.colspan}"' if c.colspan > 1 else "") + \
                        (f' rowspan="{c.rowspan}"' if c.rowspan > 1 else "")
            texte = "<br>".join(html.escape(l.strip(), quote=False) for l in c.texte.split("\n"))
            cases.append(f"<td{attributs}>{texte}</td>")
        lignes.append("<tr>" + "".join(cases) + "</tr>")
    return "<table>" + "".join(lignes) + "</table>"


def rendre_tableaux(tableaux: list[Tableau], mode: str) -> list[str]:
    """Règle de EX-44 sur une unité (document, feuille ou diapositive)."""
    en_html = mode == "html" or (mode == "auto" and any(t.complexe() for t in tableaux))
    return [tableau_html(t) if en_html else tableau_markdown(t) for t in tableaux]


def _assembler(blocs: list, mode_tableaux: str) -> str:
    """Blocs : (genre, texte) ou ("tableau", Tableau). Les éléments consécutifs d'une même
    liste (« puce » ou « numero ») sont séparés par un saut de ligne, les autres blocs par
    une ligne vide."""
    rendus = iter(rendre_tableaux([b[1] for b in blocs if b[0] == "tableau"], mode_tableaux))
    sortie, precedent = [], None
    for genre, contenu in blocs:
        texte = next(rendus) if genre == "tableau" else contenu
        if sortie:
            sortie.append("\n" if genre == precedent and genre in ("puce", "numero") else "\n\n")
        sortie.append(texte)
        precedent = genre
    return "".join(sortie)


# ------------------------------------------------------------------------------ .docx
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
MC = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"
REVISIONS = {W + n for n in ("ins", "del", "moveFrom", "moveTo", "rPrChange", "pPrChange", "sectPrChange",
                             "tblPrChange", "trPrChange", "tcPrChange", "numberingChange")}
# Sous-arbres jamais lus : texte supprimé, codes de champ, propriétés, variante de repli.
IGNORES = {W + n for n in ("del", "moveFrom", "delText", "instrText", "delInstrText", "rPr", "pPr", "tblPr",
                           "trPr", "tcPr", "commentReference", "annotationRef")} | {MC + "Fallback"}


def _vrai(element, attribut=W + "val") -> bool:
    return element is not None and element.get(attribut, "true") not in ("0", "false", "off")


class _StylesDocx:
    def __init__(self, document):
        from docx.enum.style import WD_STYLE_TYPE
        self.par_id = {s.style_id: s for s in document.styles}
        defaut = document.styles.default(WD_STYLE_TYPE.PARAGRAPH)
        self.defaut = defaut.style_id if defaut is not None else None

    def _chaine(self, p):
        ppr = p.find(W + "pPr")
        ps = ppr.find(W + "pStyle") if ppr is not None else None
        style = self.par_id.get(ps.get(W + "val") if ps is not None else self.defaut)
        vus = set()
        while style is not None and style.style_id not in vus:
            vus.add(style.style_id)
            yield style
            style = style.base_style

    def niveau_titre(self, p) -> int:
        ppr = p.find(W + "pPr")
        niveau = ppr.find(W + "outlineLvl") if ppr is not None else None
        if niveau is not None:
            n = int(niveau.get(W + "val", "9"))
            return n + 1 if n < 9 else 0
        for style in self._chaine(p):
            nom = (style.name or "").lower()
            if nom == "title":
                return 1
            m = re.fullmatch(r"heading (\d)", nom)
            if m:
                return int(m.group(1))
            spr = style.element.find(W + "pPr")
            niveau = spr.find(W + "outlineLvl") if spr is not None else None
            if niveau is not None:
                n = int(niveau.get(W + "val", "9"))
                return n + 1 if n < 9 else 0
        return 0

    def numerotation(self, p) -> tuple[str, int] | None:
        """(numId, niveau) du paragraphe, direct ou hérité du style ; None hors liste."""
        ppr = p.find(W + "pPr")
        num = ppr.find(W + "numPr") if ppr is not None else None
        if num is None:
            for style in self._chaine(p):
                spr = style.element.find(W + "pPr")
                num = spr.find(W + "numPr") if spr is not None else None
                if num is not None:
                    break
        if num is None:
            return None
        ident, niveau = num.find(W + "numId"), num.find(W + "ilvl")
        ident = ident.get(W + "val") if ident is not None else None
        if ident in (None, "0"):
            return None
        return ident, int(niveau.get(W + "val", "0")) if niveau is not None else 0


def _formats_numerotation(document) -> dict[tuple[str, int], str]:
    """(numId, niveau) -> format (« bullet », « decimal », ...)."""
    try:
        racine = document.part.numbering_part.element
    except (KeyError, NotImplementedError, AttributeError):
        return {}
    abstraits = {}
    for a in racine.findall(W + "abstractNum"):
        abstraits[a.get(W + "abstractNumId")] = {
            int(l.get(W + "ilvl", "0")): (l.find(W + "numFmt").get(W + "val") if l.find(W + "numFmt") is not None
                                          else "decimal") for l in a.findall(W + "lvl")}
    formats = {}
    for n in racine.findall(W + "num"):
        ref = n.find(W + "abstractNumId")
        for niveau, fmt in abstraits.get(ref.get(W + "val") if ref is not None else None, {}).items():
            formats[(n.get(W + "numId"), niveau)] = fmt
    return formats


def _partie_liee(document, suffixe: str):
    """Élément racine de la partie liée au document dont le type se termine par `suffixe`."""
    from docx.oxml import parse_xml
    for rel in document.part.rels.values():
        if not rel.is_external and rel.reltype.endswith("/" + suffixe):
            return parse_xml(rel.target_part.blob)
    return None


class _LecteurDocx:
    def __init__(self, document, arret):
        self.styles = _StylesDocx(document)
        self.formats = _formats_numerotation(document)
        self.arret = arret
        self.paragraphes = 0

    # Texte d'un paragraphe (état final), zones de texte mises de côté.
    def _texte(self, element, zones: list) -> str:
        morceaux = []

        def parcourir(e):
            for enfant in e:
                balise = enfant.tag
                if not isinstance(balise, str) or balise in IGNORES:
                    continue
                if balise == W + "t":
                    morceaux.append(enfant.text or "")
                elif balise in (W + "tab", W + "ptab"):
                    morceaux.append(" ")
                elif balise in (W + "br", W + "cr"):
                    morceaux.append("\n")
                elif balise == W + "noBreakHyphen":
                    morceaux.append("-")
                elif balise == W + "footnoteReference":
                    morceaux.append(f"[^{enfant.get(W + 'id')}]")
                elif balise == W + "endnoteReference":
                    morceaux.append(f"[^fin-{enfant.get(W + 'id')}]")
                elif balise == W + "txbxContent":
                    zones.append(enfant)
                else:
                    parcourir(enfant)

        parcourir(element)
        return "".join(morceaux)

    def blocs(self, conteneur) -> list:
        blocs = []
        for e in conteneur:
            balise = e.tag
            if balise == W + "p":
                blocs += self._paragraphe(e)
            elif balise == W + "tbl":
                blocs.append(("tableau", self._tableau(e)))
            elif balise in (W + "sdt", W + "customXml"):
                contenu = e.find(W + "sdtContent") if balise == W + "sdt" else e
                if contenu is not None:
                    blocs += self.blocs(contenu)
        return blocs

    def _paragraphe(self, p) -> list:
        self.paragraphes += 1
        if self.paragraphes % 200 == 0:
            self.arret()
        zones = []
        texte = self._texte(p, zones).strip()
        blocs = []
        if texte:
            niveau = self.styles.niveau_titre(p)
            liste = None if niveau else self.styles.numerotation(p)
            if niveau:
                blocs.append(("titre", "#" * min(niveau, 6) + " " + " ".join(texte.split())))
            elif liste:
                ident, rang = liste
                a_puce = self.formats.get((ident, rang), "bullet") in ("bullet", "none")
                blocs.append(("puce" if a_puce else "numero",
                              "  " * rang + ("- " if a_puce else "1. ") + texte.replace("\n", " ")))
            else:
                blocs.append(("texte", texte))
        for zone in zones:
            contenu = self.blocs(zone)
            if contenu:
                blocs.append(("repere", REPERE_ZONE_TEXTE))
                blocs += contenu
        return blocs

    def texte_cellule(self, tc) -> str:
        lignes = []
        for e in tc:
            if e.tag == W + "p":
                zones = []
                t = self._texte(e, zones).strip()
                if t:
                    lignes.append(t)
                for z in zones:
                    lignes += [self.texte_cellule(z)]
            elif e.tag == W + "tbl":
                lignes.append(" ; ".join(c.texte for l in self._tableau(e).grille for c in l if c and c.texte))
            elif e.tag in (W + "sdt", W + "customXml"):
                contenu = e.find(W + "sdtContent") if e.tag == W + "sdt" else e
                if contenu is not None:
                    lignes.append(self.texte_cellule(contenu))
        return "\n".join(l for l in lignes if l)

    def _tableau(self, tbl) -> Tableau:
        grille, entetes, en_tete = [], 0, True
        origines: dict[int, Case] = {}
        for tr in tbl.iter(W + "tr"):
            if tr.getparent() is not tbl and tr.getparent().tag != W + "sdtContent":
                continue  # ligne d'un tableau imbriqué
            trpr = tr.find(W + "trPr")
            if en_tete and trpr is not None and _vrai(trpr.find(W + "tblHeader")):
                entetes += 1
            else:
                en_tete = False
            ligne, colonne = [], 0
            avant = trpr.find(W + "gridBefore") if trpr is not None else None
            for _ in range(int(avant.get(W + "val", "0")) if avant is not None else 0):
                ligne.append(Case(""))
                colonne += 1
            for tc in tr.iter(W + "tc"):
                if tc.getparent() is not tr and tc.getparent().tag != W + "sdtContent":
                    continue
                tcpr = tc.find(W + "tcPr")
                span = tcpr.find(W + "gridSpan") if tcpr is not None else None
                largeur = int(span.get(W + "val", "1")) if span is not None else 1
                fusion = tcpr.find(W + "vMerge") if tcpr is not None else None
                if fusion is not None and fusion.get(W + "val", "continue") != "restart" and colonne in origines:
                    origines[colonne].rowspan += 1
                    ligne += [None] * largeur
                else:
                    case = Case(self.texte_cellule(tc), colspan=largeur)
                    ligne += [case] + [None] * (largeur - 1)
                    if fusion is not None:
                        origines[colonne] = case
                    else:
                        origines.pop(colonne, None)
                colonne += largeur
            grille.append(ligne)
        largeur = max((len(l) for l in grille), default=0)
        for l in grille:
            l += [Case("") for _ in range(largeur - len(l))]
        return Tableau(grille or [[Case("")]], max(entetes, 1))

    def notes(self, racine, balise: str, prefixe: str) -> list[str]:
        if racine is None:
            return []
        definitions = []
        for note in racine.findall(W + balise):
            if note.get(W + "type") in ("separator", "continuationSeparator", "continuationNotice"):
                continue
            zones = []
            textes = [self._texte(p, zones).strip() for p in note.iter(W + "p")]
            texte = " ".join(t for t in textes if t)
            if texte:
                definitions.append(f"[^{prefixe}{note.get(W + 'id')}]: {texte}")
        return definitions


def _revisions(*racines) -> bool:
    return any(e.tag in REVISIONS for r in racines if r is not None for e in r.iter() if isinstance(e.tag, str))


def convertir_docx(chemin, *, tableaux: str = "auto", arret=_sans_arret) -> ResultatOffice:
    import docx
    document = docx.Document(str(chemin))
    lecteur = _LecteurDocx(document, arret)
    corps = document.element.body
    blocs = lecteur.blocs(corps)
    notes = _partie_liee(document, "footnotes")
    fin = _partie_liee(document, "endnotes")
    commentaires = _partie_liee(document, "comments")
    definitions = lecteur.notes(notes, "footnote", "") + lecteur.notes(fin, "endnote", "fin-")
    texte = _assembler(blocs, tableaux)
    if definitions:
        texte += "\n\n" + "\n\n".join(definitions)
    return ResultatOffice(
        corps=texte + "\n" if texte else "", pages=None, moteur_md=f"python-docx {_version('python-docx')}",
        revisions=_revisions(corps, notes, fin),
        commentaires=len(commentaires.findall(W + "comment")) if commentaires is not None else 0)


# ------------------------------------------------------------------------------ .xlsx
def nombre(valeur) -> str:
    """Nombre en écriture française : virgule décimale, sans exposant, arrondi à 12 chiffres
    significatifs (retire les artefacts de virgule flottante sans perdre les centimes)."""
    if isinstance(valeur, int):
        return str(valeur)
    if valeur != valeur or valeur in (float("inf"), float("-inf")):
        return str(valeur)
    d = decimal.Decimal(f"{valeur:.{CHIFFRES_SIGNIFICATIFS}g}")
    texte = format(d.normalize(), "f")
    if "." in texte:
        texte = texte.rstrip("0").rstrip(".")
    return "0" if texte in ("-0", "") else texte.replace(".", ",")


def valeur_cellule(valeur, format_nombre: str | None = None, formule=None) -> str:
    """Texte d'une cellule à partir de sa valeur en cache ; formule sans valeur en cache :
    `[formule non calculée : =…]`."""
    if valeur is None:
        texte_formule = getattr(formule, "text", formule)
        if isinstance(texte_formule, str) and texte_formule.startswith("="):
            return f"[formule non calculée : {texte_formule}]"
        return ""
    if isinstance(valeur, bool):
        return "VRAI" if valeur else "FAUX"
    if isinstance(valeur, (int, float)):
        if format_nombre and "%" in format_nombre:
            return nombre(valeur * 100) + " %"
        return nombre(valeur)
    if isinstance(valeur, datetime.datetime):
        if (valeur.hour, valeur.minute, valeur.second, valeur.microsecond) == (0, 0, 0, 0):
            return valeur.date().isoformat()
        return valeur.isoformat(sep=" ", timespec="seconds")
    if isinstance(valeur, (datetime.date, datetime.time)):
        return valeur.isoformat()
    if isinstance(valeur, datetime.timedelta):
        return str(valeur)
    return str(valeur)


def _fusions_feuille(archive: zipfile.ZipFile, chemin_feuille: str | None) -> list[tuple[int, int, int, int]]:
    """Plages fusionnées (col_min, ligne_min, col_max, ligne_max), lues dans le XML de la
    feuille (le mode lecture seule d'openpyxl ne les donne pas)."""
    from defusedxml.ElementTree import iterparse
    from openpyxl.utils.cell import range_boundaries
    if not chemin_feuille:
        return []
    nom = chemin_feuille.lstrip("/")
    if nom not in archive.namelist():
        return []
    plages = []
    with archive.open(nom) as flux:
        for _, e in iterparse(flux, events=("end",)):
            if e.tag.endswith("}mergeCell") and e.get("ref"):
                try:
                    plages.append(range_boundaries(e.get("ref")))
                except ValueError:
                    pass
            e.clear()
    return plages


def _lire_feuille(feuille_valeurs, feuille_formules, lignes_max: int, arret):
    """Lignes 1 à lignes_max (listes de textes par colonne) et rang de la dernière ligne
    non vide de la feuille."""
    lignes, derniere = [], 0
    for rang, (lv, lf) in enumerate(itertools.zip_longest(feuille_valeurs.iter_rows(),
                                                         feuille_formules.iter_rows(), fillvalue=()), 1):
        if rang % 1000 == 0:
            arret()
        textes = [valeur_cellule(getattr(cv, "value", None), getattr(cv, "number_format", None),
                                 getattr(cf, "value", None))
                  for cv, cf in itertools.zip_longest(lv, lf)]
        if any(textes):
            derniere = rang
        if rang <= lignes_max:
            lignes.append(textes)
    return lignes[:derniere], derniere


def _tableau_feuille(lignes: list[list[str]], fusions) -> Tableau | None:
    """Tableau de la feuille, lignes et colonnes vides des bords retirées, fusions appliquées."""
    non_vides = [i for i, l in enumerate(lignes) if any(l)]
    if not non_vides:
        return None
    colonnes = [j for l in lignes for j, t in enumerate(l) if t]
    l0, l1, c0, c1 = non_vides[0], non_vides[-1], min(colonnes), max(colonnes)
    for (cmin, rmin, cmax, rmax) in fusions:  # une fusion déborde parfois sur des cellules vides
        if rmin - 1 <= l1 and cmin - 1 <= c1 and rmin - 1 >= l0 and cmin - 1 >= c0:
            l1, c1 = max(l1, min(rmax - 1, len(lignes) - 1)), max(c1, cmax - 1)
    grille = [[Case(l[j] if j < len(l) else "") for j in range(c0, c1 + 1)] for l in lignes[l0:l1 + 1]]
    for (cmin, rmin, cmax, rmax) in fusions:
        r0, r1 = rmin - 1 - l0, min(rmax - 1, l1) - l0
        k0, k1 = cmin - 1 - c0, min(cmax - 1, c1) - c0
        if r0 < 0 or k0 < 0 or r0 >= len(grille) or k0 >= len(grille[0]) or (r0, k0) == (r1, k1):
            continue
        origine = grille[r0][k0]
        origine.rowspan, origine.colspan = r1 - r0 + 1, k1 - k0 + 1
        for r in range(r0, r1 + 1):
            for k in range(k0, k1 + 1):
                if (r, k) != (r0, k0):
                    grille[r][k] = None
    return Tableau(grille)


def _guillemets(nom: str) -> str:
    return '"' + nom.replace('"', '\\"').replace("--", "- -") + '"'


def convertir_xlsx(chemin, *, tableaux: str = "auto", lignes_max: int = 2000, arret=_sans_arret) -> ResultatOffice:
    import openpyxl
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        valeurs = openpyxl.load_workbook(str(chemin), read_only=True, data_only=True)
        formules = openpyxl.load_workbook(str(chemin), read_only=True, data_only=False)
    sections, masquees, rang_visible = [], [], 0
    try:
        with zipfile.ZipFile(str(chemin)) as archive, warnings.catch_warnings():
            warnings.simplefilter("ignore")
            for fv, ff in zip(valeurs.worksheets, formules.worksheets):
                arret()
                if fv.sheet_state != "visible":
                    masquees.append(fv.title)
                    continue
                rang_visible += 1
                lignes, derniere = _lire_feuille(fv, ff, lignes_max, arret)
                fusions = _fusions_feuille(archive, getattr(fv, "_worksheet_path", None))
                tableau = _tableau_feuille(lignes, fusions)
                blocs = [("repere", f"<!-- feuille {rang_visible} : {_guillemets(fv.title)} -->")]
                blocs.append(("tableau", tableau) if tableau else ("texte", FEUILLE_VIDE))
                if derniere > lignes_max:
                    blocs.append(("texte", f"*(feuille tronquée : seules les {lignes_max} premières lignes sur "
                                           f"{derniere} sont reprises ; consulter le classeur d'origine pour la "
                                           "suite)*"))
                sections.append(_assembler(blocs, tableaux))
    finally:
        valeurs.close()
        formules.close()
    if masquees:
        sections.append(f"{REPERE_FEUILLES_MASQUEES}\n\nFeuilles masquées du classeur, contenu non repris : "
                        + ", ".join(_guillemets(n) for n in masquees) + ".")
    return ResultatOffice(corps="\n\n".join(sections) + "\n" if sections else "", pages=None,
                          moteur_md=f"openpyxl {_version('openpyxl')}")


# ------------------------------------------------------------------------------ .pptx
def _position(forme):
    return (forme.top if forme.top is not None else 0, forme.left if forme.left is not None else 0)


def _texte_pptx(texte: str) -> str:
    return texte.replace("\v", "\n").replace("\x0b", "\n").strip()


def _formes(formes, titre_id, blocs: list) -> None:
    from pptx.enum.shapes import MSO_SHAPE_TYPE, PP_PLACEHOLDER
    for forme in sorted(formes, key=_position):
        if forme.shape_id == titre_id:
            continue
        if forme.shape_type == MSO_SHAPE_TYPE.GROUP:
            _formes(forme.shapes, titre_id, blocs)
            continue
        if getattr(forme, "has_table", False) and forme.has_table:
            t = forme.table
            grille = []
            for ligne in t.rows:
                cases = []
                for cellule in ligne.cells:
                    if cellule.is_spanned:
                        cases.append(None)
                    elif cellule.is_merge_origin:
                        cases.append(Case(_texte_pptx(cellule.text), cellule.span_width, cellule.span_height))
                    else:
                        cases.append(Case(_texte_pptx(cellule.text)))
                grille.append(cases)
            if grille:
                blocs.append(("tableau", Tableau(grille)))
            continue
        if not getattr(forme, "has_text_frame", False) or not forme.has_text_frame:
            continue
        puces = forme.is_placeholder and forme.placeholder_format.type in (PP_PLACEHOLDER.BODY, PP_PLACEHOLDER.OBJECT)
        for paragraphe in forme.text_frame.paragraphs:
            texte = _texte_pptx(paragraphe.text)
            if not texte:
                continue
            if puces:
                blocs.append(("puce", "  " * paragraphe.level + "- " + texte.replace("\n", " ")))
            else:
                blocs.append(("texte", texte))


def convertir_pptx(chemin, *, tableaux: str = "auto", arret=_sans_arret) -> ResultatOffice:
    from pptx import Presentation
    presentation = Presentation(str(chemin))
    sections, n = [], 0
    for n, diapositive in enumerate(presentation.slides, 1):
        arret()
        blocs = [("repere", f"<!-- diapositive {n} -->")]
        if diapositive._element.get("show") in ("0", "false"):
            blocs.append(("texte", DIAPOSITIVE_MASQUEE))
        titre = diapositive.shapes.title
        titre_id = None
        if titre is not None:
            titre_id = titre.shape_id
            if titre.has_text_frame and titre.text_frame.text.strip():
                blocs.append(("titre", "## " + " ".join(_texte_pptx(titre.text_frame.text).split())))
        _formes(diapositive.shapes, titre_id, blocs)
        if diapositive.has_notes_slide and diapositive.notes_slide.notes_text_frame is not None:
            notes = [_texte_pptx(p.text) for p in diapositive.notes_slide.notes_text_frame.paragraphs]
            notes = [t for t in notes if t]
            if notes:
                blocs.append(("texte", "**Commentaires du présentateur :**"))
                blocs += [("texte", t) for t in notes]
        sections.append(_assembler(blocs, tableaux))
    return ResultatOffice(corps="\n\n".join(sections) + "\n" if sections else "", pages=n,
                          moteur_md=f"python-pptx {_version('python-pptx')}")


CONVERTISSEURS = {"docx": convertir_docx, "xlsx": convertir_xlsx, "pptx": convertir_pptx}
