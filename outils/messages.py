"""Messages d'erreur et d'information émis par l'outil (EX-80) : constantes `MESSAGE*`, messages
des formats non pris en charge, message du moteur OCR absent, et partie fixe des messages des
exceptions de l'outil (texte avant la première partie variable). Sert au test qui vérifie que
chaque message figure dans le guide administrateur avec sa cause et son remède.

Usage : uv run python outils/messages.py (liste les messages)."""

import ast
import pathlib
import sys

RACINE = pathlib.Path(__file__).resolve().parents[1]
EXCEPTIONS = {"ErreurFichier", "ErreurUsage", "MoteurIndisponible", "ErreurRaccourcis", "ErreurConfiguration"}
LONGUEUR_MIN = 12  # parties fixes plus courtes : trop peu spécifiques pour être cherchées


def _texte(noeud) -> str | None:
    """Texte d'une chaîne, ou partie fixe initiale d'une f-chaîne ; None sinon."""
    if isinstance(noeud, ast.Constant) and isinstance(noeud.value, str):
        return noeud.value
    if isinstance(noeud, ast.JoinedStr):
        debut = ""
        for partie in noeud.values:
            if isinstance(partie, ast.Constant):
                debut += partie.value
            else:
                break
        return debut
    if isinstance(noeud, ast.BinOp):  # concaténation implicite déjà fusionnée ; « + » explicite
        return _texte(noeud.left)
    return None


def messages() -> list[str]:
    trouves = []
    for fichier in sorted((RACINE / "src" / "ocr_md").rglob("*.py")):
        arbre = ast.parse(fichier.read_text(encoding="utf-8"))
        for noeud in ast.walk(arbre):
            if isinstance(noeud, ast.Assign) and len(noeud.targets) == 1 and isinstance(noeud.targets[0], ast.Name):
                nom = noeud.targets[0].id
                if nom.startswith("MESSAGE") and nom != "MESSAGES_NON_PRIS_EN_CHARGE":
                    t = _texte(noeud.value)
                    if t:
                        trouves.append(t)
            # Messages construits : valeur renvoyée par une fonction « message… », variable
            # « message », ajout à une liste « messages ».
            if isinstance(noeud, ast.FunctionDef) and "message" in noeud.name:
                for r in ast.walk(noeud):
                    if isinstance(r, ast.Return) and r.value is not None:
                        t = _texte(r.value)
                        if t and len(t.strip(" :«")) >= LONGUEUR_MIN:
                            trouves.append(t.rstrip(" «"))
            if (isinstance(noeud, ast.Assign) and len(noeud.targets) == 1 and isinstance(noeud.targets[0], ast.Name)
                    and noeud.targets[0].id == "message"):
                t = _texte(noeud.value)
                if t and len(t.strip(" :«")) >= LONGUEUR_MIN:
                    trouves.append(t.rstrip(" «"))
            if (isinstance(noeud, ast.Call) and isinstance(noeud.func, ast.Attribute) and noeud.func.attr == "append"
                    and isinstance(noeud.func.value, ast.Name) and noeud.func.value.id == "messages" and noeud.args):
                t = _texte(noeud.args[0])
                if t and len(t.strip(" :«")) >= LONGUEUR_MIN:
                    trouves.append(t.rstrip(" «"))
            if isinstance(noeud, ast.Call) and isinstance(noeud.func, ast.Name) and noeud.func.id in EXCEPTIONS:
                if noeud.args:
                    t = _texte(noeud.args[0])
                    if t and len(t.strip(" :«")) >= LONGUEUR_MIN:
                        trouves.append(t.rstrip(" «"))
    sys.path.insert(0, str(RACINE / "src"))
    from ocr_md import inventaire, ocr
    trouves += list(dict.fromkeys(inventaire.MESSAGES_NON_PRIS_EN_CHARGE.values()))
    from ocr_md import plateforme
    vrai = plateforme.systeme
    try:
        for s in ("windows", "macos", "linux"):
            plateforme.systeme = lambda s=s: s
            trouves.append(ocr.message_moteur_absent())
    finally:
        plateforme.systeme = vrai
    return list(dict.fromkeys(m.strip() for m in trouves if m.strip()))


if __name__ == "__main__":
    for m in messages():
        print(m)
