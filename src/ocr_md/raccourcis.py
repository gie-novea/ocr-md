"""Raccourcis de l'outil (EX-13, EX-15, EX-70) : trois entrées « Envoyer vers » sous Windows,
trois Actions rapides du Finder sous macOS, créées et retirées sans droits d'administrateur.

- Windows : fichiers `.lnk` dans `%APPDATA%\\Microsoft\\Windows\\SendTo`, cible = lanceur sans
  console de l'outil (`ocr-mdw.exe`, chemin absolu) suivi de `--sortie …`. Le `.lnk` est écrit
  par l'objet COM `WScript.Shell`, appelé depuis Windows PowerShell (PV-02 : aucune dépendance
  ajoutée, aucun droit requis).
- macOS : lots `.workflow` dans `~/Library/Services`, recevant « fichiers ou dossiers » dans le
  Finder et exécutant un script shell qui appelle l'outil par son chemin absolu avec les
  éléments sélectionnés comme arguments (`"$@"`). Le Finder est prévenu par `pbs -update`.
Libellés préfixés de façon identique (REC-01) pour rester groupés dans les menus.
"""

import os
import pathlib
import plistlib
import shutil
import subprocess
import sys
import uuid

ENTREES = (("pdf", "OCR - Rendre lisible (PDF)"), ("md", "OCR - Convertir en Markdown"),
           ("les-deux", "OCR - Les deux"))


class ErreurRaccourcis(Exception):
    """Création ou suppression impossible : message en français."""


# ------------------------------------------------------------------------------ cibles
def lanceur() -> pathlib.Path:
    """Chemin absolu du lanceur appelé par les raccourcis : lanceur sans console sous Windows
    (`ocr-mdw.exe`), commande `ocr-md` sous macOS, dans l'installation courante."""
    nom = "ocr-mdw.exe" if sys.platform == "win32" else "ocr-md"
    voisin = pathlib.Path(sys.executable).parent / nom
    if voisin.is_file():
        return voisin
    trouve = shutil.which(nom)
    if trouve:
        return pathlib.Path(trouve).resolve()
    raise ErreurRaccourcis(f"lanceur {nom} introuvable : relancer le script d'installation")


def dossier_raccourcis() -> pathlib.Path:
    if sys.platform == "win32":
        return pathlib.Path(os.environ.get("APPDATA", pathlib.Path.home() / "AppData" / "Roaming")) / \
            "Microsoft" / "Windows" / "SendTo"
    return pathlib.Path.home() / "Library" / "Services"


def chemins() -> dict[str, pathlib.Path]:
    extension = ".lnk" if sys.platform == "win32" else ".workflow"
    return {sortie: dossier_raccourcis() / f"{libelle}{extension}" for sortie, libelle in ENTREES}


# ------------------------------------------------------------------------------ Windows
def _powershell(script: str) -> subprocess.CompletedProcess:
    options = {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}
    return subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                           "-Command", script], capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=60, **options)


def _ps(valeur) -> str:
    return "'" + str(valeur).replace("'", "''") + "'"


def _creer_lnk(chemin: pathlib.Path, cible: pathlib.Path, arguments: str) -> None:
    r = _powershell(
        "$s = New-Object -ComObject WScript.Shell; "
        f"$l = $s.CreateShortcut({_ps(chemin)}); $l.TargetPath = {_ps(cible)}; "
        f"$l.Arguments = {_ps(arguments)}; $l.WorkingDirectory = {_ps(pathlib.Path.home())}; "
        f"$l.Description = {_ps('ocr-md ' + arguments)}; $l.WindowStyle = 7; $l.Save()")
    if r.returncode != 0 or not chemin.is_file():
        raise ErreurRaccourcis(f"création du raccourci {chemin.name} impossible : {r.stderr.strip()[:300]}")


def lire_lnk(chemin: pathlib.Path) -> tuple[str, str] | None:
    """(cible, arguments) d'un raccourci .lnk, ou None s'il est illisible."""
    r = _powershell("$s = New-Object -ComObject WScript.Shell; "
                    f"$l = $s.CreateShortcut({_ps(chemin)}); Write-Output $l.TargetPath; Write-Output $l.Arguments")
    lignes = r.stdout.splitlines()
    return (lignes[0].strip(), lignes[1].strip()) if r.returncode == 0 and len(lignes) >= 2 else None


# ------------------------------------------------------------------------------ macOS
def script_action(cible: pathlib.Path, sortie: str) -> str:
    return f'"{cible}" --sortie {sortie} "$@"\n'


