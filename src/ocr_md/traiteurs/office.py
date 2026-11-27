"""Traiteur des fichiers Office (EX-45) : Markdown seul (pas de PDF consultable, EX-20, réglé
par l'orchestrateur), front matter de la section 11.1 avec `moteur_ocr: aucun`, `pages: null`
pour .docx et .xlsx et le nombre de diapositives pour .pptx."""

from .. import avertissements, markdown_office
from ..inventaire import ErreurFichier
from . import Annulation, ResultatTraitement, Traiteur

ORIGINE_NATIF = "texte natif du document"
MESSAGE_ILLISIBLE = ("fichier Office endommagé ou illisible : l'ouvrir dans son application, l'enregistrer de "
                     "nouveau, puis relancer")


def _ecrire(texte: str):
    def ecrire(chemin):
        with open(chemin, "w", encoding="utf-8", newline="\n") as f:
            f.write(texte)
    return ecrire


class TraiteurOffice(Traiteur):
    def __init__(self, type_source: str):
        self.type_source = type_source

    def traiter(self, ctx) -> ResultatTraitement:
        convertir = markdown_office.CONVERTISSEURS[self.type_source]
        options = {"tableaux": ctx.options.tableaux, "arret": ctx.verifier_arret}
        if self.type_source == "xlsx":
            options["lignes_max"] = ctx.parametres.xlsx_lignes_max
        try:
            r = convertir(ctx.element.source, **options)
        except (Annulation, ErreurFichier, MemoryError):
            raise
        except Exception as e:  # paquet Office endommagé : message clair, détail au journal
            ctx.journal.erreur(ctx.element.relatif, e)
            raise ErreurFichier(MESSAGE_ILLISIBLE) from e
        revisions = avertissements.valeur_revisions(r.revisions, r.commentaires)
        if revisions:
            ctx.journal.info(f"{ctx.element.relatif} : {revisions} (texte en état final, commentaires non repris)")
        if "md" in ctx.prevues:
            champs = avertissements.champs_document(
                source=ctx.element.relatif, type_source=self.type_source, pages=r.pages, moteur_md=r.moteur_md,
                moteur_ocr="aucun", pages_ocr=(), pages_douteuses=(), origine=ORIGINE_NATIF,
                pages_couche_existante=())
            texte = avertissements.document_markdown(
                champs, r.corps, mention=avertissements.mention_revisions(r.revisions, r.commentaires))
            ctx.ecrivain.preparer(ctx.prevues["md"], _ecrire(texte))
        return ResultatTraitement("natif", pages=r.pages, origine=ORIGINE_NATIF, revisions_commentaires=revisions)