def _document_wflow(cible: pathlib.Path, sortie: str) -> dict:
    """Description Automator d'une Action rapide « Exécuter un script shell », entrée des
    fichiers ou dossiers du Finder transmise comme arguments (inputMethod 1)."""
    return {
        "AMApplicationBuild": "523", "AMApplicationVersion": "2.10", "AMDocumentVersion": "2",
        "actions": [{"action": {
            "AMAccepts": {"Container": "List", "Optional": True, "Types": ["com.apple.cocoa.string"]},
            "AMActionVersion": "2.0.3", "AMApplication": ["Automator"], "AMParameterProperties": {
                "COMMAND_STRING": {}, "CheckedForUserDefaultShell": {}, "inputMethod": {}, "shell": {},
                "source": {}},
            "AMProvides": {"Container": "List", "Types": ["com.apple.cocoa.string"]},
            "ActionBundlePath": "/System/Library/Automator/Run Shell Script.action",
            "ActionName": "Exécuter un script shell",
            "ActionParameters": {"COMMAND_STRING": script_action(cible, sortie), "CheckedForUserDefaultShell": True,
                                 "inputMethod": 1, "shell": "/bin/zsh", "source": ""},
            "BundleIdentifier": "com.apple.RunShellScript", "CFBundleVersion": "2.0.3",
            "CanShowSelectedItemsWhenRun": False, "CanShowWhenRun": True, "Category": ["AMCategoryUtilities"],
            "Class Name": "RunShellScriptAction", "InputUUID": str(uuid.uuid5(uuid.NAMESPACE_URL, f"e{sortie}")).upper(),
            "Keywords": ["Shell", "Script", "Command", "Run", "Unix"],
            "OutputUUID": str(uuid.uuid5(uuid.NAMESPACE_URL, f"s{sortie}")).upper(),
            "UUID": str(uuid.uuid5(uuid.NAMESPACE_URL, f"a{sortie}")).upper(),
            "UnlocalizedApplications": ["Automator"], "arguments": {}, "isViewVisible": 1,
            "location": "309.000000:253.000000", "nibPath": "/System/Library/Automator/Run Shell Script.action/"
                                                            "Contents/Resources/Base.lproj/main.nib"},
            "isViewVisible": 1}],
        "connectors": {},
        "workflowMetaData": {"applicationBundleIDsByPath": {}, "applicationPaths": [], "inputTypeIdentifier":
                             "com.apple.Automator.fileSystemObject", "outputTypeIdentifier":
                             "com.apple.Automator.nothing", "presentationMode": 15, "processesInput": False,
                             "serviceInputTypeIdentifier": "com.apple.Automator.fileSystemObject",
                             "serviceOutputTypeIdentifier": "com.apple.Automator.nothing",
                             "serviceProcessesInput": False, "systemImageName": "NSActionTemplate",
                             "useAutomaticInputType": False, "workflowTypeIdentifier":
                             "com.apple.Automator.servicesMenu"},
    }


def _info_plist(libelle: str) -> dict:
    return {"NSServices": [{"NSBackgroundColorName": "background", "NSIconName": "NSActionTemplate",
                            "NSMenuItem": {"default": libelle}, "NSMessage": "runWorkflowAsService",
                            "NSRequiredContext": {"NSApplicationIdentifier": "com.apple.finder"},
                            "NSSendFileTypes": ["public.item"]}]}


def _creer_workflow(chemin: pathlib.Path, libelle: str, cible: pathlib.Path, sortie: str) -> None:
    if chemin.exists():
        shutil.rmtree(chemin)
    contenu = chemin / "Contents"
    contenu.mkdir(parents=True)
    with open(contenu / "Info.plist", "wb") as f:
        plistlib.dump(_info_plist(libelle), f)
    with open(contenu / "document.wflow", "wb") as f:
        plistlib.dump(_document_wflow(cible, sortie), f)


def lire_workflow(chemin: pathlib.Path) -> str | None:
    """Script shell d'une Action rapide, ou None si elle est illisible."""
    try:
        with open(chemin / "Contents" / "document.wflow", "rb") as f:
            return plistlib.load(f)["actions"][0]["action"]["ActionParameters"]["COMMAND_STRING"]
    except (OSError, KeyError, IndexError, plistlib.InvalidFileException):
        return None


def _actualiser_services() -> None:
    pbs = pathlib.Path("/System/Library/CoreServices/pbs")
    if pbs.exists():
        subprocess.run([str(pbs), "-update"], capture_output=True, timeout=60, check=False)


# ------------------------------------------------------------------------------ commandes
def creer() -> list[pathlib.Path]:
    """Crée (ou recrée, sans doublon) les trois entrées ; renvoie leurs chemins."""
    if sys.platform not in ("win32", "darwin"):
        raise ErreurRaccourcis("raccourcis disponibles sous Windows et macOS seulement")
    cible = lanceur()
    dossier = dossier_raccourcis()
    dossier.mkdir(parents=True, exist_ok=True)
    crees = []
    for (sortie, libelle), chemin in zip(ENTREES, chemins().values()):
        if sys.platform == "win32":
            _creer_lnk(chemin, cible, f"--sortie {sortie}")
        else:
            _creer_workflow(chemin, libelle, cible, sortie)
        crees.append(chemin)
    if sys.platform == "darwin":
        _actualiser_services()
    return crees


def supprimer() -> list[pathlib.Path]:
    """Retire les trois entrées de l'outil, et elles seules ; renvoie les chemins retirés."""
    retires = []
    for chemin in chemins().values():
        if chemin.is_dir():
            shutil.rmtree(chemin)
            retires.append(chemin)
        elif chemin.exists():
            chemin.unlink()
            retires.append(chemin)
    if sys.platform == "darwin" and retires:
        _actualiser_services()
    return retires


def etat() -> tuple[bool, str]:
    """Contrôle de `verifier` (EX-71) : les trois entrées existent et pointent vers
    l'installation courante."""
    if sys.platform not in ("win32", "darwin"):
        return False, "raccourcis disponibles sous Windows et macOS seulement"
    try:
        cible = lanceur()
    except ErreurRaccourcis as e:
        return False, str(e)
    for (sortie, libelle), chemin in zip(ENTREES, chemins().values()):
        if not chemin.exists():
            return False, f"raccourci « {libelle} » absent : relancer le script d'installation"
        if sys.platform == "win32":
            lu = lire_lnk(chemin)
            bon = lu is not None and pathlib.Path(lu[0]) == cible and lu[1] == f"--sortie {sortie}"
        else:
            bon = lire_workflow(chemin) == script_action(cible, sortie)
        if not bon:
            return False, f"raccourci « {libelle} » ne pointe pas vers l'installation courante : relancer le script d'installation"
    return True, f"trois raccourcis présents dans {dossier_raccourcis()}"
